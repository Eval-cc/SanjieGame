#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : LocalDBManager.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2026/02/02 22:44
@Desc    : 
"""

import sqlite3
import threading
import re

from src.manager.SourceManager import SourceManager


class LocalDBManager:
    _instance_lock = threading.Lock()

    def __init__(self, db_name="game_data.db"):
        self.db_name = db_name
        # check_same_thread=False 允许在多线程（如异步加载视频时）共享连接
        self.conn = sqlite3.connect(f"{SourceManager.cfg_db_path}/{self.db_name}", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_default_tables()

    def _get_sql_dict(self,file_path):
        sql_dict = {}
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        # 逻辑优化：
        # 1. 先用 --# 拆分（保留你原始的结构感）
        # 2. 或者用更健壮的正向匹配：找 CREATE TABLE 直到下一个 CREATE TABLE 或文件末尾

        # 这里的正则改用“正向预查”，匹配两个 CREATE 之间的所有内容，或者到文件结尾
        pattern = r"(CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([\w_]+)[\s\S]+?)(?=CREATE\s+TABLE|$)"

        matches = re.findall(pattern, content, flags=re.IGNORECASE)

        for full_sql, table_name in matches:
            # 清理多余的空白字符
            clean_sql = full_sql.strip()
            # 如果最后有多余的注释或空行，确保以 ) 结尾（可选）
            sql_dict[table_name] = clean_sql

        return sql_dict

    def _init_default_tables(self):
        """初始化游戏核心表结构"""
        # 尝试读取本地sql文件
        sql_list = self._get_sql_dict(f"{SourceManager.cfg_db_path}/本地SQLite数据库.sql")
        for table in sql_list.values():
            self.execute_non_query(table)
        # 不使用get确保没有找到这个sql直接异常
        # 1. 系统设置表 (存全局配置)
        # self.execute_non_query(sql_list["system_settings"])
        # # 2. 账号表 (增加基础管理字段)
        # self.execute_non_query(sql_list["accounts"])
        # # 3. 角色表 (通过 account_id 关联账号)
        # self.execute_non_query(sql_list["fso"])


    # ========== 封装的方法 ==========

    def execute_non_query(self, sql: str, params: tuple = ()) -> int:
        """1. 直接执行SQL，返回影响行数 (增/删/改)"""
        with self._instance_lock:
            cursor = self.conn.cursor()
            try:
                cursor.execute(sql, params)
                self.conn.commit()
                return cursor.rowcount
            except Exception as e:
                self.conn.rollback()
                print(f"[DB Error] Execute failed: {e}")
                return -1
            finally:
                cursor.close()

    def fetch_all(self, sql: str, params: tuple = ()) -> list[dict]:
        """2. 执行查询，返回字典列表"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def fetch_on(self, sql: str, params: tuple = ()) -> dict:
        """执行查询，首行数据"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, params)
            dt = cursor.fetchall()
            if len(dt):
                return dict(dt[0])
            return None
        finally:
            cursor.close()

    def insert_row(self, table_name: str, data: dict) -> int:
        """3. 新增行: InsertRow('table', {'col1': val1})"""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        return self.execute_non_query(sql, tuple(data.values()))

    def update_row(self, table_name: str, data: dict, condition: str, condition_params: tuple = ()) -> int:
        """4. 更新行: UpdateRow('table', {'hp': 100}, 'name=?', ('eval',))"""
        set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
        sql = f"UPDATE {table_name} SET {set_clause} WHERE {condition}"
        params = tuple(data.values()) + condition_params
        return self.execute_non_query(sql, params)

    def close(self):
        self.conn.close()