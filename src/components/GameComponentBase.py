#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : GameComponentBase.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/26 15:06
@Desc    : 游戏组件基类--属于是精灵基类的额外实现. 将针对空间的公共方法声明
"""
from typing import Tuple, Any

import pygame


class GameComponentBase:
    def __init__(self):
        self.rect: pygame.Rect = None
        self.offset: Tuple[int, int] = None
        self.need_redraw = True
        self.parent_id = None
        self.type = "GameComponentBase"

    @property
    def value(self) -> str:
        """获取当前值"""
        return ""

    def render(self):
        pass

    def update(self):
        """更新滑块状态"""
        if self.need_redraw:
            self.render()

    def update_pos(self, x: int, y: int):
        """
        更新组件位置
        :param x: x坐标
        :param y: y坐标
        """
        self.rect.x = self.offset[0] + x
        self.rect.y = self.offset[1] + y
        self.need_redraw = True

    def update_size(self, w: int, h: int):
        """
        更新组件尺寸
        :param w: 宽
        :param h: 高
        """
        self.rect.w = w
        self.rect.h = h
        self.need_redraw = True

    def destroy(self):
        """
        组件销毁
        :return:
        """
        pass

    def update_value(self, value: Any):
        """
        更新组件值
        :param value: 值
        :return:
        """
        pass
