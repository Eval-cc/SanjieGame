#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : GameCheckBox.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/26 14:52
@Desc    : 单选框/复选框组件
"""

import pygame
from typing import Dict, Tuple, Optional, Callable, List
from src.code.SpriteBase import SpriteBase
from src.components.GameComponentBase import GameComponentBase
from src.manager.GameFont import GameFont
from src.manager.SourceManager import SourceManager
from src.system.GameMusic import GameMusicManager


class GameCheckBox(SpriteBase, GameComponentBase):
    def __init__(self, render_surface: pygame.Surface, rect: pygame.Rect,
                 text: str = "", is_checked: bool = False, is_radio: bool = True,
                 group: Optional[List['GameCheckBox']] = None,
                 font_size: int = 16, text_color: str = "#000000",
                 bg_color: str = "#FFFFFF", border_color: str = "#000000",
                 check_color: str = "#000000", hover_color: str = "#DDDDDD",
                 border_width: int = 1, check_width: int = 2,
                 offset: Tuple[int, int] = (0, 0),
                 bg_image: Optional[str | pygame.Surface] = None,
                 bg_check_image: Optional[str | pygame.Surface] = None,
                 parent_id:str = None):
        """
        初始化单选框/复选框组件
        :param render_surface: 渲染目标表面
        :param rect: 组件位置和大小
        :param text: 显示的文本
        :param is_checked: 初始是否选中
        :param is_radio: 是否是单选框(True为单选框，False为复选框)
        :param group: 单选框组(仅对单选框有效)
        :param font_size: 字体大小
        :param text_color: 文本颜色
        :param bg_color: 背景颜色
        :param border_color: 边框颜色
        :param check_color: 选中标记颜色
        :param hover_color: 鼠标悬停时的背景色
        :param border_width: 边框宽度
        :param check_width: 选中标记宽度
        :param offset: 位置偏移量
        :param bg_image: 图片 -- 当传入了surface的时候优先展示图片
        :param bg_check_image: 选中的图片
        :param parent_id: 父组件ID
        """
        super().__init__([["切换事件"], [1]])
        self.rect = rect
        self.rect.x += offset[0]
        self.rect.y += offset[1]
        self.text = text
        self._is_checked = is_checked
        self.is_radio = is_radio
        self.group = group if group else []
        self.font_size = font_size
        self.text_color = text_color
        self.bg_color = bg_color
        self.border_color = border_color
        self.check_color = check_color
        self.hover_color = hover_color
        self.border_width = border_width
        self.check_width = check_width
        self.render_surface = render_surface
        self.offset = offset

        self.bg_image = None
        self.parent_id = parent_id
        self.type = "checkbox"

        if bg_image:
            # 未选中的状态
            if type(bg_image) == "str":
                self.bg_image = SourceManager.load(bg_image, list(self.rect.size))
            else:
                self.bg_image = bg_image
            if bg_check_image is None:
                bg_check_image = self.bg_image.copy()

        if bg_check_image:
            # 选中的状态
            if type(bg_check_image) == "str":
                self.bg_check_image = SourceManager.load(bg_check_image, list(self.rect.size))
            else:
                self.bg_check_image = bg_check_image

        # 组件状态
        self.is_hovered = False

        # 事件回调
        self.on_toggle: Optional[Callable] = None

        # 缓存表面
        self.cached_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.need_redraw = True

        # 如果是单选框且属于某个组，确保组内只有一个被选中
        if self.is_radio and self._is_checked:
            for toggle in self.group:
                if toggle != self:
                    toggle.is_checked = False

    @property
    def is_checked(self) -> bool:
        """获取当前选中状态"""
        return self._is_checked

    @is_checked.setter
    def is_checked(self, value: bool):
        """设置选中状态"""
        if self._is_checked != value:
            self._is_checked = value
            self.need_redraw = True

            # 如果是单选框且被选中，取消同组其他选项的选中状态
            if self.is_radio and value and self.group:
                for toggle in self.group:
                    if toggle != self:
                        toggle.is_checked = False

            if self.on_toggle:
                self.on_toggle(self._is_checked)

    @property
    def value(self) -> bool:
        """获取当前值"""
        return self._is_checked

    def set_rect(self, rect: pygame.Rect):
        """设置组件位置和大小"""
        self.rect = rect
        self.cached_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.need_redraw = True

    def set_text(self, text: str):
        """设置显示文本"""
        self.text = text
        self.need_redraw = True

    def render(self):
        """渲染组件到指定表面"""
        if not self.need_redraw:
            self.render_surface.blit(self.cached_surface, self.rect)
            return self.cached_surface

        # 清空缓存表面
        self.cached_surface.fill((0, 0, 0, 0))

        # 计算选框区域
        box_size = min(self.rect.height, self.rect.width // 3)
        box_rect = pygame.Rect(
            0,
            (self.rect.height - box_size) // 2,
            box_size,
            box_size
        )

        if self.bg_image is None:
            # 绘制背景
            bg_color = self.hover_color if self.is_hovered else self.bg_color
            pygame.draw.rect(self.cached_surface, pygame.Color(bg_color), box_rect)

            # 绘制边框
            pygame.draw.rect(
                self.cached_surface,
                pygame.Color(self.border_color),
                box_rect,
                self.border_width
            )

            # 绘制选中标记
            if self._is_checked:
                if self.is_radio:
                    # 单选框: 圆形填充
                    center = (
                        box_rect.x + box_rect.width // 2,
                        box_rect.y + box_rect.height // 2
                    )
                    radius = box_rect.width // 2 - self.border_width * 2
                    pygame.draw.circle(
                        self.cached_surface,
                        pygame.Color(self.check_color),
                        center,
                        radius
                    )
                else:
                    # 复选框: 打勾标记
                    margin = box_rect.width // 4
                    points = [
                        (box_rect.x + margin, box_rect.y + box_rect.height // 2),
                        (box_rect.x + box_rect.width // 2, box_rect.y + box_rect.height - margin),
                        (box_rect.x + box_rect.width - margin, box_rect.y + margin)
                    ]
                    pygame.draw.lines(
                        self.cached_surface,
                        pygame.Color(self.check_color),
                        False,
                        points,
                        self.check_width
                    )

        else:
            if self._is_checked:
                self.cached_surface.blit(self.bg_check_image)
            else:
                self.cached_surface.blit(self.bg_image)

        # 绘制文本
        if self.text:
            text_surface = GameFont.get_text_surface_line(
                self.text,
                True,
                self.font_size,
                self.text_color
            )
            text_rect = text_surface.get_rect(
                midleft=(box_rect.right + 5,
                         self.rect.height // 2)
            )
            self.cached_surface.blit(text_surface, text_rect)

        # 渲染到目标表面
        self.render_surface.blit(self.cached_surface, self.rect)
        self.need_redraw = False

        return self.cached_surface

    def mouse_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标按下事件"""
        self.is_checked = not self.is_checked
        self.need_redraw = True
        GameMusicManager.play_sound("mbutton")
        return False

    def mouse_up(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标释放事件"""
        return True

    def mouse_enter(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标进入区域事件"""
        self.is_hovered = True
        self.need_redraw = True
        return True

    def mouse_out(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标离开区域事件"""
        self.is_hovered = False
        self.need_redraw = True
        return True

    def set_on_toggle(self, callback: Callable[[bool], None]):
        """设置状态改变回调函数"""
        self.on_toggle = callback
