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
import json
import os
import sys
from typing import Dict
from copy import deepcopy
import imageio
import pygame

from src.manager.GameLogManger import GameLogManager


class SourceManager:
    """资源管理器"""
    __source_dict: Dict[str, pygame.Surface] = {}
    __csv_dict: Dict[str, dict] = {}
    __offset_cfg_dict: Dict[str, list[dict]] = {}
    """ui资源的根目录"""
    ui_root_path = r"Graphics"
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
    cfg_ui_path = r"resources\language\ui"
    """游戏UI目录"""
    cfg_db_path = r"resources\config\db"
    """游戏本地数据库目录"""
    cfg_animation_offset_path = r"resources\animation_offset"
    """游戏精灵偏移值目录"""
    cfg_root_path = "resources"
    """资源包目录"""

    audio_root_path = "audio"
    """音效根目录"""
    audio_dream_bgm_path = r"audio\BGM"
    """梦幻背景音乐根目录"""
    audio_dream_source_path = r"audio\SE"
    """梦幻音效根目录"""
    audio_zfs_bgm_path = r"audio\zfs_BGM"
    """zfs背景音乐根目录"""
    audio_zfs_source_path = r"audio\zfsSE"
    """zfs音效根目录"""

    log_root_path = "logs"

    @classmethod
    def Awake(cls):
        # 如果是生产环境
        game_root = os.path.dirname(os.path.abspath(sys.argv[0]))

        # 重写所有路径为绝对路径- 解决打包之后无法找到资源的问题
        SourceManager.ui_root_path = os.path.join(game_root, "Graphics")
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
        SourceManager.cfg_ui_path = os.path.join(game_root, r"resources\language\ui")
        SourceManager.cfg_db_path = os.path.join(game_root, r"resources\config\db")
        SourceManager.cfg_animation_offset_path = os.path.join(game_root, cls.cfg_animation_offset_path)

        SourceManager.cfg_root_path = os.path.join(game_root, "resources")

        SourceManager.log_root_path = os.path.join(game_root, "logs")

        SourceManager.audio_root_path = os.path.join(game_root, "audio")
        SourceManager.audio_dream_bgm_path = os.path.join(game_root, "audio/BGM")
        SourceManager.audio_dream_source_path = os.path.join(game_root, "audio/SE")
        SourceManager.audio_zfs_bgm_path = os.path.join(game_root, r"audio\zfs_BGM")
        SourceManager.audio_zfs_source_path = os.path.join(game_root, r"audio\zfsSE")

    @staticmethod
    def load_gif_as_atlas(gif_path, frame_padding=0):
        """
        将GIF所有帧拼接成单个大Surface（水平排列）
        参数:
        gif_path: GIF文件路径
        frame_padding: 帧间距（像素）

        返回:
        (surface, frame_rects)
        - surface: 包含所有帧的PyGame Surface
        - frame_rects: 每帧在surface中的位置列表[pygame.Rect, ...]
        """
        # 1. 读取 GIF
        gif_frames = imageio.mimread(gif_path)
        if not gif_frames:
            return None

        # 2. 预计算尺寸 (直接从原始帧获取)
        # imageio 返回的是 (H, W, C)
        max_w = max(f.shape[1] for f in gif_frames)
        max_h = max(f.shape[0] for f in gif_frames)
        count = len(gif_frames)

        total_width = (max_w + frame_padding) * count - frame_padding

        # 3. 创建大 Surface (保持开启 SRCALPHA)
        atlas_surface = pygame.Surface((total_width, max_h), pygame.SRCALPHA)
        frame_rects = []

        for i, frame in enumerate(gif_frames):
            # 处理颜色空间 (imageio 读取的是 RGB 或 RGBA)
            if frame.shape[2] == 3:
                # RGB -> RGBA
                temp_surface = pygame.image.fromstring(frame.tobytes(), (frame.shape[1], frame.shape[0]),
                                                       'RGB').convert_alpha()
            else:
                temp_surface = pygame.image.fromstring(frame.tobytes(), (frame.shape[1], frame.shape[0]),
                                                       'RGBA').convert_alpha()

            # 4. 关键点：统一缩放到最大帧尺寸，防止不贴合
            if temp_surface.get_size() != (max_w, max_h):
                temp_surface = pygame.transform.smoothscale(temp_surface, (max_w, max_h))

            x_pos = i * (max_w + frame_padding)
            # 强制 (x, 0) 起始，不再使用 (max_height - h) // 2
            rect = pygame.Rect(x_pos, 0, max_w, max_h)
            atlas_surface.blit(temp_surface, rect)
            frame_rects.append(rect)

        return {
            "surface": atlas_surface,
            "rects": frame_rects,
            "len": count
        }

    @staticmethod
    def load(file_path: str, scale: list[int] = None):
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
                return SourceManager.surface_scale(SourceManager.__source_dict[file_path], scale)
            return SourceManager.__source_dict[file_path]
        try:
            if file_name.lower().endswith(".png"):
                SourceManager.__source_dict[file_path] = pygame.image.load(root_path).convert_alpha()
            elif file_name.lower().endswith(".jpg"):
                SourceManager.__source_dict[file_path] = pygame.image.load(root_path)


            elif file_name.lower().endswith(".gif"):
                sur = SourceManager.load_gif_as_atlas(root_path)

                if scale:
                    target_w, target_h = scale[0], scale[1]
                    frame_count = sur.get("len")
                    # 2. 重新计算总宽度，确保不丢失精度
                    total_scale_w = target_w * frame_count
                    sur["surface"] = SourceManager.surface_scale(sur.get("surface"), [total_scale_w, target_h])

                    # 因为旧 rects 包含了居中偏移量，我们要的是铺满整个 target_h
                    new_rects = []
                    for i in range(frame_count):
                        # 严格平分，起始点从 0 开始，高度填满 target_h
                        rect = pygame.Rect(i * target_w, 0, target_w, target_h)
                        new_rects.append(rect)
                        curr_skill_bg = sur["surface"].subsurface(rect)
                    sur["rects"] = new_rects
                return sur
            else:
                raise Exception(f"暂不支持的文件类型,{file_name.split(".").pop()}")
            # 是否指定了缩放
            if scale:
                return SourceManager.surface_scale(SourceManager.__source_dict[file_path], scale)
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
    def export_surface(surface: pygame.Surface, out_path: str, out_name: str, mkdir: bool = False):
        """将surface导出为本地文件,需要携带后缀"""
        if not os.path.isdir(out_path):
            if not mkdir:
                GameLogManager.log_service_error(f"无法导出surface,不存在的目录:{out_path}")
                return False
            # 创建目录
            os.makedirs(out_path)
        pygame.image.save(surface, f"{out_path}/{out_name}")
        return True

    @staticmethod
    def get_csv(csv_name: str, find_id: str = None):
        """获取指定csv配置文件"""
        if find_id:
            return deepcopy(SourceManager.__csv_dict.get(csv_name).get(str(find_id)))
        return deepcopy(SourceManager.__csv_dict.get(csv_name))

    @staticmethod
    def set_csv(csv_name: str, csv_data: list, has_raw: bool = False):
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
        dict_list = [dict(zip(head_list, values)) for values in csv_data]
        SourceManager.__csv_dict[csv_name] = {val.get("ID"): val for val in dict_list}
        GameLogManager.log_service_debug(f"加载脚本: {csv_name} 完成")

    @staticmethod
    def surface_scale(surface: pygame.Surface, size: list[float | int]):
        """平滑的将surface缩放到任意大小"""
        if surface is None:
            return surface
        return pygame.transform.smoothscale(surface, tuple(size))

    @staticmethod
    def create_surface_mask(surface: pygame.Surface):
        """给精灵生成遮罩计算"""
        if type(surface) != pygame.surface.Surface:
            raise Exception(f"获取遮罩错误,请传入正确的surface对象, 当前:[{type(surface)}]")
        if surface is None:
            return surface
        return pygame.mask.from_surface(surface)

    @staticmethod
    def set_surface_alpha(surface: pygame.Surface, alpha: int = 255):
        """调整精灵的透明通道"""
        sur = surface.copy()
        sur.set_alpha(alpha)
        return sur

    @classmethod
    def load_sprite_offset_config(cls, name: str):
        """
        返回指定精灵的偏移配置参数
        :param name:
        :return:
        """
        data = cls.__offset_cfg_dict.get(name)
        if data:
            return data
        base_dir = os.path.join(cls.cfg_animation_offset_path, f"{name}.json")
        if not os.path.exists(base_dir):
            return None
        with open(base_dir, "r", encoding="utf-8") as f:
            jsonc = json.load(f)
            # 提前转换一下, 逻辑直接用
            da = [{"offX": int(curr["offX"]), "offY": int(curr["offY"])} for curr in jsonc.get("frames", [])]
            cls.__offset_cfg_dict[name] = da
            return da
