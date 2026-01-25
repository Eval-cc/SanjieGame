#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：GameFont.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/2/14 下午10:00 
@Describe: 
"""

import pygame
import pygame.freetype
import re
import os
from typing import Dict, List, Tuple

from src.manager.GameLogManger import GameLogManager
from src.manager.SourceManager import SourceManager

# 设置环境变量 SDL_IME_SHOW_UI 的值为 1,显示文本候选
os.environ["SDL_IME_SHOW_UI"] = "1"


class GameFont:
    """全局游戏字体管理器"""
    # 字体对象字典，按名称存储字体
    __font_dict: Dict[str, pygame.freetype.Font] = {}
    # 渲染的对象字典
    __surface_list: Dict[str, pygame.Surface] = {}

    __default_font_path: List[str] = []

    win_main: None


    @classmethod
    def instance(cls):
        return cls

    @staticmethod
    def load(win_main):
        """初始化字体管理器"""
        pygame.font.init()
        pygame.freetype.init()
        GameFont.win_main = win_main
        GameFont.__default_font_path = [f"{SourceManager.cfg_root_path}/fonts/{f}.ttf" for f in [
            "AaBanRuoKaiShuJiaCu（JianFan）-2",
            "FZY4JW"
        ]]

    @staticmethod
    def __get_target_text(text: str, font_size: int = None, font_color: tuple | str = None, baking: bool = False,
                          mask_color: tuple | str = (0, 0, 0)):
        if type(font_color) == "str":
            font_color = GameFont.hex_color_to_rgb(font_color)
        if font_size and font_color:
            sur = GameFont.__surface_list.get(f"{text}_{font_size}_{font_color}")
            if sur:
                return sur
            else:
                if baking:
                    GameFont.add(text, font_size=font_size, font_color=font_color, mask_color=mask_color)
                    return GameFont.__get_target_text(text, font_size, font_color, False)
        for sur in GameFont.__surface_list.values():
            if sur.get("text") == text:
                return sur
        return None

    @staticmethod
    def parse_color_string(format_str: str):
        """格式化文本, 把十六进制的颜色转为 RGB格式"""
        pattern = re.compile(r"(?:\[#([0-9A-Fa-f]{6}|end)])?([^\[#]+)")
        result = []

        current_color = None
        for match in pattern.finditer(format_str):
            color_tag, text = match.groups()
            if color_tag:
                if color_tag.lower() == "end":
                    current_color = None
                else:
                    current_color = GameFont.hex_color_to_rgb(f"#{color_tag}")
            result.append({
                "label": text,
                "color": current_color
            })

        return result

    @staticmethod
    def _hex_color_to_rgb__deprecate(hex_str: str) -> tuple | str:
        """将十六进制的颜色转为 rgb，如果输入不是以#开头的6位十六进制颜色字符串，则直接返回原参数,,
        弃用API
        """
        if hex_str is None:
            return 0, 0, 0
        if not isinstance(hex_str, str) or not hex_str.startswith('#') or len(hex_str) != 7:
            return hex_str

        # 将十六进制的颜色转为 rgb
        r = int(hex_str[1:3], 16)  # 提取R部分并转为10进制
        g = int(hex_str[3:5], 16)  # 提取G部分
        b = int(hex_str[5:7], 16)  # 提取B部分

        return r, g, b

    @staticmethod
    def hex_color_to_rgb(color_str: str) -> tuple[int, int, int] | str:
        """
        将颜色字符串转为 RGB 元组，支持以下格式（大小写不敏感）：
        - 十六进制颜色（如 `#FF0000` 或 `#ff0000`）
        - RGB 字符串（如 `rgb(255,0,0)` 或 `RGB(255, 0, 0)`）

        如果输入格式无效，则返回原字符串。

        Args:
            color_str: 颜色字符串（`#RRGGBB` 或 `rgb(R,G,B)`）

        Returns:
            RGB 元组 `(R, G, B)`，或原字符串（如果输入无效）
        """
        if color_str is None:
            return 0, 0, 0

        if not isinstance(color_str, str):
            return color_str

        # 统一转换为小写（或大写）以支持大小写不敏感
        lower_str = color_str.lower()

        # 1. 检查是否是十六进制颜色（#RRGGBB）
        if lower_str.startswith('#') and len(lower_str) == 7:
            try:
                r = int(lower_str[1:3], 16)
                g = int(lower_str[3:5], 16)
                b = int(lower_str[5:7], 16)
                return r, g, b
            except ValueError:
                return color_str

        # 2. 检查是否是 RGB 字符串（rgb(R,G,B)），支持大小写不敏感
        rgb_match = re.match(
            r'^rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$',
            lower_str.strip(),
            re.IGNORECASE  # 忽略大小写
        )
        if rgb_match:
            try:
                r, g, b = map(int, rgb_match.groups())
                if all(0 <= x <= 255 for x in (r, g, b)):
                    return r, g, b
            except ValueError:
                pass

        # 3. 如果都不匹配，返回原字符串
        return color_str

    @staticmethod
    def add(text: str, font_size: int = 13, font_color: tuple | str = (255, 255, 255), font_path: str = None,
              mask_color: tuple | str = (0, 0, 0)):
        """将字体加载并添加到全局字体管理器
        弃用API
        """
        if not pygame.freetype.get_init():
            raise Exception("请调用[GameFont.load()]方法,初始化字体类")
        if font_path is None:
            font_path = GameFont.__default_font_path[1]

        font_color = GameFont.hex_color_to_rgb(font_color)

        font_surface = GameFont.__font_dict.get(f"{text}_{font_size}_{font_color}_{font_path}")
        if font_surface:
            # 跳过重复添加的
            return
        font_surface = pygame.freetype.Font(font_path, font_size)
        font_surface.vertical = False
        GameFont.__font_dict[f"{text}_{font_size}_{font_color}_{font_path}"] = font_surface

        font_sur, rect = font_surface.render(text, font_color)
        rect.bottom = font_size
        mask_color = GameFont.hex_color_to_rgb(mask_color)
        GameFont.__surface_list[f"{text}_{font_size}_{font_color}"] = {
            "text": text,
            "surface": font_sur,
            "mask_surface": font_surface.render(text, mask_color)[0],
            "mask_color": mask_color,
            "rect": rect,
            "font_path": font_path,
            "font_color": font_color
        }

    # @staticmethod
    # def add(text: str, font_size: int = 13, font_color: tuple | str = (255, 255, 255), font_path: str = None,
    #         mask_color: tuple | str = (0, 0, 0)):
    #     """将字体加载并添加到全局字体管理器 - 优化版：字符级烘焙"""
    #     if not pygame.freetype.get_init():
    #         raise Exception("请调用[GameFont.load()]方法,初始化字体类")
    #     if font_path is None:
    #         font_path = GameFont.__default_font_path[1]
    #
    #     font_color = GameFont.hex_color_to_rgb(font_color)
    #     mask_color = GameFont.hex_color_to_rgb(mask_color)
    #
    #     # 检查是否已缓存整个文本
    #     text_key = f"{text}_{font_size}_{font_color}_{font_path}"
    #     if text_key in GameFont.__font_dict:
    #         return
    #
    #     # 获取或创建字体对象
    #     font_key = f"{font_path}_{font_size}"
    #     if font_key not in GameFont.__font_dict:
    #         font_surface = pygame.freetype.Font(font_path, font_size)
    #         font_surface.vertical = False
    #         GameFont.__font_dict[font_key] = font_surface
    #     else:
    #         font_surface = GameFont.__font_dict[font_key]
    #
    #     # 烘焙每个字符（避免重复烘焙）
    #     for char in text:
    #         char_key = f"{char}_{font_size}_{font_color}_{font_path}"
    #         if char_key not in GameFont.__surface_list:
    #             char_sur, char_rect = font_surface.render(char, font_color)
    #             char_mask_sur, _ = font_surface.render(char, mask_color)
    #
    #             GameFont.__surface_list[char_key] = {
    #                 "text": char,
    #                 "surface": char_sur,
    #                 "mask_surface": char_mask_sur,
    #                 "mask_color": mask_color,
    #                 "rect": char_rect,
    #                 "font_path": font_path,
    #                 "font_color": font_color
    #             }
    #
    #     # 同时缓存整个文本（保持向后兼容）
    #     text_sur, text_rect = font_surface.render(text, font_color)
    #     text_mask_sur, _ = font_surface.render(text, mask_color)
    #
    #     GameFont.__font_dict[text_key] = font_surface
    #     GameFont.__surface_list[f"{text}_{font_size}_{font_color}"] = {
    #         "text": text,
    #         "surface": text_sur,
    #         "mask_surface": text_mask_sur,
    #         "mask_color": mask_color,
    #         "rect": text_rect,
    #         "font_path": font_path,
    #         "font_color": font_color
    #     }

    @staticmethod
    def get_text_size(text: str):
        """获取字体尺寸"""
        sur = GameFont.__get_target_text(text)
        if sur is None: return [0, 0]
        return [sur["rect"].width, sur["rect"].height]

    @staticmethod
    def render_line_text(text: str, x: int, y: int, baking: bool = False, font_color: tuple | str = (255, 255, 255),
                         mask_color: tuple | str = (0, 0, 0)):
        """渲染单行文本, 请先提前加载"""
        surface = GameFont.__get_target_text(text)
        t_color = GameFont.hex_color_to_rgb(font_color)
        if surface is None:
            if not baking:
                GameLogManager.log_service_debug(f"未烘焙的文本:{text}")
                return
            # 开启了强制烘焙
            GameFont.add(text, mask_color=mask_color, font_color=t_color)
            surface = GameFont.__get_target_text(text)
        surface["rect"].x = x
        surface["rect"].y = y
        GameFont.win_main.blit(surface["mask_surface"], [x - 1, y - 1])
        GameFont.win_main.blit(surface["mask_surface"], [x + 1, y + 1])
        GameFont.win_main.blit(surface["surface"], surface["rect"])

    @staticmethod
    def render_multiple_text(text: str, x: int, y: int, width: int, font_size: int = 13, baking: bool = False):
        """渲染多行文本, 请先提前烘焙"""
        GameFont.render_multiple_text_by_max_height(text, x, y, width, GameFont.win_main.width, font_size, baking)

    @staticmethod
    def render_multiple_text_by_max_height(text: str, x: int, y: int, width: int, max_height: int,
                                           font_size: int = 13, baking: bool = False,
                                           mask_color: tuple | str = (0, 0, 0)):
        """
        高性能版本：按最大高度直接渲染多行文本到窗口，不生成中间 Surface。
        支持显式换行符 \n，并优化性能（使用宽度缓存）。
        """
        if not isinstance(text, str):
            text = str(text)

        render_x = x
        render_y = y
        current_line = ''
        ch_h = font_size  # 默认字体高度
        width_cache: dict[str, int] = {}

        for ch in text:
            if ch == '\n':
                # 显式换行：渲染当前行，跳行
                if current_line:
                    GameFont.render_line_text(current_line, x, render_y, baking, mask_color)
                render_y += ch_h
                if render_y + ch_h > y + max_height:
                    return
                current_line = ''
                render_x = x
                continue

            # 获取字符宽度（使用缓存）
            if ch not in width_cache:
                ch_w, ch_h = GameFont.get_text_size(ch)
                if ch_w == 0:
                    ch_w = ch_h = font_size
                width_cache[ch] = ch_w
            else:
                ch_w = width_cache[ch]

            # 判断是否超出行宽
            if render_x + ch_w > x + width:
                # 自动换行
                if current_line:
                    GameFont.render_line_text(current_line, x, render_y, baking, mask_color)
                render_y += ch_h
                if render_y + ch_h > y + max_height:
                    return
                current_line = ch
                render_x = x + ch_w
            else:
                current_line += ch
                render_x += ch_w

        # 渲染最后一行
        if current_line and render_y + ch_h <= y + max_height:
            GameFont.render_line_text(current_line, x, render_y, baking, mask_color)

    @staticmethod
    def get_text_surface_line(text: str, baking: bool = False, font_size: int = 13,
                              font_color: tuple | str = (255, 255, 255),
                              bolder: bool = False, mask_color: tuple | str = (0, 0, 0)):
        """返回surface给调用处"""
        if type(text) != str:
            text = str(text)

        max_font_wight = font_size
        max_font_height = font_size
        for t in text:
            font_w, font_h = GameFont.get_text_size(t)
            max_font_height = max(max_font_height, font_h)
            max_font_wight = max(max_font_wight, font_w)

        render_x = 0
        render_y = 0
        text_surface = pygame.Surface((max_font_wight * len(text), max_font_height), pygame.SRCALPHA)

        text_arr = GameFont.parse_color_string(text)
        for t in text_arr:
            if t.get("color") is None:
                t["color"] = GameFont.hex_color_to_rgb(font_color)
            t_label = t.get("label")
            t_color = t.get("color")

            surface = GameFont.__get_target_text(t_label, font_size, t_color, baking)
            if surface is None:
                if not baking:
                    GameLogManager.log_service_debug(f"未烘焙的文本:{t_label}")
                    return text_surface
                # 开启了强制烘焙
                GameFont.add(t_label, font_size=font_size, font_color=t_color, mask_color=mask_color)
                surface = GameFont.__get_target_text(t_label, font_size, t_color, baking)

            vertical_offset = (max_font_height - surface["surface"].get_height()) // 2
            if bolder:
                text_surface.blit(surface["mask_surface"], [render_x - 1, render_y - 1 + vertical_offset])
                text_surface.blit(surface["mask_surface"], [render_x + 1, render_y + 1 + vertical_offset])

            text_surface.blit(surface["surface"], (render_x, render_y + vertical_offset))
            render_x += GameFont.get_text_size(t_label)[0]

        return text_surface

    @staticmethod
    def get_multiple_text_DEPRECATE(text: str, width: int, height: int, baking: bool = False, font_size: int = 13,
                                    font_color: tuple | str = (255, 255, 255), bolder: bool = False,
                                    mask_color: tuple | str = (0, 0, 0)):
        """ @:remark 请注意,该API已经废弃 """
        if type(text) != str:
            text = str(text)
        max_font_wight = font_size
        max_font_height = font_size

        for t in text:
            font_w, font_h = GameFont.get_text_size(t)
            max_font_height = max(max_font_height, font_h)
            max_font_wight = max(max_font_wight, font_w)

        render_x = 0
        render_y = 0
        text_surface = pygame.Surface((width, height), pygame.SRCALPHA)

        text_arr = GameFont.parse_color_string(text)
        for ta in text_arr:
            if ta.get("color") is None:
                ta["color"] = GameFont.hex_color_to_rgb(font_color)
            t_label = ta.get("label")
            t_color = ta.get("color")

            for t in t_label:
                if t_label.find("从真封神借来的武器") >= 0:
                    pass
                surface = GameFont.__get_target_text(t, font_size, t_color, baking)
                if surface is None:
                    if not baking:
                        GameLogManager.log_service_debug(f"未烘焙的文本:{t}")
                        return text_surface
                    # 开启了强制烘焙
                    GameFont.add(t, font_size=font_size, font_color=t_color, mask_color=mask_color)
                    surface = GameFont.__get_target_text(t, font_size, t_color, baking)

                if render_x >= width - max_font_wight:
                    render_x = 0
                    render_y += max_font_height

                if bolder:
                    text_surface.blit(surface["mask_surface"], [render_x - 1, render_y - 1])
                    text_surface.blit(surface["mask_surface"], [render_x + 1, render_y + 1])

                vertical_offset = (max_font_height - surface["surface"].get_height())
                text_surface.blit(surface["surface"], (render_x, render_y + vertical_offset))
                render_x += max_font_wight
        return text_surface

    @staticmethod
    def get_multiple_text(text: str, width: int, height: int, baking: bool = False, font_size: int = 13,
                          font_color: tuple | str = (255, 255, 255), bolder: bool = False,
                          mask_color: tuple | str = (0, 0, 0)):
        """
        渲染多行文本，使用实际宽度判断换行位置，支持烘焙与多色
        :return: 渲染好的 pygame.Surface 对象
        """
        if not isinstance(text, str):
            text = str(text)

        text_arr = GameFont.parse_color_string(text)
        current_line = ''
        current_color = font_color  # 默认颜色

        render_text_list: list[Tuple[str, tuple]] = []  # 每行的内容和颜色：[(line_text, color)]

        for ta in text_arr:
            t_color = ta.get("color") or GameFont.hex_color_to_rgb(font_color)
            t_label = ta.get("label")

            for char in t_label:
                test_line = current_line + char
                # 用实际渲染宽度判断是否换行
                line_surface = GameFont.get_text_surface_line(test_line, baking=baking,
                                                              font_size=font_size, font_color=t_color,
                                                              bolder=bolder, mask_color=mask_color)
                if line_surface.get_width() > width:
                    if current_line:
                        render_text_list.append((current_line, current_color))
                    current_line = char
                    current_color = t_color
                else:
                    current_line = test_line
                    current_color = t_color

        if current_line:
            render_text_list.append((current_line, current_color))

        # 计算行高
        max_font_height = font_size
        for char in text:
            _, font_h = GameFont.get_text_size(char)
            max_font_height = max(max_font_height, font_h)

        # 创建目标 surface
        text_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        render_y = 0

        ont_width = 0
        for line_text, line_color in render_text_list:
            line_surface = GameFont.get_text_surface_line(line_text,
                                                          baking=baking,
                                                          font_size=font_size,
                                                          font_color=line_color,
                                                          bolder=bolder,
                                                          mask_color=mask_color)
            ont_width = line_surface.width # 获取最后一行数据的宽度
            # 垂直方向居中对齐（可选，当前为顶部对齐）
            if render_y + line_surface.get_height() > height:
                break  # 超出高度，不再渲染

            text_surface.blit(line_surface, (0, render_y))
            render_y += line_surface.get_height()

        # 如果只有一行. 那么宽度不一定是传入的宽度.  需要拿到上面保存的最新的宽度
        if len(render_text_list) == 1:
            width = ont_width
        # 转换为实际的大小
        mask_sur_full = pygame.Surface((width, render_y + 5), pygame.SRCALPHA)
        mask_sur_full.blit(text_surface, (0, 0))
        return mask_sur_full

    @staticmethod
    def get_multiple_text_by_max_height(text: str, width: int, max_height: int,
                                        baking: bool = False, font_size: int = 13,
                                        font_color: tuple | str = (255, 255, 255),
                                        bolder: bool = False, mask_color: tuple | str = (0, 0, 0)):
        """
        渲染多行文本，限制最大高度，超过部分截断
        :return: 渲染好的 pygame.Surface 对象
        """
        if not isinstance(text, str):
            text = str(text)

        text_arr = GameFont.parse_color_string(text)
        render_text_list = []  # 每行: [(line_text, color)]

        current_line = ''
        current_color = font_color

        for ta in text_arr:
            t_color = ta.get("color") or GameFont.hex_color_to_rgb(font_color)
            t_label = ta.get("label")

            for char in t_label:
                test_line = current_line + char
                line_surface = GameFont.get_text_surface_line(test_line, baking=baking,
                                                              font_size=font_size, font_color=t_color,
                                                              bolder=bolder, mask_color=mask_color)
                if line_surface.get_width() > width:
                    if current_line:
                        render_text_list.append((current_line, current_color))
                    current_line = char
                    current_color = t_color
                else:
                    current_line = test_line
                    current_color = t_color

        if current_line:
            render_text_list.append((current_line, current_color))

        # 行高估算
        max_font_height = font_size
        for char in text:
            _, font_h = GameFont.get_text_size(char)
            max_font_height = max(max_font_height, font_h)

        # 最多可容纳行数
        max_lines = max_height // max_font_height

        # 创建 surface：高度为 min(实际行数, max_lines)
        actual_lines = render_text_list[:max_lines]
        actual_height = len(actual_lines) * max_font_height

        text_surface = pygame.Surface((width, actual_height), pygame.SRCALPHA)
        render_y = 0

        for line_text, line_color in actual_lines:
            line_surface = GameFont.get_text_surface_line(line_text,
                                                          baking=baking,
                                                          font_size=font_size,
                                                          font_color=line_color,
                                                          bolder=bolder,
                                                          mask_color=mask_color)
            text_surface.blit(line_surface, (0, render_y))
            render_y += line_surface.get_height()

        return text_surface
