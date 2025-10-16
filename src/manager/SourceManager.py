#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：SourceManager.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/2/13 下午9:29 
@Describe: 
"""
import os
import sys
from typing import Dict
from copy import deepcopy

import pygame

from src.manager.GameLogManger import GameLogManager


class SourceManager:
    """资源管理器"""
    __source_dict: Dict[str, pygame.Surface] = {}
    __csv_dict:Dict[str,dict] = {}
    """存放csv的资源"""
    ui_face_path = r"Graphics\Faces"
    """头像资源目录"""
    ui_map_path = r"Graphics\Maps"
    """地图资源目录"""
    ui_item_path = r"Graphics\Icons\items"
    """道具图标资源目录"""
    ui_skill_path = r"Graphics\Icons\skills"
    """技能图标资源目录"""
    ui_npc_path = r"Graphics\Characters"
    """npc贴图资源目录"""
    ui_system_path = r"Graphics\System"
    """系统相关的UI资源目录"""
    ui_battle_path = r"Graphics\Battlers"
    """战斗相关的UI"""
    ui_animation_path = r"Graphics\Animations"
    """特性动画相关的UI"""

    cfg_csv_path = r"resources\sv_table"
    """csv配置脚本目录"""
    cfg_lua_path = r"resources\scripts"
    """Lua脚本目录"""
    cfg_map_path = r"resources\config"
    """地图json配置脚本目录"""
    cfg_task_path = r"resources\sv_task"
    """对话脚本目录"""
    cfg_root_path = "resources"
    """资源包目录"""

    log_root_path = "logs"

    @staticmethod
    def Awake():
        # 如果是开发生产环境
        game_root = os.path.dirname(os.path.abspath(sys.argv[0]))

        # 重写所有路径为绝对路径- 解决打包之后无法找打资源的问题
        SourceManager.ui_face_path = os.path.join(game_root, "Graphics/Faces")
        SourceManager.ui_map_path = os.path.join(game_root, "Graphics/Maps")
        SourceManager.ui_item_path = os.path.join(game_root, "Graphics/Icons/items")
        SourceManager.ui_skill_path = os.path.join(game_root, "Graphics/Icons/skills")
        SourceManager.ui_npc_path = os.path.join(game_root, "Graphics/Characters")
        SourceManager.ui_system_path = os.path.join(game_root, "Graphics/System")
        SourceManager.ui_battle_path = os.path.join(game_root, "Graphics/Battlers")
        SourceManager.ui_animation_path = os.path.join(game_root, "Graphics/Animations")

        SourceManager.cfg_csv_path = os.path.join(game_root, "resources/sv_table")
        SourceManager.cfg_lua_path = os.path.join(game_root, "resources/scripts")
        SourceManager.cfg_map_path = os.path.join(game_root, "resources/config")
        SourceManager.cfg_task_path = os.path.join(game_root, "resources/sv_task")
        SourceManager.cfg_root_path = os.path.join(game_root, "resources")

        SourceManager.log_root_path = os.path.join(game_root, "logs")

    @staticmethod
    def load(file_path: str, scale:list[int] = None):
        """
        加载Graphics目录下面的资源
        @file_path 文件路径
        @scale 缩放的宽高
        """
        root_path = os.path.join(os.getcwd(), file_path)
        if not os.path.exists(root_path):
            raise Exception(f"不存在的资源路径,{root_path}")
        file_name = os.path.basename(root_path)
        if SourceManager.__source_dict.get(file_path):
            # 是否指定了缩放
            if scale:
                return SourceManager.surface_cale(SourceManager.__source_dict[file_path], scale)
            return SourceManager.__source_dict[file_path]
        try:
            if file_name.lower().endswith(".png"):
                SourceManager.__source_dict[file_path] = pygame.image.load(root_path).convert_alpha()
            elif file_name.lower().endswith(".jpg"):
                SourceManager.__source_dict[file_path] = pygame.image.load(root_path)
            else:
                raise Exception(f"暂不支持的文件类型,{file_name.split(".").pop()}")
            # 是否指定了缩放
            if scale:
                return SourceManager.surface_cale(SourceManager.__source_dict[file_path], scale)
            return SourceManager.__source_dict[file_path]
        except pygame.error as e:
            if str(e).find("Unsupported image format") >= 0:
                GameLogManager.log_service_error(f"加载资源出错,来自pygame模块的异常,{e}, 无法加载资源")
                return
            GameLogManager.log_service_error(f"加载资源出错,来自pygame模块的异常,{e}")
        except Exception as e:
            GameLogManager.log_service_error(f"加载资源出错了, {e}")

    @staticmethod
    def remove(file_path: str):
        """移除资源"""
        if SourceManager.__source_dict.get(file_path):
            del SourceManager.__source_dict[file_path]
            return True
        return False

    @staticmethod
    def copy(file_path: str, new_path: str):
        """复制资源为新的对象"""
        if file_path == new_path:
            return
        if SourceManager.__source_dict.get(file_path):
            SourceManager.__source_dict[new_path] = SourceManager.__source_dict.get(file_path).copy()
            return SourceManager.__source_dict[new_path]
        return None

    @staticmethod
    def export_surface(surface:pygame.Surface, out_path:str, out_name:str, mkdir: bool = False):
        """将surface导出为本地文件,需要携带后缀"""
        if not os.path.isdir(out_path):
            if not mkdir:
                GameLogManager.log_service_error(f"无法导出surface,不存在的目录:{out_path}")
                return False
            # 创建目录
            os.makedirs(out_path)
        pygame.image.save(surface,f"{out_path}/{out_name}")
        return True

    @staticmethod
    def get_csv(csv_name:str, find_id:str = None):
        """获取指定csv配置文件"""
        if find_id:
            return deepcopy(SourceManager.__csv_dict.get(csv_name).get(str(find_id)))
        return deepcopy(SourceManager.__csv_dict.get(csv_name))

    @staticmethod
    def set_csv(csv_name:str,csv_data:list, has_raw:bool = False):
        """更新csv配置文件信息"""
        if len(csv_data) == 0:
            GameLogManager.log_service_error("无效的csv列表数据")
            return

        # 特殊数据不需要序列化? 那就直接存储源数据
        if has_raw:
            SourceManager.__csv_dict[csv_name] = csv_data
            return
        # 数组的首位元素列表是 表头字段, 弹出来
        head_list = csv_data.pop(0)
        dict_list  = [dict(zip(head_list, values)) for values in csv_data]
        SourceManager.__csv_dict[csv_name] = {val.get("ID"): val for val in dict_list}


    @staticmethod
    def surface_cale(surface:pygame.Surface,size:list[float|int]):
        """平滑的将surface缩放到任意大小"""
        if surface is None:
            return surface
        return pygame.transform.smoothscale(surface,size)

    @staticmethod
    def create_surface_mask(surface:pygame.Surface):
        """给精灵生成遮罩计算"""
        if type(surface) != pygame.surface.Surface:
            raise Exception(f"获取遮罩错误,请传入正确的surface对象, 当前:[{type(surface)}]")
        if surface is None:
            return surface
        return pygame.mask.from_surface(surface)

    @staticmethod
    def set_surface_alpha(surface:pygame.Surface, alpha:int = 255):
        """调整精灵的透明通道"""
        sur = surface.copy()
        sur.set_alpha(alpha)
        return sur
