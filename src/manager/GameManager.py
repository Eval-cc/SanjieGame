#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：GameManager.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/2/13 下午9:48 
@Describe: 
"""
import os.path
from typing import Dict, TYPE_CHECKING

import pygame

from src.code.SpriteBase import SpriteBase
from src.lib.FindPath_Theta import ThetaStarPathfinder
from src.lib.FindPath_AStart import AStarPathfinder
from src.lib.TaskParingEngine import TaskParingEngine

from src.manager.GameFont import GameFont
from src.manager.GameLoadCsv import GameLoadCSV
from src.manager.GameLogManger import GameLogManager
from src.manager.GameMapManager import GameMapManager
from src.manager.SourceManager import SourceManager
from src.system.GameDialog import GameDialog
from src.system.GameToast import GameToastManager
from src.system.ShopSystem import ShopSystem

if TYPE_CHECKING:
    from src.manager.GameCamera import GameCamera
    from src.render.GameUI import GameUI


class GameManager:
    """全局游戏管理器"""
    __render_dict: Dict[str, SpriteBase] = {}
    """精灵字典"""
    __render_list: list[SpriteBase] = []
    """用于渲染的精灵数组"""

    game_win: pygame.Surface = None
    """全局游戏窗口管理"""
    game_win_rect: pygame.rect.Rect = None
    """当前视图区域的尺寸"""
    game_box_size: int = 20
    """单个地图格子的大小"""
    game_map_size: list[int] = []
    """当前游戏的尺寸"""

    game_delay: int = 0
    __game_delay: int = 100

    """是否启用地图格子渲染"""

    game_camera:"GameCamera" = None
    """游戏相机"""

    game_font: "GameFont" = None
    """游戏字体对象"""

    game_dialog: "GameDialog" = None
    """游戏对话对象"""

    game_task_paring_engine: "TaskParingEngine" = None
    """对话脚本解析引擎"""

    find_path_list = []
    """需要触发获取点击地图坐标的对象列表 ,追加的格式是: {get_pos:'获取当前寻路精灵的坐标, move:可调用的精灵移动方法}"""

    has_debug_render = False
    """是否启用debug模式的渲染,  此模式下会显示具体的障碍点方块以及一些详细的信息"""

    __manager_dict = {}
    """全局游戏静态类管理映射"""
    shop_system: "ShopSystem" = None

    __items_need_floor = []
    __items_need_body = []
    __items_need_mask = []
    __items_need_sticky = []

    clock: pygame.Clock = None

    @staticmethod
    def Awake():
        pygame.key.start_text_input()
        SourceManager.Awake()
        # 初始化消息管理器
        GameToastManager.Awake(GameManager.game_win.get_width(), GameManager.game_win.get_height(), GameManager)
        if GameManager.game_win_rect is None:
            GameManager.game_win_rect = GameManager.game_win.get_rect()

        if GameManager.game_camera is None:
            from src.manager.GameCamera import GameCamera
            GameManager.game_camera = GameCamera()
            GameManager.add("相机", GameManager.game_camera)

        # 初始化脚本
        load_cav_arr = ["npcs", "items", "item_type", "skills"]
        for csv_name in load_cav_arr:
            if not os.path.exists(rf"{SourceManager.cfg_csv_path}/{csv_name}.csv"):
                GameLogManager.log_service_error(f"无法找到脚本:{csv_name}")
                continue
            has_raw = False
            if csv_name == "item_type":
                has_raw = True
            SourceManager.set_csv(csv_name, GameLoadCSV.load(rf"{SourceManager.cfg_csv_path}/{csv_name}.csv"), has_raw)

        # 游戏的字体对象
        GameManager.game_font = GameFont
        GameManager.game_task_paring_engine = TaskParingEngine()
        GameManager.game_dialog = GameDialog(GameManager)

    @staticmethod
    def __refresh_layer():
        """初始化渲染数组"""
        GameManager.__items_need_floor = [item.render_floor for item in GameManager.__render_list if item.render_floor]
        GameManager.__items_need_body = [item.render for item in GameManager.__render_list if item.render]
        GameManager.__items_need_mask = [item.render_mask for item in GameManager.__render_list if item.render_mask]
        GameManager.__items_need_sticky = [item.render_sticky for item in GameManager.__render_list if
                                           item.render_sticky]

    @staticmethod
    def add(name: str, sprite: SpriteBase):
        """追加精灵对象到全局游戏管理器
        Args:
            name (str): 精灵的唯一标识名称（例如："player", "enemy_01"），用于后续引用和管理。
            sprite (SpriteBase): 精灵的基础表面对象（如图像、动画等）。
        """
        if GameManager.__render_dict.get(name):
            return
        GameManager.__render_dict[name] = sprite
        GameManager.__render_list.append(sprite)
        # 每次最追加都根据精灵的层级排个序
        GameManager.__render_list.sort(key=lambda sur: sur.layer_order, reverse=False)
        #  初始化渲染数组
        GameManager.__refresh_layer()

    @staticmethod
    def remove(name: str | SpriteBase):
        """移除指定 的精灵资源"""
        if type(name) == str:
            sprite = GameManager.__render_dict.get(name)
            if sprite:
                GameManager.__render_list.remove(sprite)
                del GameManager.__render_dict[name]
        else:
            target = name
            for k in GameManager.__render_dict.keys():
                if GameManager.__render_dict.get(k) == target:
                    GameManager.__render_list.remove(target)
                    del GameManager.__render_dict[k]
                    # 初始化渲染数组
                    break

        GameManager.__refresh_layer()

    @staticmethod
    def get(name: str):
        """获取指定名称的精灵"""
        return GameManager.__render_dict.get(name)

    @staticmethod
    def add_manager(name: str, mgr_obj: object):
        """追加静态管理类到全局游戏管理器
        Args:
            name (str): 精灵的唯一标识名称（例如："player", "enemy_01"），用于后续引用和管理。
            mgr_obj (object): 精灵的基础表面对象（如图像、动画等）。
        """
        if GameManager.__manager_dict.get(name):
            return
        GameManager.__manager_dict[name] = mgr_obj

    @staticmethod
    def get_manager(name: str):
        """获取指定名称的静态类"""
        return GameManager.__manager_dict.get(name)

    @staticmethod
    def find(name: str):
        """模糊查询包含了名称的精灵列表"""
        __arr = []
        for key in GameManager.__render_dict.keys():
            if key.find(name):
                __arr.append(GameManager.__render_dict[key])
        return __arr

    @staticmethod
    def render():
        """全局游戏渲染管理器"""
        # 渲染地板
        for render in GameManager.__items_need_floor:
            render()

        # 渲染逻辑层
        for render in GameManager.__items_need_body:
            render()

        # 渲染遮罩（必须在 render() 之后）
        for render in GameManager.__items_need_mask:
            render()

        # 置顶的渲染
        for render in GameManager.__items_need_sticky:
            render()

    @staticmethod
    def find_path(target_pos: list[int], passable: list, start_pos=None, has_npc: bool = False):
        """
        寻路
        :param target_pos: 终点格子坐标
        :param passable: 可通行格子列表
        :param start_pos: 起点格子坐标（NPC时为NPC当前位置）
        :param has_npc: 是否为NPC寻路
        """
        if start_pos is None:
            start_pos = [0, 0]
        game_ui: GameUI = GameManager.get("游戏UI")
        if game_ui.has_un_allow_move():
            return []

        path_list = []

        if has_npc:
            # NPC 用这个寻路
            pathfinder = ThetaStarPathfinder(passable)  # ThetaStarPathfinder
            # NPC：直接计算路径，不遍历 find_path_list
            start = (start_pos[0], start_pos[1])
            end = (target_pos[0], target_pos[1])
            path = pathfinder.find_path(start, end)
            if path:
                path_list = path

        else:
            # 玩家：遍历 find_path_list（多主角跟随用）
            pathfinder = AStarPathfinder(passable)
            end = (target_pos[0], target_pos[1])
            for en in GameManager.find_path_list:
                get_pos = en.get("get_pos")
                if get_pos is None:
                    GameLogManager.log_service_debug("无法找到当前精灵的get_pos方法 @return (x,y)")
                    continue

                start = get_pos()
                path = pathfinder.find_path(start, end)
                if path:
                    en["move"](path)
                    path_list = path
                else:
                    GameLogManager.log_service_debug("寻路失败, 没有找到路径")

        return path_list

    @staticmethod
    def scene_to_global_pos_box(x: int, y: int, **args):
        """转屏幕坐标转为世界坐标,
        @return 地图格子索引
        """
        cameraPos = GameManager.game_camera.get_position()
        localX = int((x + cameraPos[0]) / GameManager.game_box_size)
        localY = int((y + cameraPos[1]) / GameManager.game_box_size)
        return [localX, localY]

    @staticmethod
    def scene_to_global_pos(x: int, y: int):
        """转屏幕坐标转为世界坐标,
        @return 地图的真实坐标
        """
        cameraPos = GameManager.game_camera.get_position()
        localX = (int(x) + cameraPos[0])
        localY = (int(y) + cameraPos[1])
        return [localX, localY]

    @staticmethod
    def scene_box_to_global_box(x: int, y: int):
        """
        将屏幕的格子坐标转换为世界格子坐标
        @param x: 屏幕格子坐标 X
        @param y: 屏幕格子坐标 Y
        @return: [世界格子坐标X, 世界格子坐标Y]
        """
        cameraPos = GameManager.game_camera.get_position()
        global_x = x + cameraPos[0] // GameManager.game_box_size
        global_y = y + cameraPos[1] // GameManager.game_box_size
        return [global_x, global_y]

    @staticmethod
    def global_to_scene_pos(x: int, y: int):
        """世界坐标转为屏幕坐标
        @return 屏幕的真实坐标
        """
        cameraPos = GameManager.game_camera.get_position()
        render_x = int(x) - cameraPos[0]
        render_y = int(y) - cameraPos[1]
        return [render_x, render_y]

    @staticmethod
    def logout():
        """
        游戏下线操作, 清空场景NPC 以及其他添加的类. 后续重新加进来
        :return:
        """
        from src.render.GameLogin import GameLogin
        GameManager.shop_system = None

        _map:"SpriteBase" = GameManager.get("地图")
        _map.destroy()
        # 取消相机挂载
        GameManager.game_camera.unmounted()
        GameManager.remove("地图")
        GameManager.remove("主角")
        GameMapManager.clear_map_npc()
        GameManager.add("登录页面", GameLogin(GameManager))
