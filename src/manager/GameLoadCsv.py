#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：GameLoadCsv.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/6/14 16:48 
@Describe: 加载csv脚本类
"""


class GameLoadCSV:
    def __init__(self):
        raise Exception("当前类是单例的工具类,请勿初始化")

    @classmethod
    def load(cls, file_path: str):
        """交给游戏管理类调用,请勿在外部逻辑层调用"""
        with open(file_path, "r", encoding="gb2312") as f:
            csv_data = f.read()
            """
            #开头的是注释,不用加载
            """
            column_index = 0  # 当前列索引
            has_part = False  # 是否处于文本段, 比如 "1,2,\n4,5,6" 这样的, 在这种情况下的换行符不做处理
            has_pass = False  ## 是否忽略当前行, 直到 遇到非 文本段状态的换行符

            data_list = []  # 解析总结果
            data_line_txt = ""  # 当前行文本
            for t in csv_data:
                if (t == "#") and column_index == 0:
                    has_pass = True
                if t == "\"":
                    has_part = not has_part

                # 遇到英文逗号需要特殊转换一下-  将文本段里面的逗号转换为 中文的逗号
                if t == "," and has_part:
                    t = "，"

                if t == "\n":
                    if not has_part and not has_pass:
                        data_list.append(
                            [str(tx.replace("，", ",").replace("\"", "")) for tx in data_line_txt.split(",")])
                        column_index = 0  # 换行了
                        data_line_txt = ""

                    if not has_part and has_pass:
                        # 结束忽略行
                        has_pass = False
                        column_index += 1
                    continue

                column_index += 1
                if has_pass:
                    continue
                data_line_txt += t
            if len(data_line_txt) > 0:
                data_list.append([str(tx.replace("，", ",").replace("\"", "")) for tx in data_line_txt.split(",")])
            return data_list
