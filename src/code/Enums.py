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
    ACTION = 5
    """所有行动执行完毕 → 判定战斗是否结束"""
    REPEAT = 6
    """如果未结束 → 进入下一轮"""
    OVER = 7
    """战斗结束 → 结算"""
