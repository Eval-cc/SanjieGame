#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : GameInput.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/17 22:11
@Desc    : 输入框组件
"""
from typing import Dict, Tuple
import pygame
from pygame.key import ScancodeWrapper

from src.code.SpriteBase import SpriteBase
from src.components.GameComponentBase import GameComponentBase
from src.manager.GameEvent import GameEvent
from src.manager.GameFont import GameFont


class GameInput(SpriteBase,GameComponentBase):
    def __init__(self, render_surface: pygame.Surface, rect: pygame.Rect, placeholder: str = "", font_size: int = 16,
                 text_color: str = "#000000", bg_color: str = "#FFFFFF",
                 border_color: str = "#000000", border_width: int = 1, is_password: bool = False,
                 offset: Tuple[int, int] = (0, 0), field: str = ""):
        """
        初始化输入框组件
        :param rect: 输入框位置和大小
        :param placeholder: 占位文本
        :param font_size: 字体大小
        :param text_color: 文本颜色
        :param bg_color: 背景颜色
        :param border_color: 边框颜色
        :param border_width: 边框宽度
        :param is_password: 是否为密码框
        :param offset: 偏移值
        :param field: 是否有字段
        """
        super().__init__([
            ["输入框点击事件", "输入框键盘按下事件", "输入框键盘抬起事件", "输入框键盘长按事件", "输入框候选字事件"],
            [1, 6, 7, 8, 9]
        ])
        self.rect = rect
        self.rect.x += offset[0]
        self.rect.y += offset[1]
        self.placeholder = placeholder
        self.font_size = font_size
        self.text_color = text_color
        self.bg_color = bg_color
        self.border_color = border_color
        self.border_width = border_width
        self.render_surface = render_surface
        self.is_password = is_password
        self.offset = offset
        self._raw_field_text = field
        self.field_surface = None
        if len(field) > 0:
            self.field_surface = GameFont.get_text_surface_line(field, True, font_color=text_color,
                                                                font_size=font_size - 2)
            self.__field_size = GameFont.get_text_size(field)
            self.__field_size[0] += 5
            self._field_rect = self.rect.copy()
            self.rect.x += self.__field_size[0]
            self._field_rect.y = self.__field_size[1] // 2 + self.rect.y
            self.rect.width -= self.__field_size[0]

        # 输入状态
        self.text = ""
        self.has_focus = False
        self.cursor_index = 0
        self.blink_interval = 30  # 闪烁间隔帧数（约500ms）
        self.blink_tick = 0
        self.blink_show = True
        self.scroll_offset = 0

        # 渲染缓存
        self.cached_surface = None
        self.need_redraw = True

        # 事件回调
        self.on_change = None
        self.on_submit = None

        # 在初始化方法中添加
        self.ime_composing = False  # 是否正在输入法组合状态
        self.composing_text = ""  # 输入法组合文本

        GameEvent.add_input(self)
        # 初始化缓存表面
        self._create_base_surface()

    def __str__(self):
        return self.text

    def set_rect(self, rect: pygame.Rect):
        self.rect = rect
        self.rect.x += self.offset[0] + self.__field_size[0]
        self.rect.y += self.offset[1]

        self._field_rect.x += self.offset[0]
        self._field_rect.y = self.__field_size[1] // 2 + self.rect.y
        self._create_base_surface()
        self.need_redraw = True

    def _create_base_surface(self):
        """创建基础表面（背景+边框）"""
        self.cached_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        self.cached_surface.fill(pygame.Color(self.bg_color))
        pygame.draw.rect(
            self.cached_surface,
            pygame.Color(self.border_color),
            (0, 0, self.rect.width, self.rect.height),
            self.border_width
        )

    def render(self):
        """
        渲染输入框到指定表面
        """
        self.update()
        if not self.need_redraw and self.cached_surface:
            # 渲染字段名
            if self.field_surface:
                self.render_surface.blit(self.field_surface, self._field_rect)
            self.render_surface.blit(self.cached_surface, self.rect)
            return
        self._create_base_surface()
        # 处理文本显示
        display_text = self.text if self.text else self.placeholder
        # 如果是密码框且不是占位文本，则显示星号
        if self.is_password and self.text:
            display_text = "*" * len(self.text)

        text_color = self.text_color if self.text else "#888888"
        # 计算可见文本
        text_surface = GameFont.get_text_surface_line(display_text, True, font_color=text_color)
        text_width = GameFont.get_text_size(self.text)[0]

        # 处理文本滚动
        if text_width > self.rect.width - 10:  # 留出边距
            # 计算光标位置
            # prefix = self.text[:self.cursor_index]
            prefix_width = text_width

            # 调整滚动偏移
            cursor_screen_pos = prefix_width - self.scroll_offset
            if cursor_screen_pos > self.rect.width - 15:  # 光标接近右边界
                self.scroll_offset = prefix_width - (self.rect.width - 15)
            elif cursor_screen_pos < 5:  # 光标接近左边界
                self.scroll_offset = max(0, prefix_width - 5)

            # 裁剪文本表面
            visible_width = min(text_width, self.rect.width - 10)
            cropped_surface = pygame.Surface((visible_width, self.rect.height - 4), pygame.SRCALPHA)
            cropped_surface.blit(text_surface, (-self.scroll_offset, 0))
            text_surface = cropped_surface

        # 绘制文本
        text_y = (self.rect.height - text_surface.get_height()) // 2
        self.cached_surface.blit(text_surface, (5, text_y))

        # 绘制光标（只在获得焦点、闪烁显示状态且不是密码框时显示）
        if self.has_focus and self.blink_show:
            prefix = self.text[:self.cursor_index]
            prefix_width = GameFont.get_text_size(prefix)[0] - self.scroll_offset
            cursor_x = max(5, min(5 + prefix_width, self.rect.width - 5))
            pygame.draw.line(
                self.cached_surface,
                pygame.Color(self.text_color),
                (cursor_x, 5),
                (cursor_x, self.rect.height - 5),
                1
            )

        # 渲染到目标表面
        self.render_surface.blit(self.cached_surface, self.rect)
        self.need_redraw = False

        # 渲染字段名
        if self.field_surface:
            self.render_surface.blit(self.field_surface, self._field_rect)


    def mouse_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标点击事件"""
        mouse_pos = event.get("mouse_pos", (0, 0))
        if self.rect.collidepoint(mouse_pos):
            for _com in GameEvent.all_input_pool():
                if _com == self:
                    continue
                _com.blur()

            self.has_focus = True
            self._update_cursor_position(mouse_pos)
            self.need_redraw = True
            # 如果启动了密码模式, 就不允许输入文本
            if not self.is_password:
                pygame.key.start_text_input()  # 启用文本输入
            pygame.key.set_text_input_rect(self.rect)  # 设置输入区域
        else:
            if self.has_focus:
                self.has_focus = False
                self.need_redraw = True
                if self.on_submit and self.text:
                    self.on_submit(self.text)

    def _update_cursor_position(self, mouse_pos: Tuple[int, int]):
        """根据鼠标点击位置更新光标位置"""
        if not self.text:
            self.cursor_index = 0
            return

        relative_x = mouse_pos[0] - self.rect.x + self.scroll_offset - 5

        # 统一使用显示文本来计算位置
        display_text = "*" * len(self.text) if self.is_password else self.text

        best_pos = 0
        min_dist = float('inf')  # 得到一个无穷大的数

        for i in range(len(display_text) + 1):
            prefix = display_text[:i]
            width = GameFont.get_text_size(prefix)[0]
            dist = abs(width - relative_x)
            if dist < min_dist:
                min_dist = dist
                best_pos = i

        # 确保光标位置不超过实际文本长度
        self.cursor_index = min(best_pos, len(self.text))
        self.blink_tick = 0
        self.blink_show = True

    def listen_keyboard(self):
        return self.has_focus

    def key_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理键盘按下事件"""
        if not self.has_focus:
            return

        key_event = event.get("event")
        key = key_event.key
        # unicode = key_event.unicode

        # 处理特殊按键
        if key == pygame.K_BACKSPACE:
            if self.cursor_index > 0:
                self.text = self.text[:self.cursor_index - 1] + self.text[self.cursor_index:]
                self.cursor_index -= 1
                self._trigger_change()
        elif key == pygame.K_DELETE:
            if self.cursor_index < len(self.text):
                self.text = self.text[:self.cursor_index] + self.text[self.cursor_index + 1:]
                self._trigger_change()
        elif key == pygame.K_LEFT:
            self.cursor_index = max(0, self.cursor_index - 1)
            self._reset_blink()
        elif key == pygame.K_RIGHT:
            self.cursor_index = min(len(self.text), self.cursor_index + 1)
            self._reset_blink()
        elif key == pygame.K_HOME:
            self.cursor_index = 0
            self.scroll_offset = 0
            self._reset_blink()
        elif key == pygame.K_END:
            self.cursor_index = len(self.text)
            self._reset_blink()
        elif key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
            if self.on_submit:
                self.on_submit(self.text)
        elif key == pygame.K_ESCAPE:
            self.blur()
        # 放在key_text 事件接收. 这里不要接收.会重复
        # elif unicode:
        #     # 直接接收所有unicode字符
        #     self.text = self.text[:self.cursor_index] + unicode + self.text[self.cursor_index:]
        #     self.cursor_index += len(unicode)
        #     self._trigger_change()

        self.need_redraw = True

    def keyboard_pressed(self, event: Dict[str, ScancodeWrapper] | pygame.event.EventType):
        """处理键盘长按事件"""
        self.key_down(event)

    def key_text(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        key_event = event.get("event")
        self.text = self.text[:self.cursor_index] + key_event.text + self.text[self.cursor_index:]
        self.cursor_index += len(key_event.text)
        self._trigger_change()
        self.need_redraw = True

    def _reset_blink(self):
        """重置光标闪烁状态"""
        self.blink_tick = 0
        self.blink_show = True
        self.need_redraw = True

    def _trigger_change(self):
        """触发文本变化回调"""
        self._reset_blink()
        self.need_redraw = True
        if self.on_change:
            self.on_change(self.text)

    def update(self):
        """更新输入框状态"""
        if self.has_focus:  # 只在获得焦点时闪烁
            self.blink_tick += 1
            if self.blink_tick >= self.blink_interval:
                self.blink_tick = 0
                self.blink_show = not self.blink_show
                self.need_redraw = True

    def clear(self):
        """清空输入框内容"""
        self.text = ""
        self.cursor_index = 0
        self.scroll_offset = 0
        self._trigger_change()

    def set_text(self, text: str):
        """设置输入框文本"""
        self.text = text
        self.cursor_index = len(text)
        self.scroll_offset = 0
        self._trigger_change()

    def blur(self):
        """ 失去焦点 """
        self.blink_tick = 0
        self.has_focus = False
        self.blink_show = False
        self.need_redraw = True
        pygame.key.stop_text_input()

    def destroy(self):
        if self.has_focus:
            pygame.key.stop_text_input()
        for e in ["输入框点击事件", "输入框键盘按下事件", "输入框键盘抬起事件", "输入框键盘长按事件",
                  "输入框候选字事件"]:
            GameEvent.remove(f"{e}_{self.UID}")
        GameEvent.remove_input(self)

    def update_pos(self, x: int, y: int):
        """
        更新组件位置,
        :param x:
        :param y:
        :return:
        """
        self.rect.x = self.offset[0] + x + self.__field_size[0]
        self.rect.y = self.offset[1] + y
        self._field_rect.x = self.offset[0] + x
        self._field_rect.y = self.__field_size[1] // 2 + self.rect.y
        self.need_redraw = True
