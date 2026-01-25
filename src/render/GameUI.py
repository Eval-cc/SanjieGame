#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：GameUI.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/6/15 11:16 
@Describe: 页面UI管理
"""

from typing import Dict

import pygame

from pygame.key import ScancodeWrapper

from src.code.Enums import MouseState
from src.code.SpriteBase import SpriteBase
from src.manager.GameLogManger import GameLogManager
from src.manager.SourceManager import SourceManager
from src.system.Animator import Animator
from src.system.GameTipDialog import GameDialogBoxManager
from src.system.GameToast import GameToastManager


class GameUI(SpriteBase):
    def __init__(self, gm):
        super().__init__([
            ["游戏UI点击事件", "游戏UI键盘按下事件", "游戏UI键盘抬起事件", "游戏UI上滚轮事件", "游戏UI下滚轮事件",
             "游戏UI键盘长按事件", "输入框候选字事件"],
            [1, 6, 7, 4, 5, 8, 9]])
        self.layer_order = 999
        self.rect_list: list = []

        # 渲染的字典
        self.__sort_surface: dict[str:dict] = {}
        self.__hover_surface = None
        self.__click_surface = None

        self.__sort_layer_layer()

        # 需要交给UI全局显示的精灵
        self.__canvas_ui = []

        self.gm = gm

        # 鼠标光标配置
        cursor_configs = [
            ("default", "mouse_default.png", 11),
            ("attack", "mouse_attack.png", 9),
            ("ban", "mouse_ban.png", 9),
            ("capture", "mouse_capture.png", 10),
            ("pick_item", "mouse_item.png", 9)
        ]

        # 创建鼠标光标字典
        self.__mouse_cursor_dict = {}
        # 默认光标
        self.__curr_mouse = "default"
        for cursor_type, filename, cursor_len in cursor_configs:
            ani = Animator(gm)
            ani.surface_to_animation_row(
                SourceManager.load(f"{SourceManager.ui_system_path}/{filename}"),
                cursor_type, cursor_len, cursor_len
            )
            self.__mouse_cursor_dict[cursor_type] = ani

        pygame.mouse.set_visible(False)  # 隐藏默认光标

    def __str__(self):
        return "游戏UI"

    def __sort_layer_layer(self):
        # 根据事件的order排序
        self.rect_list.sort(key=lambda sur: sur["event_layer"], reverse=True)
        # 渲染的字典根据 渲染的order排序
        self.__sort_surface: dict[str:dict] = {ui_sur["name"]: ui_sur for ui_sur in
                                               sorted(self.rect_list, key=lambda sur: sur["render_layer"],
                                                      reverse=False)}

    def load_system_ui(self, path: str | pygame.Surface, size: list[int] = None, loc: str = None, options: dict = None,
                       pos: list = None, sort: bool = False):
        """
        加载系统级别的UI
        @:param
            sort: 对于需要全局显示的UI, 请确保该参数为 True
        """

        if options.get("name") is None:
            GameLogManager.log_service_error("无法写入渲染列表,没有找到name属性")
            return None

        ui_surface = path
        if type(path) == str:
            ui_surface = SourceManager.ssurface_scale(SourceManager.load(path), size) if size else SourceManager.load(
                path)

        sur_rect = ui_surface.get_rect()
        if loc is not None:
            if loc == "middle":
                sur_rect.x = int(self.gm.game_win_rect.width / 2) - int(sur_rect.width / 2)
                sur_rect.y = int(self.gm.game_win_rect.height / 2) - int(sur_rect.height / 2)
            elif loc == "top_right":
                sur_rect.x = self.gm.game_win_rect.right - sur_rect.width
            elif loc == "top_right_center":
                sur_rect.x = self.gm.game_win_rect.right - sur_rect.width
                sur_rect.y = int(self.gm.game_win_rect.height / 2) - int(sur_rect.height / 2)
        elif pos is not None:
            sur_rect.x = pos[0]
            sur_rect.y = pos[1]
        elif options is not None and options.get("frame") and options.get("frame").get("loc"):
            sur_rect.x = options.get("frame").get("loc")[0]
            sur_rect.y = options.get("frame").get("loc")[1]
            sur_rect.width = options.get("frame").get("size")

        if options is None:
            return [ui_surface, sur_rect]

        params = {
            "name": options.get("name"),
            "surface": ui_surface,
            "surface_raw": ui_surface,
            "rect": sur_rect,
            "mask": SourceManager.create_surface_mask(ui_surface),
            "mouse_down": None if options.get("mouse_down") is None else options.get("mouse_down", lambda e : None),
            "event_layer": len(self.rect_list) + 2 if options.get("event_layer") is None else options.get(
                "event_layer"),
            "render_layer": len(self.rect_list) + 5 if options.get("render_layer") is None else options.get(
                "render_layer"),
            "show": False if options.get("show") is None else options.get("show"),
            "drag": False if options.get("drag") is None else options.get("drag"),
            "drag_rect": None,
            "mask_surface": None,
            "update_blit": [] if options.get("update_blit") is None else options.get("update_blit"),
            "listen_keyboard": options.get("listen_keyboard"),
            "move_callback": options.get("move_callback"),  # 当前ui的拖拽事件回调, ui发生移动时触发
        }
        for k in options:
            if params.get(k) is None:
                params[k] = options[k]
        # 保存旧的层级,方便恢复
        params["old_event_layer"] = params["event_layer"]
        params["old_render_layer"] = params["render_layer"]
        if options.get("drag_rect") is not None:
            drag_pos = options.get("drag_rect")
            if drag_pos[0] == "auto":
                drag_pos[0] = sur_rect.x
            if drag_pos[1] == "auto":
                drag_pos[1] = sur_rect.y

            # 处理宽度（drag_pos[2]）
            drag_pos[2] = self.parse_size(drag_pos[2], sur_rect.width)

            # 处理高度（drag_pos[3]）
            drag_pos[3] = self.parse_size(drag_pos[3], sur_rect.height)

            params["drag_rect"] = [int(i) for i in drag_pos]

        if size and pos and options.get("is_share") and \
                options.get("frame") and options.get("frame").get("loc"):
            """否是共享组件, 如果是共享组件,那么就根据传入的新位置来直接更新"""
            params.get("frame")["loc"] = pos
            sur_rect = pygame.Rect([*pos, *size])
            if options.get("frame").get("size"):
                sur_rect.width = options.get("frame").get("size")

        self.rect_list.append(params)
        if sort:
            self.__sort_layer_layer()
        return [ui_surface, sur_rect, params]

    # 渲染
    def render_mask(self):
        top_render = []
        # 推拽事件放在渲染里面执行, 不能放在分发的移动事件里面
        if self.__hover_surface is not None:
            if self.is_dragging:
                mouse_pos = pygame.mouse.get_pos()
                # 得到鼠标距离当前元素最左侧的 值
                offset_x, offset_y = self.drag_offset_pos
                # 鼠标移动的坐标 减去 鼠标点击的时候距离贴图最左侧的距离
                target_x = mouse_pos[0] - offset_x
                target_y = mouse_pos[1] - offset_y
                self.__hover_surface.get("rect").x = max(0, min(target_x,
                                                                self.gm.game_win_rect.width - self.__hover_surface.get(
                                                                    "rect").width))
                self.__hover_surface.get("rect").y = max(0, min(target_y,
                                                                self.gm.game_win_rect.height - self.__hover_surface.get(
                                                                    "rect").height))
                # 触发移动事件回调
                if self.__hover_surface.get("move_callback"):
                    self.__hover_surface.get("move_callback")(self.__hover_surface.get("rect"))
        for ui_surface in self.__sort_surface.values():
            if ui_surface.get("show"):
                # 当前UI控件是否有刷新surface的方法, 每个UI自己实现重绘的逻辑
                if ui_surface.get("update_blit"):
                    ui_surface.get("update_blit")()

                # 有父级组件的, 需要减去父级组件的偏移,因为此时的组件坐标是依赖父组件的
                draw_rect = [ui_surface.get("rect").x, ui_surface.get("rect").y]

                # 是否是序列帧动画UI
                if ui_surface.get("frame"):
                    frame_size = ui_surface.get("frame").get("size")
                    frame_index = ui_surface.get("frame").get("index")
                    # 是否允许播放帧动画, 不允许播放的就默认0帧
                    if ui_surface.get("frame").get("play"):
                        if ui_surface.get("frame").get("time", 0) > 0:
                            ui_surface.get("frame")["time"] -= 1
                        else:
                            ui_surface.get("frame")["time"] = ui_surface.get("frame").get("timer", 0)
                            ui_surface.get("frame")["index"] = (frame_index + 1) % ui_surface.get("frame").get("count")
                    self.gm.game_win.blit(ui_surface.get("surface"),
                                          draw_rect,
                                          (frame_index * frame_size, 0, frame_size, frame_size))

                else:
                    self.gm.game_win.blit(ui_surface.get("surface"), draw_rect)

                if ui_surface.get("label"):
                    # 计算文本坐标,确保文本处于ui的中间
                    width = len(ui_surface.get("label").get("text")) * ui_surface.get("label").get("size")
                    lab_left = 0 if ui_surface.get("rect").width < width else (ui_surface.get(
                        "rect").width - width) // 2
                    lab_top = 0 \
                        if ui_surface.get("rect").height < ui_surface.get("label").get("size") \
                        else (ui_surface.get("rect").height - ui_surface.get("label").get("size")) // 2
                    self.gm.game_win.blit(
                        self.gm.game_font.get_text_surface_line(ui_surface.get("label").get("text"), True,
                                                                ui_surface.get("label").get("size"),
                                                                font_color=ui_surface.get("label").get("font-color",
                                                                                                       "#0000CD")),
                        (
                            draw_rect[0] + lab_left,
                            draw_rect[1] + lab_top))

                mask_sur = ui_surface.get("mask_surface")
                if mask_sur:
                    self.gm.game_win.blit(mask_sur, ui_surface.get("rect"))
                if ui_surface.get("item_event") and self.mouse_tap:
                    mouse_pos = pygame.mouse.get_pos()
                    # self.gm.game_win.blit(ui_surface.get("item_event")["texture"],
                    #                           (mouse_pos[0] - 35, mouse_pos[1] - 30))
                    top_render.append([ui_surface.get("item_event")["texture"], (mouse_pos[0] - 35, mouse_pos[1] - 30)])
                # 是否有帧事件
                if ui_surface.get("update_event"):
                    ui_surface.get("update_event")()

            # 需要特殊渲染的拿出来单独显示
            for tr in top_render:
                self.gm.game_win.blit(tr[0], tr[1])

    def render_sticky(self):
        # 获取鼠标位置
        mouse_pos = pygame.mouse.get_pos()

        self.animator = self.__mouse_cursor_dict[self.__curr_mouse]
        if self.animator is None:
            return
        if not self.animator.is_playing(self.__curr_mouse):
            self.animator.play(self.__curr_mouse)
            self.animator.speed = 0.1

        # 更新动画
        self.animator.update(0.5)  # 以 60fps 作为基准
        # 渲染背景特效
        self.animator.render(mouse_pos[0], mouse_pos[1])

    def has_clicked_condition(self, params=None):
        if params is None:
            return True
        # 根据当前传进来的区域精灵的状态决定是否允许触发点击状态
        return params.get("show")

    def mouse_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        super().mouse_down(event)
        if self.get_click_sprite_index() >= 0:
            target: dict = self.rect_list[self.get_click_sprite_index()]
            self.__click_surface = target

            if target.get("frame"):
                target.get("frame")["index"] = 1 if target.get("frame").get("target_index") is None else target.get(
                    "frame").get("target_index")
            cl = target.get("mouse_down")
            # 是否允许拖动
            if target.get("drag"):
                self.change_ui_layer(target.get("name"), target.get("drag"))
                # 点击的范围在允许拖动的区域
                if target.get("drag_rect") is not None and \
                        not pygame.Rect(target.get("drag_rect")).collidepoint(event.get("mouse_pos")[0],
                                                                              event.get("mouse_pos")[1]):
                    # 进来这就是没有触发到拖拽区域- 点击拖拽区域不允许往下分发点击事件

                    if target.get("bubble"):
                        # 如果当前UI 是允许冒泡的. 那么执行事件之后照样返回True
                        if cl:
                            cl(event=event)
                        return True
                    return False if cl is None else cl(event=event)

                self.drag_first_pos = [event.get("mouse_pos")[0], event.get("mouse_pos")[1]]
                self.__hover_surface = target  # self.rect_list[self.get_click_sprite_index()]
                self.drag_offset_pos = [self.drag_first_pos[0] - self.__hover_surface.get("rect").x,
                                        self.drag_first_pos[1] - self.__hover_surface.get("rect").y]
                return False

            return False if cl is None else cl(event=event)
        return True

    def mouse_up(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        super().mouse_up(event)
        if self.__click_surface is not None:
            up_fun = self.__click_surface.get("mouse_up")
            if self.__click_surface.get("frame"):
                self.__click_surface.get("frame")["index"] = 0
            if up_fun:
                up_fun()
        if self.__hover_surface is None:
            return True
        # 每次松开前都需要更新一下当前ui的可拖拽坐标
        if self.__hover_surface.get("drag_rect") is not None:
            drag_pos = self.__hover_surface.get("drag_rect")
            drag_pos[0] = self.__hover_surface.get("rect").x
            drag_pos[1] = self.__hover_surface.get("rect").y

            self.__hover_surface["drag_rect"] = [int(i) for i in drag_pos]

        self.__hover_surface = None
        return True

    def mouse_move(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        if self.get_click_sprite_index() >= 0:
            target: dict = self.rect_list[self.get_click_sprite_index()]
            self.__click_surface = target
            move_fun = target.get("mouse_move")
            if not move_fun:
                return False
            return move_fun()
        return True

    def mouse_enter(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        if self.get_click_sprite_index() >= 0:
            target: dict = self.rect_list[self.get_click_sprite_index()]
            self.__click_surface = target
            move_fun = target.get("mouse_enter")
            if not move_fun:
                return False
            move_fun()
            return False
        return True

    def mouse_out(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        if self.get_click_sprite_index() >= 0:
            if self.get_click_sprite_index() > len(self.rect_list):
                return False
            target: dict = self.rect_list[self.get_click_sprite_index()]
            self.__click_surface = target
            move_fun = target.get("mouse_out")
            if not move_fun:
                return False
            move_fun()
            return False
        return True

    def mouse_double_click(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """
        UI的双击事件
        :param event:
        :return:
        """
        if self.get_click_sprite_index() >= 0:
            target: dict = self.rect_list[self.get_click_sprite_index()]
            self.__click_surface = target
            move_fun = target.get("mouse_double_click")
            if not move_fun:
                return False
            move_fun()
            return False
        return True

    def mouse_scroll_wheel_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """
        UI的滚轮向下事件
        :param event:
        :return:
        """
        if self.get_click_sprite_index() >= 0:
            target: dict = self.rect_list[self.get_click_sprite_index()]
            self.__click_surface = target
            move_fun = target.get("mouse_scroll_wheel_down")
            if not move_fun:
                return False
            move_fun()
            return False
        return True

    def mouse_scroll_wheel_up(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """
        UI的滚轮向上事件
        :param event:
        :return:
        """
        if self.get_click_sprite_index() >= 0:
            target: dict = self.rect_list[self.get_click_sprite_index()]
            self.__click_surface = target
            move_fun = target.get("mouse_scroll_wheel_up")
            if not move_fun:
                return False
            move_fun()
            return False
        return True

    def keyboard_pressed(self, event: Dict[str, ScancodeWrapper] | pygame.event.EventType):
        if self.get_click_sprite_index() >= 0:
            target: dict = self.rect_list[self.get_click_sprite_index()]
            self.__click_surface = target
            move_fun = target.get("keyboard_pressed")
            if not move_fun:
                return False
            move_fun(event)
            return False
        return True

    def change_ui_layer(self, name: str, drag: bool = False, center: bool = False, right: bool = False):
        """ 修改UI层级"""
        target_ui: dict = self.__sort_surface.get(name)
        if target_ui is None:
            GameToastManager.add_message(f"打开UI失败! 未知的UI组件:{name}")
            GameLogManager.log_service_debug(f"打开UI失败! 未知的UI组件:{name}")
            return
        # 得到当前最大的层级, 每次操作都会进行排序, 所以索引 0 一定的最上面的ui
        layer_level = int(self.rect_list[0]["render_layer"])
        event_level = int(self.rect_list[0]["event_layer"])

        old_layer = int(target_ui["render_layer"])
        for sur in self.rect_list:
            # 恢复被点击的层级
            if sur.get("drag") and sur.get("name") != target_ui.get("name"):
                sur["render_layer"] = sur["old_render_layer"]
                sur["event_layer"] = sur["old_event_layer"]
        if not target_ui["show"]:
            target_ui["show"] = not target_ui["show"]
            target_ui["render_layer"] = layer_level + 1
            target_ui["event_layer"] = event_level + 1
        else:
            if old_layer == layer_level and not drag:
                # 如果是需要触发关闭, 那就调用关闭的方法
                if target_ui["show"]:
                    self.close_surface_ui(target_ui.get("name"))
                else:
                    target_ui["show"] = True
            else:
                target_ui["render_layer"] = layer_level + 1
                target_ui["event_layer"] = event_level + 1
        self.__sort_layer_layer()
        # 是否需要恢复到屏幕中间
        if center:
            self.reset_ui_center(name)
        elif right:
            self.reset_ui_center(name)

    def listen_keyboard(self):
        """
        根据对应的ui自己实现的监听按键回调来控制是否允许触发键盘事件. 不能直接依靠是否显示
        :return:
        """
        for sur in self.rect_list:
            if sur.get("listen_keyboard"):
                return sur.get("listen_keyboard")()
        return False

    def key_up(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        # 给优先级最高的UI触发键盘时间
        for sur in self.rect_list:
            if sur.get("listen_keyboard") and sur.get("show"):
                if sur.get("key_up"):
                    sur["key_up"](event)
                    return False
        return True

    def key_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        if event.get("event").scancode == 41:
            # Esc关闭UI, 根据事件的顺序
            for sur in self.rect_list:
                if sur.get("listen_keyboard") and sur.get("show"):
                    self.close_surface_ui(sur.get("name"))
                    return False
            return True
        # 给优先级最高的UI触发键盘时间
        for sur in self.rect_list:
            if sur.get("listen_keyboard") and sur.get("show"):
                if sur.get("key_down"):
                    sur["key_down"](event)
                    return False
        return True


    def key_text(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        # 给优先级最高的UI触发键盘时间
        for sur in self.rect_list:
            if sur.get("listen_keyboard") and sur.get("show"):
                if sur.get("key_text"):
                    sur["key_text"](event)
                    break

    def get_surface_show(self, name: str):
        """返回指定名称的UI是否显示"""
        sur = self.__sort_surface.get(name)
        if sur is None:
            return False
        return sur["show"]

    def close_surface_ui(self, name: str):
        """关闭UI显示"""
        sur = self.__sort_surface.get(name)
        if sur is None:
            return False
        if not sur.get("show"):
            return False
        sur["show"] = False

        # 是否触发关闭UI的回调
        if sur.get("hide_callback"):
            sur["hide_callback"]()
        elif sur.get("hide_callback_once_auto"):
            sur["hide_callback_once_auto"]()
            del sur["hide_callback_once_auto"]
        elif sur.get("hide_callback_once"):
            # 不会自动执行
            del sur["hide_callback_once"]
        return True

    def get_surface_ui(self, name: str) -> pygame.Surface | None:
        """获取指定UI的surface精灵"""
        sur = self.__sort_surface.get(name)
        if sur is None:
            return None
        return sur["surface_raw"].copy()  # 返回精灵的引用, 不然会数据污染

    def set_surface_ui(self, name: str, surface: pygame.Surface, show: bool = False):
        """更新指定UI的surface精灵"""
        sur = self.__sort_surface.get(name)
        if sur is None:
            return False
        sur["surface"] = surface

        x, y = sur["rect"].x, sur["rect"].y
        old_w = sur["rect"].width
        sur["rect"] = surface.get_rect()  # 刷新尺寸
        sur["rect"].x, sur["rect"].y = x, y
        sur["mask"] = SourceManager.create_surface_mask(surface)
        if sur.get("drag_rect") is not None:
            drag_pos = sur.get("drag_rect")
            # "drag_rect": ["auto", "auto", "-25px", 30],
            drag_pos[0] = x
            drag_pos[1] = y
            # 新的宽度可拖拽区域也要根据新的宽度来更新
            drag_pos[2] = sur["rect"].width - (old_w - drag_pos[2])
            sur["drag_rect"] = [int(i) for i in drag_pos]
        if show:
            sur["show"] = True
        return True

    def remove_surface_ui(self, name: str):
        """移除指定UI"""
        if name in self.__sort_surface:
            del self.__sort_surface[name]
            for ui in self.rect_list:
                if ui.get("name") == name:
                    self.rect_list.remove(ui)
                    break
            self.__sort_layer_layer()  # 刷新一下ui
            return True
        return False

    def reset_ui_center(self, name: str, right: bool = False):
        """调整UI恢复到屏幕中间"""
        sur = self.__sort_surface.get(name)
        sur_rect = sur.get("rect")
        if right:
            # 靠右对齐
            sur_rect.x = self.gm.game_win_rect.width - sur_rect.width
        else:
            # 居中
            sur_rect.x = int(self.gm.game_win_rect.width / 2) - int(sur_rect.width / 2)

        sur_rect.y = int(self.gm.game_win_rect.height / 2) - int(sur_rect.height / 2)

        sur["rect"] = sur_rect
        if sur.get("drag_rect") is not None:
            drag_pos = sur.get("drag_rect")
            drag_pos[0] = sur_rect.x
            drag_pos[1] = sur_rect.y
            # 新的宽度可拖拽区域也要根据新的宽度来更新
            # drag_pos[2] = sur["rect"].width - drag_pos[2]
            sur["drag_rect"] = [int(i) for i in drag_pos]


    def remove_all_ui(self):
        """
        移除所有UI
        :return:
        """
        self.rect_list.clear()
        self.__sort_surface.clear()
        self.__sort_layer_layer()  # 刷新一下ui

    def get_surface_sprite(self, name: str):
        return self.__sort_surface.get(name)

    def has_un_allow_move(self):
        """当前显示的UI中是否有禁止触发人物移动的被渲染出来了"""
        for ui in self.__sort_surface.values():
            if ui.get("show") and ui.get("un_allow"):
                return True
        return False

    def set_surface_cbk(self, name: str, cbk):
        """
        给指定的ui追加单次回调事件
        :param name:
        :param cbk:
        :return:
        """
        sur = self.__sort_surface.get(name)
        if sur is None:
            return False
        sur["hide_callback_once"] = cbk
        return True

    def parse_size(self, value, ref_size):
        """解析尺寸值，支持:
        - 'auto' → 使用参考尺寸
        - '100%'/'50%' → 百分比计算
        - '-5px' → 参考尺寸减去指定值
        - 固定数值 → 直接返回"""
        if value == "auto":
            return ref_size

        # 处理百分比情况
        elif isinstance(value, str) and value.endswith("%"):
            percent = float(value.strip("%"))
            return int(ref_size * percent / 100)

        # 处理偏移情况(如"-5px")
        elif isinstance(value, str) and value.endswith("px"):
            offset = int(value[:-2])  # 提取数字部分(去掉"-"和"px")
            return max(0, ref_size + int(offset))  # 确保不小于0

        # 默认情况(固定数值或非px单位)
        else:
            return value

    def set_btn_text(self, name: str, value: str) -> bool:
        """
        修改按钮UI控件的文本
        :param name:
        :param value:
        :return:
        """
        sur = self.__sort_surface.get(name)
        if sur is None or sur.get("label") is None:
            return False
        sur["label"]["text"] = value
        return True

    def change_mouse_cursor(self, state: MouseState):
        if state == MouseState.DEFAULT:
            self.__curr_mouse = "default"
        elif state == MouseState.ATTACK:
            self.__curr_mouse = "attack"
        elif state == MouseState.BAN:
            self.__curr_mouse = "ban"
        elif state == MouseState.CAPTURE:
            self.__curr_mouse = "capture"
        elif state == MouseState.PICK_ITEM:
            self.__curr_mouse = "pick_item"
        else:
            self.__curr_mouse = "default"
