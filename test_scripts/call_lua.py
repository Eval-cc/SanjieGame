#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：call_lua.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/6/15 09:34
@Describe: 
"""
from lupa import LuaRuntime
lua = LuaRuntime(unpack_returned_tuples=True)
import  re

class Bag:
    def __init__(self):
        self.money = 0

    def __str__(self):
        return f"剩余金币:{self.money}"

if __name__ == "__main__":
    # with open("../resources/scripts/test.lua", "r", encoding="utf-8") as f:
    #     # print(f.read())
    #     lua.execute(f.read())
    #     aaa = lua.globals().aaa
    #     # def py_add1(n): return n + 1
    #     value = aaa("eval",19)
    #     print(value)

    bag = Bag()
    with open("../resources/scripts/script_bag.lua", "r", encoding="utf-8") as f:
        # print(f.read())
        lua.execute(f.read())
        add_money = lua.globals().add_money
        # def py_add1(n): return n + 1
        print(bag)
        add_money(bag,999)
        print(bag)