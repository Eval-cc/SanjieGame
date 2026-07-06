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
from typing import Dict, Tuple, Any
import pygame
from pygame.key import ScancodeWrapper

from src.code.SpriteBase import SpriteBase
from src.components.GameComponentBase import GameComponentBase
from src.manager.GameFont import GameFont


class GameInput(SpriteBase, GameComponentBase):
    def __init__(self, render_surface: pygame.Surface, rect: pygame.Rect, placeholder: str = "", font_size: int = 16,
                 text_color: str = "#000000", bg_color: str = "#FFFFFF",
                 border_color: str = "#000000", border_width: int = 1, is_password: bool = False,
                 offset: Tuple[int, int] = (0, 0), field: str = "", parent_id: str = None):
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
        :param parent_id: 父组件ID
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
        self.parent_id = parent_id
        self.type = "input"

        self._field_rect = self.rect.copy()
        if len(field) > 0:
            self.field_surface = GameFont.get_text_surface_line(field, True, font_color=text_color,
                                                                font_size=font_size - 2)
            self.__field_size = GameFont.get_text_size(field)
            self.__field_size[0] += 5
            self.rect.x += self.__field_size[0]
            self._field_rect.y = self.__field_size[1] // 2 + self.rect.y
            self.rect.width -= self.__field_size[0]
        else:
            self.__field_size = [0, 0]

        # 输入状态
        self.text = ""
        self.has_focus = False
        self.cursor_index = 0
        self.blink_interval = 30  # 闪烁间隔帧数（约500ms）
        self.blink_tick = 0
        self.blink_show = True
        self.scroll_offset = 0
        self.selection_start = 0
        self.selection_end = 0
        self.__selection_anchor = 0
        self.__drag_selecting = False
        self.__undo_stack: list[tuple[str, int, int, int]] = []
        self.__undo_limit = 80

        # 渲染缓存
        self.cached_surface = None
        self.need_redraw = True

        # 事件回调
        self.on_change = None
        self.on_submit = None
        self.on_history = None

        # # 在初始化方法中添加
        # self.ime_composing = False  # 是否正在输入法组合状态
        # self.composing_text = ""  # 输入法组合文本

        from src.manager.GameEvent import GameEvent
        GameEvent.add_input(self)
        # 初始化缓存表面
        self._create_base_surface()

    def __display_value(self, value: str | None = None) -> str:
        value = self.text if value is None else value
        if self.is_password and value:
            return "*" * len(value)
        return value

    @staticmethod
    def __text_width(text: str) -> int:
        return GameFont.get_text_size(text)[0]

    def __normalize_cursor_view(self):
        self.cursor_index = max(0, min(self.cursor_index, len(self.text)))
        self.selection_start = max(0, min(self.selection_start, len(self.text)))
        self.selection_end = max(0, min(self.selection_end, len(self.text)))
        if not self.text:
            self.scroll_offset = 0
            self.selection_start = 0
            self.selection_end = 0
            return

        visible_width = max(1, self.rect.width - 10)
        display_text = self.__display_value()
        text_width = self.__text_width(display_text)
        if text_width <= visible_width:
            self.scroll_offset = 0
            return

        cursor_text = self.__display_value(self.text[:self.cursor_index])
        cursor_width = self.__text_width(cursor_text)
        cursor_screen_pos = cursor_width - self.scroll_offset
        if cursor_screen_pos > self.rect.width - 15:
            self.scroll_offset = cursor_width - (self.rect.width - 15)
        elif cursor_screen_pos < 5:
            self.scroll_offset = max(0, cursor_width - 5)

        max_scroll = max(0, text_width - visible_width)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

    def __has_selection(self) -> bool:
        return self.selection_start != self.selection_end

    def __selection_range(self) -> tuple[int, int]:
        return min(self.selection_start, self.selection_end), max(self.selection_start, self.selection_end)

    def __clear_selection(self):
        self.selection_start = self.cursor_index
        self.selection_end = self.cursor_index
        self.__selection_anchor = self.cursor_index

    def __set_selection(self, start: int, end: int):
        text_len = len(self.text)
        self.selection_start = max(0, min(start, text_len))
        self.selection_end = max(0, min(end, text_len))
        self.cursor_index = self.selection_end
        self.__selection_anchor = self.selection_start
        self.__normalize_cursor_view()
        self._reset_blink()

    def __select_all(self):
        self.selection_start = 0
        self.selection_end = len(self.text)
        self.cursor_index = len(self.text)
        self.__selection_anchor = 0
        self.__normalize_cursor_view()
        self._reset_blink()

    def __push_undo(self):
        state = (self.text, self.cursor_index, self.selection_start, self.selection_end)
        if self.__undo_stack and self.__undo_stack[-1] == state:
            return
        self.__undo_stack.append(state)
        if len(self.__undo_stack) > self.__undo_limit:
            self.__undo_stack.pop(0)

    def __undo(self):
        if not self.__undo_stack:
            return
        self.text, self.cursor_index, self.selection_start, self.selection_end = self.__undo_stack.pop()
        self.__normalize_cursor_view()
        self._trigger_change()

    @staticmethod
    def __normalize_paste_text(text: str) -> str:
        return str(text or "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")

    __clipboard_fallback = ""

    @classmethod
    def __set_clipboard(cls, text: str):
        cls.__clipboard_fallback = text
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
        except Exception:
            pass

    @classmethod
    def __get_clipboard(cls) -> str:
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            data = pygame.scrap.get(pygame.SCRAP_TEXT)
            if data:
                for encoding in ("utf-8", "gbk", "latin-1"):
                    try:
                        return data.decode(encoding).rstrip("\x00")
                    except UnicodeDecodeError:
                        continue
        except Exception:
            pass
        return cls.__clipboard_fallback

    def __copy_selection(self) -> str:
        if not self.__has_selection():
            return ""
        start, end = self.__selection_range()
        text = self.text[start:end]
        self.__set_clipboard(text)
        return text

    def __replace_range(self, start: int, end: int, insert_text: str = "", push_undo: bool = True):
        start = max(0, min(start, len(self.text)))
        end = max(start, min(end, len(self.text)))
        insert_text = self.__normalize_paste_text(insert_text)
        if self.text[start:end] == insert_text and start == 0 and end == len(self.text):
            return
        if push_undo:
            self.__push_undo()
        self.text = self.text[:start] + insert_text + self.text[end:]
        self.cursor_index = start + len(insert_text)
        self.__clear_selection()
        self._trigger_change()

    def __insert_text(self, insert_text: str):
        if insert_text is None or insert_text == "":
            return
        if self.__has_selection():
            start, end = self.__selection_range()
        else:
            start = end = self.cursor_index
        self.__replace_range(start, end, insert_text)

    def __delete_selection(self):
        if not self.__has_selection():
            return False
        start, end = self.__selection_range()
        self.__replace_range(start, end, "")
        return True

    def __position_from_mouse(self, mouse_pos: Tuple[int, int]) -> int:
        if not self.text:
            return 0

        relative_x = mouse_pos[0] - self.rect.x + self.scroll_offset - 5
        display_text = self.__display_value()
        best_pos = 0
        min_dist = float('inf')
        for i in range(len(display_text) + 1):
            width = self.__text_width(display_text[:i])
            dist = abs(width - relative_x)
            if dist < min_dist:
                min_dist = dist
                best_pos = i
        return min(best_pos, len(self.text))

    @staticmethod
    def __has_ctrl(key_event) -> bool:
        mods = getattr(key_event, "mod", 0) or pygame.key.get_mods()
        return bool(mods & (pygame.KMOD_CTRL | getattr(pygame, "KMOD_META", 0)))

    @staticmethod
    def __has_shift(key_event) -> bool:
        mods = getattr(key_event, "mod", 0) or pygame.key.get_mods()
        return bool(mods & pygame.KMOD_SHIFT)

    def __move_cursor(self, index: int, selecting: bool = False):
        index = max(0, min(index, len(self.text)))
        if selecting:
            if not self.__has_selection():
                self.__selection_anchor = self.cursor_index
            self.cursor_index = index
            self.selection_start = self.__selection_anchor
            self.selection_end = self.cursor_index
        else:
            self.cursor_index = index
            self.__clear_selection()
        self.__normalize_cursor_view()
        self._reset_blink()

    @property
    def value(self) -> str:
        """获取当前值"""
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
        """创建基础表面（包含标签空间和输入框）"""
        # 计算总尺寸：标签宽度 + 输入框宽度
        total_width = self.rect.width + self.__field_size[0]
        total_height = max(self.rect.height, self.__field_size[1])

        # 创建一个支持透明的大表面作为完整容器
        self.cached_surface = pygame.Surface((total_width, total_height), pygame.SRCALPHA)

        # 1. 绘制标签 (如果存在)
        if self.field_surface:
            # 垂直居中对齐标签
            field_y = (total_height - self.field_surface.get_height()) // 2
            self.cached_surface.blit(self.field_surface, (0, field_y))

        # 2. 绘制输入框背景
        # 输入框的位置要偏移开标签的宽度
        input_rect = pygame.Rect(self.__field_size[0], 0, self.rect.width, self.rect.height)
        pygame.draw.rect(self.cached_surface, pygame.Color(self.bg_color), input_rect)

        # 3. 绘制边框
        if self.border_color:
            pygame.draw.rect(
                self.cached_surface,
                pygame.Color(self.border_color),
                input_rect,
                self.border_width
            )

    def render(self):
        """
        渲染完整输入框组件（含标签）
        """
        self.update()

        # 如果不需要重绘且已有缓存
        if not self.need_redraw and self.cached_surface:
            # 渲染位置需要向左偏移标签宽度，因为 self.rect 指向的是输入框
            self.render_surface.blit(self.cached_surface, (self.rect.x - self.__field_size[0], self.rect.y))
            return self.cached_surface

        # 创建基础底图
        self._create_base_surface()
        self.__normalize_cursor_view()

        # --- 处理文本内容 ---
        display_text = self.__display_value() if self.text else self.placeholder

        text_color = self.text_color if self.text else "#888888"
        text_surface = GameFont.get_text_surface_line(display_text, True, font_color=text_color)
        text_width = self.__text_width(display_text) if self.text else 0

        # 文本滚动逻辑 (保持原样，但注意绘制坐标需加上偏移)
        input_field_offset = self.__field_size[0]

        if text_width > self.rect.width - 10:
            visible_width = min(text_width, max(1, self.rect.width - 10))
            cropped_surface = pygame.Surface((visible_width, self.rect.height), pygame.SRCALPHA)
            cropped_surface.blit(text_surface, (-self.scroll_offset, 0))
            text_surface = cropped_surface

        # 绘制选区背景，再绘制文本
        text_y = (self.rect.height - text_surface.get_height()) // 2
        if self.has_focus and self.__has_selection() and self.text:
            start, end = self.__selection_range()
            display_value = self.__display_value()
            start_width = self.__text_width(display_value[:start])
            end_width = self.__text_width(display_value[:end])
            select_x = max(5, 5 + start_width - self.scroll_offset)
            select_end_x = min(self.rect.width - 5, 5 + end_width - self.scroll_offset)
            if select_end_x > select_x:
                select_rect = pygame.Rect(
                    input_field_offset + select_x,
                    max(2, text_y - 2),
                    select_end_x - select_x,
                    min(self.rect.height - 4, text_surface.get_height() + 4)
                )
                pygame.draw.rect(self.cached_surface, pygame.Color("#2F80ED"), select_rect)

        # 绘制文本到 cached_surface (x坐标需加上偏移)
        self.cached_surface.blit(text_surface, (input_field_offset + 5, text_y))

        # --- 绘制光标 ---
        if self.has_focus and self.blink_show and not self.__has_selection():
            prefix = self.__display_value(self.text[:self.cursor_index])
            prefix_width = self.__text_width(prefix) - self.scroll_offset
            cursor_x = max(5, min(5 + prefix_width, self.rect.width - 5))
            pygame.draw.line(
                self.cached_surface,
                pygame.Color(self.text_color),
                (input_field_offset + cursor_x, 5),
                (input_field_offset + cursor_x, self.rect.height - 5),
                1
            )

        # 最终输出到主渲染表面
        render_pos = (self.rect.x - input_field_offset, self.rect.y)
        self.render_surface.blit(self.cached_surface, render_pos)
        self.need_redraw = False

        return self.cached_surface

    # def _create_base_surface(self):
    #     """创建基础表面（背景+边框）"""
    #     self.cached_surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)
    #     self.cached_surface.fill(pygame.Color(self.bg_color))
    #
    #     if self.border_color:
    #         pygame.draw.rect(
    #             self.cached_surface,
    #             pygame.Color(self.border_color),
    #             (0, 0, self.rect.width, self.rect.height),
    #             self.border_width
    #         )
    #
    # def render(self):
    #     """
    #     渲染输入框到指定表面
    #     """
    #     self.update()
    #     if not self.need_redraw and self.cached_surface:
    #         # 渲染字段名
    #         if self.field_surface:
    #             self.render_surface.blit(self.field_surface, self._field_rect)
    #         self.render_surface.blit(self.cached_surface, self.rect)
    #         return self.cached_surface
    #
    #     self._create_base_surface()
    #     # 处理文本显示
    #     display_text = self.text if self.text else self.placeholder
    #     # 如果是密码框且不是占位文本，则显示星号
    #     if self.is_password and self.text:
    #         display_text = "*" * len(self.text)
    #
    #     text_color = self.text_color if self.text else "#888888"
    #     # 计算可见文本
    #     text_surface = GameFont.get_text_surface_line(display_text, True, font_color=text_color)
    #     text_width = GameFont.get_text_size(self.text)[0]
    #
    #     # 处理文本滚动
    #     if text_width > self.rect.width - 10:  # 留出边距
    #         # 计算光标位置
    #         # prefix = self.text[:self.cursor_index]
    #         prefix_width = text_width
    #
    #         # 调整滚动偏移
    #         cursor_screen_pos = prefix_width - self.scroll_offset
    #         if cursor_screen_pos > self.rect.width - 15:  # 光标接近右边界
    #             self.scroll_offset = prefix_width - (self.rect.width - 15)
    #         elif cursor_screen_pos < 5:  # 光标接近左边界
    #             self.scroll_offset = max(0, prefix_width - 5)
    #
    #         # 裁剪文本表面
    #         visible_width = min(text_width, self.rect.width - 10)
    #         cropped_surface = pygame.Surface((visible_width, self.rect.height), pygame.SRCALPHA)
    #         cropped_surface.blit(text_surface, (-self.scroll_offset, 0))
    #         text_surface = cropped_surface
    #
    #     # 绘制文本
    #     text_y = (self.rect.height - text_surface.get_height()) // 2
    #     self.cached_surface.blit(text_surface, (5, text_y))
    #
    #     # 绘制光标（只在获得焦点、闪烁显示状态时显示）
    #     if self.has_focus and self.blink_show:
    #         prefix = self.text[:self.cursor_index]
    #         _w = GameFont.get_text_size(prefix)[0]
    #         prefix_width = _w - self.scroll_offset
    #         cursor_x = max(5, min(5 + prefix_width, self.rect.width - 5))
    #         pygame.draw.line(
    #             self.cached_surface,
    #             pygame.Color(self.text_color),
    #             (cursor_x, 5),
    #             (cursor_x, self.rect.height - 5),
    #             1
    #         )
    #
    #     # 渲染到目标表面
    #     self.render_surface.blit(self.cached_surface, self.rect)
    #     self.need_redraw = False
    #
    #     # 渲染字段名
    #     if self.field_surface:
    #         self.render_surface.blit(self.field_surface, self._field_rect)
    #     return self.cached_surface

    def mouse_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标点击事件"""
        from src.manager.GameEvent import GameEvent
        for _com in GameEvent.all_input_pool():
            if _com == self:
                continue
            _com.blur()

        mouse_pos = event.get("mouse_pos", (self.rect.x, self.rect.y))
        self.has_focus = True
        self._update_cursor_position(mouse_pos)
        self.__selection_anchor = self.cursor_index
        self.__drag_selecting = True
        self.need_redraw = True
        # 如果启动了密码模式, 就不允许输入文本
        if not self.is_password:
            pygame.key.start_text_input()  # 启用文本输入
        pygame.key.set_text_input_rect(self.rect)  # 设置输入区域

    def mouse_move(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理鼠标拖动选择"""
        if not self.__drag_selecting:
            return
        mouse_pos = event.get("mouse_pos", (self.rect.x, self.rect.y))
        self.cursor_index = self.__position_from_mouse(mouse_pos)
        self.selection_start = self.__selection_anchor
        self.selection_end = self.cursor_index
        self.__normalize_cursor_view()
        self._reset_blink()

    def mouse_up(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType = None):
        """处理鼠标释放"""
        self.__drag_selecting = False
        self.need_redraw = True

    def is_drag_selecting(self) -> bool:
        return self.__drag_selecting

    def _update_cursor_position(self, mouse_pos: Tuple[int, int]):
        """根据鼠标点击位置更新光标位置"""
        self.cursor_index = self.__position_from_mouse(mouse_pos)
        self.__clear_selection()
        self.__normalize_cursor_view()
        self._reset_blink()

    def listen_keyboard(self):
        return self.has_focus

    def key_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """处理键盘按下事件"""
        if not self.has_focus:
            return

        key_event = event.get("event")
        key = key_event.key
        unicode = key_event.unicode
        has_ctrl = self.__has_ctrl(key_event)
        has_shift = self.__has_shift(key_event)

        if has_ctrl:
            if key == pygame.K_a:
                self.__select_all()
            elif key == pygame.K_c:
                self.__copy_selection()
            elif key == pygame.K_x:
                if self.__copy_selection():
                    self.__delete_selection()
            elif key == pygame.K_v:
                self.__insert_text(self.__get_clipboard())
            elif key == pygame.K_z:
                self.__undo()
            self.need_redraw = True
            return

        # 处理特殊按键
        if key == pygame.K_BACKSPACE:
            if not self.__delete_selection() and self.cursor_index > 0:
                self.__replace_range(self.cursor_index - 1, self.cursor_index, "")
        elif key == pygame.K_DELETE:
            if not self.__delete_selection() and self.cursor_index < len(self.text):
                self.__replace_range(self.cursor_index, self.cursor_index + 1, "")
        elif key == pygame.K_LEFT:
            if self.__has_selection() and not has_shift:
                self.__move_cursor(self.__selection_range()[0])
            else:
                self.__move_cursor(self.cursor_index - 1, has_shift)
        elif key == pygame.K_RIGHT:
            if self.__has_selection() and not has_shift:
                self.__move_cursor(self.__selection_range()[1])
            else:
                self.__move_cursor(self.cursor_index + 1, has_shift)
        elif key == pygame.K_HOME:
            self.__move_cursor(0, has_shift)
        elif key == pygame.K_END:
            self.__move_cursor(len(self.text), has_shift)
        elif key == pygame.K_UP or key == pygame.K_DOWN:
            if self.on_history:
                direction = "up" if key == pygame.K_UP else "down"
                next_text = self.on_history(direction, self.text)
                if next_text is not None:
                    self.set_text(str(next_text))
                return
        elif key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
            if self.on_submit:
                self.on_submit(self.text)
        elif key == pygame.K_ESCAPE:
            self.blur()
        # 放在key_text 事件接收. 这里不要接收.会重复
        elif unicode:
            if self.is_password:
                text_color = self.text_color if self.text else "#888888"
                GameFont.add(unicode, font_size=self.font_size, font_color=text_color, mask_color=text_color)
                self.__insert_text(unicode)

        self.need_redraw = True

    def keyboard_pressed(self, event: Dict[str, ScancodeWrapper] | pygame.event.EventType):
        """处理键盘长按事件"""
        key_event = event.get("event")
        if key_event and self.__has_ctrl(key_event):
            return
        self.key_down(event)

    def key_text(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        key_event = event.get("event")
        if not self.is_password:
            self.__insert_text(key_event.text)
            self.need_redraw = True

    def _reset_blink(self):
        """重置光标闪烁状态"""
        self.blink_tick = 0
        self.blink_show = True
        self.need_redraw = True

    def _trigger_change(self):
        """触发文本变化回调"""
        self.__normalize_cursor_view()
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
        self.__clear_selection()
        self.__drag_selecting = False
        self._trigger_change()

    def set_text(self, text: str):
        """设置输入框文本"""
        self.text = "" if text is None else str(text)
        self.cursor_index = len(self.text)
        self.scroll_offset = 0
        self.__clear_selection()
        self.__drag_selecting = False
        self._trigger_change()

    def insert_text(self, text: str):
        """在当前光标或选区位置插入文本."""
        self.__insert_text(text)

    def move_cursor_to_end(self):
        """把光标移动到文本末尾."""
        self.cursor_index = len(self.text)
        self.__clear_selection()
        self.__normalize_cursor_view()
        self._reset_blink()

    def get_state(self) -> dict[str, Any]:
        """保存文本、光标和选区状态, 供对话框重渲染后恢复."""
        return {
            "text": self.text,
            "cursor_index": self.cursor_index,
            "selection_start": self.selection_start,
            "selection_end": self.selection_end,
            "scroll_offset": self.scroll_offset,
            "has_focus": self.has_focus,
        }

    def restore_state(self, state: dict[str, Any]):
        """恢复输入框状态."""
        if not isinstance(state, dict):
            return
        self.text = "" if state.get("text") is None else str(state.get("text"))
        self.cursor_index = int(state.get("cursor_index", len(self.text)) or 0)
        self.selection_start = int(state.get("selection_start", self.cursor_index) or 0)
        self.selection_end = int(state.get("selection_end", self.cursor_index) or 0)
        self.scroll_offset = max(0, int(state.get("scroll_offset", 0) or 0))
        self.has_focus = bool(state.get("has_focus", self.has_focus))
        self.__drag_selecting = False
        self.__normalize_cursor_view()
        self._reset_blink()

    def blur(self):
        """ 失去焦点 """
        self.blink_tick = 0
        self.has_focus = False
        self.blink_show = False
        self.__drag_selecting = False
        self.need_redraw = True
        pygame.key.stop_text_input()

    def destroy(self):
        super().destroy()
        # if self.has_focus:
        #     pygame.key.stop_text_input()
        from src.manager.GameEvent import GameEvent
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


    def update_value(self, value: Any):
        self.set_text(str(value))
