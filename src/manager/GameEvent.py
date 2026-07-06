#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：GameEvent.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/2/14 下午12:11 
@Describe: 
"""
import time
from typing import TYPE_CHECKING

import pygame
import sys

from src.code.Enums import SpriteLayer, MouseState
from src.manager.GameLogManger import GameLogManager
from src.manager.GameManager import GameManager

if TYPE_CHECKING:
    from src.render.GameUI import GameUI
    from src.components.GameInput import GameInput
    from pygame.event import Event

keyword_dict = {
    6: "key_down",
    7: "key_up",
    8: "keyboard_pressed",
    9: "key_text",
}

global_key_dict = {
    101: "e"
}


class GameEvent:
    __events = {}
    """存放所有事件的字典"""
    __sort_regin_events = []
    """存放逆序的事件数组
        仅在每次追加事件的时候更新,提升效率
    """
    __global_event = {}
    """全局事件消息, 触发的key 唯一"""

    # 用于计时键盘是否处于长按状态
    keyboard_down_time = 0
    keyboard_down_timer = 0.5

    # 键盘是否按下
    has_key_down = False
    has_control_down = False

    # 存放首次进入鼠标范围的精灵事件
    __first_sprite_hover: dict = {}
    # 首次点击的精灵
    __first_sprite_click: dict = {}

    # 保存上次按下的事件,用于触发长按
    __first_keyboard_event: pygame.event.Event = None

    __input_pool: list["GameInput"] = []

    @staticmethod
    def add(event_name_list: list[str], event_type_list: list[int], event_fun: object):
        """
        追加事件
        :param event_name_list: 事件名称
        :param event_type_list: 事件类型数组: 1 鼠标左键, 2 鼠标中键, 3 鼠标右键,
                                4 滚动向上, 5 滚轮向下
                                6 键盘按下, 7 键盘抬起, 8 连续触发的键盘按下事件
        :param event_fun:  需要触发事件的类
        :return:
        """

        # 默认精灵层级
        sprite_order = getattr(event_fun, "layer_order")
        for i in range(len(event_name_list)):
            event_type = event_type_list[i]
            if GameEvent.__events.get(event_name_list[i]):
                GameLogManager.log_service_debug(f"事件被覆盖: {event_name_list[i]}")
            GameEvent.__events[event_name_list[i]] = {
                "id": len(GameEvent.__events.values()) + 1 + sprite_order,
                "type": event_type,
                "cls": event_fun,
            }
        # 获取字典值的列表，按'id'从大到小排序, 确保触发的点击事件的最上层的- 每次排序都需要带上 layer_order 保证层级在最上面
        GameEvent.__sort_regin_events = sorted(GameEvent.__events.values(),
                                               key=lambda x: (getattr(x['cls'], "layer_order"), x['id']),
                                               reverse=True)

    @staticmethod
    def remove(event_name: str):
        """移除事件"""
        try:
            if GameEvent.__events.get(event_name):
                del GameEvent.__events[event_name]
                GameEvent.__sort_regin_events = sorted(GameEvent.__events.values(),
                                                       key=lambda x: (getattr(x['cls'], "layer_order"), x['id']),
                                                       reverse=True)
        except Exception as e:
            GameLogManager.log_service_error(f"移除事件失败: {event_name} {e}")

    @staticmethod
    def listen_event():
        if GameEvent.keyboard_down_time > 0 and time.time() - GameEvent.keyboard_down_time > GameEvent.keyboard_down_timer:
            if GameEvent.__first_keyboard_event:
                GameEvent.trigger_keyboard_event(GameEvent.__first_keyboard_event, 8)

        for event in pygame.event.get():
            if event.type == pygame.USEREVENT and hasattr(event, "callback"):
                event.callback()  # 直接执行回调
                break
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:  # 当有键盘按下事件时
                GameEvent.__first_keyboard_event = event
                GameEvent.keyboard_down_time = time.time()
                GameEvent.trigger_keyboard_event(event, 6)

            elif event.type == pygame.KEYUP:  # 当有键盘抬起事件时
                GameEvent.__first_keyboard_event = None
                GameEvent.keyboard_down_time = 0
                GameEvent.trigger_keyboard_event(event, 7)
            # 鼠标按下
            elif event.type == pygame.MOUSEBUTTONDOWN:
                ent = {
                    'pos': event.pos, 'button': event.button,
                    'touch': event.touch, 'window': event.window
                }
                type_name = "mouse_down"
                if event.button == 4:
                    type_name = "mouse_scroll_wheel_up"
                if event.button == 5:
                    type_name = "mouse_scroll_wheel_down"
                GameEvent.trigger_mouse_event(ent, type_name)

            # 鼠标抬起
            elif event.type == pygame.MOUSEBUTTONUP:
                # 如果有保存的精灵对象,  那么在抬起的时候需要确保触发一次抬起事件, 避免离开ui范围之后 不会触发
                out_var = GameEvent.__first_sprite_click.get("cls")
                if out_var:
                    out_method = getattr(out_var, "mouse_up")
                    out_method({"type": "mouse_up", "mouse_pos": pygame.mouse.get_pos()})
                    GameEvent.__first_sprite_click = {}

                if event.pos[0] < 0 or event.pos[0] > GameManager.game_win_rect.width or event.pos[1] < 0 or event.pos[
                    1] > GameManager.game_win_rect.height:
                    ent = {
                        'pos': event.pos, 'button': 1,
                        'touch': event.touch, 'window': event.window
                    }
                    GameEvent.trigger_mouse_event(ent, "mouse_up", True)
                    return
                ent = {
                    'pos': event.pos, 'button': event.button,
                    'touch': event.touch, 'window': event.window
                }
                GameEvent.trigger_mouse_event(ent, "mouse_up")
            # 鼠标移动
            elif event.type == pygame.MOUSEMOTION:
                ent = {
                    'pos': event.pos, 'rel': event.rel, 'button': event.buttons.index(max(event.buttons)) + 1,
                    'touch': event.touch, 'window': event.window
                }
                GameEvent.trigger_mouse_event(ent, "mouse_move")
            elif event.type == pygame.TEXTINPUT:
                GameEvent.trigger_keyboard_event(event, 9)

    @staticmethod
    def trigger_mouse_event(event: dict, mouse_type: str, must_exec: bool = False):
        """

        :param event:
        :param mouse_type:
        :param must_exec: 是否强制执行, 无论是否在区域内
        :return:
        """
        if mouse_type == "mouse_down":
            pass
        game_ui: GameUI = GameManager.get("游戏UI")
        # 遍历所有鼠标事件,
        for game_event in GameEvent.__sort_regin_events:
            if game_event.get("type") == event.get("button") and game_event.get("cls") is not None:
                var = game_event.get("cls")

                if hasattr(var, "is_clicked") and hasattr(var, mouse_type):
                    mouse_pos = pygame.mouse.get_pos()
                    if var.is_clicked(mouse_pos[0], mouse_pos[1]) or must_exec:
                        if mouse_type == "mouse_down" and GameEvent.__first_sprite_click.get('id') != game_event.get(
                                "id"):
                            GameEvent.__first_sprite_click = game_event
                        elif mouse_type == "mouse_move" and \
                                GameEvent.__first_sprite_hover.get('id') != game_event.get("id"):
                            out_var = GameEvent.__first_sprite_hover.get("cls")
                            if out_var:
                                out_method = getattr(out_var, "mouse_out")
                                out_method({"type": "mouse_out", "mouse_pos": mouse_pos})
                            GameEvent.__first_sprite_hover = game_event
                            #  调用目标的首次进入事件
                            enter_method = getattr(var, "mouse_enter")
                            enter_method({"type": "mouse_enter", "mouse_pos": mouse_pos})
                        # 拿到对应的触发方法
                        # 比如 method({"type": mouse_type, "mouse_pos": mouse_pos}) => mouse_down({"type": mouse_type, "mouse_pos": mouse_pos})
                        method = getattr(var, mouse_type)

                        # GameLogManager.log_service_debug(
                        #         f"来自: {method.__qualname__ if hasattr(method, '__qualname__') else method.__class__.__name__}"
                        #     )
                        # 更新鼠标光标动画
                        if mouse_type == "mouse_move":
                            var_layer = getattr(var, "layer")
                            if var_layer == SpriteLayer.DEFAULT:
                                game_ui.change_mouse_cursor(MouseState.DEFAULT)
                            elif var_layer == SpriteLayer.ENEMY:
                                game_ui.change_mouse_cursor(MouseState.ATTACK)
                            elif var_layer == SpriteLayer.PICK_ITEM:
                                game_ui.change_mouse_cursor(MouseState.PICK_ITEM)

                        # 如果调用方法返回 False 就结束,  如果返回True就说明允许向下穿透
                        if not method({"type": mouse_type, "mouse_pos": mouse_pos, "button": event.get("button")}):
                            return


                else:
                    GameLogManager.log_service_error(
                        f"未能找到类:{getattr(var, "clsName")}的点击监听方法 [is_clicked=>{hasattr(var, "is_clicked")}] 或 [{mouse_type}=>{hasattr(var, mouse_type)}]")

    @staticmethod
    def trigger_keyboard_event(event: pygame.Event | int, key_type: int):
        event_key = event if type(event) == int else event.key if hasattr(event, "key") else event
        if key_type == 6:
            has_focused_input = GameEvent.has_focused_input()
            if not GameEvent.has_control_down:
                lr_control = [1073742048, 1073742052]  # 左右ctrl
                if event_key in lr_control:
                    GameLogManager.log_service_debug("左右ctrl")
                    GameEvent.has_control_down = True
            else:
                if not has_focused_input:
                    event_fun = GameEvent.__global_event.get(f"ctrl_{global_key_dict.get(event_key)}")
                    if event_fun:
                        event_fun()
                    GameLogManager.log_service_debug(f"触发快捷键事件,全局唯一,不用处理分发,code:[{event_key}]")
            if GameEvent.has_control_down and not has_focused_input:
                return
        else:
            GameEvent.has_key_down = False
            GameEvent.has_control_down = False
        # 执行触发键盘事件,
        for game_event in GameEvent.__sort_regin_events:
            if game_event.get("type") == key_type and game_event.get("cls") is not None:
                var = game_event.get("cls")
                # 先判断一下,当前精灵是否启用了允许监听键盘的事件
                listen_keyboard = getattr(var, "listen_keyboard")
                if not listen_keyboard():
                    continue
                type_name = keyword_dict.get(
                    int(key_type))  # "key_down" if key_type == 6 else "key_up" if key_type == 7 else "keyboard_pressed"
                if type_name is None:
                    GameLogManager.log_service_error(f"未知的键盘事件类型:{key_type}")
                    return
                if hasattr(var, type_name):
                    method = getattr(var, type_name)
                    # 如果调用方法返回 False 就结束,  如果返回True就说明允许向下穿透
                    if hasattr(event, "text"):
                        method({"event": event, "type": type_name, "key_name": "", "text": event.text})
                        return
                    key_name = pygame.key.name(event_key)

                    if not method({"event": event, "type": type_name, "key_name": key_name}):
                        return

                else:
                    GameLogManager.log_service_error(
                        f"未能找到类:{getattr(var, "clsName")}的键盘监听方法 [{type_name}=>{hasattr(var, type_name)}]")

    @staticmethod
    def add_input(component: "GameInput"):
        """ 将输入框加入事件池 """
        GameEvent.__input_pool.append(component)

    @staticmethod
    def remove_input(component: "GameInput"):
        """ 移除输入框 """
        GameEvent.__input_pool.remove(component)

    @staticmethod
    def all_input_pool():
        return GameEvent.__input_pool

    @staticmethod
    def has_focused_input() -> bool:
        return any(getattr(component, "has_focus", False) for component in GameEvent.__input_pool)
