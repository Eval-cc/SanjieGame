# #!/usr/bin/env python
# # -*- coding: UTF-8 -*-
# """
# @Project ：三界奇谈
# @File    ：GameDialog.py
# @IDE     ：PyCharm
# @Author  ：eval-
# @Email  ： eval-email@qq.com
# @Date    ：2025/7/19 20:14
# @Describe: 对话框
# """

import os.path
from typing import TYPE_CHECKING, Dict, Any
import pygame

from src.components.GameButton import GameButton
from src.components.GameCheckBox import GameCheckBox
from src.components.GameComponentBase import GameComponentBase
from src.components.GameInput import GameInput
from src.components.GameSlider import GameSlider
from src.code.Enums import ShopType
from src.manager.GameLogManger import GameLogManager
from uuid import uuid4
from src.manager.GameMapManager import GameMapManager
from src.system.GameMusic import GameMusicManager
from src.system.GameToast import GameToastManager
from src.manager.SourceManager import SourceManager

if TYPE_CHECKING:
    from src.manager.GameManager import GameManager
    from src.render.GameUI import GameUI
    from src.character.NPC import NpcSprite


class GameDialog:
    def __init__(self, gm, win_key="游戏UI"):
        # 基础属性
        self.rect = None
        self.gm: GameManager = gm
        self.update_blit = True

        self.__curr_npc: NpcSprite = None

        self.__GUI_rect_list = []

        self.__scroll_y = 0
        self.__scroll_max = 0
        self.__render_full_height = 0
        self.__cached_result = None

        self.blink_tick = 0
        self.blink_show = True  # 是否显示光标

        self.__has_focus = False
        self.__focus_node = None
        self.__cursor_index = 0  # 光标索引

        self.__has_scroll_wheel = False  # 是否通过滚轮触发的重绘

        self.dialog_title: pygame.Surface = None
        self.has_close = False  # 窗口是否显示关闭按钮- 默认false

        # 缓存一个不可变的UI, 比如p标签和 a标签, 没必要每次都要不断的生成
        self.__ui_cache_dict = {}
        self.__render_offset = []
        # 触发UI里面的点击事件之后, 触发的回调
        self.dialog_callback = None
        self.dialog_hover_callback = False
        self.__hover_node_key = None
        self.__listen_keyboard_callback = None
        # 存放对应的事件字典
        self.dialog_event_dict = {}
        # 存放单独的控件
        self._alone_component: Dict[str, GameComponentBase] = {}

        self.dialog_key = win_key

    def __focused_component(self):
        if self.__focus_node is None:
            return None
        return self._alone_component.get(self.__focus_node.get("target"))

    @staticmethod
    def __local_mouse_event(event, win_sprite):
        local_event = dict(event or {})
        mouse_pos = local_event.get("mouse_pos", pygame.mouse.get_pos())
        win_rect = win_sprite.get("rect")
        local_event["mouse_pos"] = (
            mouse_pos[0] - win_rect.x,
            mouse_pos[1] - win_rect.y
        )
        return local_event

    def show_dialog(self, dialog_path: str, npc=None, render_x: int = 5, render_y: int = -1, dialog_callback=None,
                    overwrite_path: bool = False, dialog_event_dict: Dict[str, Any] = None, loc: str = "middle",
                    load_val: Dict[str, Any] = None, always_on_top: bool = False, hover_callback: bool = False,
                    listen_keyboard=None, esc_close: bool = True):

        """调用NPC对话"""
        self.__scroll_y = 0
        self.__cached_result = None
        for _com in self._alone_component.values():
            _com.destroy()
        self._alone_component.clear()  # 清空组件
        self.__ui_cache_dict.clear()  # 传入新的对话内容, 清空上一轮的UI缓存
        self.__curr_npc = npc
        render_x, render_y = 5 if render_x == -1 else max(render_x, 5), 60 if render_y == -1 else max(render_y, 35)
        self.__render_offset = [render_x, render_y]
        self.__GUI_rect_list.clear()  # 清空点击的坐标信息
        self.__hover_node_key = None
        self.__focus_node = None
        self.__has_focus = False
        self.dialog_hover_callback = hover_callback

        self.dialog_event_dict = dialog_event_dict or {}
        self.__listen_keyboard_callback = listen_keyboard

        dialog_file_path = dialog_path  # 默认指向的就是传入的路径
        if not overwrite_path:
            dialog_file_path = f"{SourceManager.cfg_task_path}/{dialog_path}.html"
            if not os.path.exists(dialog_file_path):
                GameToastManager.add_message(f"不存在的对话文件:{dialog_file_path}")
                GameLogManager.log_service_debug(f"不存在的对话文件:{dialog_file_path}")
                return
        with open(dialog_file_path, "r", encoding="utf-8") as f:
            result = self.gm.game_task_paring_engine.get_paring_engine(f.read())
            if result is None:
                GameToastManager.add_message(f"非法的对话文件")
                GameLogManager.log_service_debug(f"非法的对话文件")
                return
            width, height = result.get('attrs').get("width"), result.get('attrs').get("height")
            _has_bg = len(result.get('attrs',{}).get("background-image","")) > 0 # 是否有背景
            # 此属性控制是否允许关闭改UI, 以及 标题栏显示关闭按钮
            self.has_close = result.get('attrs',{}).get('close', "false") == "true"
            if bool(width) ^ bool(height):
                GameToastManager.add_message(f"非法的对话文件")
                GameLogManager.log_service_debug(f"非法的对话文件")
                return
            # 指定回调方法
            self.dialog_callback = dialog_callback

            game_ui: GameUI = self.gm.get("游戏UI")
            dialog_sur: pygame.Surface = game_ui.get_surface_ui(self.dialog_key)

            if self.dialog_title is None or self.dialog_title.width != int(width):
                self.dialog_title = SourceManager.surface_scale(
                    SourceManager.load(f"{SourceManager.ui_system_path}/dialog_title.png"),
                    [int(width), 32]).convert_alpha()

            dialog_bg = pygame.Surface((int(width), int(height) - 30), pygame.SRCALPHA)
            dialog_bg.fill(self.gm.game_font.hex_color_to_rgb("#000000"))
            dialog_bg.set_alpha(170)

            if dialog_sur is None:
                dialog_sur = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)
                dialog_sur.fill((0, 0, 0, 0))
                dialog_sur.blit(self.dialog_title, (2, 0))
                # 有背景图片就不显示默认的边框了
                if not _has_bg:
                    dialog_sur.blit(dialog_bg, (0, 30))
                    pygame.draw.rect(dialog_sur, (self.gm.game_font.hex_color_to_rgb("#228B22")),
                                     (0, 30, int(width), int(height) - 30), 1)

                game_ui.load_system_ui(
                    f"{SourceManager.ui_system_path}/ui-button.png",
                    [240, 20],
                    options=
                    {
                        "name": f"{self.dialog_key}_按钮",
                        "frame": {
                            "size": 60,
                            "count": 2,
                            "index": 0,
                            "loc": (160, 363),
                        }
                    }, )

                [_, rect, _] = game_ui.load_system_ui(dialog_sur,
                                                      [int(width), int(height)],
                                                      loc,
                                                      {
                                                          "name": self.dialog_key,
                                                          "mouse_down": self.mouse_down,
                                                          "mouse_up": self.mouse_up,
                                                          "mouse_move": self.mouse_move,
                                                          # "mouse_out": self.mouse_out,
                                                          "mouse_double_click": self.mouse_double_click,
                                                          "update_event": self.render,
                                                          "mouse_scroll_wheel_down": self.mouse_scroll_wheel_down,
                                                          "mouse_scroll_wheel_up": self.mouse_scroll_wheel_up,
                                                          "keyboard_pressed": self.keyboard_pressed,
                                                          "drag": True,
                                                          "drag_rect": ["auto", "auto", "-25px", 30],
                                                          "bag_offset": pygame.Rect([25, 180, 200, 172]),
                                                          # "key_up": self.key_up,
                                                          "key_down": self.key_down,
                                                          "key_text": self.key_text,
                                                          # "bag_size": [45, 40],
                                                          # "item_event": None,
                                                          # "item_hover_event": None,
                                                          "update_blit": self.__update_blit,
                                                          "listen_keyboard": self.__listen_keyboard,
                                                          "hide_callback": self.__hide_callback,
                                                          "always_on_top": always_on_top,
                                                          "esc_close": esc_close
                                                          # "un_allow": True  # 显示此UI的时候 禁止其他操作, 除了另一个UI
                                                      }, sort=True)
                self.rect = rect
            else:
                """宽度和当前UI管理的不一样了?  那就重新加载一下"""
                dialog_sur = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)
                dialog_sur.blit(self.dialog_title, (2, 0))
                if not _has_bg:
                    dialog_sur.blit(dialog_bg, (0, 30))
                if self.rect is None:
                    self.rect = dialog_sur.get_rect()
                self.rect.width = int(width)
                self.rect.height = int(height)

                if not _has_bg:
                    pygame.draw.rect(dialog_sur, (self.gm.game_font.hex_color_to_rgb("#228B22")),
                                     (0, 30, int(width), int(height) - 30), 1)

            visible_height = dialog_sur.get_height()

            self.__cached_result = result  # 缓存结构
            actual_render_end = self.create_node(dialog_sur, self.__cached_result, render_x, render_y)
            self.__render_full_height = actual_render_end
            self.__scroll_max = max(0, self.__render_full_height - dialog_sur.get_height() + 20)

            # 节点创建完成, 开始尝试初始化值
            if load_val is not None:
                self._load_val(load_val)

            game_ui.set_surface_ui(self.dialog_key, dialog_sur)
            win_sprite = game_ui.get_surface_sprite(self.dialog_key)
            if win_sprite is not None:
                win_sprite["always_on_top"] = always_on_top
                win_sprite["listen_keyboard"] = self.__listen_keyboard
                win_sprite["esc_close"] = esc_close
            if self.__scroll_max > 0:
                scrollbar_x = dialog_sur.get_width() - 8
                scrollbar_height = max(20, (visible_height / (self.__render_full_height + 1)) * visible_height)
                scrollbar_y = int((self.__scroll_y / self.__scroll_max) * (visible_height - scrollbar_height))
                pygame.draw.rect(dialog_sur, (100, 100, 100), (scrollbar_x, 30 + scrollbar_y, 6, scrollbar_height))

            if game_ui.get_surface_show(self.dialog_key):
                return


            game_ui.change_ui_layer(self.dialog_key, center=loc == "middle")
            self.update_blit = True  # 触发页面重绘

    def mouse_down(self, **args):
        self.__has_focus = False
        event = args.get("event")
        mouse_pos = pygame.mouse.get_pos()
        game_ui: GameUI = self.gm.get("游戏UI")
        win_sprite = game_ui.get_surface_sprite(self.dialog_key)  # 需要加上UI的偏移

        # 小于拖拽区域高度的只能是关闭按钮了
        if mouse_pos[1] <= int(win_sprite.get("rect").y) + int(win_sprite.get("drag_rect")[3]):
            x_offset = int(win_sprite.get("drag_rect")[2]) - win_sprite.get("rect").width
            if mouse_pos[0] > int(win_sprite.get("rect").x) + int(win_sprite.get("rect").width) + x_offset:
                if not self.has_close:
                    # 没有关闭按钮. 不允许关闭
                    return
                self.close_dialog()
                return

        for [node, gui_rect] in self.__GUI_rect_list:
            if gui_rect.collidepoint(mouse_pos[0] - win_sprite.get("rect").x, mouse_pos[1] - win_sprite.get("rect").y):
                if self.dialog_callback:
                    self.dialog_callback(node)
                    return
                if node.get('tag') not in ("a", "button", "input", "tab-item", "slider", "checkbox"):
                    _be = node.get("attrs", {}).get("@click")
                    if _be and self.dialog_event_dict.get(_be):
                        self.dialog_event_dict[_be]()
                        self.update_blit = True
                        return
                if node.get('tag') == "a":
                    _be = node.get("attrs").get("@click")
                    if _be and self.dialog_event_dict.get(_be):
                        self.dialog_event_dict[_be]()
                        return
                    self.__cached_result = None
                    href = node.get('attrs').get("href", "")
                    hash_index = href.find("#")
                    if hash_index != -1:  # 如果找到 #
                        href = href[hash_index + 1:]  # 直接切片取 # 之后的部分
                    self.show_dialog(href)
                    self.update_blit = True
                    return
                elif node.get('tag') == "button":
                    _com = self._alone_component.get(node.get("target"))
                    if _com and hasattr(_com, "mouse_down"):
                        if _com.mouse_down(event):  # 返回True 表示有问题. 不让执行,可能被禁用了
                            return
                    else:
                        GameMusicManager.play_sound("mbutton")
                    self.update_blit = True
                    # 找到指定的key事件
                    _be = node.get("attrs").get("@click")
                    if _be and self.dialog_event_dict.get(_be):
                        self.dialog_event_dict[_be]()
                        return

                    self.__exec_event(node.get("attrs").get("data-client"))
                    return
                elif node.get('tag') == "input":
                    if node.get("attrs").get("disabled"):
                        return
                    self.__has_focus = True
                    self.__focus_node = node
                    _com = self._alone_component.get(node.get("target"))
                    if _com and hasattr(_com, "mouse_down"):
                        local_event = self.__local_mouse_event(event, win_sprite)
                        if _com.mouse_down(local_event):  # 返回True 表示有问题. 不让执行,可能被禁用了
                            return
                        self.update_blit = True
                        return
                    node["attrs"]["focus"] = True
                    # 设置候选框的位置
                    inp_offset = [
                        win_sprite.get("rect").x + gui_rect.x,
                        win_sprite.get("rect").y + gui_rect.y + gui_rect.height,
                        200,
                        50
                    ]
                    pygame.key.set_text_input_rect(inp_offset)
                    self.update_blit = True
                    return

                elif node.get('tag') == "tab-item":
                    group_id = node.get("group")
                    target_id = node.get("target")
                    self.__ui_cache_dict[group_id] = target_id  # 更新选中的标签
                    self.update_blit = True  # 触发重绘
                    return
                elif node.get('tag') == "slider":
                    _com = self._alone_component.get(node.get("target"))
                    if _com and hasattr(_com, "mouse_down"):
                        event["mouse_pos"] = (
                            event["mouse_pos"][0] - win_sprite.get("rect").x,
                            event["mouse_pos"][1] - win_sprite.get("rect").y
                        )
                        _com.mouse_down(event)
                    return

                elif node.get('tag') == "checkbox":
                    _com = self._alone_component.get(node.get("target"))
                    if _com and hasattr(_com, "mouse_down"):
                        if _com.mouse_down(event):  # 返回True 表示有问题. 不让执行,可能被禁用了
                            return
                        # 触发变化事件
                        _be = node.get("attrs").get("@change")
                        if _be and self.dialog_event_dict.get(_be):
                            self.dialog_event_dict[_be](_com.value)
                    self.update_blit = True
                    return
                GameLogManager.log_service_debug(f"点击:{node.get('tag')}")
                # self.update_blit = True
                return

    def mouse_up(self, **args):
        event = args.get("event")
        mouse_pos = pygame.mouse.get_pos()
        game_ui: GameUI = self.gm.get("游戏UI")
        win_sprite = game_ui.get_surface_sprite(self.dialog_key)  # 需要加上UI的偏移

        focused_com = self.__focused_component()
        if focused_com and hasattr(focused_com, "mouse_up"):
            local_event = self.__local_mouse_event(event, win_sprite)
            focused_com.mouse_up(local_event)
            self.update_blit = True

        for [node, gui_rect] in self.__GUI_rect_list:
            if gui_rect.collidepoint(mouse_pos[0] - win_sprite.get("rect").x, mouse_pos[1] - win_sprite.get("rect").y):
                if node.get('tag') == "button":
                    _com = self._alone_component.get(node.get("target"))
                    if _com and hasattr(_com, "mouse_up"):
                        if _com.mouse_up(None):  # 返回True 表示有问题. 不让执行,可能被禁用了
                            return
                    self.update_blit = True
                    return

                elif node.get('tag') == "slider":
                    _com = self._alone_component.get(node.get("target"))
                    if _com and hasattr(_com, "mouse_up"):
                        _com.mouse_up(event)
                    return
                return

    #
    def mouse_move(self, **args):
        event = args.get("event")
        mouse_pos = pygame.mouse.get_pos()
        game_ui: GameUI = self.gm.get("游戏UI")
        win_sprite = game_ui.get_surface_sprite(self.dialog_key)  # 需要加上UI的偏移
        focused_com = self.__focused_component()
        if focused_com and hasattr(focused_com, "mouse_move") and \
                hasattr(focused_com, "is_drag_selecting") and focused_com.is_drag_selecting():
            local_event = self.__local_mouse_event(event, win_sprite)
            focused_com.mouse_move(local_event)
            self.update_blit = True
            return

        hover_node = None
        for [node, gui_rect] in self.__GUI_rect_list:
            if gui_rect.collidepoint(mouse_pos[0] - win_sprite.get("rect").x, mouse_pos[1] - win_sprite.get("rect").y):
                hover_node = node
                node_rect = pygame.Rect(gui_rect)
                node_rect.x += win_sprite.get("rect").x
                node_rect.y += win_sprite.get("rect").y
                self.__emit_hover_node(node, mouse_pos, node_rect)
                if node.get('tag') == "slider":
                    _com = self._alone_component.get(node.get("target"))
                    if _com and hasattr(_com, "mouse_move"):
                        event["mouse_pos"] = (
                            event["mouse_pos"][0] - win_sprite.get("rect").x,
                            event["mouse_pos"][1] - win_sprite.get("rect").y
                        )
                        if _com.mouse_move(event):
                            return

                        # 触发变化事件
                        _be = node.get("attrs").get("@change")
                        if _be and self.dialog_event_dict.get(_be):
                            self.dialog_event_dict[_be](_com.value)
                        self.update_blit = True
                    return
                return
        if hover_node is None:
            self.__emit_hover_node(None, mouse_pos)

    def __emit_hover_node(self, node, mouse_pos, node_rect=None):
        if not self.dialog_hover_callback or not self.dialog_callback:
            return
        payload_rect = None
        if node_rect is not None:
            payload_rect = [node_rect.x, node_rect.y, node_rect.width, node_rect.height]
        hover_key = id(node) if node is not None else None
        if hover_key == self.__hover_node_key and node is not None:
            self.dialog_callback({"__type": "hover_move", "node": node, "mouse_pos": mouse_pos, "node_rect": payload_rect})
            return
        self.__hover_node_key = hover_key
        if node is None:
            self.dialog_callback({"__type": "hover_out", "mouse_pos": mouse_pos})
            return
        self.dialog_callback({"__type": "hover", "node": node, "mouse_pos": mouse_pos, "node_rect": payload_rect})

    #
    # def mouse_out(self):
    #     pass
    #
    def mouse_double_click(self, **args):
        event = args.get("event")
        mouse_pos = pygame.mouse.get_pos()
        game_ui: GameUI = self.gm.get("游戏UI")
        win_sprite = game_ui.get_surface_sprite(self.dialog_key)
        if win_sprite is None:
            return False

        for [node, gui_rect] in self.__GUI_rect_list:
            if gui_rect.collidepoint(mouse_pos[0] - win_sprite.get("rect").x, mouse_pos[1] - win_sprite.get("rect").y):
                if self.dialog_callback:
                    self.dialog_callback({"__type": "double_click", "node": node, "mouse_pos": mouse_pos})
                    return False
                return False
        return False

    def mouse_scroll_wheel_down(self):
        """
        UI的滚轮向下事件
        :return:
        """
        scroll_event = self.dialog_event_dict.get("__scroll_down")
        if scroll_event:
            if scroll_event() is not True:
                return False

        if self.__scroll_y < self.__scroll_max:
            self.__has_focus = True
            self.__GUI_rect_list.clear()
            self.__scroll_y = min(self.__scroll_y + 30, self.__scroll_max)
            self.update_blit = True
            self.__has_scroll_wheel = True
            return False
        return True

    def mouse_scroll_wheel_up(self):
        """
        UI的滚轮向上事件
        :return:
        """
        scroll_event = self.dialog_event_dict.get("__scroll_up")
        if scroll_event:
            if scroll_event() is not True:
                return False

        if self.__scroll_y > 0:
            self.__has_focus = True
            self.__GUI_rect_list.clear()
            self.__scroll_y = max(self.__scroll_y - 30, 0)
            self.update_blit = True
            self.__has_scroll_wheel = True
            return False
        return True

    def key_text(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        if self.__focus_node is None:
            return

        _com = self._alone_component.get(self.__focus_node.get("target"))
        if _com and hasattr(_com, "key_text"):
            if _com.key_text(event):  # 返回True 表示有问题. 不让执行,可能被禁用了
                return
            return

    def key_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        if not self.__listen_keyboard():
            return
        if self.__focus_node:
            _com = self._alone_component.get(self.__focus_node.get("target"))
            if _com and hasattr(_com, "key_down"):
                if _com.key_down(event):  # 返回True 表示有问题. 不让执行,可能被禁用了
                    return
                if hasattr(_com, "listen_keyboard") and not _com.listen_keyboard():
                    self.__focus_node = None
                    self.__has_focus = False
                return

    def keyboard_pressed(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """键盘长按事件"""
        self.key_down(event)

    def render(self):
        self.blink_tick += 1
        if self.blink_tick >= 30:  # 每 30 帧切换一次状态（大约 500ms）
            self.blink_tick = 0
            self.blink_show = not self.blink_show

    def __update_blit(self):
        """用于提供给游戏UI进行重绘的方法"""
        if not self.update_blit and not self.__has_focus:
            return
        self.update_blit = False

        # 如果是通过滚轮触发的重绘, 那么就重置状态
        if self.__has_scroll_wheel:
            self.__has_scroll_wheel = False
            self.__has_focus = False

        if self.__cached_result is None:
            return
        game_ui: GameUI = self.gm.get("游戏UI")
        width, height = int(self.__cached_result.get('attrs').get("width")), int(
            self.__cached_result.get('attrs').get("height"))
        dialog_sur = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)
        dialog_sur.fill((0, 0, 0, 0))

        dialog_bg = pygame.Surface((width, height - 30), pygame.SRCALPHA)
        dialog_bg.fill(self.gm.game_font.hex_color_to_rgb("#000000"))
        dialog_bg.set_alpha(170)

        dialog_sur.blit(self.dialog_title, (2, 0))
        dialog_sur.blit(dialog_bg, (0, 30))
        pygame.draw.rect(dialog_sur, self.gm.game_font.hex_color_to_rgb("#228B22"),
                         (0, 30, width, height - 30), 1)

        self.__GUI_rect_list = []
        # 解析节点信息
        self.create_node(dialog_sur, self.__cached_result, self.__render_offset[0],
                         self.__render_offset[1] - self.__scroll_y)

        if self.__scroll_max > 0:
            scrollbar_x = dialog_sur.get_width() - 8
            scrollbar_height = max(20, int(height / (self.__render_full_height + 1)) * height)
            scrollbar_y = int((self.__scroll_y / self.__scroll_max) * (height - scrollbar_height))
            pygame.draw.rect(dialog_sur, (100, 100, 100), (scrollbar_x, 30 + scrollbar_y, 6, scrollbar_height - 20), 5)
        # 渲染NPC名称
        if self.__curr_npc:
            text_surface = self.gm.game_font.get_text_surface_line(self.__curr_npc.name, True, 14, "#FFFF00")
            dialog_sur.blit(text_surface, (10, 35))
        game_ui.set_surface_ui(self.dialog_key, dialog_sur)

    def blit_with_clipping(self, target_surface, source_surface, render_x, render_y, clip_top):
        """根据置顶的位置裁切UI, 让滚动之后,不会超出UI范围显示, 且平滑的渲染"""
        if render_y >= clip_top:
            target_surface.blit(source_surface, (render_x, render_y))
        else:
            cut_y = clip_top - render_y
            visible_height = source_surface.get_height() - cut_y
            if visible_height > 0:
                cut_area = pygame.Rect(0, cut_y, source_surface.get_width(), visible_height)
                target_surface.blit(source_surface, (render_x, clip_top), area=cut_area)
                return cut_area
        return None

    def create_node(self, dialog_sur: pygame.Surface, node: dict, render_x: int, render_y: int, inherited_style=None,
                    parent_color: str = None):
        if inherited_style is None:
            inherited_style = {
                "font-size": 12,
                "color": "#000000",
                "background-color": None,
            }
        attrs = node.get("attrs", {})
        dom_id = attrs.get("id")
        tag = node.get("tag")
        node_text = node.get("text") or attrs.get("label") or ""
        children = node.get("children", [])
        view_height = self.__render_offset[1]  # 可视区域

        curr_style = inherited_style.copy()

        # 线存为上一级传进来的父级颜色, 文本的颜色向下继承 允许
        if parent_color:
            curr_style["color"] = parent_color

        if "font-size" in attrs:
            curr_style["font-size"] = int(attrs["font-size"])
        if "color" in attrs:
            color_val = attrs.get("color", "#FFFFFF")
            if not color_val.startswith("#") and len(color_val) >= 6:
                color_val = "#" + color_val[:6]
            curr_style["color"] = color_val
        if "background-color" in attrs:
            curr_style["background-color"] = attrs.get("background-color", "#000000")
        if "img-size" in attrs:
            curr_style["img-size"] = [int(i) for i in attrs.get("img-size").split(",")]

        if "src" in attrs:
            curr_style["src"] = attrs.get("src")

        if "sticky" in attrs:
            curr_style["sticky"] = True
        el_padding = attrs.get("padding", "0").split()

        # padding的顺序和 html的规范保持一致. 上右下左
        __el_padding = [0, 0, 0, 0]
        match el_padding:
            case [p]:
                # 单值：[all] -> [top, right, bottom, left]
                __el_padding = [int(p)] * 4

            case [v, h]:
                # 双值：[vertical, horizontal] -> [top, right, bottom, left]
                __el_padding = [int(v), int(h), int(v), int(h)]

            case [t, h, b]:
                # 三值：[top, horizontal, bottom] -> [top, right, bottom, left]
                __el_padding = [int(t), int(h), int(b), int(h)]

            case [t, r, b, l]:
                # 四值：[top, right, bottom, left]
                __el_padding = [int(t), int(r), int(b), int(l)]

            case _:
                # 其他不匹配的情况
                pass

        render_x += __el_padding[3]
        render_y += __el_padding[0]

        def __render_bg_img(_ax=None, _ay=None, _attr=None):
            if _attr is None:
                _attr = attrs
            if "background-image" in _attr:
                cbg_path: str = _attr.get("background-image")
                clip_path: str = _attr.get("clip-path")  # 是否存在裁剪属性
                curr_style["background-image"] = cbg_path
                curr_style["background-image"] = clip_path
                if cbg_path.startswith("#ROOT_S"):
                    cbg_path = cbg_path.replace("#ROOT_S", SourceManager.ui_system_path)
                _cbg_w = max(int(_attr.get("width", "0")) - __el_padding[1], 0)
                _cbg_h = max(int(_attr.get("height", "0")) - __el_padding[2], 0)
                cbg_sur = SourceManager.load(cbg_path)
                if cbg_sur:
                    if type(cbg_sur) == dict:
                        cbg_sur = cbg_sur.get("surface")
                    if clip_path:
                        clip_path_arr = [int(i) for i in clip_path.split(" ")]
                        clip_x = 0 if clip_path_arr[0] == -1 else clip_path_arr[0]
                        clip_y = 0 if clip_path_arr[1] == -1 else clip_path_arr[1]
                        clip_w = cbg_sur.width if clip_path_arr[2] == -1 else clip_path_arr[2]
                        clip_h = cbg_sur.height if clip_path_arr[3] == -1 else clip_path_arr[3]
                        cbg_sur = cbg_sur.subsurface((clip_x, clip_y, clip_w - clip_x, clip_h - clip_y))

                    if dom_id == "app":
                        # 获取容器设定的宽高
                        container_w = int(_attr.get("width", "0"))
                        container_h = int(_attr.get("height", "0"))
                        # 如果是根节点，强制缩放到对话框主体区域大小（宽, 高-30）
                        target_size = (container_w, container_h - 30)
                        cbg_sur = pygame.transform.smoothscale(cbg_sur, target_size)
                        dialog_sur.blit(cbg_sur, (0, 30))
                        _cbg_w, _cbg_h = target_size
                    else:
                        if _cbg_w > 0 and _cbg_h > 0:
                            cbg_sur = SourceManager.surface_scale(cbg_sur, [_cbg_w, _cbg_h])
                        else:
                            _cbg_w, _cbg_h = cbg_sur.get_size()
                        if dom_id == "app":  # 根节点不跟随滚动.
                            dialog_sur.blit(cbg_sur, (0, 30))
                        else:
                            if _ax is None:
                                _ax = render_x
                            if _ay is None:
                                _ay = render_y
                            self.blit_with_clipping(dialog_sur, cbg_sur, _ax, _ay, view_height)
                        # dialog_sur.blit(cbg_sur, (render_x, render_y))
                        curr_style["background-color"] = None  # 优先背景图片
                return _cbg_w, _cbg_h
            return 0, 0

        _biw, _bih = 0, 0
        if tag not in ["tabs", "tab-item", "row", "input", "button", "checkbox"]:
            # 渲染bg
            _biw, _bih = __render_bg_img()

        # 为每个节点生成一个唯一的节点id
        if "__node_uuid" not in attrs:
            attrs["__node_uuid"] = uuid4().hex[:8]
            node["attrs"] = attrs

        # 替换NPC占位
        if node_text and self.__curr_npc:
            node_text = node_text.replace("{{NPC_NAME}}", self.__curr_npc.name)

        if tag == "p":
            if node_text:
                text_surface = self.__ui_cache_dict.get(f"ui_label_{node_text}")
                if text_surface is None:
                    text_surface = self.gm.game_font.get_multiple_text_by_max_height(
                        str(node_text),
                        dialog_sur.width - render_x - __el_padding[1],
                        dialog_sur.height - __el_padding[2],
                        True,
                        curr_style["font-size"],
                        curr_style["color"]
                    )
                    self.__ui_cache_dict[f"ui_label_{node_text}"] = text_surface
                node_rect = text_surface.get_rect()
                node_rect.x = render_x
                node_rect.y = render_y
                # if curr_style.get("sticky"):
                #     node_rect.y = render_y + self.__scroll_y
                # 跳过不可视区域
                self.blit_with_clipping(dialog_sur, text_surface, render_x, node_rect.y, view_height)

                render_y += text_surface.height + 10

        elif tag == "a":
            if node_text:
                text_surface = self.__ui_cache_dict.get(f"ui_link_{node_text}")
                curr_style["color"] = "#1E90FF"
                if text_surface is None:
                    text_surface = self.gm.game_font.get_text_surface_line(
                        str(node_text),
                        True,
                        curr_style["font-size"],
                        curr_style["color"]
                    )
                    self.__ui_cache_dict[f"ui_link_{node_text}"] = text_surface

                node_rect = text_surface.get_rect()
                node_rect.x = render_x
                node_rect.y = render_y
                self.__GUI_rect_list.append([node, node_rect])

                self.blit_with_clipping(dialog_sur, text_surface, render_x, render_y, view_height)
                # 跳过不可视区域
                if render_y + node_rect.height > view_height:
                    pygame.draw.aaline(dialog_sur, curr_style["color"],
                                       (render_x, render_y + curr_style["font-size"] + 2),
                                       (node_rect.width + render_x, render_y + curr_style["font-size"] + 2))
                render_y += text_surface.height + 10

        elif tag == "button11":
            if node_text:
                game_ui: GameUI = self.gm.get("游戏UI")
                params = game_ui.get_surface_sprite(f"{self.dialog_key}_按钮")
                frame_size = params["frame"]["size"]
                # frame_index = params["frame"]["index"]

                text_surface = self.__ui_cache_dict.get(f"ui_btn-text_{node_text}")
                if text_surface is None:
                    text_surface = self.gm.game_font.get_text_surface_line(
                        str(node_text),
                        True,
                        curr_style["font-size"],
                        curr_style["color"]
                    )
                    self.__ui_cache_dict[f"ui_btn-text_{node_text}"] = text_surface

                node_rect = text_surface.get_rect()
                node_rect.x = render_x
                node_rect.y = render_y
                if _biw == 0 or _bih == 0:
                    btn_surface = self.__ui_cache_dict.get(f"ui_btn-bg_{node_text}")
                    if btn_surface is None:
                        btn_surface = SourceManager.surface_scale(params["surface"],
                                                                  [text_surface.width + 20, frame_size // 2.5])
                    btn_rect = btn_surface.get_rect()
                    btn_rect.x = render_x
                    btn_rect.y = render_y

                    node_rect.center = btn_rect.center
                    self.blit_with_clipping(dialog_sur, btn_surface, btn_rect.x, btn_rect.y, view_height)
                    self.blit_with_clipping(dialog_sur, text_surface, node_rect.x, node_rect.y, view_height)
                    self.__GUI_rect_list.append([node, btn_rect])

                else:
                    btn_rect = node_rect.copy()
                    btn_rect.width = _biw
                    btn_rect.height = _bih

                    node_rect.center = btn_rect.center
                    self.blit_with_clipping(dialog_sur, text_surface, node_rect.x, node_rect.y, view_height)
                    self.__GUI_rect_list.append([node, btn_rect])

                render_y += text_surface.height + 20

        elif tag == "button":
            if node_text:
                _com_id = node_text if dom_id is None else dom_id
                # 避免循环new
                exist_com = self._alone_component.get(_com_id)

                game_ui: GameUI = self.gm.get("游戏UI")
                params = game_ui.get_surface_sprite(f"{self.dialog_key}_按钮")
                # frame_size = params["frame"]["size"]

                input_width = int(attrs.get("width", 80))
                input_height = int(attrs.get("height", 25))
                # frame_index = params["frame"]["index"]

                text_surface = self.__ui_cache_dict.get(f"ui_btn-text_{node_text}")
                if text_surface is None:
                    text_surface = self.gm.game_font.get_text_surface_line(
                        str(node_text),
                        True,
                        curr_style["font-size"],
                        curr_style["color"]
                    )
                    self.__ui_cache_dict[f"ui_btn-text_{node_text}"] = text_surface

                node_rect = text_surface.get_rect()
                node_rect.width = max(node_rect.width, input_width)
                node_rect.height = max(node_rect.height, input_height)
                # _biw, _bih = __render_bg_img(node_rect.x,node_rect.y)
                if exist_com is None:
                    common_props = {
                        "font_size": 10,
                        "text_color": "#FFFFFF",
                        "hover_color": "#2980b9",
                        "press_color": "#1a5276",
                        "bg_image": SourceManager.ui_system_path + "/gw_b1.png",
                        "bg_press_image": SourceManager.ui_system_path + "/gw_b2.png"
                    }

                    exist_com = GameButton(
                        pygame.Surface(node_rect.size, pygame.SRCALPHA),
                        pygame.Rect(render_x, render_y, node_rect.width, node_rect.height),  # 位置和大小
                        node_text,
                        parent_id=_com_id,
                        border_color="#2980b9",
                        **common_props
                    )
                    self.blit_with_clipping(dialog_sur, exist_com.render(), render_x, render_y, view_height)
                    self._alone_component[_com_id] = exist_com
                    render_y += exist_com.rect.height
                else:
                    exist_com.update_pos(render_x, render_y)
                    self.blit_with_clipping(dialog_sur, exist_com.render(), render_x, render_y, view_height)
                    render_y += exist_com.rect.height

                render_y += 5
                self.__GUI_rect_list.append([{"tag": tag, "target": _com_id, "attrs": attrs}, exist_com.rect])

        elif tag == "img":
            if not curr_style["src"]:
                placeholder_size = curr_style.get("img-size") or [
                    int(attrs.get("width", 50)),
                    int(attrs.get("height", 50))
                ]
                img_surface = self.__ui_cache_dict.get(f"ui_img_none_{placeholder_size[0]}_{placeholder_size[1]}")
                if img_surface is None:
                    img_surface = pygame.Surface(placeholder_size, pygame.SRCALPHA)
                    self.__ui_cache_dict[f"ui_img_none_{placeholder_size[0]}_{placeholder_size[1]}"] = img_surface

                # 跳过不可视区域
                self.blit_with_clipping(dialog_sur, img_surface, render_x, render_y, view_height)
                node_rect = pygame.Rect(render_x, render_y, img_surface.width, img_surface.height)
                if attrs.get("@click"):
                    self.__GUI_rect_list.append([node, node_rect])
                render_y += img_surface.height
            else:
                img_url = curr_style["src"]
                img_size = curr_style.get("img-size")
                img_cache_key = f"ui_img_{curr_style['src']}"
                if img_size:
                    img_cache_key = f"{img_cache_key}_{img_size[0]}_{img_size[1]}"
                img_surface = self.__ui_cache_dict.get(img_cache_key)
                if img_surface is None:
                    raw_cache_key = f"ui_img_raw_{curr_style['src']}"
                    raw_surface = self.__ui_cache_dict.get(raw_cache_key)
                    if img_url == "{{NPC_AVATAR}}":
                        # 指定了用当前NPC的头像, 但是当前NPC又没有配置头像的情况下, 直接跳出 不渲染img标签
                        if not hasattr(self.__curr_npc, "avatar") or self.__curr_npc.avatar is None:
                            return render_y
                        raw_surface = self.__curr_npc.avatar
                    else:
                        if raw_surface is None:
                            if img_url.startswith("#ROOT_SKILL"):
                                img_url = img_url.replace("#ROOT_SKILL", SourceManager.ui_skill_path)
                                raw_surface = SourceManager.load(img_url)
                            elif img_url.startswith("#ROOT_ITEM"):
                                img_url = img_url.replace("#ROOT_ITEM", SourceManager.ui_item_path)
                                raw_surface = SourceManager.load(img_url)
                            else:
                                raw_surface = SourceManager.load(f"{SourceManager.cfg_task_path}/{curr_style['src']}")
                            self.__ui_cache_dict[raw_cache_key] = raw_surface

                    img_surface = SourceManager.surface_scale(raw_surface, img_size) if img_size else raw_surface
                    self.__ui_cache_dict[img_cache_key] = img_surface

                # 跳过不可视区域
                self.blit_with_clipping(dialog_sur, img_surface, render_x, render_y, view_height)
                node_rect = pygame.Rect(render_x, render_y, img_surface.width, img_surface.height)
                if attrs.get("@click"):
                    self.__GUI_rect_list.append([node, node_rect])
                render_y += img_surface.height

        elif tag == "input11":
            input_width = int(attrs.get("width", 160))
            input_height = int(attrs.get("height", 28))
            _attr = attrs
            _attr["width"] = input_width
            _attr["height"] = input_height
            i_w, i_h = __render_bg_img(_attr=_attr)
            if i_w > 0:
                input_width = i_w
            if i_h > 0:
                input_height = i_h

            is_disabled = "disabled" in attrs
            is_focused = node is self.__focus_node

            bg_color = "#7c7c00" if is_disabled else "#FFFFFF"
            border_color = "#999999" if is_disabled else "#000000"
            text_color = "#AAAAAA" if is_disabled else curr_style["color"]

            font_size = curr_style["font-size"]
            font = self.gm.game_font

            text = node.get("text", "")
            if is_focused and not is_disabled and text == "请输入内容":  # 这里是个雷, 玩家要是正好输入这段话就被清空了
                node["text"] = ""
                text = ""

            # 滚动偏移初始化
            if "__offset_x" not in attrs:
                attrs["__offset_x"] = 0

            input_surface = pygame.Surface((input_width, input_height), pygame.SRCALPHA)
            if "background-image" not in attrs:  # 仅没有背景图像的时候生效
                input_surface.fill(self.gm.game_font.hex_color_to_rgb(bg_color))

            pygame.draw.rect(input_surface, self.gm.game_font.hex_color_to_rgb(border_color), (0, 0, input_width, 0), 1)

            if text is None:
                text = ""
            visible_text = text
            text_prefix = text[:self.__cursor_index]
            cursor_px = font.get_text_size(text_prefix)[0]

            # 滚动控制
            if cursor_px - attrs["__offset_x"] > input_width - 10:
                attrs["__offset_x"] = cursor_px - input_width + 10
            elif cursor_px - attrs["__offset_x"] < 0:
                attrs["__offset_x"] = cursor_px - 5
            attrs["__offset_x"] = max(0, attrs["__offset_x"])

            text_surface = font.get_text_surface_line(visible_text, True, font_size, text_color)
            input_surface.blit(text_surface, (5 - attrs["__offset_x"], (input_height - text_surface.get_height()) // 2))

            if is_focused and not is_disabled and self.blink_show:
                cursor_x = 5 + cursor_px - attrs["__offset_x"]
                pygame.draw.line(input_surface, pygame.Color(text_color), (cursor_x, 5), (cursor_x, input_height - 5),
                                 1)

            self.blit_with_clipping(dialog_sur, input_surface, render_x, render_y, view_height)
            input_rect = pygame.Rect(render_x, render_y, input_width, input_height)
            self.__GUI_rect_list.append([node, input_rect])
            render_y += input_height + 8

        elif tag == "input":
            # 避免循环new
            exist_com = self._alone_component.get(dom_id)
            if exist_com is None:
                input_width = int(attrs.get("width", 160))
                input_height = int(attrs.get("height", 28))
                field = attrs.get("field", "")
                # border_color = attrs.get("border-color", "#10c34e")
                border_color = attrs.get("border-color")
                is_password = attrs.get("type", "text") == "password"
                exist_com = GameInput(pygame.Surface((input_width, input_height), pygame.SRCALPHA),
                                      pygame.Rect([render_x, render_y, input_width, input_height]),
                                      placeholder=attrs.get("placeholder", ""), is_password=is_password,
                                      bg_color="#000000",
                                      text_color="#FFFFFF", parent_id=dom_id, field=field, border_color=border_color)
                self.blit_with_clipping(dialog_sur, exist_com.render(), render_x, render_y, view_height)
                self._alone_component[dom_id] = exist_com
                render_y += exist_com.rect.height
            else:
                exist_com.update_pos(render_x, render_y)
                self.blit_with_clipping(dialog_sur, exist_com.render(), render_x, render_y, view_height)
                render_y += exist_com.rect.height
            submit_event = attrs.get("@submit")
            if submit_event and self.dialog_event_dict.get(submit_event):
                exist_com.on_submit = lambda value, event_key=submit_event: self.dialog_event_dict[event_key](value)
            else:
                exist_com.on_submit = None
            history_event = attrs.get("@history")
            if history_event and self.dialog_event_dict.get(history_event):
                exist_com.on_history = lambda direction, value, event_key=history_event: self.dialog_event_dict[event_key](
                    direction, value)
            else:
                exist_com.on_history = None
            render_y += 5
            self.__GUI_rect_list.append([{"tag": tag, "target": dom_id, "attrs": attrs}, exist_com.rect])

        elif tag == "table":
            table_width = int(attrs.get("width", 300)) - __el_padding[1]
            table_height = int(attrs.get("height", 200)) - __el_padding[2]
            border_color = pygame.Color("#000000")
            bg_color = pygame.Color(attrs.get("background-color", "#FFFFFF"))
            has_border = attrs.get("border", "false") == "true"

            # 整个表格 surface
            table_surface = pygame.Surface((table_width, table_height), pygame.SRCALPHA)
            if "background-image" not in attrs:  # 仅没有背景图像的时候生效
                table_surface.fill(bg_color)

            cell_x = 5
            cell_y = 5
            cell_width = 100
            cell_height = 25
            font = self.gm.game_font
            font_size = 18
            color = "#000000"

            for row_block in children:
                if row_block["tag"] in ("thead", "tbody"):
                    for tr in row_block["children"]:
                        for cell in tr["children"]:
                            cell_text = str(cell.get("text", ""))
                            max_pixel_width = cell_width - 10
                            display_text = cell_text
                            while font.get_text_surface_line(display_text, True, font_size,
                                                             color).get_width() > max_pixel_width:
                                if len(display_text) <= 1:
                                    break
                                display_text = display_text[:-1]
                            if display_text != cell_text:
                                display_text = display_text[:-1] + "..."

                            text_surface = font.get_text_surface_line(display_text, True, font_size, color)
                            text_rect = text_surface.get_rect()
                            text_rect.topleft = (cell_x, cell_y)
                            table_surface.blit(text_surface, text_rect)

                            if has_border:
                                pygame.draw.rect(table_surface, border_color, (cell_x, cell_y, cell_width, cell_height),
                                                 1)

                            cell_x += cell_width
                        cell_y += cell_height
                        cell_x = 5

            # 表格外围边框（绘制在 table_surface 之外）
            table_rect = pygame.Rect(render_x, render_y, table_width, table_height)
            self.__GUI_rect_list.append([node, table_rect])
            # 用裁切方式渲染
            self.blit_with_clipping(dialog_sur, table_surface, render_x, render_y, view_height)

            render_y += table_height + 10

        elif tag == "ul":
            # 获取ul的样式属性
            ul_width = int(attrs.get("width", dialog_sur.width - render_x - 10))
            margin = int(attrs.get("margin", 5))

            # 计算grid布局的起始位置，考虑滚动偏移
            start_x = render_x
            start_y = render_y

            # 计算布局
            current_x = start_x
            current_y = start_y
            max_row_height = 0

            # 遍历所有li子元素
            for child in children:
                if child.get("tag") == "li":
                    li_attrs = child.get("attrs", {})
                    li_width = int(li_attrs.get("width", 50))
                    li_height = int(li_attrs.get("height", 50))
                    li_outer_width = li_width
                    li_outer_height = li_height
                    li_margin = int(li_attrs.get("margin", 0))
                    li_padding = li_attrs.get("padding", "0").split()

                    __li_padding = [0, 0, 0, 0]  # 内边距 -- 仅支持单个边距以及四个方向的边距. 其他格式的一律忽略
                    match li_padding:
                        case [p]:  # 单值 → 复制 4 份
                            __li_padding = [int(p)] * 4
                        case [a, b, c, d]:  # 4 值 → 直接转换
                            __li_padding = [int(a), int(b), int(c), int(d)]
                    align_items = li_attrs.get("align-items", "center")  # 获取垂直对齐方式，默认为center

                    # 检查是否需要换行
                    if current_x + li_width > start_x + ul_width:
                        current_x = start_x
                        current_y += max_row_height + li_margin
                        max_row_height = 0

                    # 创建li元素
                    li_surface = pygame.Surface((li_outer_width, li_outer_height), pygame.SRCALPHA)
                    bg_image = li_attrs.get("background-image")
                    if bg_image:
                        bg_surface = self.__ui_cache_dict.get(f"ui_bg_{bg_image}_{li_outer_width}_{li_outer_height}")
                        if bg_surface is None:
                            if bg_image.startswith("#ROOT_S"):
                                bg_surface = SourceManager.load(
                                    bg_image.replace("#ROOT_S", SourceManager.ui_system_path)
                                )
                            elif bg_image.startswith("#ROOT_SKILL"):
                                bg_surface = SourceManager.load(
                                    bg_image.replace("#ROOT_SKILL", SourceManager.ui_skill_path)
                                )
                            elif bg_image.startswith("#ROOT_ITEM"):
                                bg_surface = SourceManager.load(
                                    bg_image.replace("#ROOT_ITEM", SourceManager.ui_item_path)
                                )
                            else:
                                bg_surface = SourceManager.load(f"{SourceManager.cfg_task_path}/{bg_image}")
                            bg_surface = SourceManager.surface_scale(bg_surface, [li_outer_width, li_outer_height])
                            self.__ui_cache_dict[f"ui_bg_{bg_image}_{li_outer_width}_{li_outer_height}"] = bg_surface
                        if bg_surface:
                            li_surface.blit(bg_surface, (0, 0))
                    elif "background-color" in li_attrs:
                        li_surface.fill(self.gm.game_font.hex_color_to_rgb(li_attrs["background-color"]))

                    # 初始化渲染位置 -- padding的顺序和 html的规范保持一致. 上右下左
                    base_offset = 0 if li_attrs.get("tight") == "true" else 5
                    element_x = base_offset + __li_padding[3]
                    element_y = base_offset + __li_padding[0]
                    li_width -= __li_padding[1]
                    li_height -= __li_padding[2]
                    max_line_height = 0

                    # 处理li元素的直接文本内容
                    direct_text = child.get("text", "")
                    if direct_text:
                        font = self.gm.game_font
                        font_size = curr_style["font-size"]
                        color = curr_style["color"]

                        text_surface = font.get_text_surface_line(direct_text, True, font_size, color)
                        text_rect = text_surface.get_rect()

                        # 设置文本位置
                        if align_items == "top":
                            text_rect.topleft = (element_x, element_y)
                        elif align_items == "bottom":
                            text_rect.bottomleft = (element_x, li_height - 5)
                        else:  # center
                            text_rect.left = element_x
                            text_rect.centery = li_height // 2

                        li_surface.blit(text_surface, text_rect)
                        element_x += text_rect.width + 5
                        max_line_height = max(max_line_height, text_rect.height)

                    # 按照源码顺序处理所有子元素
                    if "children" in child:
                        for sub_child in child["children"]:
                            if sub_child.get("tag") == "p":
                                # 处理p标签内的文本
                                text = sub_child.get("text", "")
                                if text:
                                    font = self.gm.game_font
                                    font_size = curr_style["font-size"]
                                    color = curr_style["color"]

                                    text_surface = font.get_text_surface_line(text, True, font_size, color)
                                    text_rect = text_surface.get_rect()

                                    # 设置文本位置
                                    if align_items == "top":
                                        text_rect.topleft = (element_x, element_y)
                                    elif align_items == "bottom":
                                        text_rect.bottomleft = (element_x, li_height - 5)
                                    else:  # center
                                        text_rect.left = element_x
                                        text_rect.centery = li_height // 2

                                    li_surface.blit(text_surface, text_rect)
                                    element_x += text_rect.width + 5
                                    max_line_height = max(max_line_height, text_rect.height)

                            elif sub_child.get("tag") == "img":
                                # 处理图片
                                img_attrs = sub_child.get("attrs", {})
                                img_src = img_attrs.get("src", "")
                                img_width = int(img_attrs.get("width", 0) or 0)
                                img_height = int(img_attrs.get("height", 0) or 0)

                                if img_src:
                                    # 加载图片
                                    img_cache_key = f"ui_img_{img_src}_{img_width}_{img_height}"
                                    img_surface = self.__ui_cache_dict.get(img_cache_key)
                                    if img_surface is None:
                                        if img_src.startswith("#ROOT_SKILL"):
                                            img_surface = SourceManager.load(
                                                img_src.replace("#ROOT_SKILL", SourceManager.ui_skill_path)
                                            )
                                        elif img_src.startswith("#ROOT_ITEM"):
                                            img_surface = SourceManager.load(
                                                img_src.replace("#ROOT_ITEM", SourceManager.ui_item_path)
                                            )
                                        else:
                                            img_surface = SourceManager.load(f"{SourceManager.cfg_task_path}/{img_src}")
                                        if img_surface and img_width > 0 and img_height > 0:
                                            img_surface = SourceManager.surface_scale(img_surface, [img_width, img_height])
                                        self.__ui_cache_dict[img_cache_key] = img_surface

                                    if img_surface:
                                        img_rect = img_surface.get_rect()

                                        # 设置图片位置
                                        if align_items == "top":
                                            img_rect.topleft = (element_x, element_y)
                                        elif align_items == "bottom":
                                            img_rect.bottomleft = (element_x, li_height - 5)
                                        else:  # center
                                            img_rect.left = element_x
                                            img_rect.centery = li_height // 2
                                        if img_surface.height > li_height:
                                            prop_w = li_height / img_surface.height
                                            img_bak = SourceManager.surface_scale(img_surface,
                                                                                  [round(img_surface.width * prop_w),
                                                                                    li_height])
                                            img_rect.y = 0
                                            element_x += img_bak.width + 5 + __li_padding[3]
                                            li_surface.blit(img_bak, img_rect)
                                        else:
                                            li_surface.blit(img_surface, img_rect)
                                            element_x += img_rect.width + 5
                                        max_line_height = max(max_line_height, img_rect.height)
                                else:
                                    img_width = int(img_attrs.get("width", 36))
                                    img_height = int(img_attrs.get("height", 36))
                                    element_x += img_width + 5
                                    max_line_height = max(max_line_height, img_height)

                            # 检查是否需要换行
                            if element_x > li_width - 5:
                                element_x = base_offset + __li_padding[3]
                                element_y += max_line_height + 5 + __li_padding[0]
                                max_line_height = 0

                    # 将li渲染到dialog_sur上
                    self.blit_with_clipping(dialog_sur, li_surface, current_x, current_y, view_height)

                    # 记录li的位置用于点击检测
                    li_rect = pygame.Rect(current_x, current_y, li_outer_width, li_outer_height)
                    self.__GUI_rect_list.append([child, li_rect])

                    # 更新位置
                    current_x += li_outer_width + li_margin
                    max_row_height = max(max_row_height, li_outer_height)

            # 更新render_y为ul的底部位置
            render_y = current_y + max_row_height + margin

        elif tag == "row":
            current_x = render_x
            max_height = 0
            for child in children:
                # 强制给子元素传入当前水平位置
                # 注意：子元素渲染后应返回它占用的高度
                child_bottom_y = self.create_node(dialog_sur, child, current_x, render_y, curr_style)

                # 假设每个组件我们给它一个默认宽度，或者从 html attrs 拿
                node_width = int(child.get("attrs", {}).get("width", 100))
                current_x += node_width + 10  # 10 是间距

                # 记录这一行中最高的组件，用于最后更新全局 render_y
                max_height = max(max_height, child_bottom_y - render_y)

            return render_y + max_height

        elif tag == "tabs":
            # 1. 确定当前选中的 tab ID (如果没有则默认选第一个)
            tab_id = dom_id or "default_tabs"
            if tab_id not in self.__ui_cache_dict:  # 借用缓存字典存状态
                self.__ui_cache_dict[tab_id] = children[0].get("attrs", {}).get("id")
            # 默认选中第一个
            active_id = self.__ui_cache_dict[tab_id]

            # 2. 渲染 Tab 头部按钮
            head_x = render_x
            for child in children:
                attrs = child.get("attrs", {})
                tabs_tag = child.get("tag", "tag-item")
                tabs_id = attrs.get("id", "")

                # 1. 获取背景/按钮的宽高
                i_w, i_h = __render_bg_img(head_x, render_y, attrs)
                if i_w == 0:
                    i_w = attrs.get("width", 80)
                if i_h == 0:
                    i_h = attrs.get("height", 25)

                tab_title = attrs.get("title", "Tab")

                # 2. 定义按钮矩形区域并绑定事件
                btn_rect = pygame.Rect(head_x, render_y, i_w, i_h)
                self.__GUI_rect_list.append(
                    [{"tag": tabs_tag, "target": tabs_id, "group": tab_id}, btn_rect])

                # 3. 渲染文本
                color = "#FFFF00" if tabs_id == active_id else "#FFFFFF"
                txt_surf = self.gm.game_font.get_text_surface_line(tab_title, True, 12, color)

                # --- 居中逻辑开始 ---
                # 获取文本的矩形对象
                txt_rect = txt_surf.get_rect()
                # 将文本矩形的中心点(center)设置为按钮矩形的中心点
                txt_rect.center = btn_rect.center

                # 绘制文本
                self.blit_with_clipping(dialog_sur, txt_surf, txt_rect.x, txt_rect.y, view_height)

                # 4. 递增横坐标 (建议根据实际宽度 i_w 递增，或保持固定间距)
                head_x += (i_w + 5)

            render_y += 35  # 头部高度

            # 3. 渲染选中的内容
            for child in children:
                if child.get("attrs", {}).get("id") == active_id:
                    render_y = self.create_node(dialog_sur, child, render_x, render_y, curr_style)

        elif tag == "slider":
            # 避免循环new
            exist_com = self._alone_component.get(dom_id)
            if exist_com is None:
                com_width = int(attrs.get("width", 150))
                com_height = int(attrs.get("height", 30))
                slider_width = int(attrs.get("slider-width", 20))
                slider_height = int(attrs.get("slider-height", 30))
                border_width = int(attrs.get("border-width", 1))
                bg_color = attrs.get("background-color", "#CCCCCC")
                slider_color = attrs.get("slider-color", "#666666")
                slider_active_color = attrs.get("slider-active-color", "#333333")
                border_color = attrs.get("border-color", "#000000")
                color = attrs.get("color", "#FFFFFF")

                val = attrs.get("value", "0")
                min_val = attrs.get("min", "0")
                max_val = attrs.get("max", "1")
                # 创建滑块实例
                exist_com = GameSlider(
                    pygame.Surface((com_width, com_height), pygame.SRCALPHA),
                    pygame.Rect(render_x, render_y, com_width, com_height),  # 位置和大小
                    min_value=float(min_val),  # 最小值
                    max_value=float(max_val),  # 最大值
                    initial_value=float(val),  # 初始值
                    bg_color=bg_color,  # 轨道背景颜色
                    slider_color=slider_color,  # 滑块颜色
                    active_slider_color=slider_active_color,  # 滑块激活时的颜色
                    border_color=border_color,  # 边框颜色
                    value_color=color,
                    border_width=border_width,  # 边框宽度
                    slider_width=slider_width,  # 滑块宽度
                    slider_height=slider_height,  # 滑块高度
                    show_value=True,  # 是否显示当前值
                    value_format="{:.0f}%",  # 值显示格式
                    parent_id=dom_id
                )
                self.blit_with_clipping(dialog_sur, exist_com.render(), render_x, render_y, view_height)
                self._alone_component[dom_id] = exist_com
                render_y += exist_com.rect.height
            else:
                exist_com.update_pos(render_x, render_y)
                self.blit_with_clipping(dialog_sur, exist_com.render(), render_x, render_y, view_height)
                render_y += exist_com.rect.height
            render_y += 5
            self.__GUI_rect_list.append([{"tag": tag, "target": dom_id, "attrs": attrs}, exist_com.rect])

        elif tag == "checkbox":
            if node_text == "" or node is None:
                node_text = ""
            _com_id = node_text if dom_id is None else dom_id
            # 避免循环new
            exist_com = self._alone_component.get(_com_id)

            com_width = int(attrs.get("width", 120))
            com_height = int(attrs.get("height", 30))

            text_surface = self.__ui_cache_dict.get(f"ui_btn-text_{node_text}")
            if text_surface is None:
                text_surface = self.gm.game_font.get_text_surface_line(
                    str(node_text),
                    True,
                    curr_style["font-size"],
                    curr_style["color"]
                )
                self.__ui_cache_dict[f"ui_btn-text_{node_text}"] = text_surface

            if exist_com is None:
                border_width = int(attrs.get("border-width", 1))
                bg_color = attrs.get("background-color", "#FFFFFF")
                check_color = attrs.get("check-color", "#0000FF")
                hover_color = attrs.get("hover-color", "#333333")
                border_color = attrs.get("border-color", "#FFFF00")
                color = attrs.get("color", "#FF0000")

                bg_image = attrs.get("background-image")
                bg_check_image = attrs.get("background-image-check")
                bg_image_clip = attrs.get("background-image-clip")
                bg_check_image_clip = attrs.get("background-image-check-clip")

                if bg_image:
                    if bg_image.startswith("#ROOT_S"):
                        bg_image = bg_image.replace("#ROOT_S", SourceManager.ui_system_path)
                        if bg_image_clip:
                            bg_image_clip = tuple(int(i) for i in bg_image_clip.split(","))
                            if len(bg_image_clip) == 4:
                                bg_image = SourceManager.load(bg_image).subsurface(bg_image_clip)
                            else:
                                bg_image = None
                        else:
                            bg_image = SourceManager.load(bg_image)
                    else:
                        bg_image = None

                if bg_check_image:
                    if bg_check_image.startswith("#ROOT_S"):
                        bg_check_image = bg_check_image.replace("#ROOT_S", SourceManager.ui_system_path)
                        if bg_check_image_clip:
                            bg_check_image_clip = tuple(int(i) for i in bg_check_image_clip.split(","))
                            if len(bg_check_image_clip) == 4:
                                bg_check_image = SourceManager.load(bg_check_image).subsurface(bg_check_image_clip)
                        else:
                            bg_check_image = SourceManager.load(bg_check_image)

                exist_com = GameCheckBox(
                    pygame.Surface((com_width, com_height), pygame.SRCALPHA),
                    pygame.Rect(render_x, render_y, com_width, com_height),
                    text=str(node_text),
                    is_checked=True,
                    is_radio=True,
                    font_size=12,
                    text_color=color,  # 红色文本
                    bg_color=bg_color,  # 白色背景
                    border_color=border_color,  # 绿色边框
                    check_color=check_color,  # 蓝色选中标记
                    hover_color=hover_color,  # 黄色悬停背景
                    border_width=2,
                    check_width=3,
                    bg_image=bg_image,
                    bg_check_image=bg_check_image,
                    parent_id=dom_id
                )
                self.blit_with_clipping(dialog_sur, exist_com.render(), render_x, render_y, view_height)
                self._alone_component[_com_id] = exist_com
                render_y += exist_com.rect.height + 5

            else:
                exist_com.update_pos(render_x, render_y)
                self.blit_with_clipping(dialog_sur, exist_com.render(), render_x, render_y, view_height)
                render_y += exist_com.rect.height

            render_y += 5
            self.__GUI_rect_list.append([{"tag": tag, "target": _com_id, "attrs": attrs}, exist_com.rect])

        elif tag == "br":
            render_y += 20
        elif tag == "hr":
            render_y += 3
            color = attrs.get("color", "#FFFFFF")
            start = (render_x, render_y)
            end = (dialog_sur.width - render_x, render_y)
            width = 1
            pygame.draw.line(dialog_sur, color, start, end, width)
            render_y += 3
        else:
            fixed_height = int(attrs.get("height", 0) or 0) if tag == "div" and dom_id != "app" else 0
            start_render_y = render_y
            old_clip = None
            if fixed_height > 0:
                fixed_width = int(attrs.get("width", dialog_sur.width - render_x - __el_padding[1]) or 0)
                fixed_rect = pygame.Rect(render_x, render_y, fixed_width, fixed_height)
                old_clip = dialog_sur.get_clip()
                dialog_sur.set_clip(fixed_rect.clip(old_clip))
            for child in children:
                render_y = self.create_node(dialog_sur, child, render_x, render_y, curr_style,
                                            parent_color=curr_style["color"])
            if old_clip is not None:
                dialog_sur.set_clip(old_clip)
            if fixed_height > 0:
                render_y = start_render_y + fixed_height

        return render_y

    def __exec_event(self, cmd_name: str):
        """触发对话开窗的事件命令"""
        if cmd_name is None:
            return
        game_ui: GameUI = self.gm.get("游戏UI")
        # 购买
        if cmd_name == "client://shop&buy":
            game_ui.change_ui_layer(self.dialog_key)
            self.gm.shop_system.add_shops(self.__curr_npc.shop_item, self.__curr_npc.name, ShopType.BUY)
            return

        # 出售
        if cmd_name == "client://shop&sell":
            game_ui.change_ui_layer(self.dialog_key)
            self.gm.shop_system.add_shops(self.gm.get("主角").bag.get_items_all(), self.__curr_npc.name, ShopType.SELL)
            return

        # 触发战斗
        if cmd_name == "client://enemy&battle":
            self.__curr_npc.battle()
            return

        # 关闭对话框
        if cmd_name == "client://dialog&close":
            self.close_dialog()
            return

        # 触发场景切换
        if cmd_name.startswith("client://moveto&"):
            self.close_dialog()
            # 解析格式：client://moveto&map_id&x&y 或 client://moveto&map_id
            parts = cmd_name.split("&")[1:]  # 移除协议头，得到参数列表

            if len(parts) >= 1:
                map_id = parts[0]  # 第一个参数总是map_id（可以是任意字符串）

                # 处理坐标参数（可选）
                x = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else None
                y = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None

                try:
                    GameMapManager.move_player_to(map_id, x, y)
                except Exception as e:
                    GameToastManager.add_message("切换地图出错")
                    GameLogManager.log_service_error(f"移动地图出错: {e}")
            else:
                GameToastManager.add_message(f"移动地图参数错误: {cmd_name}")
                GameLogManager.log_service_error(f"移动地图参数错误: {cmd_name}")
            return

    # def update_element_by_uuid(self, node: dict, target_uuid: str, new_text: str | int | list | dict):
    #     """
    #     根据 __node_uuid 更新元素的 text 字段
    #
    #     :param node: 嵌套的字典结构
    #     :param target_uuid: 要查找的 __node_uuid
    #     :param new_text: 要设置的新文本值
    #     :return: 是否找到并更新了元素
    #     """
    #     # 存在禁用的元素不允许获取
    #     if "disabled" in node.get("attrs"):
    #         return None
    #     # 检查当前元素是否是目标元素
    #     if node.get("attrs").get('__node_uuid') == target_uuid:
    #         node['text'] = new_text
    #         return node
    #
    #     # 如果有子元素，递归检查子元素
    #     if 'children' in node and isinstance(node['children'], list):
    #         for child in node['children']:
    #             res_node = self.update_element_by_uuid(child, target_uuid, new_text)
    #             if res_node:
    #                 return res_node
    #
    #     return None

    def __hide_callback(self):
        # 触发NPC的关闭回调
        if self.__curr_npc:
            self.__curr_npc.hide_dialog()
        # 触发开窗的回调
        if self.dialog_callback:
            self.dialog_callback({"__type": "close"})

    def close_dialog(self):
        """
        关闭对话框
        :return:
        """
        for _com in self._alone_component.values():
            _com.destroy()
        self._alone_component.clear()  # 清空组件
        game_ui: GameUI = self.gm.get("游戏UI")
        game_ui.close_surface_ui(self.dialog_key)
        self.__cached_result = None
        # if self.dialog_callback:
        #     self.dialog_callback({"__type": "close"})

    def get_val(self, dom_id: str):
        """
        获取指定id的控件值
        :param dom_id: 节点ID
        :return:
        """
        _com = self._alone_component.get(dom_id)
        if _com:
            return _com.value

        def _find(node: dict):
            if node.get("attrs").get("id") == dom_id:
                tag = node.get("tag")
                if tag in ["input", "a", "p"]:
                    return node.get("text", "")

            if node.get("children"):
                for i in node.get("children"):
                    res = _find(i)
                    if res:
                        return res

            return None

        return _find(self.__cached_result)

    def get_component_state(self, dom_id: str):
        component = self._alone_component.get(dom_id)
        if component is None:
            return None
        if hasattr(component, "get_state"):
            return component.get_state()
        return {"value": getattr(component, "value", None), "has_focus": getattr(component, "has_focus", False)}

    def visible(self):
        """
        当前开窗是否可见
        :return:
        """
        return self.__cached_result is not None

    def node_at_mouse(self, mouse_pos=None):
        """返回当前鼠标命中的对话节点, 给外部拖拽投放使用."""
        game_ui: GameUI = self.gm.get("游戏UI")
        win_sprite = game_ui.get_surface_sprite(self.dialog_key)
        if win_sprite is None or not win_sprite.get("show"):
            return None

        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()
        rect = win_sprite.get("rect")
        local_pos = (mouse_pos[0] - rect.x, mouse_pos[1] - rect.y)
        for node, gui_rect in reversed(self.__GUI_rect_list):
            if gui_rect.collidepoint(*local_pos):
                return node
        return None

    def has_focus(self):
        """当前对话框内部是否有控件正在接收键盘输入."""
        return self.__focus_node is not None

    def __listen_keyboard(self):
        if self.__listen_keyboard_callback is None:
            return self.has_close
        if callable(self.__listen_keyboard_callback):
            return bool(self.__listen_keyboard_callback())
        return bool(self.__listen_keyboard_callback)

    def set_val(self, dom_id: str, value: Any):
        """公开的控件赋值入口, 给聊天框这类常驻UI使用."""
        self._load_val({dom_id: value})
        self.update_blit = True

    def insert_text(self, dom_id: str, text: str):
        component = self._alone_component.get(dom_id)
        if component is None:
            return False
        if hasattr(component, "has_focus") and not component.has_focus and hasattr(component, "move_cursor_to_end"):
            component.move_cursor_to_end()
        if hasattr(component, "insert_text"):
            component.insert_text(text)
        else:
            value = getattr(component, "value", "") or ""
            if hasattr(component, "set_text"):
                component.set_text(f"{value}{text}")
            else:
                return False
        self.update_blit = True
        return True

    def focus(self, dom_id: str, move_cursor_to_end: bool = False):
        component = self._alone_component.get(dom_id)
        if component is None:
            return False

        from src.manager.GameEvent import GameEvent
        for _com in GameEvent.all_input_pool():
            if _com != component and hasattr(_com, "blur"):
                _com.blur()

        if hasattr(component, "has_focus"):
            component.has_focus = True
        if move_cursor_to_end and hasattr(component, "move_cursor_to_end"):
            component.move_cursor_to_end()
        elif move_cursor_to_end and hasattr(component, "cursor_index") and hasattr(component, "text"):
            component.cursor_index = len(component.text)
        if hasattr(component, "need_redraw"):
            component.need_redraw = True

        for node, _ in self.__GUI_rect_list:
            if node.get("target") == dom_id or node.get("attrs", {}).get("id") == dom_id:
                self.__focus_node = node
                break

        game_ui: GameUI = self.gm.get("游戏UI")
        win_sprite = game_ui.get_surface_sprite(self.dialog_key) if game_ui else None
        if win_sprite is not None and getattr(component, "rect", None) is not None:
            pygame.key.start_text_input()
            pygame.key.set_text_input_rect([
                win_sprite.get("rect").x + component.rect.x,
                win_sprite.get("rect").y + component.rect.y + component.rect.height,
                component.rect.width,
                component.rect.height,
            ])

        self.__has_focus = True
        self.update_blit = True
        return True

    def _load_val(self, val: Dict[str, Any]):
        """
        根据传入的字典，自动为指定 ID 的控件或节点加载值
        :param val: 格式如 {"username": "eval", "volume_slider": 0.5}
        """
        if not val or not isinstance(val, dict):
            return

        for dom_id, value in val.items():
            # 1. 首先尝试从独立组件中查找 (GameInput, GameSlider, GameCheckBox等)
            if dom_id in self._alone_component:
                component = self._alone_component[dom_id]
                # 动态调用组件的 value 设置（GameComponentBase 子类通常有 value 属性）
                try:
                    if isinstance(value, dict) and hasattr(component, "restore_state"):
                        component.restore_state(value)
                    else:
                        component.update_value(value)
                except Exception as e:
                    GameLogManager.log_service_error(f"加载组件值失败 [ID:{dom_id}]: {e}")
                continue

            # 2. 如果独立组件里没找到，则递归遍历渲染树，更新静态标签的内容
            if self.__cached_result:
                self.__update_node_text_recursive(self.__cached_result, dom_id, value)

    def __update_node_text_recursive(self, node: dict, target_id: str, new_value: Any):
        """递归查找并更新节点 text"""
        # 检查当前节点 ID
        if node.get("attrs", {}).get("id") == target_id:
            # 更新 text 字段，并确保它是字符串用于显示
            node["text"] = str(new_value)
            # 标记需要清理缓存，以便在下一次重绘时重新生成 Surface
            cache_key_p = f"ui_label_{node.get('text')}"
            cache_key_a = f"ui_link_{node.get('text')}"
            self.__ui_cache_dict.pop(cache_key_p, None)
            self.__ui_cache_dict.pop(cache_key_a, None)
            return True

        # 递归子节点
        children = node.get("children", [])
        for child in children:
            if self.__update_node_text_recursive(child, target_id, new_value):
                return True
        return False
