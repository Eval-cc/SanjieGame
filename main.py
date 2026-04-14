#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：main.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/2/13 下午8:15 
@Describe: 
"""

from src.code.win import GameWin
import pygame, sys
# 检查是否为社区版 (CE)
is_ce = hasattr(pygame, "IS_CE")

# 项目指定必须使用 pygame-ce
if not is_ce:
    print("错误: 检测到安装了官方版 pygame，但本项目需要 pygame-ce。")
    print("请运行: pip uninstall pygame -y && pip install pygame-ce")
    sys.exit(1)

if __name__ == "__main__":
    GameWin(910, 630, "三界奇谈")