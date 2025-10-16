#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：GameLuaManager.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/7/15 12:18 
@Describe: LUA 脚本管理
"""

import re
import os
from lupa import LuaRuntime
from src.manager.GameLogManger import GameLogManager
from src.manager.SourceManager import SourceManager
lua = LuaRuntime(unpack_returned_tuples=True)

class GameLuaManager:
    __lua_dict = {}

    @staticmethod
    def Awake():
        lua_scripts_dir = SourceManager.cfg_lua_path
        # 遍历目录下所有以 "script_" 开头的 .lua 文件
        for filename in os.listdir(lua_scripts_dir):
            if filename.startswith("script_") and filename.endswith(".lua"):
                filepath = os.path.join(lua_scripts_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    lua_str = f.read()
                    lua.execute(lua_str)
                    # 提取当前文件中的函数名
                    GameLuaManager.get_lua_functions(lua.globals(),lua_str)

    @staticmethod
    def get_lua_functions(lua_obj, lua_str:str):
        """获取 Lua 全局环境中的所有函数"""
        pattern = r'function\s+(\w+)\s*\('
        # 查找所有匹配的函数名 并将对应的
        for val in re.findall(pattern, lua_str):
            obj = getattr(lua_obj, val)
            # 检查是否是 Lua 函数
            if hasattr(obj, '__call__'):
                GameLuaManager.__lua_dict[val] = obj
            else:
                GameLogManager.log_service_debug(f"无效的LUA脚本函数:{val}")

    @staticmethod
    def exec_lua(lua_name:str, params:list):
        """执行lua脚本"""
        lua_call = GameLuaManager.__lua_dict.get(lua_name)
        if lua_call:
            return lua_call(params)
        return None

    @staticmethod
    def load_map_lua(map_name:str):
        """加载地图的lua脚本"""
        lua_path = f"{SourceManager.cfg_lua_path}/map/{map_name}.lua"
        if not os.path.exists(lua_path):
            GameLogManager.log_service_debug(f"无法加载场景:[{map_name}]的lua脚本信息")
            return None
        with open(lua_path, "r", encoding="utf-8") as f:
            lua_str = f.read()
            lua.execute(lua_str)
            return lua.globals()