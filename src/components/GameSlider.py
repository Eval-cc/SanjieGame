#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : GameSlider.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/26 14:51
@Desc    : 滑块组件
"""

import pygame
from typing import Dict, Tuple, Optional, Callable
from src.code.SpriteBase import SpriteBase
from src.components.GameComponentBase import GameComponentBase
from src.manager.GameFont import GameFont
from src.manager.SourceManager import SourceManager


class GameSlider(SpriteBase, GameComponentBase):
    def __init__(self, render_surface: pygame.Surface, rect: pygame.Rect,
                 min_value: float = 0, max_value: float = 100, initial_value: float = 50,
                 bg_color: str = "#CCCCCC", slider_color: str = "#666666",
                 active_slider_color: str = "#333333", border_color: str = "#000000",
                 value_color: str = "#000000",
                 border_width: int = 1, slider_width: int = 20, slider_height: int = 30,
                 show_value: bool = True, value_format: str = "{:.0f}",
                 offset: Tuple[int, int] = (0, 0),
                 bg_slider_image: Optional[str | pygame.Surface] = None,
                 bg_border_image: Optional[str | pygame.Surface] = None,
                 parent_id: str = None
                 ):
        """
        初始化滑块组件
        :param render_surface: 渲染目标表面
        :param rect: 滑块轨道位置和大小
        :param min_value: 最小值
        :param max_value: 最大值
        :param initial_value: 初始值
        :param bg_color: 轨道背景颜色
        :param slider_color: 滑块颜色
        :param active_slider_color: 滑块激活时的颜色
        :param border_color: 边框颜色
        :param value_color: 值颜色
        :param border_width: 边框宽度
        :param slider_width: 滑块宽度
        :param slider_height: 滑块高度
        :param show_value: 是否显示当前值
        :param value_format: 值显示格式
        :param offset: 位置偏移量
        :param bg_slider_image: 滑块背景
        :param bg_border_image: 滑块矩形
        :param parent_id: 父组件ID
        """
        super().__init__([["滑块拖动事件"], [1]])
        self.rect = rect
        self.rect.x += offset[0]
        self.rect.y += offset[1]
        self.min_value = min_value
        self.max_value = max_value
        self._value = initial_value
        self.bg_color = bg_color
        self.slider_color = slider_color
        self.active_slider_color = active_slider_color
        self.border_color = border_color
        self.value_color = value_color
        self.border_width = border_width
        self.slider_width = slider_width
        self.slider_height = slider_height
        self.show_value = show_value
        self.value_format = value_format
        self.render_surface = render_surface
        self.offset = offset
        self.type = "slider"

        if bg_slider_image:
            # 未选中的状态
            if type(bg_slider_image) == "str":
                self.bg_slider_image = SourceManager.load(bg_slider_image, list(self.rect.size))
            else:
                self.bg_slider_image = bg_slider_image
            if bg_border_image is None:
                bg_check_image = self.bg_slider_image.copy()

        if bg_border_image:
            # 选中的状态
            if type(bg_border_image) == "str":
                self.bg_border_image = SourceManager.load(bg_border_image, list(self.rect.size))
            else:
                self.bg_border_image = bg_border_image

        # 滑块状态
        self.is_dragging = False
        self.is_hovered = False
        self.is_down = False

        # 事件回调
        self.on_value_changed: Optional[Callable] = None

        # 缓存表面
        self.cached_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.need_redraw = True
        self.parent_id = parent_id

    @property
    def value(self) -> float:
        """获取当前值"""
        return self._value

    @value.setter
    def value(self, new_value: float):
        """设置当前值"""
        self._value = max(self.min_value, min(self.max_value, new_value))
        self.need_redraw = True
        if self.on_value_changed:
            self.on_value_changed(self._value)

    def set_rect(self, rect: pygame.Rect):
        """设置滑块轨道位置和大小"""
        self.rect = rect
        self.cached_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.need_redraw = True

    def render(self):
        """渲染滑块到指定表面"""
        if not self.need_redraw:
            self.render_surface.blit(self.cached_surface, self.rect)
            return self.cached_surface

        # 清空缓存表面
        self.cached_surface.fill((0, 0, 0, 0))

        # 绘制轨道背景
        pygame.draw.rect(
            self.cached_surface,
            pygame.Color(self.bg_color),
            (0, (self.rect.height - self.border_width) // 2,
             self.rect.width, self.border_width)
        )

        # 绘制轨道边框
        pygame.draw.rect(
            self.cached_surface,
            pygame.Color(self.border_color),
            (0, (self.rect.height - self.border_width) // 2,
             self.rect.width, self.border_width),
            self.border_width
        )

        # 计算滑块位置
        value_range = self.max_value - self.min_value
        slider_pos = int((self._value - self.min_value) / value_range *
                         (self.rect.width - self.slider_width))

        # 绘制滑块
        slider_color = self.active_slider_color if self.is_dragging or self.is_hovered else self.slider_color
        slider_rect = pygame.Rect(
            slider_pos,
            (self.rect.height - self.slider_height) // 2,
            self.slider_width,
            self.slider_height
        )
        pygame.draw.rect(self.cached_surface, pygame.Color(slider_color), slider_rect)
        pygame.draw.rect(
            self.cached_surface,
            pygame.Color(self.border_color),
            slider_rect,
            self.border_width
        )

        # 显示当前值
        if self.show_value:
            value_text = self.value_format.format(self._value)
            text_surface = GameFont.get_text_surface_line(
                value_text,
                True,
                12,
                self.value_color
            )
            text_rect = text_surface.get_rect(
                center=(self.rect.width // 2,
                        self.rect.height - text_surface.get_height() // 2 - 5)
            )
            self.cached_surface.blit(text_surface, text_rect)

        # 渲染到目标表面
        dest = self.rect
        if self.render_surface.get_size() == self.rect.size:
            dest = (0, 0)
        self.render_surface.blit(self.cached_surface, dest)
        self.need_redraw = False

        return self.cached_surface

    def mouse_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标按下事件"""
        mouse_pos = event.get("mouse_pos", (0, 0))
        # 计算滑块位置
        value_range = self.max_value - self.min_value
        slider_pos = int((self._value - self.min_value) / value_range *
                         (self.rect.width - self.slider_width))
        slider_rect = pygame.Rect(
            self.rect.x + slider_pos,
            self.rect.y + (self.rect.height - self.slider_height) // 2,
            self.slider_width,
            self.slider_height
        )

        if slider_rect.collidepoint(mouse_pos):
            self.is_dragging = True
            self.need_redraw = True
            # GameMusicManager.play_sound("mslider")
            self.is_down = True
            return False
        return True

    def mouse_up(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标释放事件"""
        self.is_down = False
        if self.is_dragging:
            self.is_dragging = False
            self.need_redraw = True
            return False
        return True

    def mouse_move(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标移动事件"""
        if not self.is_down:
            return True
        mouse_pos = event.get("mouse_pos", (0, 0))

        # 检查鼠标是否悬停在滑块上
        value_range = self.max_value - self.min_value
        slider_pos = int((self._value - self.min_value) / value_range *
                         (self.rect.width - self.slider_width))
        slider_rect = pygame.Rect(
            self.rect.x + slider_pos,
            self.rect.y + (self.rect.height - self.slider_height) // 2,
            self.slider_width,
            self.slider_height
        )

        was_hovered = self.is_hovered
        self.is_hovered = slider_rect.collidepoint(mouse_pos)
        if was_hovered != self.is_hovered:
            self.need_redraw = True

        # 处理拖动
        if self.is_dragging:
            relative_x = mouse_pos[0] - self.rect.x
            new_pos = max(0, min(self.rect.width - self.slider_width, relative_x - self.slider_width // 2))
            self.value = self.min_value + (new_pos / (self.rect.width - self.slider_width)) * value_range
            return False
        return True

    def mouse_enter(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标进入区域事件"""
        self.is_hovered = True
        self.need_redraw = True
        return True

    def mouse_out(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标离开区域事件"""
        self.is_hovered = False
        if self.is_dragging:
            self.is_dragging = False
        self.need_redraw = True
        return True

    def set_on_value_changed(self, callback: Callable[[float], None]):
        """设置值改变回调函数"""
        self.on_value_changed = callback
