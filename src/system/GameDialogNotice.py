# #!/usr/bin/env python
# # -*- coding: UTF-8 -*-
# """
# @Project ：三界奇谈
# @File    ：GameDialog.py
# @IDE     ：PyCharm
# @Author  ：eval-
# @Email  ： eval-email@qq.com
# @Date    ：2025/10/25 14:21
# @Describe: 告示开窗
# """

import os.path
from typing import TYPE_CHECKING
import pygame

from src.manager.GameLogManger import GameLogManager
from uuid import uuid4
from src.system.GameToast import GameToastManager
from src.manager.SourceManager import SourceManager

if TYPE_CHECKING:
    from src.manager.GameManager import GameManager
    from src.render.GameUI import GameUI


class GameDialogNotice:
    def __init__(self, gm):
        # 基础属性
        self.rect = None
        self.gm: GameManager = gm
        self.update_blit = True

        self.__scroll_y = 0
        self.__scroll_max = 0
        self.__render_full_height = 0
        self.__cached_result = None

        self.dialog_title: pygame.Surface = None

        # 缓存一个不可变的UI, 比如p标签和 a标签, 没必要每次都要不断的生成
        self.__ui_cache_dict = {}
        self.__render_offset = []

    def show_dialog(self, dialog_path: str, render_x: int = 5, render_y: int = 40):
        """调用NPC对话"""
        self.__scroll_y = 0
        self.__cached_result = None
        self.__ui_cache_dict.clear()  # 传入新的对话内容, 清空上一轮的UI缓存
        render_x, render_y = max(render_x, 5), max(render_y, 40)
        self.__render_offset = [render_x, render_y]

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

            game_ui: GameUI = self.gm.get("游戏UI")
            dialog_sur: pygame.Surface = game_ui.get_surface_ui("对话UI")

            if self.dialog_title is None or self.dialog_title.width != int(width):
                self.dialog_title = SourceManager.ssurface_scale(
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
                                                          "drag": True,
                                                          "drag_rect": ["auto", "auto", "-25px", 30],
                                                          "bag_offset": pygame.Rect([25, 180, 200, 172]),
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
        node_text = node.get("text")
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
                        cbg_sur = SourceManager.ssurface_scale(cbg_sur, [_cbg_w, _cbg_h])
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
                # 跳过不可视区域
                self.blit_with_clipping(dialog_sur, text_surface, render_x, node_rect.y, view_height)

                render_y += text_surface.height + 10

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
                img_surface = self.__ui_cache_dict.get(f"ui_img_{curr_style["src"]}")
                if img_surface is None:
                    img_surface = SourceManager.load(f"{SourceManager.cfg_task_path}/{curr_style['src']}")
                    self.__ui_cache_dict[f"ui_img_{curr_style["src"]}"] = img_surface

                    if curr_style.get("img-size"):
                        img_surface = SourceManager.ssurface_scale(img_surface, curr_style.get("img-size", [0, 0]))

                # 跳过不可视区域
                self.blit_with_clipping(dialog_sur, img_surface, render_x, render_y, view_height)
                render_y += img_surface.height

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
                                            img_bak = SourceManager.ssurface_scale(img_surface,
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

    def close_dialog(self):
        """
        关闭对话框
        :return:
        """
        game_ui: GameUI = self.gm.get("游戏UI")
        game_ui.close_surface_ui("对话UI")
