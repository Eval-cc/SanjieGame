#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : GameButton.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/18 12:01
@Desc    : 按钮组件
"""

from typing import Dict, Tuple, Optional, Callable, Any
import pygame
from src.code.SpriteBase import SpriteBase
from src.components.GameComponentBase import GameComponentBase
from src.manager.GameFont import GameFont
from src.manager.GameLogManger import GameLogManager
from src.manager.SourceManager import SourceManager
from src.system.GameMusic import GameMusicManager


class GameButton(SpriteBase,GameComponentBase):
    def __init__(self, render_surface: pygame.Surface, rect: pygame.Rect, text: str = "", font_size: int = 16,
                 text_color: str = "#000000", bg_color: str = "#FFFFFF",
                 border_color: str = "#000000", border_width: int = 1,
                 hover_color: str = "#DDDDDD", press_color: str = "#AAAAAA",
                 bg_image: Optional[str] = None, bg_press_image: Optional[str] = None,
                 offset: Tuple[int, int] = (0, 0), parent_id:str = None):
        """
        初始化按钮组件
        :param render_surface: 渲染目标表面
        :param rect: 按钮位置和大小
        :param text: 默认的按钮文本
        :param font_size: 字体大小
        :param text_color: 文本颜色
        :param bg_color: 背景颜色
        :param border_color: 边框颜色
        :param border_width: 边框宽度
        :param hover_color: 鼠标悬停时的背景色
        :param press_color: 鼠标按下时的背景色
        :param bg_image: 背景图片路径（可选）
        :param parent_id: 父组件ID
        """
        super().__init__([["按钮点击事件"], [1]])
        self.rect = rect
        self.rect.x += offset[0]
        self.rect.y += offset[1]
        self.font_size = font_size
        self.text_color = text_color
        self.bg_color = bg_color
        self.border_color = border_color
        self.border_width = border_width
        self.hover_color = hover_color
        self.press_color = press_color
        self.render_surface = render_surface

        # 图片背景相关属性
        self.bg_image_path = bg_image
        self.bg_image = None
        self.bg_image_hover = None
        self.bg_image_press_path= bg_press_image
        self.bg_image_press = None
        self.__load_bg_images()

        # 按钮状态
        self.is_hovered = False
        self.is_pressed = False
        self.text = text
        self.offset: Tuple[int, int] = offset
        # 事件回调
        self.on_click: Optional[Callable] = None

        # 缓存表面
        self.cached_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.need_redraw = True
        # 是否启用
        self.enable = True
        self.parent_id = parent_id
        self.type = "button"

    def __str__(self):
        return self.text

    def __load_bg_images(self):
        """加载背景图片"""
        if self.bg_image_path:
            try:
                # 加载普通状态图片
                self.bg_image = SourceManager.load(self.bg_image_path, list(self.rect.size))
                # self.bg_image = pygame.transform.scale(self.bg_image, self.rect.size)

                # 生成悬停状态图片（稍微变亮）
                self.bg_image_hover = self.bg_image.copy()
                # 使用 RGBA 颜色 (30, 30, 30, 0) 来变亮
                overlay = pygame.Surface(self.bg_image.get_size(), pygame.SRCALPHA)
                overlay.fill((30, 30, 30, 0))
                self.bg_image_hover.blit(overlay, (0, 0), special_flags=pygame.BLEND_ADD)

                # 生成按下状态图片（稍微变暗）
                if self.bg_image_press_path is None:
                    self.bg_image_press = self.bg_image.copy()
                    # 使用 RGBA 颜色 (30, 30, 30, 0) 来变暗（通过减法）
                    overlay.fill((30, 30, 30, 0))
                    self.bg_image_press.blit(overlay, (0, 0), special_flags=pygame.BLEND_SUB)
                else:
                    self.bg_image_press = SourceManager.load(self.bg_image_press_path, list(self.rect.size))

            except Exception as e:
                GameLogManager.log_service_error(f"加载按钮背景图片失败: {e}")
                self.bg_image = None
                self.bg_image_hover = None
                self.bg_image_press = None
                self.bg_image_press_path = ""

    def set_rect(self, rect: pygame.Rect):
        """设置按钮位置和大小"""
        self.rect = rect
        self.cached_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.__load_bg_images()  # 重新加载图片以适应新尺寸
        self.need_redraw = True

    def set_text(self, text: str):
        """设置按钮文本"""
        self.text = text
        self.need_redraw = True

    def set_bg_image(self, image_path: str):
        """设置背景图片"""
        self.bg_image_path = image_path
        self.__load_bg_images()
        self.need_redraw = True

    def render(self):
        """
        渲染按钮到指定表面
        """
        if not self.need_redraw:
            self.render_surface.blit(self.cached_surface, self.rect)
            return self.cached_surface

        # 清空缓存表面
        self.cached_surface.fill((0, 0, 0, 0))

        # 绘制背景（图片或颜色）
        if self.bg_image:
            # 使用图片背景
            if self.is_pressed and self.bg_image_press:
                self.cached_surface.blit(self.bg_image_press, (0, 0))
            elif self.is_hovered and self.bg_image_hover:
                self.cached_surface.blit(self.bg_image_hover, (0, 0))
            else:
                self.cached_surface.blit(self.bg_image, (0, 0))
        else:
            # 使用颜色背景
            if self.is_pressed:
                bg_color = self.press_color
            elif self.is_hovered:
                bg_color = self.hover_color
            else:
                bg_color = self.bg_color

            self.cached_surface.fill(pygame.Color(bg_color))

        # 绘制边框（仅在纯色背景或需要时显示）
        if not self.bg_image or self.border_width > 0:
            pygame.draw.rect(
                self.cached_surface,
                pygame.Color(self.border_color),
                (0, 0, self.rect.width, self.rect.height),
                self.border_width
            )

        # 绘制文本
        if self.text:
            text_surface = GameFont.get_text_surface_line(
                self.text,
                True,
                self.font_size,
                self.text_color
            )
            text_rect = text_surface.get_rect(center=(
                self.rect.width // 2,
                self.rect.height // 2
            ))
            self.cached_surface.blit(text_surface, text_rect)

        # 渲染到目标表面
        self.render_surface.blit(self.cached_surface, self.rect)
        self.need_redraw = False
        return self.cached_surface

    def mouse_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标按下事件"""
        if not self.enable:
            # 禁用了 不触发
            return True
        self.is_pressed = True
        self.need_redraw = True
        GameMusicManager.play_sound("mbutton")
        return False

    def mouse_up(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标释放事件"""
        if self.is_pressed:
            self.is_pressed = False
            self.need_redraw = True
            if self.on_click:
                self.on_click()
            return False
        return True

    def mouse_enter(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标进入按钮区域事件"""
        self.is_hovered = True
        self.need_redraw = True
        return True

    def mouse_out(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标离开按钮区域事件"""
        self.is_hovered = False
        self.need_redraw = True
        return True

    def set_on_click(self, callback: Callable):
        """设置点击回调函数"""
        self.on_click = callback

    def update_value(self, value: Any):
        self.text = value