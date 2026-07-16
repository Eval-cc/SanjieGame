#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：GameMapManager.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/6/15 09:30 
@Describe: 地图事件管理器
"""
import json
import os.path
import random
import pygame
from scipy.spatial import Delaunay
import numpy as np
from math import sqrt

from src.manager.GameLogManger import GameLogManager
from src.manager.GameLuaManager import GameLuaManager
import time

from src.manager.SourceManager import SourceManager

from typing import TYPE_CHECKING, Tuple, List, TypedDict, Dict

from src.system.GameMusic import GameMusicManager
from src.system.GameTipDialog import GameDialogBoxManager
from src.system.GameToast import GameToastManager

if TYPE_CHECKING:
    from src.character.NPC import NpcSprite
    from src.network.GameWorldServer import GameWorldServer
    from src.code.SpriteBase import SpriteBase


# 地图遮罩的类型
class MapMask(TypedDict):
    name: str
    x: int
    y: int
    left: int
    right: int
    top: int
    bottom: int
    width: int
    height: int
    path: str
    surface: pygame.Surface


class MapTile(TypedDict):
    map_index: int
    map_name: str
    image: pygame.Surface
    x: int
    y: int


class GameMapManager:
    map_timer = None
    """当前场景的lua定时器"""
    map_id: str = ""
    """地图ID"""
    scene_name: str = ""
    """当前场景名称"""

    __map_size = [0, 0]
    """地图格子-- 表示每行每列的帧数量- 切换地图的时候会根据场景配置文件初始化"""

    __frame_size = [0, 0]
    """单帧地图块的尺寸-- 生成场景的时候请务必确保每帧都一致"""
    last_execution_time = 0
    """添加一个类变量来记录上次执行的时间"""
    EXECUTION_INTERVAL = 1
    """定义lua脚本的定时器 时间间隔"""
    __map_timer_total = 0
    """当前场景的定时器计数"""

    __map_npc_dict = {}
    """当前地图的NPC信息"""

    __map: list[str] = []
    """当前场景的地图精灵"""
    __render_map: Dict[str, MapTile] = {}
    """实际渲染的地图"""
    __passable = []
    """地图障碍点数组"""
    grid_surface = None
    """场景格子缓存"""
    mask_surface = None
    """遮罩层surface"""

    __map_mask: dict[str:MapMask] = {}
    """地图遮罩数据, 存放遮罩数据"""

    NPC_RESTART_TIME = 1
    """记录NPC重生计时器间隔"""

    CURR_BATTLE_NPC_UID = []
    """"当前触发了战斗的npc uid"""

    @classmethod
    def point_in_polygon(point: Tuple[int, int], polygon: List[Tuple[int, int]]) -> bool:
        """修正版的射线法判断点是否在多边形内"""
        x, y = point
        n = len(polygon)
        inside = False

        # 缓存第一个点
        px, py = polygon[0]
        for i in range(1, n + 1):
            # 获取下一个点（循环处理）
            qx, qy = polygon[i % n]

            # 检查点的y坐标是否在边范围内
            if y > min(py, qy):
                if y <= max(py, qy):
                    if x <= max(px, qx):
                        # 处理水平线特殊情况
                        if py == qy:
                            # 点在水平边上则认为在内部
                            if min(px, qx) <= x <= max(px, qx):
                                return True
                        else:
                            # 计算水平交点
                            if px == qx or x <= (y - py) * (qx - px) / (qy - py) + px:
                                inside = not inside
            px, py = qx, qy

        return inside

    @classmethod
    def is_passable_grid(cls, x: int, y: int) -> bool:
        """判断地图格子是否可通行."""
        if not cls.__passable:
            return False
        if y < 0 or y >= len(cls.__passable):
            return False
        if x < 0 or x >= len(cls.__passable[y]):
            return False
        return str(cls.__passable[y][x]) != "0"

    @classmethod
    def nearest_passable_grid(cls, x: int, y: int, max_radius: int = 8) -> tuple[int, int] | None:
        """返回目标格或目标附近最近的可通行格."""
        if cls.is_passable_grid(x, y):
            return x, y

        for radius in range(1, max_radius + 1):
            candidates = []
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if max(abs(dx), abs(dy)) != radius:
                        continue
                    nx, ny = x + dx, y + dy
                    if cls.is_passable_grid(nx, ny):
                        candidates.append((nx, ny))
            if candidates:
                return min(candidates, key=lambda p: (p[0] - x) ** 2 + (p[1] - y) ** 2)
        return None

    @classmethod
    def normalize_world_pos(cls, target_x: int, target_y: int, max_radius: int = 8) -> dict:
        """按地图障碍数据修正世界坐标."""
        from src.manager.GameManager import GameManager

        box_size = GameManager.game_box_size
        grid_x = int(target_x // box_size)
        grid_y = int(target_y // box_size)
        result = {
            "world_x": int(target_x),
            "world_y": int(target_y),
            "grid_x": grid_x,
            "grid_y": grid_y,
            "adjusted": False,
        }

        if not cls.__passable:
            return result

        passable_grid = cls.nearest_passable_grid(grid_x, grid_y, max_radius)
        if passable_grid is None:
            raise ValueError(f"目标坐标附近没有可通行格子: {grid_x},{grid_y}")

        passable_x, passable_y = passable_grid
        if passable_x != grid_x or passable_y != grid_y:
            result["world_x"] = passable_x * box_size
            result["world_y"] = passable_y * box_size
            result["grid_x"] = passable_x
            result["grid_y"] = passable_y
            result["adjusted"] = True
        return result

    @classmethod
    def move_player_in_current_map(cls, target_x: int, target_y: int) -> dict:
        """在当前地图移动主角, 不重新加载地图."""
        from src.manager.GameManager import GameManager

        player = GameManager.get("主角")
        if player is None:
            raise ValueError("当前没有可移动的角色")

        result = cls.normalize_world_pos(target_x, target_y)
        w_server: "GameWorldServer" = GameManager.get_manager("w_server")
        if w_server and getattr(w_server, "connected", False) and hasattr(w_server, "send_moveto"):
            w_server.send_moveto(result["world_x"], result["world_y"])
            result["mode"] = "network"
            return result

        try:
            player.set_pos(result["world_x"], result["world_y"], notify_server=False)
        except TypeError:
            player.set_pos(result["world_x"], result["world_y"])
        result["mode"] = "local"
        return result

    @classmethod
    def move_player_to(cls, map_name: str | None, target_x: int = None, target_y: int = None) -> dict:
        """移动主角到目标地图/坐标, 当前地图内不触发地图重载."""
        if map_name is None or str(map_name) == str(cls.map_id):
            if target_x is None or target_y is None:
                return {"mode": "noop", "map_id": cls.map_id}
            result = cls.move_player_in_current_map(target_x, target_y)
            result["map_id"] = cls.map_id
            return result

        cls.change_map(map_name, target_x, target_y)
        return {
            "mode": "map_changed",
            "map_id": map_name,
            "world_x": target_x,
            "world_y": target_y,
        }

    @classmethod
    def generate_spawn_points(cls, config: dict):
        """基于三角剖分的多边形刷怪点生成"""
        spawn_areas = config.get("spawn_areas", [])

        for area_cfg in spawn_areas:
            monster_id = area_cfg["monster_id"]
            polygon = area_cfg["polygon"]
            max_count = int(area_cfg.get("max_count", 1))

            if len(polygon) < 3:
                continue  # 不是有效多边形

            # 转换为numpy数组
            points = np.array(polygon, dtype=np.float32)

            # 三角剖分 (自动处理凸/凹多边形)
            try:
                tri = Delaunay(points)
            except Exception as ex:
                GameLogManager.log_service_debug(f"生成三角区域的刷怪点出错:{ex}, 已跳过")
                continue

            # 计算每个三角形的面积
            triangles = points[tri.simplices]
            vectors = triangles[:, 1:] - triangles[:, :1]
            areas = 0.5 * np.abs(np.cross(vectors[:, 0], vectors[:, 1]))
            total_area = np.sum(areas)

            if total_area <= 0:
                GameLogManager.log_service_debug(f"该刷怪点属于 零面积区域, 已跳过")
                continue

            # 按面积比例分配每个三角形要生成的数量
            counts = np.random.multinomial(
                max_count,
                areas / total_area
            )

            # 在每个三角形内生成指定数量的点
            generated = 0
            for i, count in enumerate(counts):
                if count == 0:
                    continue
                # 获取当前三角形的三个顶点
                a, b, c = triangles[i]
                for _ in range(count):
                    # 在三角形内均匀随机采样
                    r1, r2 = random.random(), random.random()
                    x = (1 - sqrt(r1)) * a[0] + sqrt(r1) * (1 - r2) * b[0] + sqrt(r1) * r2 * c[0]
                    y = (1 - sqrt(r1)) * a[1] + sqrt(r1) * (1 - r2) * b[1] + sqrt(r1) * r2 * c[1]

                    cls.add_npc(monster_id, int(x), int(y), 0)
                    generated += 1

            if generated < max_count:
                GameLogManager.log_service_debug(f"怪物生成警告：{monster_id} 实际生成 {generated}/{max_count}")

    @classmethod
    def change_map(cls, map_name: str, target_x: int = None, target_y: int = None):
        """
        切换游戏地图
        :param map_name: 新场景的id
        :param target_x: 切换场景之后, 主角需要出现的x坐标
        :param target_y: 切换场景之后, 主角需要出现的y坐标
        :return:
        """
        from src.manager.GameManager import GameManager
        from src.manager.DungeonManager import DungeonManager

        cls.clear_map_npc()  # 把之前的NPC给移除掉
        DungeonManager.clear_current_map_spawns()
        cls.map_id = map_name
        cls.scene_name = str(map_name)
        GameManager.game_camera.unmounted()  # 卸载相机挂载
        is_dungeon_map = DungeonManager.is_in_dungeon() and str(map_name) == str(
            DungeonManager.active_instance.template.map_id
        )

        map_cfg_path = fr"{SourceManager.cfg_map_path}/map/{map_name}.json"
        if os.path.exists(map_cfg_path):
            """读取地图的配置表"""
            with open(map_cfg_path, "r", encoding="utf8") as f:
                map_cfg = json.load(f)
                if not is_dungeon_map:
                    npc_list = map_cfg.get("npc", [])
                    for nd in npc_list:
                        nid = nd.get("id")
                        position = nd.get("position")
                        _npc = GameMapManager.add_npc(nid, position[0], position[1], 0)
                        if nd.get("task"):
                            _npc.default_dialog = nd.get("task")
                    # 生成刷怪区域
                    GameMapManager.generate_spawn_points(map_cfg)

                w, h, column, row, frame_w, frame_h = [map_cfg.get("map_width", None), map_cfg.get("map_height", None),
                                                       map_cfg.get("map_tile_column", None),
                                                       map_cfg.get("map_tile_row", None),
                                                       map_cfg.get("map_tile_width", None),
                                                       map_cfg.get("map_tile_height", None)
                                                       ]
                if w is None or h is None or column is None or row is None:
                    GameLogManager.log_service_error(f"出错了,请确保地图的配置文件关于场景的 [尺寸 ,行列] 计数是否合法")
                    raise Exception(f"出错了,请确保地图的配置文件是否合法")

                cls.scene_name = map_cfg.get("scene_name") or str(map_name)
                GameMapManager.__map_size = [column, row]
                GameMapManager.__frame_size = [frame_w, frame_h]

                # 这里的宽高表示地图帧 对于的行和列数量
                GameManager.game_map_size = [w, h]
                # 场景音乐
                scene_music = map_cfg.get("music")
                if scene_music:
                    GameMusicManager.play_bgm(scene_music)
                else:
                    GameMusicManager.pause_bgm()
                # 加载天气系统
                if map_cfg.get("environment"):
                    weather_type = map_cfg.get("environment").get("weather")
                    GameManager.weather_sys.setWeather(weather_type)
                elif GameManager.weather_sys:
                    GameManager.weather_sys.clear()

        else:
            GameLogManager.log_service_error(f"未找到当前地图[{map_name}]的json配置文件")
            raise FileNotFoundError(f"未找到当前地图[{map_name}]的json配置文件")
        # 通知服务器.我换场景了
        w_server: "GameWorldServer" = GameManager.get_manager("w_server")
        if w_server:
            w_server.change_room(map_name)

        # 读取当前场景的lua脚本
        lua_obj = GameLuaManager.load_map_lua(map_name)
        if lua_obj is not None:
            # 挂载定时器方法
            cls.map_timer = lua_obj.OnTimer
            cls.__map_timer_total = 0  # 重置计数器
            if lua_obj.OnCreate:
                # 开始执行地图lua的初始化脚本方法, 切换地图的时候执行一次. 可用于刷新特殊精灵.  比如用于副本场景,
                lua_obj.OnCreate(cls)

        map_path = fr"{SourceManager.ui_map_path}/{map_name}"
        # 存放当前地图的所有资源块
        cls.__map = [
            f"{map_path}/{str(row).rjust(5, '0')}.png"
            for row in range(cls.__map_size[0] * cls.__map_size[1])
        ]

        # 重置实际渲染的地图
        cls.__render_map.clear()
        cls.grid_surface = None
        # 遮罩层surface
        cls.mask_surface = None
        """读取地图的障碍点"""
        cls.__passable.clear()
        # 清空遮罩
        cls.__map_mask.clear()

        try:
            with open(map_path + "/passable.txt", "r") as f:
                map_pass_list = f.read().split("\n")
                for pa in map_pass_list:
                    if len(pa) == 0:
                        continue
                    cls.__passable.append(list(pa))
        except Exception as e:
            GameToastManager.add_message(f"读取地图障碍文件出错")
            GameLogManager.log_service_error(f"读取地图障碍文件出错, {e}")

        """读取遮罩数据"""
        try:
            with open(f"{map_path}/mask/mask.txt", "r") as f:
                mask_data = f.read().split("\n")
                for m in range(len(mask_data)):
                    data = mask_data[m]
                    if len(data) == 0:
                        continue
                    if data.lstrip().startswith("#"):
                        continue
                    map_arr = data.split(",")
                    mask_name = str(m).rjust(5, "0")
                    cls.__map_mask[mask_name] = {
                        "name": mask_name,
                        "x": int(map_arr[0]),
                        "y": int(map_arr[1]),
                        "left": int(map_arr[0]),
                        "right": int(map_arr[0]) + int(map_arr[2]),
                        "top": int(map_arr[1]),
                        "bottom": int(map_arr[1]) + int(map_arr[3]),
                        "width": int(map_arr[2]),
                        "height": int(map_arr[3]),
                        "path": f"{map_path}/mask/{mask_name}.png",
                        "surface": None
                    }
        except  Exception as e:
            GameLogManager.log_service_error(f"读取遮罩文件出错, {e}")

        u_player: "SpriteBase" = GameManager.get("主角")
        if u_player:
            # 是否需要移动主角的坐标
            if target_x is not None and target_y is not None:
                u_player.set_pos(target_x, target_y)
            # 挂载相机
            GameManager.game_camera.mounted(u_player)
            if hasattr(u_player, "update_blit_map"):
                u_player.update_blit_map = True
        else:
            GameDialogBoxManager.dialog("无法执行相机挂载. 未找到角色信息")

        if is_dungeon_map:
            DungeonManager.populate_current_map()

    @classmethod
    def game_map_passable(cls) -> list:
        """得到地图障碍点信息"""
        return GameMapManager.__passable

    @classmethod
    def game_map_mask_data(cls) -> dict:
        """得到地图遮罩信息"""
        return cls.__map_mask

    @classmethod
    def game_map_npcs(cls) -> list["NpcSprite"]:
        """得到当前地图的NPC/怪物列表"""
        return list(cls.__map_npc_dict.values())

    @classmethod
    def map_scene_name(cls) -> str:
        """得到当前场景显示名称"""
        return cls.scene_name or str(cls.map_id)

    @classmethod
    def game_map_surface_path(cls) -> list[str]:
        """得到当前地图的所有地图块的路径"""
        return cls.__map

    @classmethod
    def game_map_column_row_size(cls) -> list[int]:
        """得到当前地图的 row 和 col 的数量"""
        return cls.__map_size

    # cls.
    @classmethod
    def game_map_tile_size(cls) -> list[int]:
        """得到当前地图的单帧地图块的尺寸"""
        return cls.__frame_size

    @classmethod
    def game_map_render_map(cls):
        """返回实际的渲染地图"""
        return cls.__render_map

    @classmethod
    def set_game_map_render_map(cls, tile_name: str, tile_data: MapTile):
        """更新实际的渲染地图"""
        cls.__render_map[tile_name] = tile_data

    @classmethod
    def loop(cls):
        """
        1s执行一次
        :return:
        """
        current_time = time.time()
        # 检查是否已经过了足够的时间间隔
        if cls.map_timer and (
                current_time - cls.last_execution_time) >= cls.EXECUTION_INTERVAL:
            cls.map_timer(cls, cls.map_id, cls.__map_timer_total)
            # 更新最后执行时间
            cls.last_execution_time = current_time

            cls.__map_timer_total += 1

        # for _npc_k in cls.__map_npc_dict.keys():
        #     npc: NpcSprite = cls.__map_npc_dict[_npc_k]
        #     if npc.restart_time > 0:
        #         # 是否死亡
        #         if npc.npc_state == SpriteState.DEAD:
        #             if current_time - cls.last_execution_time >= cls.NPC_RESTART_TIME:
        #                 npc.re_curr_time += cls.NPC_RESTART_TIME
        #                 if npc.re_curr_time >= npc.restart_time:
        #                     # TODO: 复活
        #                     pass
        # cls.AddNpc(npc.ID, npc.scene_pos[0], npc.scene_pos[1], npc.direction)

    @classmethod
    def add_npc(cls, npc_id: str | int, x: int, y: int, direction: int):
        """追加NPC"""
        from src.character.NPC import NpcSprite
        from src.manager.GameManager import GameManager
        npc_data = SourceManager.get_csv("npcs", npc_id)
        npc = NpcSprite(npc_data, x, y, direction)

        cls.__map_npc_dict[npc.UID] = npc
        GameManager.add(npc.UID, npc)
        GameLogManager.log_service_debug(f"地图[{cls.map_id}]  坐标:[{x},{y}] 生成NPC:{npc.name}")
        return npc

    @classmethod
    def log(cls, msg: str):
        GameLogManager.log_service_debug(f"场景信息:{msg}")

    @classmethod
    def clear_map_npc(cls):
        """移除当前场景的NPC"""
        from src.manager.GameManager import GameManager
        for nid in cls.__map_npc_dict.keys():
            npc: "NpcSprite" = cls.__map_npc_dict.get(nid)
            npc.destroy()
            GameManager.remove(nid)

        cls.__map_npc_dict.clear()

    @classmethod
    def remove_map_npc(cls, uid: str):
        """移除指定uid的NPC"""
        from src.manager.GameManager import GameManager
        from src.manager.DungeonManager import DungeonManager
        GameManager.remove(uid)

        npc: "NpcSprite" = cls.__map_npc_dict.get(uid)
        if npc:
            DungeonManager.on_map_npc_removed(npc)
            npc.destroy()
            del cls.__map_npc_dict[uid]
        if uid in cls.CURR_BATTLE_NPC_UID:
            cls.CURR_BATTLE_NPC_UID.remove(uid)
