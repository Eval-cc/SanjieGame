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
from typing import TYPE_CHECKING, Dict
import pygame

from src.lib.GameEnum import ShopType
from src.manager.GameLogManger import GameLogManager
from uuid import uuid4
from src.manager.GameMapManager import GameMapManager
from src.system.GameToast import GameToastManager
from src.manager.SourceManager import SourceManager

if TYPE_CHECKING:
    from src.manager.GameManager import GameManager
    from src.render.GameUI import GameUI
    from src.character.NPC import NpcSprite


class GameDialog:
    def __init__(self, gm):
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

        # 缓存一个不可变的UI, 比如p标签和 a标签, 没必要每次都要不断的生成
        self.__ui_cache_dict = {}
        self.__render_offset = []
        # 触发UI里面的点击事件之后, 触发的回调
        self.dialog_callback = None

    def show_dialog(self, dialog_path: str, npc=None, render_x: int = 5, render_y: int = 60, dialog_callback=None):
        """调用NPC对话"""
        self.__scroll_y = 0
        self.__cached_result = None
        self.__ui_cache_dict.clear()  # 传入新的对话内容, 清空上一轮的UI缓存
        self.__curr_npc = npc
        render_x, render_y = max(render_x, 5), max(render_y, 60)
        self.__render_offset = [render_x, render_y]
        self.__GUI_rect_list.clear()  # 清空点击的坐标信息

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
            if bool(width) ^ bool(height):
                GameToastManager.add_message(f"非法的对话文件")
                GameLogManager.log_service_debug(f"非法的对话文件")
                return
            # 指定回调方法
            self.dialog_callback = dialog_callback

            game_ui: GameUI = self.gm.get("游戏UI")
            dialog_sur: pygame.Surface = game_ui.get_surface_ui("对话UI")

            if self.dialog_title is None or self.dialog_title.width != int(width):
                self.dialog_title = SourceManager.surface_cale(
                    SourceManager.load(f"{SourceManager.ui_system_path}/dialog_title.png"),
                    [int(width), 32]).convert_alpha()

            dialog_bg = pygame.Surface((int(width), int(height) - 30), pygame.SRCALPHA)
            dialog_bg.fill(self.gm.game_font.hex_color_to_rgb("#000000"))
            dialog_bg.set_alpha(170)

            if dialog_sur is None:
                dialog_sur = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)
                dialog_sur.fill((0, 0, 0, 0))
                dialog_sur.blit(self.dialog_title, (2, 0))
                dialog_sur.blit(dialog_bg, (0, 30))
                pygame.draw.rect(dialog_sur, (self.gm.game_font.hex_color_to_rgb("#228B22")),
                                 (0, 30, int(width), int(height) - 30), 1)

                game_ui.load_system_ui(
                    f"{SourceManager.ui_system_path}/ui-button.png",
                    [240, 20],
                    options=
                    {
                        "name": "对话UI_按钮",
                        "frame": {
                            "size": 60,
                            "count": 2,
                            "index": 0,
                            "loc": (160, 363),
                        }
                    }, )

                [_, rect, _] = game_ui.load_system_ui(dialog_sur,
                                                      [int(width), int(height)],
                                                      "middle",
                                                      {
                                                          "name": "对话UI",
                                                          "mouse_down": self.mouse_down,
                                                          # "mouse_up": self.mouse_up,
                                                          # "mouse_move": self.mouse_move,
                                                          # "mouse_out": self.mouse_out,
                                                          # "mouse_double_click": self.mouse_double_click,
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
                                                          "listen_keyboard": lambda: True,
                                                          "hide_callback": self.__hide_callback
                                                          # "un_allow": True  # 显示此UI的时候 禁止其他操作, 除了另一个UI
                                                      }, sort=True)
                self.rect = rect
            else:
                """宽度和当前UI管理的不一样了?  那就重新加载一下"""
                dialog_sur = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)
                dialog_sur.blit(self.dialog_title, (2, 0))
                dialog_sur.blit(dialog_bg, (0, 30))

                self.rect.width = int(width)
                self.rect.height = int(height)

                pygame.draw.rect(dialog_sur, (self.gm.game_font.hex_color_to_rgb("#228B22")),
                                 (0, 30, int(width), int(height) - 30), 1)

            visible_height = dialog_sur.get_height()

            self.__cached_result = result  # 缓存结构
            actual_render_end = self.create_node(dialog_sur, self.__cached_result, render_x, render_y)
            self.__render_full_height = actual_render_end
            self.__scroll_max = max(0, self.__render_full_height - dialog_sur.get_height() + 20)

            game_ui.set_surface_ui("对话UI", dialog_sur)
            if self.__scroll_max > 0:
                scrollbar_x = dialog_sur.get_width() - 8
                scrollbar_height = max(20, (visible_height / (self.__render_full_height + 1)) * visible_height)
                scrollbar_y = int((self.__scroll_y / self.__scroll_max) * (visible_height - scrollbar_height))
                pygame.draw.rect(dialog_sur, (100, 100, 100), (scrollbar_x, 30 + scrollbar_y, 6, scrollbar_height))

            if game_ui.get_surface_show("对话UI"):
                return

            game_ui.change_ui_layer("对话UI", center=True)
            self.update_blit = True  # 触发页面重绘

    def mouse_down(self):
        self.__has_focus = False
        mouse_pos = pygame.mouse.get_pos()
        game_ui: GameUI = self.gm.get("游戏UI")
        bag_sprite = game_ui.get_surface_sprite("对话UI")  # 需要加上UI的偏移

        # 小于拖拽区域高度的只能是关闭按钮了
        if mouse_pos[1] <= int(bag_sprite.get("rect").y) + int(bag_sprite.get("drag_rect")[3]):
            x_offset = int(bag_sprite.get("drag_rect")[2]) - bag_sprite.get("rect").width
            if mouse_pos[0] > int(bag_sprite.get("rect").x) + int(bag_sprite.get("rect").width) + x_offset:
                self.close_dialog()
                return

        for [node, gui_rect] in self.__GUI_rect_list:
            if gui_rect.collidepoint(mouse_pos[0] - bag_sprite.get("rect").x, mouse_pos[1] - bag_sprite.get("rect").y):
                if self.dialog_callback:
                    self.dialog_callback(node)
                    return
                if node.get('tag') == "a":
                    self.__cached_result = None
                    href = node.get('attrs').get("href", "")
                    hash_index = href.find("#")
                    if hash_index != -1:  # 如果找到 #
                        href = href[hash_index + 1:]  # 直接切片取 # 之后的部分
                    self.show_dialog(href)
                    self.update_blit = True
                    return
                elif node.get('tag') == "button":
                    self.__exec_event(node.get("attrs").get("data-client"))
                    self.update_blit = True
                    return
                elif node.get('tag') == "input":
                    if node.get("attrs").get("disabled"):
                        return
                    self.__has_focus = True
                    node["attrs"]["focus"] = True
                    self.__focus_node = node
                    # 设置候选框的位置
                    inp_offset = [
                        bag_sprite.get("rect").x + gui_rect.x,
                        bag_sprite.get("rect").y + gui_rect.y + gui_rect.height,
                        200,
                        50
                    ]
                    pygame.key.set_text_input_rect(inp_offset)
                    self.update_blit = True
                    return

                GameLogManager.log_service_debug(f"点击:{node.get('tag')}")
                # self.update_blit = True
                return

    # def mouse_up(self):
    #     pass
    #
    # def mouse_move(self):
    #     pass
    #
    # def mouse_out(self):
    #     pass
    #
    # def mouse_double_click(self):
    #     pass

    def mouse_scroll_wheel_down(self):
        """
        UI的滚轮向下事件
        :return:
        """
        if self.__scroll_y < self.__scroll_max:
            self.__has_focus = True
            self.__GUI_rect_list.clear()
            self.__scroll_y = min(self.__scroll_y + 30, self.__scroll_max)
            self.update_blit = True
            self.__has_scroll_wheel = True

    def mouse_scroll_wheel_up(self):
        """
        UI的滚轮向上事件
        :return:
        """
        if self.__scroll_y > 0:
            self.__has_focus = True
            self.__GUI_rect_list.clear()
            self.__scroll_y = max(self.__scroll_y - 30, 0)
            self.update_blit = True
            self.__has_scroll_wheel = True

    def key_text(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        key_event = event.get("event")

        target_uuid = self.__focus_node.get("attrs").get("__node_uuid")
        text = self.__focus_node.get("text", "")
        if text is None:
            text = ""
        new_text = f"{text}{key_event.text}"

        # 调用函数进行更新
        updated = self.update_element_by_uuid(self.__cached_result, target_uuid, new_text)
        if updated:
            self.__cursor_index += len(key_event.text)
            self.__focus_node["text"] = str(new_text)
            self.update_blit = True
            self.__has_focus = True

    # def key_up(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
    #     """键盘抬起事件"""
    #     pass

    def key_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        if self.__focus_node:
            # 要更新的 __node_uuid 和新文本
            target_uuid = self.__focus_node.get("attrs").get("__node_uuid")
            new_text = self.__focus_node.get("text", "")
            if new_text is None:
                new_text = ""
            if hasattr(event.get("event"), "text"):
                return

            match event.get("key_name"):
                case "escape":
                    self.__has_focus = False
                    self.__focus_node["attrs"]["focus"] = False
                    self.update_blit = True
                    self.__has_focus = True
                    return
                # 制表符
                case "tab":
                    new_text = "﹒" * 4
                    self.__cursor_index += 4
                # 左移
                case "left":
                    self.__cursor_index = max(self.__cursor_index - 1, 0)
                    self.blink_tick = 0
                    self.blink_show = True
                    self.update_blit = True
                    self.__has_focus = True
                    return
                # 右移
                case "right":
                    self.__cursor_index = min(len(new_text), self.__cursor_index + 1)
                    self.blink_tick = 0
                    self.blink_show = True
                    self.update_blit = True
                    self.__has_focus = True
                    return

                # 退格键,删除光标之前的元素
                case "backspace":
                    if self.__cursor_index > 0:  # 确保光标不在最前面
                        # 删除光标前一个字符
                        new_text = new_text[:self.__cursor_index - 1] + new_text[self.__cursor_index:]
                        self.__cursor_index -= 1  # 光标前移
                        self.blink_tick = 0
                        self.blink_show = True
                    else:
                        return
                # 撤销后一位元素
                case "delete":
                    if self.__cursor_index < len(new_text):  # 确保光标不在最后面
                        # 删除光标后一个字符
                        new_text = new_text[:self.__cursor_index] + new_text[self.__cursor_index + 1:]
                        # 光标位置不需要移动
                        self.blink_tick = 0
                        self.blink_show = True
                    else:
                        return

                case _:
                    # self.__cursor_index += 1
                    return

            # 调用函数进行更新
            updated = self.update_element_by_uuid(self.__cached_result, target_uuid, new_text)
            if updated:
                self.__focus_node["text"] = str(new_text)
                self.update_blit = True
                self.__has_focus = True

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

        game_ui.set_surface_ui("对话UI", dialog_sur)

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
        node_text = node.get("text","")
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
        __el_padding = [0, 0, 0, 0]  # 内边距 -- 仅支持单个边距以及四个方向的边距. 其他格式的一律忽略
        match el_padding:
            case [p]:  # 单值 → 复制 4 份
                __el_padding = [int(p)] * 4
            case [a, b, c, d]:  # 4 值 → 直接转换
                __el_padding = [int(a), int(b), int(c), int(d)]

        render_x += __el_padding[3]
        render_y += __el_padding[0]

        def __render_bg_img():
            if "background-image" in attrs:
                cbg_path: str = attrs.get("background-image")
                clip_path: str = attrs.get("clip-path")  # 是否存在裁剪属性
                curr_style["background-image"] = cbg_path
                curr_style["background-image"] = clip_path
                if cbg_path.startswith("#ROOT_S"):
                    cbg_path = cbg_path.replace("#ROOT_S", SourceManager.ui_system_path)
                _cbg_w = max(int(attrs.get("width", "0")) - __el_padding[1], 0)
                _cbg_h = max(int(attrs.get("height", "0")) - __el_padding[2], 0)
                cbg_sur = SourceManager.load(cbg_path)
                if cbg_sur:
                    if clip_path:
                        clip_path_arr = [int(i) for i in clip_path.split(" ")]
                        clip_x = 0 if clip_path_arr[0] == -1 else clip_path_arr[0]
                        clip_y = 0 if clip_path_arr[1] == -1 else clip_path_arr[1]
                        clip_w = cbg_sur.width if clip_path_arr[2] == -1 else clip_path_arr[2]
                        clip_h = cbg_sur.height if clip_path_arr[3] == -1 else clip_path_arr[3]
                        cbg_sur = cbg_sur.subsurface((clip_x, clip_y, clip_w - clip_x, clip_h - clip_y))
                    if _cbg_w > 0 and _cbg_h > 0:
                        cbg_sur = SourceManager.surface_cale(cbg_sur, [_cbg_w, _cbg_h])
                    else:
                        _cbg_w, _cbg_h = cbg_sur.get_size()
                    if dom_id == "app":  # 根节点不跟随滚动.
                        dialog_sur.blit(cbg_sur, (0, 30))
                    else:

                        self.blit_with_clipping(dialog_sur, cbg_sur, render_x, render_y, view_height)
                        # dialog_sur.blit(cbg_sur, (render_x, render_y))
                        curr_style["background-color"] = None  # 优先背景图片
                return _cbg_w, _cbg_h
            return 0, 0

        # 渲染bg
        __render_bg_img()

        # 为每个节点生成一个唯一的节点id
        if "__node_uuid" not in attrs:
            attrs["__node_uuid"] = uuid4().hex[:8]
            node["attrs"] = attrs

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

        elif tag == "button":
            if node_text:
                game_ui: GameUI = self.gm.get("游戏UI")
                params = game_ui.get_surface_sprite("对话UI_按钮")
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

                btn_surface = self.__ui_cache_dict.get(f"ui_btn-bg_{node_text}")
                if btn_surface is None:
                    btn_surface = SourceManager.surface_cale(params["surface"],
                                                             [text_surface.width + 20, frame_size // 2.5])
                btn_rect = btn_surface.get_rect()
                btn_rect.x = render_x
                btn_rect.y = render_y

                node_rect = text_surface.get_rect()
                node_rect.x = render_x
                node_rect.y = render_y
                node_rect.center = btn_rect.center
                self.blit_with_clipping(dialog_sur, btn_surface, btn_rect.x, btn_rect.y, view_height)
                self.blit_with_clipping(dialog_sur, text_surface, node_rect.x, node_rect.y, view_height)
                self.__GUI_rect_list.append([node, btn_rect])
                render_y += text_surface.height + 20

        elif tag == "img":
            if not curr_style["src"]:
                img_surface = self.__ui_cache_dict.get(f"ui_img_none")
                if img_surface is None:
                    img_surface = pygame.Surface((50, 50))
                    img_surface.fill((200, 200, 200))
                    self.__ui_cache_dict["ui_img_none"] = img_surface

                # 跳过不可视区域
                self.blit_with_clipping(dialog_sur, img_surface, render_x, render_y, view_height)
                render_y += img_surface.height
            else:
                img_url = curr_style["src"]
                img_surface = self.__ui_cache_dict.get(f"ui_img_{curr_style["src"]}")
                if img_surface is None:
                    if img_url == "{{NPC_AVATAR}}":
                        # 指定了用当前NPC的头像, 但是当前NPC又没有配置头像的情况下, 直接跳出 不渲染img标签
                        if not hasattr(self.__curr_npc, "avatar") or self.__curr_npc.avatar is None:
                            return render_y
                        img_surface = self.__curr_npc.avatar
                    else:
                        img_surface = SourceManager.load(f"{SourceManager.cfg_task_path}/{curr_style['src']}")
                        self.__ui_cache_dict[f"ui_img_{curr_style["src"]}"] = img_surface

                    if curr_style.get("img-size"):
                        img_surface = SourceManager.surface_cale(img_surface, curr_style.get("img-size", [0, 0]))

                # 跳过不可视区域
                self.blit_with_clipping(dialog_sur, img_surface, render_x, render_y, view_height)
                render_y += img_surface.height

        elif tag == "input":
            input_width = int(attrs.get("width", 160))
            input_height = int(attrs.get("height", 28))

            if attrs.get("width") is None or attrs.get("height") is None:
                i_w, i_h = __render_bg_img()
                if i_w > 0:
                    input_width = i_w
                if i_h > 0:
                    input_height = i_h

            is_disabled = "disabled" in attrs
            is_focused = node is self.__focus_node

            bg_color = "#F0F0F0" if is_disabled else "#FFFFFF"
            border_color = "#999999" if is_disabled else "#000000"
            text_color = "#AAAAAA" if is_disabled else curr_style["color"]

            font_size = curr_style["font-size"]
            font = self.gm.game_font

            text = node.get("text", "")
            if is_focused and not is_disabled and text == "请输入内容":
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
                    li_surface = pygame.Surface((li_width, li_height), pygame.SRCALPHA)
                    if "background-color" in li_attrs:
                        li_surface.fill(self.gm.game_font.hex_color_to_rgb(li_attrs["background-color"]))

                    # 初始化渲染位置 -- padding的顺序和 html的规范保持一致. 上右下左
                    element_x = 5 + __li_padding[3]
                    element_y = 5 + __li_padding[0]
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

                                if img_src:
                                    # 加载图片
                                    img_surface = self.__ui_cache_dict.get(f"ui_img_{img_src}")
                                    if img_surface is None:
                                        img_surface = SourceManager.load(f"{SourceManager.cfg_task_path}/{img_src}")
                                        self.__ui_cache_dict[f"ui_img_{img_src}"] = img_surface

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
                                            img_bak = SourceManager.surface_cale(img_surface,
                                                                                 [round(img_surface.width * prop_w),
                                                                                  li_height])
                                            img_rect.y = 0
                                            element_x += img_bak.width + 5 + __li_padding[3]
                                            li_surface.blit(img_bak, img_rect)
                                        else:
                                            li_surface.blit(img_surface, img_rect)
                                            element_x += img_rect.width + 5
                                        max_line_height = max(max_line_height, img_rect.height)

                            # 检查是否需要换行
                            if element_x > li_width - 5:
                                element_x = 5 + __li_padding[3]
                                element_y += max_line_height + 5 + __li_padding[0]
                                max_line_height = 0

                    # 将li渲染到dialog_sur上
                    self.blit_with_clipping(dialog_sur, li_surface, current_x, current_y, view_height)

                    # 记录li的位置用于点击检测
                    li_rect = pygame.Rect(current_x, current_y, li_width, li_height)
                    self.__GUI_rect_list.append([child, li_rect])

                    # 更新位置
                    current_x += li_width + li_margin
                    max_row_height = max(max_row_height, li_height)

            # 更新render_y为ul的底部位置
            render_y = current_y + max_row_height + margin

        else:
            for child in children:
                render_y = self.create_node(dialog_sur, child, render_x, render_y, curr_style,
                                            parent_color=curr_style["color"])

        return render_y

    def __exec_event(self, cmd_name: str):
        """触发对话开窗的事件命令"""
        game_ui: GameUI = self.gm.get("游戏UI")
        # 购买
        if cmd_name == "client://shop&buy":
            game_ui.change_ui_layer("对话UI")
            self.gm.shop_system.add_shops(self.__curr_npc.shop_item, self.__curr_npc.name, ShopType.BUY)
            return

        # 出售
        if cmd_name == "client://shop&sell":
            game_ui.change_ui_layer("对话UI")
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
                    GameMapManager.change_map(map_id, x, y)
                except Exception as e:
                    GameToastManager.add_message("切换地图出错")
                    GameLogManager.log_service_error(f"移动地图出错: {e}")
            else:
                GameToastManager.add_message(f"移动地图参数错误: {cmd_name}")
                GameLogManager.log_service_error(f"移动地图参数错误: {cmd_name}")
            return

    def update_element_by_uuid(self, node: dict, target_uuid: str, new_text: str | int | list | dict):
        """
        根据 __node_uuid 更新元素的 text 字段

        :param node: 嵌套的字典结构
        :param target_uuid: 要查找的 __node_uuid
        :param new_text: 要设置的新文本值
        :return: 是否找到并更新了元素
        """
        # 存在禁用的元素不允许获取
        if "disabled" in node.get("attrs"):
            return None
        # 检查当前元素是否是目标元素
        if node.get("attrs").get('__node_uuid') == target_uuid:
            node['text'] = new_text
            return node

        # 如果有子元素，递归检查子元素
        if 'children' in node and isinstance(node['children'], list):
            for child in node['children']:
                res_node = self.update_element_by_uuid(child, target_uuid, new_text)
                if res_node:
                    return res_node

        return None

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
        game_ui: GameUI = self.gm.get("游戏UI")
        game_ui.close_surface_ui("对话UI")
        # if self.dialog_callback:
        #     self.dialog_callback({"__type": "close"})
