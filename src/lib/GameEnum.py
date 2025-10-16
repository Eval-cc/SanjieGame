#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：GameEnum.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/7/22 15:42 
@Describe: 枚举管理
"""
from enum import Enum

class ShopType(Enum):
    """商城类型"""
    BUY = 1
    SELL = 2