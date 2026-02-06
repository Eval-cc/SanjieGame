#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : GameWorldManager.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/28 12:53
@Desc    : 世界场景缓存管理.  管理一些需要全局管理的精灵
"""
import time
from typing import TYPE_CHECKING, Dict, List, Callable

if TYPE_CHECKING:
    from src.code.Item import Item
    from src.character.PickableItem import PickableItem


class GameWorldManager:
    __pick_items: Dict[str, "PickableItem"] = {}

    # 新增：用于存储定时事件的字典，Key为分钟(int)，Value为回调函数列表
    __timed_events: Dict[int, List[Callable]] = {}
    # 新增：记录上一次触发的时间戳
    __last_check_times: Dict[int, float] = {}

    @classmethod
    def has_pick_item(cls, puid: str):
        """
        当前的这个pick_item是否已经追加进来了
        :param puid:
        :return:
        """
        for _k in cls.__pick_items:
            pi = cls.__pick_items[_k]
            if pi.UID == puid:
                return True
        return False

    @classmethod
    def add_pick_item(cls, item: "Item", wx: int, wy: int, send_global: bool = False, puid: str = None):
        """
        给场景推送道具掉落的事件
        :param item:
        :param wx:
        :param wy:
        :param send_global: 是否需要推送世界
        :return:
        """
        pid = PickableItem(item, wx, wy, send_global)
        cls.__pick_items[pid.UID if puid is None else puid] = pid

    @classmethod
    def remove_pick_item(cls, uid: str):
        """
        收到移除这个道具的命令
        :param uid:
        :return:
        """
        if cls.__pick_items.get(uid):
            cls.__pick_items[uid].destroy()
            del cls.__pick_items[uid]

    @classmethod
    def register_timed_event(cls, minutes: int, callback: Callable):
        """
        注册一个每隔指定分钟触发一次的事件
        :param minutes: 间隔分钟数
        :param callback: 触发的回调函数
        """
        if minutes not in cls.__timed_events:
            cls.__timed_events[minutes] = []
            cls.__last_check_times[minutes] = time.time()  # 初始化计时器

        cls.__timed_events[minutes].append(callback)

    @classmethod
    def update_timed_events(cls):
        """
        心跳检查方法。建议在游戏主循环中调用（如每帧调用）
        """
        now = time.time()
        for minutes, callbacks in cls.__timed_events.items():
            # 计算时间差（秒）
            interval_seconds = minutes * 60
            if now - cls.__last_check_times[minutes] >= interval_seconds:
                # 达到间隔时间，执行所有注册的回调
                for func in callbacks:
                    try:
                        func()
                    except Exception as e:
                        print(f"Timed Event Error ({minutes} min): {e}")

                # 更新上一次触发的时间点
                cls.__last_check_times[minutes] = now