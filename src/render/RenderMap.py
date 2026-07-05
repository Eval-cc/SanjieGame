#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：RenderMap.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/2/13 下午9:28 
@Describe: 
"""
import random

from src.character.Player import Player
from src.manager.GameManager import *
from src.manager.GameMapManager import GameMapManager
from src.manager.SourceManager import *
from src.manager.GameEvent import GameEvent
from src.code.SpriteBase import SpriteBase
from typing import Dict
import math

from src.necessary.GameBattle import BattleManager


class RenderMap(SpriteBase):
    """渲染地图"""

    def __init__(self):
        super().__init__([["地图点击事件"], [1]])
        # 单帧素材的尺寸
        self.curr_one_ime_rect = None
        # 是否终止上一轮的障碍点绘制计算
        self.has_stop_grid_calculate = False

    def calculate(self):
        if self.curr_one_ime_rect is None:
            img = SourceManager.load(GameMapManager.game_map_surface_path()[0])
            self.width = img.get_width()
            self.height = img.get_height()
            self.rect = GameManager.game_win_rect
            # 单帧素材的尺寸
            self.curr_one_ime_rect = img.get_rect()

        # 获取当前页面单次渲染需要的图片数量-- 根据游戏的窗口大小计算, 并不是场景配置文件的row col
        scene_column = math.ceil(GameManager.game_win_rect.width / self.curr_one_ime_rect.width) + 1
        scene_row = math.ceil(GameManager.game_win_rect.height / self.curr_one_ime_rect.height) + 1

        camera_pos = GameManager.game_camera.get_position()
        map_size = GameMapManager.game_map_column_row_size()
        game_map = GameMapManager.game_map_surface_path()
        render_map = GameMapManager.game_map_render_map()
        for y in range(scene_row):
            for x in range(scene_column):
                offset_index_y = math.floor(camera_pos.y / self.curr_one_ime_rect.height)
                offset_index_x = math.floor(camera_pos.x / self.curr_one_ime_rect.width)
                map_index_y = (y * map_size[0]) + offset_index_y * map_size[0]
                map_index_x = offset_index_x + x + map_index_y
                if map_index_x >= len(game_map):
                    continue

                map_name_x: str = game_map[map_index_x]
                if render_map.get(map_name_x) is None:
                    surface = SourceManager.load(map_name_x)
                    render_x = x * surface.get_width() + (offset_index_x * surface.get_width())
                    if render_x >= GameManager.game_map_size[0]:
                        continue
                    #  更新地图块信息
                        # "map_name": f"{map_name_x} 动态加载地图[{GameMapManager.map_id}]",
                    GameMapManager.set_game_map_render_map(map_name_x, {
                        "map_index": map_index_x,
                        "map_name": f"块: {map_name_x}, 来自场景:[{GameMapManager.map_id}]",
                        "image": surface,
                        "x": render_x,
                        "y": y * surface.get_height() + (offset_index_y * surface.get_height()),
                    })

                    if GameManager.has_debug_render:
                        GameLogManager.log_service_debug(
                            f"动态加载地图:[{map_name_x}]) 完成,"
                            f"坐标:{render_map[map_name_x]["x"]},{render_map[map_name_x]["y"]}")

        # 创建地图格子缓存--未打开debug默认就不要执行了, 减少耗费性能
        if GameManager.has_debug_render:
            GameMapManager.grid_surface = self.create_grid_surface()
        # 创建遮罩缓存
        GameMapManager.mask_surface = self.create_map_mask()

    def render_floor(self):
        self.calculate()
        # 仅显示当前视图区域的地图
        # 获取当前页面单次渲染需要的图片数量
        scene_column = math.ceil(GameManager.game_win_rect.width / self.curr_one_ime_rect.width) + 1
        scene_row = math.ceil(GameManager.game_win_rect.height / self.curr_one_ime_rect.height) + 1

        camera_pos = GameManager.game_camera.get_position()
        offset_index_y = math.floor(camera_pos.y / self.curr_one_ime_rect.height)
        offset_index_x = math.floor(camera_pos.x / self.curr_one_ime_rect.width)
        map_size = GameMapManager.game_map_column_row_size()
        game_map = GameMapManager.game_map_surface_path()
        render_map = GameMapManager.game_map_render_map()
        for y in range(scene_column):
            map_index_y = (y * map_size[0]) + offset_index_y * map_size[0]
            for x in range(scene_row):
                map_index_x = offset_index_x + x + map_index_y
                if map_index_x >= len(game_map):
                    continue
                map_name_x = game_map[map_index_x]
                sur = render_map.get(map_name_x)
                if sur is None:
                    continue
                GameManager.game_win.blit(sur["image"], (sur["x"] - camera_pos.x, sur["y"] - camera_pos.y))
                # GameFont.render_multiple_text(f"{sur["map_name"]},[{sur["x"]},{sur["y"]}]", sur["x"] - camera_pos.x,
                #                               sur["y"] - camera_pos.y, 200,
                #                               True)

    def render_mask(self):
        if BattleManager.battle_sta():
            return
        if GameMapManager.grid_surface is not None:
            # 渲染计算的格子surface缓存
            GameManager.game_win.blit(
                GameMapManager.grid_surface,
                (0, 0),
                (0, 0, GameManager.game_win_rect.width, GameManager.game_win_rect.height)
            )
        if GameMapManager.mask_surface is not None:
            GameManager.game_win.blit(
                GameMapManager.mask_surface,
                (0, 0),
                (0, 0, GameManager.game_win_rect.width, GameManager.game_win_rect.height)
            )

        if GameManager.has_debug_render:
            scene_column = math.ceil(GameManager.game_win_rect.width / self.curr_one_ime_rect.width) + 1
            scene_row = math.ceil(GameManager.game_win_rect.height / self.curr_one_ime_rect.height) + 1

            camera_pos = GameManager.game_camera.get_position()
            offset_index_y = math.floor(camera_pos.y / self.curr_one_ime_rect.height)
            offset_index_x = math.floor(camera_pos.x / self.curr_one_ime_rect.width)

            # view_width = GameManager.game_win_rect.width  # 相机视野宽度（像素）
            # view_height = GameManager.game_win_rect.height  # 相机视野高度（像素）
            map_size = GameMapManager.game_map_column_row_size()
            game_map = GameMapManager.game_map_surface_path()
            render_map = GameMapManager.game_map_render_map()
            for y in range(scene_column):
                map_index_y = (y * map_size[0]) + offset_index_y * map_size[0]
                for x in range(scene_row):
                    map_index_x = offset_index_x + x + map_index_y
                    if map_index_x >= len(game_map):
                        continue
                    map_name_x = game_map[map_index_x]
                    sur = render_map.get(map_name_x)
                    if sur is None:
                        continue

                    render_x = sur["x"] - camera_pos.x
                    render_y = sur["y"] - camera_pos.y

                    # text_surface = GameFont.get_text_surface_line(f"遮罩点:[{mask["name"]}]",True, font_color="#00FF00",bolder=True,
                    #                                               mask_color='#BEBEBE')
                    GameFont.render_multiple_text_by_max_height(f"{sur["map_name"]},[{sur["x"]},{sur["y"]}]", render_x,
                                                                render_y, 300,
                                                                100,
                                                                baking=True, mask_color='#BEBE00')

    def mouse_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        super().mouse_down(event)
        if BattleManager.battle_sta():
            return False
        x, y = event["mouse_pos"]
        localX, localY = GameManager.scene_to_global_pos_box(x, y)
        # 执行寻路
        find_path = GameManager.find_path([localX, localY], GameMapManager.game_map_passable())
        if find_path:
            click_effect = GameManager.get("点击特效系统")
            if click_effect:
                world_x, world_y = GameManager.scene_to_global_pos(x, y)
                click_effect.add_world(world_x, world_y)

        # camera_pos = GameManager.game_camera.get_position()
        # GameLogManager.log_service_debug(f"""
        #     鼠标坐标: {[x, y]}
        #     世界坐标系: {[localX, localY]}
        #     真实世界坐标: {GameManager.scene_to_global_pos(x,y)}
        #     相机坐标: {camera_pos}
        #     寻路结果: {find_path}
        # """.strip().replace('\t',""))
        return True

    # 在初始化时创建网格 Surface
    def create_grid_surface(self):
        """创建地图格子"""
        if self.has_stop_grid_calculate or not GameManager.has_debug_render:
            return None
        passable = GameMapManager.game_map_passable()
        if len(passable) == 0:
            return None

        self.has_stop_grid_calculate = True
        # 获取相机坐标
        camera_pos = GameManager.game_camera.get_position()

        single_box = GameManager.game_box_size
        # 修正：使用正确的single_box分量计算索引
        offset_index_y = math.floor(camera_pos.y / single_box)  # y方向用height
        offset_index_x = math.floor(camera_pos.x / single_box)  # x方向用width

        # 计算相机视野范围内的格子范围
        view_width = GameManager.game_win_rect.width  # 相机视野宽度（像素）
        view_height = GameManager.game_win_rect.height  # 相机视野高度（像素）

        # 计算视野能覆盖多少个格子（更精确的计算）
        visible_cols = min(
            len(passable[0]),  # 不超过地图宽度
            math.ceil(view_width / single_box) + 2  # 多算2格确保覆盖边缘
        )
        visible_rows = min(
            len(passable),  # 不超过地图高度
            math.ceil(view_height / single_box) + 2  # 多算2格确保覆盖边缘
        )

        # 计算起始和结束的格子索引（更精确的边界检查）
        start_x = max(0, offset_index_x - 1)  # 多算1格确保左侧不漏
        start_y = max(0, offset_index_y - 1)  # 多算1格确保上方不漏
        end_x = min(len(passable[0]), offset_index_x + visible_cols)
        end_y = min(len(passable), offset_index_y + visible_rows)

        # 创建 Surface（使用视图尺寸）
        grid_surface = pygame.Surface((view_width, view_height), pygame.SRCALPHA)
        # 只遍历相机视野范围内的格子
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if passable[y][x] == "0":  # 如果该位置需要绘制
                    # 计算屏幕坐标（相对于相机位置）
                    screen_x = (x * single_box) - camera_pos.x
                    screen_y = (y * single_box) - camera_pos.y
                    # 确保只绘制在视图范围内的部分
                    if (0 <= screen_x < view_width and
                            0 <= screen_y < view_height):
                        ren_rect = (
                            screen_x,
                            screen_y,
                            single_box,
                            single_box
                        )
                        pygame.draw.rect(grid_surface, (255, 255, 255), ren_rect, 1)

        self.has_stop_grid_calculate = False
        return grid_surface

    def create_map_mask(self):
        """计算地图遮罩"""
        camera_pos = GameManager.game_camera.get_position()
        view_x, view_y = camera_pos.x,camera_pos.y
        # 计算相机视野范围内的格子范围
        view_width = GameManager.game_win_rect.width  # 相机视野宽度（像素）
        view_height = GameManager.game_win_rect.height  # 相机视野高度（像素）
        mask_surface = pygame.Surface((view_width, view_height), pygame.SRCALPHA)

        map_mask = GameMapManager.game_map_mask_data()
        for mask in map_mask.values():
            mask_x, mask_y = mask["x"] - view_x, mask["y"] - view_y
            if mask_x + mask.get("width") < 0 or mask_y + mask.get("height") < 0:
                continue
            mask_left, mask_right = mask["left"], mask["right"]
            mask_top, mask_bottom = mask["top"], mask["bottom"]

            if (mask_left <= view_x + view_width and  # 遮罩右边界 >= 相机左边界
                    mask_right >= view_x and  # 遮罩左边界 <= 相机右边界
                    mask_top <= view_y + view_height and  # 遮罩下边界 >= 相机上边界
                    mask_bottom >= view_y):  # 遮罩上边界 <= 相机下边界
                if mask.get("surface") is None and mask.get("path") is not None:
                    mask["surface"] = SourceManager.surface_scale(SourceManager.load(mask.get("path")),
                                                                  [mask.get("width"), mask.get("height")])
                if mask["surface"] is None:
                    continue
                mask_surface.blit(mask["surface"], (mask_x, mask_y))

                if GameManager.has_debug_render:
                    text_surface = GameFont.get_text_surface_line(f"遮罩点:[{mask["name"]}]", True,
                                                                  font_color="#00FF00", bolder=True,
                                                                  mask_color='#BEBEBE')
                    mask_surface.blit(text_surface, (mask_x, mask_y))
                    # mask_width, mask_height = mask["width"] , mask["height"]
                    # ren_rect = (
                    #     mask_x, mask_y,
                    #     mask_width, mask_height
                    # )
                    # pygame.draw.rect(mask_surface, (200, 200, 200), ren_rect, 1)
        return mask_surface

    def destroy(self):
        GameEvent.remove(f"地图点击事件_{self.UID}")
