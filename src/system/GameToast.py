#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : GameToast.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/16 19:57
@Desc    : 游戏轻提醒
"""
from src.code.SpriteBase import SpriteBase
import pygame
from typing import List, TYPE_CHECKING

from src.manager.GameFont import GameFont

if TYPE_CHECKING:
    from src.manager.GameManager import GameManager


class _MessageItem:
    def __init__(self, message: str, msg_type: str = "system"):
        # 字体和颜色设置
        self.type_colors = {
            "system": (255, 215, 0),  # 金色系统消息
            "player": (50, 205, 50)  # 绿色玩家消息
        }
        self.message: pygame.Surface = GameFont.get_multiple_text(message, 240, 50, True, 12,
                                                                  self.type_colors.get(msg_type))
        self.msg_type: str = msg_type  # "system" or "player"
        self.duration: float = 5.0  # 3秒自动消失
        self.timer: float = 0.0
        self.y_pos: int = 0  # 消息的Y坐标
        self.width, self.height = self.message.get_size()

    def update(self, delta_time: float):
        """更新消息计时器"""
        self.timer += delta_time

    def is_expired(self) -> bool:
        """检查消息是否已过期"""
        return self.timer >= self.duration


class _GameToast(SpriteBase):
    def __init__(self, screen_width: int, screen_height: int):
        super().__init__()
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.message_list: List[_MessageItem] = []
        self.x_pos = 10  # 左侧留10像素边距
        self.y_start = screen_height // 2  # 初始Y位置在屏幕中间
        self.spacing = 2  # 消息之间的间距

    def add_message(self, message: str, msg_type: str = "system"):
        """添加新消息"""
        new_msg = _MessageItem(message, msg_type)
        self.message_list.append(new_msg)
        if len(self.message_list) > 8:
            self.message_list.pop(0)
        # 调整所有消息的Y位置（新消息在最下面，旧消息往上移动）
        self._update_message_positions()

    def _update_message_positions(self):
        """更新所有消息的Y坐标"""
        total_height = 0
        for i, msg in enumerate(reversed(self.message_list)):
            msg.y_pos = self.y_start - total_height - msg.height
            total_height += msg.height + self.spacing

    def render(self):
        """更新所有消息状态"""
        # 更新每条消息的计时器
        for msg in self.message_list:
            msg.update(0.015)

        # 移除已过期的消息
        self.message_list = [msg for msg in self.message_list if not msg.is_expired()]

        # 更新剩余消息的位置
        if self.message_list:
            self._update_message_positions()

    def render_sticky(self, ):
        """
        渲染所有消息
        :return:
        """
        for msg in self.message_list:
            # 计算消息背景框
            # bg_rect = pygame.Rect(
            #     self.x_pos,
            #     msg.y_pos,
            #     msg.width,
            #     msg.height
            # )

            # 绘制半透明背景
            # bg_surface = pygame.Surface((msg.width, msg.height), pygame.SRCALPHA)
            # bg_surface.fill((0, 0, 0, 128))  # 半透明黑色背景
            # GameToastManager.gm.game_win.blit(bg_surface, (self.x_pos, msg.y_pos))

            # 绘制文本
            GameToastManager.gm.game_win.blit(msg.message, (self.x_pos + 5, msg.y_pos + 5))


class GameToastManager:
    _toast: _GameToast
    gm: "GameManager"

    @staticmethod
    def Awake(w, h, gm):
        GameToastManager._toast = _GameToast(w, h)
        GameToastManager.gm = gm
        GameToastManager.gm.add("GameToast", GameToastManager._toast)

    @staticmethod
    def add_message(message: str, msg_type: str = "system"):
        GameToastManager._toast.add_message(message, msg_type)
