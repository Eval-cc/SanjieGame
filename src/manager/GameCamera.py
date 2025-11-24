#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：GameCamera.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/2/25 上午11:51 
@Describe: 相机管理
"""
from typing import Dict
import pygame

from src.code.SpriteBase import SpriteBase
from src.manager.GameEvent import GameEvent
from src.manager.GameLogManger import GameLogManager
from src.manager.GameManager import GameManager
from src.manager.GameMapManager import GameMapManager


class GameCamera(SpriteBase):
    def __init__(self):
        super().__init__([["地图移动事件"], [4]])
        # self.position = [0, 0]
        """相机坐标"""
        self.__mounted:SpriteBase = None
        """相机挂载对象"""
        self.__move_speed = 50
        """相机移动速度"""
        self.__move_action = {}
        """相机移动事件表,每次相机移动的时候,都会触发一次"""
        # self.key_down_pos = [0, 0]
        """按键按下状态"""
        """记录挂载对象的上一次移动位置"""
        self.__mounted_last_pos = [-1, -1]

    def move(self):
        """相机移动"""
        if self.__mounted is None:
            return

        if len(GameManager.game_map_size) == 0:
            return

        x, y = self.__mounted.transform.get_pos_list()
        cam_w, cam_h = GameManager.game_win_rect.width, GameManager.game_win_rect.height

        # 当前相机位置
        cam_x, cam_y = self.transform.get_pos_list()

        # 定义安全区边距（你可以调整这个值）
        margin = 300

        # 相机边界
        left = cam_x + margin
        right = cam_x + cam_w - margin
        top = cam_y + margin
        bottom = cam_y + cam_h - margin

        moved = False  # 标记是否移动相机

        # 检查是否超出边界
        if x < left:
            cam_x = max(x - margin, 0)
            moved = True
        elif x > right:
            cam_x = max(x - cam_w + margin, 0)
            moved = True

        if y < top:
            cam_y = max(y - margin, 0)
            moved = True
        elif y > bottom:
            cam_y = max(y - cam_h + margin, 0)
            moved = True

        # 更新相机位置
        self.transform.set_pos(cam_x,cam_y)
        # 如果位置发生变化才触发移动事件
        if moved:
            self.__mounted_last_pos = (x, y)
            for evn in self.__move_action.values():
                evn()

        # 根据地图的配置尺寸,限制镜头的移动范围
        if self.transform.x + GameManager.game_win_rect.width >= GameManager.game_map_size[0]:
            self.set_position(x=GameManager.game_map_size[0] - GameManager.game_win_rect.width)

        # 改成计算地图的实际高度.  因为部分地图的总高度可能少了一点
        real_height = GameMapManager.game_map_tile_size()[1] * GameMapManager.game_map_column_row_size()[1]
        if self.transform.y + GameManager.game_win_rect.height > real_height:
            self.transform.y = real_height - GameManager.game_win_rect.height

    def get_position(self):
        return self.transform.get_pos()

    def set_position(self, x: int = None, y: int = None):
        """直接指定相机的位置"""
        if x is not None:
            self.transform.x = x
        if y is not None:
            self.transform.y = y

    def __set__(self, instance, value):
        GameLogManager.log_service_debug("无法直接设置相机对象")

    def __str__(self):
        return "全局游戏相机"

    def render(self):
        self.move()

    def regin_move_event(self, name: str, action: object):
        """追加相机移动事件"""
        if self.__move_action.get(name) is not None:
            GameLogManager.log_service_debug(f"重复追加相机移动事件:{name}")

        self.__move_action[name] = action

    def uninstall_move_event(self, name: str):
        """取消监听相机移动事件"""
        del self.__move_action[name]

    def mounted(self, target: object):
        """将相机挂载到目标对象上"""
        if not hasattr(target, "transform"):
            raise f"对象:{target.__class__.__name__} 没有[transform]属性,无法挂载"
        self.__mounted = target

    def unmounted(self):
        """卸载相机跟随"""
        self.__mounted = None
        self.transform.set_pos(0,0)
