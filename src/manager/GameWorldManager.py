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
from typing import TYPE_CHECKING
from src.character.PickableItem import PickableItem

if TYPE_CHECKING:
    from src.code.Item import Item


class GameWorldManager:
    __pick_items: dict[str, PickableItem] = {}

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
