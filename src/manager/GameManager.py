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
from typing import Dict, TYPE_CHECKING, Any

import pygame

from src.Mapper.FsoMapper import FsoMapper
from src.code.SpriteBase import SpriteBase
from src.lib.FindPath_Theta import ThetaStarPathfinder
from src.lib.FindPath_AStart import AStarPathfinder
from src.lib.TaskParingEngine import TaskParingEngine

from src.manager.GameFont import GameFont
from src.manager.GameLoadCsv import GameLoadCSV
from src.manager.GameLogManger import GameLogManager
from src.manager.LocalDBManager import LocalDBManager
from src.manager.SourceManager import SourceManager
from src.manager.GameWorldManager import GameWorldManager

from src.system.GameDialog import GameDialog
from src.system.GameMusic import GameMusicManager
from src.system.GameTipDialog import GameDialogBoxManager
from src.system.GameToast import GameToastManager
from src.system.ShopSystem import ShopSystem
from src.system.WeatherSystem import WeatherSystem
from src.system.ClickEffectSystem import ClickEffectSystem
from src.system.ForgeSystem import ForgeSystem

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

    game_camera: "GameCamera" = None
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

    game_local_db:LocalDBManager = None
    """游戏的本地存档"""

    __manager_dict = {}
    """全局游戏静态类管理映射"""
    shop_system: "ShopSystem" = None
    chat_system = None
    forge_system: "ForgeSystem" = None

    weather_sys:"WeatherSystem" = None
    """天气系统"""

    __items_need_floor = []
    __items_need_body = []
    __items_need_mask = []
    __items_need_sticky = []

    clock: pygame.Clock = None

    @classmethod
    def Awake(cls):
        from src.necessary.GameBattle import BattleManager
        pygame.key.start_text_input()
        SourceManager.Awake()
        cls.game_local_db = LocalDBManager()
        # 初始化消息管理器
        GameToastManager.Awake(cls.game_win.get_width(), cls.game_win.get_height(), cls)
        if cls.game_win_rect is None:
            cls.game_win_rect = cls.game_win.get_rect()

        if cls.game_camera is None:
            from src.manager.GameCamera import GameCamera
            cls.game_camera = GameCamera()
            cls.add("相机", cls.game_camera)

        # 初始化脚本
        load_cav_arr = ["npcs", "items", "item_type", "skills", "user_actor", "exp", "attribs",
                        "dungeons", "dungeon_monsters", "dungeon_spawn_groups"]
        for csv_name in load_cav_arr:
            if not os.path.exists(rf"{SourceManager.cfg_csv_path}/{csv_name}.csv"):
                GameLogManager.log_service_error(f"无法找到脚本:{csv_name}")
                continue
            has_raw = False
            if csv_name in ("item_type", "dungeon_monsters", "dungeon_spawn_groups"):
                has_raw = True
            SourceManager.set_csv(csv_name, GameLoadCSV.load(rf"{SourceManager.cfg_csv_path}/{csv_name}.csv"), has_raw)

        # 游戏的字体对象
        cls.game_font = GameFont.instance()
        cls.game_task_paring_engine = TaskParingEngine()
        cls.game_dialog = GameDialog(cls)
        GameMusicManager.Awake()
        GameDialogBoxManager.Awake(cls)
        BattleManager.Awake(cls)
        FsoMapper.Awake(cls)

        cls.weather_sys = WeatherSystem(cls)
        cls.add("天气系统", cls.weather_sys)
        cls.add("点击特效系统", ClickEffectSystem(cls))
        cls.forge_system = ForgeSystem(cls)
        cls.add("锻造系统", cls.forge_system)

    @classmethod
    def __refresh_layer(cls):
        """初始化渲染数组"""
        cls.__items_need_floor = [item.render_floor for item in cls.__render_list if item.render_floor]
        cls.__items_need_body = [item.render for item in cls.__render_list if item.render]
        cls.__items_need_mask = [item.render_mask for item in cls.__render_list if item.render_mask]
        cls.__items_need_sticky = [item.render_sticky for item in cls.__render_list if
                                   item.render_sticky]

    @classmethod
    def add(cls, name: str, sprite: SpriteBase):
        """追加精灵对象到全局游戏管理器
        Args:
            name (str): 精灵的唯一标识名称（例如："player", "enemy_01"），用于后续引用和管理。
            sprite (SpriteBase): 精灵的基础表面对象（如图像、动画等）。
        """
        if cls.__render_dict.get(name):
            return
        cls.__render_dict[name] = sprite
        cls.__render_list.append(sprite)
        # 每次最追加都根据精灵的层级排个序
        cls.__render_list.sort(key=lambda sur: sur.layer_order, reverse=False)
        #  初始化渲染数组
        cls.__refresh_layer()

    @classmethod
    def remove(cls, name: str | SpriteBase):
        """移除指定 的精灵资源"""
        if type(name) == str:
            sprite = cls.__render_dict.get(name)
            if sprite:
                cls.__render_list.remove(sprite)
                del cls.__render_dict[name]
        else:
            target = name
            for k in cls.__render_dict.keys():
                if cls.__render_dict.get(k) == target:
                    cls.__render_list.remove(target)
                    del cls.__render_dict[k]
                    # 初始化渲染数组
                    break

        cls.__refresh_layer()

    @classmethod
    def get(cls, name: str) -> Any:
        """获取指定名称的精灵"""
        return cls.__render_dict.get(name)

    @classmethod
    def add_manager(cls, name: str, mgr_obj: object):
        """追加静态管理类到全局游戏管理器
        Args:
            name (str): 精灵的唯一标识名称（例如："player", "enemy_01"），用于后续引用和管理。
            mgr_obj (object): 精灵的基础表面对象（如图像、动画等）。
        """
        if cls.__manager_dict.get(name):
            return
        cls.__manager_dict[name] = mgr_obj

    @classmethod
    def get_manager(cls, name: str):
        """获取指定名称的静态类"""
        return cls.__manager_dict.get(name)

    @classmethod
    def find(cls, name: str):
        """模糊查询包含了名称的精灵列表"""
        __arr = []
        for key in cls.__render_dict.keys():
            if key.find(name):
                __arr.append(cls.__render_dict[key])
        return __arr

    @classmethod
    def __is_passable_cell(cls, passable: list, x: int, y: int) -> bool:
        if not passable:
            return False
        if y < 0 or y >= len(passable):
            return False
        if x < 0 or x >= len(passable[y]):
            return False
        return str(passable[y][x]) != "0"

    @classmethod
    def __nearest_passable_cell(cls, passable: list, pos: tuple[int, int], max_radius: int = 8) -> tuple[int, int] | None:
        x, y = pos
        if cls.__is_passable_cell(passable, x, y):
            return pos
        for radius in range(1, max_radius + 1):
            candidates = []
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if max(abs(dx), abs(dy)) != radius:
                        continue
                    nx, ny = x + dx, y + dy
                    if cls.__is_passable_cell(passable, nx, ny):
                        candidates.append((nx, ny))
            if candidates:
                return min(candidates, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
        return None

    @classmethod
    def render(cls):
        """全局游戏渲染管理器"""
        # 渲染地板
        for render in cls.__items_need_floor:
            render()

        # 渲染逻辑层
        for render in cls.__items_need_body:
            render()

        # 渲染遮罩（必须在 render() 之后）
        for render in cls.__items_need_mask:
            render()

        # 置顶的渲染
        for render in cls.__items_need_sticky:
            render()

        GameWorldManager.update_timed_events()

    @classmethod
    def find_path(cls, target_pos: list[int], passable: list, start_pos=None, has_npc: bool = False):
        """
        寻路
        :param target_pos: 终点格子坐标
        :param passable: 可通行格子列表
        :param start_pos: 起点格子坐标（NPC时为NPC当前位置）
        :param has_npc: 是否为NPC寻路
        """
        if start_pos is None:
            start_pos = [0, 0]
        game_ui: "GameUI" = cls.get("游戏UI")
        if not has_npc:
            forge_system = getattr(cls, "forge_system", None)
            if forge_system and forge_system.blocks_player_move():
                return []
            if game_ui.has_un_allow_move():
                return []

        path_list = []

        if has_npc:
            # NPC 用这个寻路
            pathfinder = ThetaStarPathfinder(passable)  # ThetaStarPathfinder
            # NPC：直接计算路径，不遍历 find_path_list
            start = cls.__nearest_passable_cell(passable, (start_pos[0], start_pos[1]))
            end = cls.__nearest_passable_cell(passable, (target_pos[0], target_pos[1]))
            if start is None or end is None:
                return []
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

                start = cls.__nearest_passable_cell(passable, tuple(get_pos()))
                if start is None:
                    GameLogManager.log_service_debug("寻路失败, 当前角色附近没有可通行格子")
                    continue
                end = cls.__nearest_passable_cell(passable, end)
                if end is None:
                    GameLogManager.log_service_debug("寻路失败, 目标点附近没有可通行格子")
                    continue
                path = pathfinder.find_path(start, end)
                if path:
                    en["move"](path)
                    path_list = path
                else:
                    # GameMusicManager.play_sound("ui_fail")
                    GameLogManager.log_service_debug("寻路失败, 没有找到路径")

        return path_list

    @classmethod
    def scene_to_global_pos_box(cls, x: int, y: int):
        """转屏幕坐标转为世界坐标,
        @return 地图格子索引
        """
        camera_pos = cls.game_camera.get_position()
        local_x = int((x + camera_pos.x) / cls.game_box_size)
        local_y = int((y + camera_pos.y) / cls.game_box_size)
        return [local_x, local_y]

    @classmethod
    def scene_to_global_pos(cls, x: int, y: int):
        """转屏幕坐标转为世界坐标,
        @return 地图的真实坐标
        """
        camera_pos = cls.game_camera.get_position()
        local_x = (int(x) + camera_pos.x)
        local_y = (int(y) + camera_pos.y)
        return [local_x, local_y]


    @classmethod
    def global_to_scene_pos(cls, x: int, y: int):
        """世界坐标转为屏幕坐标
        @return 屏幕的真实坐标
        """
        camera_pos = cls.game_camera.get_position()
        render_x = int(x) - camera_pos.x
        render_y = int(y) - camera_pos.y
        return [render_x, render_y]

    @classmethod
    def scene_box_to_global_box(cls, x: int, y: int):
        """
        将屏幕的格子坐标转换为世界格子坐标
        @param x: 屏幕格子坐标 X
        @param y: 屏幕格子坐标 Y
        @return: [世界格子坐标X, 世界格子坐标Y]
        """
        camera_pos = cls.game_camera.get_position()
        global_x = x + camera_pos.x // cls.game_box_size
        global_y = y + camera_pos.y // cls.game_box_size
        return [global_x, global_y]


    @classmethod
    def world_box_to_scene_pos(cls, gx: int, gy: int):
        """
        【推荐使用】将世界网格坐标(gx, gy)直接转为当前屏幕上的像素坐标
        """
        camera_pos = cls.game_camera.get_position()
        # 1. 计算该格子在世界中的绝对像素位置
        world_pixel_x = gx * cls.game_box_size
        world_pixel_y = gy * cls.game_box_size

        # 2. 减去相机偏移，得到屏幕上的绘制位置
        render_x = world_pixel_x - camera_pos.x
        render_y = world_pixel_y - camera_pos.y
        return [render_x, render_y]

    @classmethod
    def logout(cls):
        """
        游戏下线操作, 清空场景NPC 以及其他添加的类. 后续重新加进来
        :return:
        """
        from src.manager.GameMapManager import GameMapManager
        from src.render.GameLogin import GameLogin
        from src.manager.DungeonManager import DungeonManager
        from src.system.TaskSystem import TaskManager
        DungeonManager.on_logout(cls.get("主角"))
        TaskManager.clear_temporary_tasks()
        if cls.chat_system:
            cls.chat_system.close()
            cls.chat_system = None
        if cls.shop_system:
            del cls.shop_system
            cls.shop_system = None
        if cls.weather_sys:
            cls.weather_sys.clear()

        game_ui: "GameUI" = cls.get("游戏UI")
        if game_ui:
            game_ui.remove_all_ui()
        _map: "SpriteBase" = cls.get("地图")
        if _map:
            _map.destroy()
        # 取消相机挂载
        cls.game_camera.unmounted()
        cls.remove("地图")
        cls.remove("主角")
        GameMapManager.clear_map_npc()
        cls.add("登录页面", GameLogin(cls))
