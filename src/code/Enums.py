#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : Enums.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/8/6
@Desc    : 全局枚举类
"""
from enum import Enum
from dataclasses import dataclass, field, fields
from typing import Optional, Callable, List, Any, Dict, Union
import pygame


class SpriteState(Enum):
    """ 精灵的状态枚举 """
    IDLE = 0  # 空闲
    WALK = 1  # 行走
    ATTACK = 2  # 攻击
    DEAD = 3  # 死亡
    HURT = 4  # 受伤
    SKILL = 5  # 技能
    JUMP = 6  # 跳跃
    FALL = 7  # 掉落
    CROUCH = 8  # 蹲下
    STANDUP = 9  # 起立
    DASH = 10  # 冲刺


class MouseState(Enum):
    """ 鼠标光标状态 """
    DEFAULT = 0  # 默认
    ATTACK = 1  # 攻击
    BAN = 2  # 禁用
    CAPTURE = 3  # 捕捉
    PICK_ITEM = 4 # 拾取道具


class SpriteLayer(Enum):
    """精灵的图层"""
    DEFAULT = 0  # 默认
    UI = 1  # UI层
    UI_MENU = 2  # 菜单层
    UI_DIALOG = 3  # 对话框层
    ENEMY = 4 # 敌人
    PLAYER = 5 # 玩家
    PICK_ITEM = 6 # 可拾取道具

#
class BattleState(Enum):
    """战斗状态枚举"""
    START = 1
    """
    战斗开始 → 初始化
    玩家与敌人进入指令阶段
    """
    CMD_ATTACK = 2
    """普通攻击指令"""
    CMD_MAGIC = 3
    """法术指令"""
    CMD_ITEM = 4
    """使用道具指令"""
    CMD_CAPTURE = 5
    """捕捉指令"""
    ACTION = 6
    """所有行动执行完毕 → 判定战斗是否结束"""
    REPEAT = 7
    """如果未结束 → 进入下一轮"""
    OVER = 8
    """战斗结束 → 结算"""


class ShopType(Enum):
    """商城类型"""
    BUY = 1
    SELL = 2

# UI组件声明, 不适用.  没有字典灵活. 将就用.  改动的地方太多了
@dataclass
class UIComponent:
    # 核心标识与显示
    name: str
    surface: pygame.Surface
    surface_raw: pygame.Surface
    rect: pygame.Rect
    mask: pygame.mask.Mask

    # 层级管理
    event_layer: int
    render_layer: int
    old_event_layer: int = field(init=False)
    old_render_layer: int = field(init=False)

    # 状态控制
    show: bool = False
    drag: bool = False
    drag_rect: Optional[pygame.Rect] = None

    # 事件回调
    mouse_down: Optional[Callable] = None
    mouse_up: Optional[Callable] = None
    mouse_move: Optional[Callable] = None
    mouse_enter: Optional[Callable] = None
    mouse_out: Optional[Callable] = None
    mouse_double_click: Optional[Callable] = None
    mouse_scroll_wheel_up: Optional[Callable] = None
    mouse_scroll_wheel_down: Optional[Callable] = None

    # 键盘回调
    listen_keyboard: Optional[Callable[[], bool]] = None
    key_down: Optional[Callable] = None
    """键盘按下"""
    key_up: Optional[Callable] = None
    """键盘抬起"""
    keyboard_pressed: Optional[Callable] = None
    """键盘长按"""
    key_text: Optional[Callable] = None


    # 渲染与生命周期回调
    update_blit: Optional[Callable] = None  # 对应原代码中的逻辑
    update_event: Optional[Callable] = None  # 帧更新事件
    move_callback: Optional[Callable[[pygame.Rect], None]] = None
    hide_callback: Optional[Callable] = None
    hide_callback_once: Optional[Callable] = None
    hide_callback_once_auto: Optional[Callable] = None

    # 特殊渲染属性 (如文字、序列帧、气泡、物品等)
    label: Optional[Dict[str, Any]] = None
    frame: Optional[Dict[str, Any]] = None
    item_event: Optional[Dict[str, Any]] = None
    bubble: bool = False
    un_allow: bool = False  # 是否禁止移动

    def __post_init__(self):
        # 自动备份初始层级，方便重置
        self.old_event_layer = self.event_layer
        self.old_render_layer = self.render_layer

    def reset_layers(self):
        """恢复到初始定义的层级"""
        self.event_layer = self.old_event_layer
        self.render_layer = self.old_render_layer


    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UIComponent':
        """将字典转换为 UIComponent 实例。
        1. 属于构造函数参数的字段通过构造函数初始化。
        2. 其他字段（包括 init=False 的字段和动态字段）通过 setattr 追加。
        """
        # 核心：只获取构造函数接受的字段名
        init_fields = {f.name for f in fields(cls) if f.init}

        init_data = {}
        extra_data = {}

        for k, v in data.items():
            if k in init_fields:
                init_data[k] = v
            else:
                # 包括 old_event_layer, old_render_layer 和用户自定义键
                extra_data[k] = v

        # 1. 实例化 (此时会执行 __post_init__ 备份初始层级)
        instance = cls(**init_data)

        # 2. 动态追加额外属性
        # 注意：如果 extra_data 里包含了 'old_event_layer'，它会覆盖掉 __post_init__ 里的值
        # 如果不希望被覆盖，可以加一个判断 if k not in init_fields_all
        for k, v in extra_data.items():
            setattr(instance, k, v)

        return instance
