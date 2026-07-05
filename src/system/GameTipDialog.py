#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : GameTipDialog.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/22 12:34
@Desc    : 游戏弹窗提示. 提供: 强提示. 以及 确认/取消 功能的回调
"""
from typing import Any, Dict, TYPE_CHECKING

import pygame

from src.code.Enums import SpriteLayer
from src.code.SpriteBase import SpriteBase
from src.components.GameButton import GameButton
from src.manager.GameFont import GameFont
from src.manager.SourceManager import SourceManager

if TYPE_CHECKING:
    from src.manager.GameManager import GameManager

class _GameTipDialog(SpriteBase):
    def __init__(self):
        super().__init__([["游戏弹窗点击事件"], ["1"]])
        self.gm: "GameManager" = GameDialogBoxManager.gm
        self.rect = self.gm.game_win_rect
        self.layer = SpriteLayer.UI_DIALOG
        # self.layer_order = 1999

        self._width = 200
        self._height = 230
        dialog_title = SourceManager.surface_scale(
            SourceManager.load(f"{SourceManager.ui_system_path}/dialog_title.png"),
            [self._width, 32]).convert_alpha()

        self.dialog_bg = pygame.Surface((self._width, self._height - 30), pygame.SRCALPHA)
        self.dialog_bg.fill((0, 0, 0, 0))
        # self.dialog_bg.set_alpha(170)

        dialog_sur = pygame.Surface((self._width, self._height), pygame.SRCALPHA)
        dialog_sur.fill(self.gm.game_font.hex_color_to_rgb("#000000"))
        dialog_sur.blit(self.dialog_bg, (0, 30))
        dialog_sur.set_alpha(170)
        self.dialog_bg.blit(dialog_title, (2, 0))
        self.dialog_bg.blit(dialog_sur, (0, 30))
        pygame.draw.rect(self.dialog_bg, (self.gm.game_font.hex_color_to_rgb("#228B22")),
                         (0, 30, self._width, self._height - 30), 1)

        _rect = self.dialog_bg.get_rect()
        _rect.y += 30
        _rect.height -= 30
        self.render_rect = _rect
        self.render_rect.x = self.rect.width // 2 - _rect.width // 2
        self.render_rect.y = self.rect.height // 2 - _rect.height // 2
        self._latest_msg = ""
        self.text_sur = None
        self.text_size = [0, 0]
        self.confirm = None
        self.cancel = None
        self.confirm_btn = GameButton(
            self.gm.game_win,  # 渲染表面
            pygame.Rect(_rect.x + 70, _rect.y + _rect.height - 30, 60, 25),  # 位置和大小
            "确认",
            font_size=10,
            text_color="#FFFFFF",
            border_color="#2980b9",
            hover_color="#2980b9",
            press_color="#1a5276",
            bg_image=SourceManager.ui_system_path + "/gw_b1.png",
            bg_press_image=SourceManager.ui_system_path + "/gw_b2.png"
        )
        self.cancel_btn = GameButton(
            self.gm.game_win,  # 渲染表面
            pygame.Rect(_rect.x + 100, _rect.y + _rect.height - 30, 60, 25),  # 位置和大小
            "取消",
            font_size=10,
            text_color="#FFFFFF",
            border_color="#2980b9",
            hover_color="#2980b9",
            press_color="#1a5276",
            bg_image=SourceManager.ui_system_path + "/gw_b1.png",
            bg_press_image=SourceManager.ui_system_path + "/gw_b2.png"
        )
        self.confirm_btn.set_on_click(lambda: self.btn_click(True))
        self.cancel_btn.set_on_click(lambda: self.btn_click(False))
        # 设置为消息层, 确保弹出消息之后, 仅这两个ui能触发点击
        self.confirm_btn.layer = SpriteLayer.UI_DIALOG
        self.cancel_btn.layer = SpriteLayer.UI_DIALOG

        self.gm.add("游戏开窗UI", self)

        self.loading_mask = pygame.Surface(self.rect.size)
        self.loading_mask.fill((0, 0, 0, 170))
        self.loading_mask.set_alpha(120)

    def set_msg(self, msg: str, confirm: Any, cancel: Any):
        self.confirm = confirm
        self.cancel = cancel
        # self.confirm_btn.enable = confirm is not None # 确认按钮需要确保能点击关闭弹窗
        self.cancel_btn.enable = cancel is not None
        if confirm:
            self.confirm_btn.update_pos(self.render_rect.x + self.render_rect.width - 65,
                                        self.render_rect.y + self.render_rect.height - 30)
        if cancel:
            self.cancel_btn.update_pos(self.render_rect.x + self.render_rect.width - 65,
                                       self.render_rect.y + self.render_rect.height - 60)

        if self._latest_msg == msg:
            return
        self._latest_msg = msg
        self.text_sur = GameFont.get_multiple_text(msg, self._width, self._height - 30, True, 12, "#FFFFFF")
        self.text_size = self.text_sur.size

    def render_sticky(self):
        self.gm.game_win.blit(self.loading_mask, self.rect)
        self.gm.game_win.blit(self.dialog_bg, self.render_rect)
        if self.text_sur:
            x = self.render_rect.x + (self.render_rect.width - self.text_size[0]) // 2
            y = self.render_rect.y + (self.render_rect.height - self.text_size[1]) // 2

            # 绘制文本（居中）
            self.gm.game_win.blit(self.text_sur, (x, y))

        if self.confirm_btn:
            self.confirm_btn.render()
        if self.cancel:
            self.cancel_btn.render()

    def mouse_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        return False  # 开窗之后, 禁止点击下面的内容

    def destroy(self):
        super().destroy()
        self.gm.remove(self)
        self._latest_msg = ""
        if self.confirm_btn:
            self.confirm_btn.destroy()
            self.confirm_btn = None
        if self.cancel:
            self.cancel_btn.destroy()
            self.cancel_btn = None
        GameDialogBoxManager._dialog_cls = None

    def btn_click(self, result: bool):
        if result:
            if self.confirm:
                self.confirm()
                self.destroy()
        else:
            if self.cancel:
                self.cancel()
        self.destroy()

class GameDialogBoxManager:
    _dialog_cls: "_GameTipDialog" = None
    gm:"GameManager" = None

    @classmethod
    def Awake(cls, gm):
        cls.gm = gm

    @classmethod
    def dialog(cls, msg: str, confirm: Any = None, cancel: Any = None):
        if GameDialogBoxManager._dialog_cls:
            GameDialogBoxManager._dialog_cls.set_msg(msg, confirm, cancel)
            return
        GameDialogBoxManager._dialog_cls = _GameTipDialog()
        GameDialogBoxManager._dialog_cls.set_msg(msg, confirm, cancel)

    @classmethod
    def has_dialog(cls):
        """
        是否存在全局消息提示
        :return:
        """
        return cls._dialog_cls is not None
