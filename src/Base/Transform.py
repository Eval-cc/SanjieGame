#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : Transform.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/11/18 13:50
@Desc    : 
"""
import math


class Position:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Transform:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def distance(self, target: "Transform"):
        """
        计算目标和当前 精灵的距离
        :param target: 目标精灵的Transform对象
        :return:
        """
        return math.sqrt((target.x - self.x) ** 2 + (target.y - self.y) ** 2)

    def get_pos(self) -> Position:
        """返回当前角色的屏幕坐标
        """
        return Position(self.x, self.y)

    def get_pos_list(self) -> list[int]:
        """
        返回当前角色的屏幕坐标
        @return: 以数组的方式返回
        """
        return [self.x, self.y]

    def set_pos(self, x, y):
        """设置精灵位置"""
        self.x = x
        self.y = y

    def __str__(self):
        return f"Transform(x={self.x}, y={self.y}"
