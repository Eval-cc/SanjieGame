#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈
@File    ：Player.py
@IDE     ：PyCharm
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/2/14 下午2:05
@Describe: 角色类
"""
import math
import time
from functools import partial
from typing import List, TYPE_CHECKING

import pygame

from src.Mapper.FsoMapper import FsoMapper
from src.code.GameBag import GameBag
from src.manager.GameMapManager import GameMapManager
from src.manager.GameLogManger import GameLogManager
from src.manager.GameWorldManager import GameWorldManager
from src.necessary.GameBattle import BattleManager
from src.system.Animator import Animator
from src.code.SpriteBase import SpriteBase
from src.manager.GameFont import GameFont
from src.manager.GameManager import GameManager
from src.manager.SourceManager import SourceManager
from src.code.Enums import SpriteState
from src.system.GameDialog import GameDialog
from src.system.GameTipDialog import GameDialogBoxManager
from src.system.SkillSystem import SkillSystem

if TYPE_CHECKING:
    from src.render.GameUI import GameUI
    from src.network.GameWorldServer import GameWorldServer

STATUS_POS = {
    "name": [130, 30],
    "level": [50, 30],
    "人气": [50, 50],
    "贡献": [50, 70],
    "healthy": [50, 117],
    "mana": [50, 140],
    "愤怒": [50, 160],
    "活力": [50, 180],
    "体力": [50, 200],
    "法防": [50, 225],
    "attack": [50, 245],
    "defense": [50, 265],
    "attack_speed": [50, 285],
    "miss": [50, 305],
    "灵力": [50, 330],
    "constitution": [142, 225],
    "magic": [142, 245],
    "strength": [142, 270],
    "endurance": [142, 290],
    "agile": [142, 310],
    "潜力": [142, 245],
    "upgrade_exp": [80, 355],
    "curr_exp": [80, 375]
}


class Player(SpriteBase):
    MINI_MAP_SIZE = (170, 130)
    MINI_MAP_VIEW_RECT = pygame.Rect(8, 22, 154, 82)
    MINI_MAP_WORLD_RANGE = 900
    MEDIUM_MAP_UI_NAME = "中地图"
    MEDIUM_MAP_SIZE = (650, 390)
    MEDIUM_MAP_VIEW_RECT = pygame.Rect(18, 50, 420, 315)
    MEDIUM_MAP_LIST_RECT = pygame.Rect(454, 50, 178, 315)
    MEDIUM_MAP_CLOSE_RECT = pygame.Rect(620, 10, 18, 18)

    def __init__(self, acc_name: str, data: dict):
        super().__init__()
        # 添加Animator组件
        self.animator = Animator(GameManager)
        self.eff_animator_stick = Animator(GameManager)
        self.acc_name = acc_name
        self.fso_id = data.get("id")

        self.__g_pos = [data.get("sx"), data.get("sy")]

        self.current_path = []  # 存储当前路径
        self.current_path_index = 0  # 当前路径索引
        self.direction = 0  # 朝向的初始值，默认为右下方向
        self.scene_pos = [0, 0]
        self.__mini_map_frame = 0
        self.__mini_map_bg_surface = None
        self.__mini_map_cursor_surface = None
        self.__medium_map_close_surface = None
        self.__medium_map_cache_key = None
        self.__medium_map_cache_surface = None
        self.__medium_map_target_rows = []
        self.__medium_map_target_scroll = 0
        self.__medium_map_target_scroll_max = 0
        self.__medium_map_hover_text = ""
        self.__auto_path_text = ""

        self.has_dialog = False

        # 挂载到相机上, 让相机跟随当前角色
        # GameManager.game_camera.mounted(self)
        # 追加到寻路的列表
        GameManager.find_path_list.append({
            "get_pos": self.get_pos,
            "move": self.set_path,
            "stop_moving": self.stop_moving
        })

        self.update_blit = False
        self.update_blit_map = False

        self.__load_ui(data)
        self.__init_status(data)

        # --- 新增：记录裸体基础属性 (Base Stats) ---
        # 只有升级、吃永久果实才会修改这些 base 变量
        self.base_attack = self.attack
        self.base_max_hp = self.max_healthy
        self.base_base_mp = self.mana
        self.base_defense = self.defense
        self.base_attack_speed = self.attack_speed
        self.base_miss = self.miss
        self.base_strength = self.strength
        self.base_constitution = self.constitution
        self.base_intelligence = self.intelligence
        self.base_agile = self.agile
        self.base_endurance = self.endurance

        # 加载动画
        self.load_animations()

        self.btn_s = [
            {
                "name": "背包",
                "source": "exp_9-91483",
                "loc": (8, 47),
                "frames": [295, 0, 40, 45],
                "frames1": [345, 0, 40, 45],
            },
            {
                "name": "属性",
                "source": "exp_9-91480",
                "loc": (18, 22),
                "frames": [110, 105, 30, 35],
                "frames1": [160, 105, 30, 35]
            },
            {
                "name": "技能",
                "source": "exp_9-91483",
                "loc": (35, 10),
                "frames": [10, 0, 30, 40],
                "frames1": [60, 0, 30, 40]
            },
            {
                "name": "退出",
                "source": "exp_9-91486",
                "loc": (65, 10),
                "frames": [209, 0, 30, 40],
                "frames1": [225, 0, 30, 40]
            }
        ]
        self.__extract_frames_from_sprite()

        self.update_blit = True

    def __load_ui(self, data: dict):
        """
        加载UI
        :return:
        """
        game_ui: GameUI = GameManager.get("游戏UI")

        avatar_name = data.get("avatar")
        sta_sur = SourceManager.load(f"{SourceManager.ui_system_path}/window_actor.png", [250, 400])
        avatar_sur = SourceManager.load(SourceManager.ui_face_path + f"/{avatar_name}.png", [55, 55])
        sta_sur.blit(avatar_sur, [170, 50])
        game_ui.load_system_ui(sta_sur,
                               [250, 400],
                               "middle",
                               options=
                               {
                                   "name": "角色属性",
                                   "mouse_down": self.__click_status_ui,
                                   "drag": True,
                                   "event_layer": 5,
                                   "drag_rect": ["auto", "auto", "auto", "20"],
                                   "update_blit": self.__update_blit,
                                   "listen_keyboard": self.listen_keyboard
                               })

        ui1_1 = SourceManager.load(f"{SourceManager.ui_system_path}/ui1_1.png").convert_alpha()
        # 左下角功能区
        _game_tool_ui1_ = [150, 150]
        game_tool = ui1_1.subsurface((_game_tool_ui1_[0], _game_tool_ui1_[1], max(ui1_1.width - _game_tool_ui1_[0], 0),
                                      max(ui1_1.height - _game_tool_ui1_[1], 0)))
        game_tool = SourceManager.surface_scale(game_tool, [120, 120])
        game_ui.load_system_ui(game_tool,
                               [250, 400],
                               # "middle",
                               pos=[GameManager.game_win.width - game_tool.width,
                                    GameManager.game_win.height - game_tool.height],
                               options=
                               {
                                   "name": "功能区",
                                   "show": True
                               })

        # 小地图
        _game_map = self.__create_minimap_surface()
        game_ui.load_system_ui(_game_map,
                               pos=[6, 6],
                               options=
                               {
                                   "name": "小地图",
                                   "show": True,
                                   "update_blit": self.__update_blit_map,
                                   "mouse_down": self.__click_map,
                               })
        self.__mini_map_cursor_surface = self.__load_map_cursor_surface([18, 18])
        game_ui.load_system_ui(self.__mini_map_cursor_surface.copy(),
                               pos=[6 + self.MINI_MAP_VIEW_RECT.centerx - self.__mini_map_cursor_surface.width // 2,
                                    6 + self.MINI_MAP_VIEW_RECT.centery - self.__mini_map_cursor_surface.height // 2],
                               options={
                                   "name": "地图光标",
                                   "show": False,
                                   # "has_draw": True
                               })

        # skill_bg = SourceManager.load(f"{SourceManager.ui_system_path}/none_window.png", [600, 400])
        # game_ui.load_system_ui(skill_bg,
        #                        [600, 400],
        #                        "middle",
        #                        options=
        #                        {
        #                            "name": "角色技能",
        #                            "mouse_down": self.__click_status_ui,
        #                            "drag": True,
        #                            "event_layer": 5,
        #                            "drag_rect": ["auto", "auto", "auto", "20"],
        #                            "update_blit": self.__update_blit,
        #                            "listen_keyboard": lambda: game_ui.get_surface_show("角色技能")
        #                        }, sort=True)
        # _rect = list(skill_bg.get_rect().size)
        # _rect[1] -= 20
        # self.skill_bg_gif = SourceManager.load(f"{SourceManager.ui_system_path}/dt_bg.gif", _rect)
        self.skill_bg_gif = None
        self.skill_bg_gif_idx = 0
        self.skill_anim_timer = 0
        self.__skill_tree_dialog = None
        self.skill_levels = SkillSystem.parse_actor_skill_levels(data.get("skill_levels") or data.get("skills"))
        self.__skill_detail_dialog = None
        self.__selected_skill = None

    def __init_status(self, data: dict):
        try:
            self.idx = data.get("id")
            self.healthy = data.get("healthy")
            self.max_healthy = data.get("healthy")
            self.mana = data.get("mana")
            self.attack = data.get("attack")
            self.defense = data.get("defense")
            self.attack_speed = data.get("attack_speed")
            # 给主角挂上背包
            self.bag = GameBag(GameManager)

            # 这里可先不添加, 点击背包显示的时候再加
            # if len(data.get("items", "")) > 0:
            #     self.bag.refresh_bag(data.get("items"))
            # _item_arr = [ii for ii in data.get("items", "").split("|") if ii]
            # for __ii in _item_arr:
            #     # 格式  page, x, y, id, 数量
            #     _item = [int(i) for i in __ii.split(",")]
            #     self.bag.add_item(str(_item[3]), _item[4], target_page=_item[0], target_x=_item[1],
            #                       target_y=_item[2])

            self.name = data.get("name")
            self.current_path_index = 0  # 当前路径索引
            # 是否触发了对话
            self.has_dialog = False

            x, y = GameManager.scene_to_global_pos_box(self.__g_pos[0], self.__g_pos[1])
            self.transform.set_pos(x * GameManager.game_box_size, y * GameManager.game_box_size)
            self.scene_pos = [x, y]
            self.has_behind = False
            self.sprite_state = SpriteState.IDLE

            # 加载模型
            user_actor_data = SourceManager.get_csv("user_actor", data.get("anim_model"))
            super().loading_model(user_actor_data)

            # 设置方向表，用于后续方向匹配（合并站立/移动方向，以保证完整性）
            self.supported_directions = sorted(set(self.stand_direction + self.move_direction))

            target = "actor"
            __npc_data = {
                f"战斗_攻击2": user_actor_data.get("战斗_攻击"),
                f"战斗_击飞": user_actor_data.get("战斗_击飞"),
                f"战斗_施法": user_actor_data.get("战斗_施法"),
                f"战斗_死亡": user_actor_data.get("战斗_死亡"),
                f"战斗_挨打": user_actor_data.get("战斗_挨打"),
            }
            anim_name = user_actor_data.get("战斗模型")
            self.load_battle_anim(target, anim_name, __npc_data)

            # 名称的宽度
            self.name_width = GameFont.get_text_size(f"{self.name}")[0]

            # 初始化完成之后, 开始加个事件监听, 每xx分钟更新角色数据
            GameWorldManager.register_timed_event(1,FsoMapper.update_pos)

        except AttributeError as ae:
            GameDialogBoxManager.dialog(f"初始化失败 {ae}")
            # GameLogManager.log_service_error(f"玩家初始化失败: {ae}")
            GameManager.logout()
            # time.sleep(1)
            # raise ae
        except Exception as e:
            GameDialogBoxManager.dialog(f"初始化失败 {e}")
            # GameLogManager.log_service_error(f"玩家初始化失败: {e}")
            GameManager.logout()
            time.sleep(1)
            raise e

    def __extract_frames_from_sprite(self):
        """从精灵表中提取指定帧并存储到类属性中"""
        game_ui: GameUI = GameManager.get("游戏UI")
        __tool_ui_rect = game_ui.get_surface_sprite("功能区").get("rect")

        _size = 22
        for b_idx, btn in enumerate(self.btn_s):
            # 加载精灵表
            try:
                sprite_sheet = SourceManager.load(
                    fr"{SourceManager.ui_system_path}\UI_JX\系统框架UI\{btn['source']}.png")
            except Exception as e:
                GameLogManager.log_service_error(f"无法加载ui: {btn['source']} {e}")
                continue

            # 获取帧坐标数据
            frame_coords = btn["frames"]
            frame_coords_1 = btn.get("frames1")
            new_surface = pygame.Surface([len(frame_coords) * _size, _size], pygame.SRCALPHA)
            # 创建新的Surface对象 (足够容纳两个帧)
            btn_sur = SourceManager.surface_scale(sprite_sheet.subsurface(frame_coords), [_size, _size])
            new_surface.blit(btn_sur, (0, 0))
            if frame_coords_1:
                btn_sur1 = SourceManager.surface_scale(sprite_sheet.subsurface(frame_coords_1), [_size, _size])
                new_surface.blit(btn_sur1, (_size, 0))
            else:
                # 没有指定高亮帧, 那么就改个透明度作为高亮帧
                btn_sur.set_alpha(100)
                new_surface.blit(btn_sur, (_size, 0))

            game_ui.load_system_ui(new_surface,
                                   pos=[
                                       __tool_ui_rect[0] + btn.get("loc")[0],
                                       __tool_ui_rect[1] + btn.get("loc")[1]
                                   ],
                                   options=
                                   {
                                       "name": f"__u_tool_{btn["name"]}",
                                       "mouse_down": partial(self._tool_btn, cbk_name=btn["name"]),
                                       "frame": {
                                           "size": _size,
                                           "count": 2,
                                           "index": 0,
                                           "loc": btn.get("loc"),
                                       },
                                       "show": True
                                   }, sort=b_idx == len(self.btn_s) - 1)

    def load_animations(self):
        """一次性加载NPC的站立和移动动画（不做偏移量计算）"""
        try:
            # 加载每一帧的图像
            def load_frames(texture, model, directions):
                frames_by_dir = {}
                if not texture:
                    return frames_by_dir
                image = SourceManager.load(f"{SourceManager.ui_npc_path}/{texture}.png")
                cols, rows = model
                fw, fh = image.get_width() // cols, image.get_height() // rows
                # 模型是否有缩放
                if self.scale_texture != 1:
                    image = SourceManager.surface_scale(image, [image.get_width() * self.scale_texture,
                                                                image.get_height() * self.scale_texture])
                    fw *= self.scale_texture
                    fh *= self.scale_texture

                self.rect = pygame.Rect(0, 0, fw, fh)
                # 遍历每个方向
                for _dir_idx, dir_val in enumerate(directions):
                    d_idx = dir_val - 1
                    if d_idx >= rows:
                        continue
                    # 自动忽略透明像素
                    # first_frame = image.subsurface((0, _dir_idx * fh, fw, fh))
                    # # 遍历每一列
                    frames_by_dir[d_idx] = [
                        image.subsurface((
                            col * fw,  # 使用基准偏移量
                            d_idx * fh,  # 使用基准偏移量
                            fw,  # 使用bounding rect的宽度
                            fh  # 使用bounding rect的高度
                        ))
                        for col in range(cols)
                    ]
                return frames_by_dir

            # 一次性加载两种动画
            stand_frames = load_frames(self.stand_texture, self.stand_model, self.stand_direction)
            move_frames = load_frames(self.move_texture, self.move_model, self.move_direction)

            # 添加到 Animator
            for dir_idx, frames in stand_frames.items():
                self.animator.add_animation(f"stand_{dir_idx}", len(frames), 2, frames)
            for dir_idx, frames in move_frames.items():
                self.animator.add_animation(f"move_{dir_idx}", len(frames), 3, frames)

            self.eff_animator_stick.surface_to_animation_row(
                SourceManager.load(f"{SourceManager.ui_animation_path}/化生唧唧歪歪.png"),
                "化生唧唧歪歪", 5, 20
            )
            self.eff_animator_stick.surface_to_animation_row(
                SourceManager.load(f"{SourceManager.ui_animation_path}/地府判官令.png"),
                "地府判官令", 5, 15
            )
            self.eff_animator_stick.surface_to_animation_row(
                SourceManager.load(f"{SourceManager.ui_animation_path}/@@@漫天花雨.png"),
                "漫天花雨", 5, 19
            )
            self.eff_animator_stick.surface_to_animation_row(
                SourceManager.load(f"{SourceManager.ui_animation_path}/龙宫龙卷雨击.png"),
                "龙卷雨击", 2, 30
            )
            self.eff_animator_stick.surface_to_animation_row(
                SourceManager.load(f"{SourceManager.ui_animation_path}/####兔子特效.png"),
                "兔几", 5, 20
            )
            self.eff_animator_stick.surface_to_animation_row(
                SourceManager.load(f"{SourceManager.ui_animation_path}/##呼风唤雨.png"),
                "呼风唤雨", 5, 25
            )
            self.eff_animator_stick.surface_to_animation_row(
                SourceManager.load(f"{SourceManager.ui_animation_path}/##魔浪滔天.png"),
                "魔浪滔天", 5, 38
            )
            self.eff_animator_stick.surface_to_animation_row(
                SourceManager.load(f"{SourceManager.ui_animation_path}/##特技-菩提.png"),
                "菩提", 5, 15
            )
            self.eff_animator_stick.surface_to_animation_row(
                SourceManager.load(f"{SourceManager.ui_animation_path}/化生紫气东来.png"),
                "紫气东来", 5, 22
            )
            self.eff_animator_stick.surface_to_animation_row(
                SourceManager.load(f"{SourceManager.ui_animation_path}/女儿情天恨海.png"),
                "情天恨海", 5, 15
            )
            # 默认播放站立动画
            self.animator.play(f"stand_{self.direction}", speed=0.15)
        except KeyboardInterrupt as ke:
            GameDialogBoxManager.dialog(str(ke))
            GameManager.logout()
        except Exception as e:
            GameDialogBoxManager.dialog(str(e))
            GameManager.logout()

    def __str__(self):
        return f"主角:{self.name}"

    def render(self):
        self.move()
        self.__mini_map_frame = (self.__mini_map_frame + 1) % 15
        if self.__mini_map_frame == 0:
            self.update_blit_map = True

        if self.eff_animator_floor:
            self.eff_animator_floor.update(0.5, True)
        # 更新动画
        self.animator.update(0.5)  # 以 60fps 作为基准

        self.sync_rect_to_foot()
        # 使用Animator获取当前帧
        current_frame = self.animator.get_frame()
        if current_frame:
            GameManager.game_win.blit(current_frame, self.rect.topleft)

        # 角色边框
        if GameManager.has_debug_render:
            pygame.draw.rect(GameManager.game_win, (100, 220, 100),
                             self.rect, 1)
            foot_x, foot_y = self.get_screen_foot_pos()
            pygame.draw.circle(GameManager.game_win, (250, 0, 0), (int(foot_x), int(foot_y)), 4)

    def render_mask(self):
        super().render_mask()
        if self.__auto_path_text and self.current_path and self.sprite_state == SpriteState.WALK:
            text = GameFont.get_text_surface_line(self.__auto_path_text, True, 12, "#FFE08A", bolder=True)
            x = int(self.rect.centerx - text.width / 2)
            y = max(6, self.rect.y - text.height - 24)
            GameManager.game_win.blit(text, (x, y))

    def move(self):
        if self.sprite_state == SpriteState.ATTACK or BattleManager.battle_sta():
            return
        """根据路径数组移动角色"""
        if self.sprite_state == SpriteState.IDLE or not self.current_path:
            # 如果当前没移动，确保播放站立动画
            if not self.animator.is_playing(f"stand_{self.direction}"):
                self.animator.play(f"stand_{self.direction}")
                self.sprite_state = SpriteState.IDLE
            return

        if self.current_path_index >= len(
                self.current_path) or self.has_dialog or self.sprite_state == SpriteState.ATTACK:
            self.stop_moving()
            return

        # 确保在移动时播放移动动画
        if not self.animator.is_playing(f"move_{self.direction}"):
            self.animator.play(f"move_{self.direction}")
            self.sprite_state = SpriteState.WALK

        # 当前目标点（世界像素坐标）
        target_x, target_y = self.current_path[self.current_path_index]
        dx = target_x - self.transform.x
        dy = target_y - self.transform.y
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance <= self.move_speed:
            # 到达目标
            self.transform.set_pos(target_x, target_y)
            self.scene_pos = [
                int(self.transform.x // GameManager.game_box_size),
                int(self.transform.y // GameManager.game_box_size)
            ]
            self.current_path_index += 1

            if self.current_path_index >= len(self.current_path):
                self.stop_moving()
            else:
                next_target = self.current_path[self.current_path_index]
                self.update_direction(next_target[0] - self.transform.x,
                                      next_target[1] - self.transform.y)

                self.update_blit_map = True  # 更新小地图
            return

        # 按速度移动
        move_x = (dx / distance) * self.move_speed
        move_y = (dy / distance) * self.move_speed
        self.transform.x += move_x
        self.transform.y += move_y
        self.update_blit_map = True
        # 更新全局格子坐标
        self.scene_pos = [
            int(self.transform.x // GameManager.game_box_size),
            int(self.transform.y // GameManager.game_box_size)
        ]
        # 通知服务器. 我移动了
        w_server: "GameWorldServer" = GameManager.get_manager("w_server")
        if w_server:
            w_server.send_move()

    def stop_moving(self):
        super().stop_moving()
        self.sprite_state = SpriteState.IDLE
        self.__auto_path_text = ""
        # 更新全局格子坐标
        self.scene_pos = [
            int(self.transform.x // GameManager.game_box_size),
            int(self.transform.y // GameManager.game_box_size)
        ]
        # 通知服务器. 我停止了
        w_server: "GameWorldServer" = GameManager.get_manager("w_server")
        if w_server:
            w_server.send_stop()
        self.update_blit_map = True

    def set_path(self, path: List[tuple]):
        """设置移动路径(网格坐标)"""
        if not path or self.sprite_state == SpriteState.ATTACK:
            self.stop_moving()
            return

        # 如果已经在移动，则停止当前移动
        # if self.sprite_state == SpriteState.WALK:
        #     self.stop_moving()

        # 将网格坐标转换为世界坐标。重新寻路时角色可能已经在两个格子中间,
        # 路径开头如果还指向当前格点, 会造成先回头再转向的抖动, 所以这里跳过已经贴近的点。
        world_path = [(x * GameManager.game_box_size, y * GameManager.game_box_size) for x, y in path]
        while len(world_path) > 1:
            dx = world_path[0][0] - self.transform.x
            dy = world_path[0][1] - self.transform.y
            if (dx ** 2 + dy ** 2) ** 0.5 > GameManager.game_box_size * 0.75:
                break
            world_path.pop(0)
        if len(world_path) > 1 and self.current_path and self.current_path_index < len(self.current_path):
            old_dx = self.current_path[self.current_path_index][0] - self.transform.x
            old_dy = self.current_path[self.current_path_index][1] - self.transform.y
            new_dx = world_path[0][0] - self.transform.x
            new_dy = world_path[0][1] - self.transform.y
            if old_dx * new_dx + old_dy * new_dy < 0:
                world_path.pop(0)

        self.current_path = world_path
        self.current_path_index = 0
        self.sprite_state = SpriteState.WALK
        self.__auto_path_text = "正在自动寻路..."

        # 立即更新方向（指向第一个目标点）
        if self.current_path:
            dx = self.current_path[0][0] - self.transform.x
            dy = self.current_path[0][1] - self.transform.y
            self.update_direction(dx, dy)

        # 通知服务器. 我移动了
        w_server: "GameWorldServer" = GameManager.get_manager("w_server")
        if w_server:
            w_server.send_move()
        self.update_blit_map = True

    def listen_keyboard(self):
        """决定是否允许触发事件"""
        game_ui: GameUI = GameManager.get("游戏UI")
        return game_ui.get_surface_show("角色属性")

    def __click_status_ui(self, **args):
        game_ui: GameUI = GameManager.get("游戏UI")
        if game_ui.get_surface_show("角色属性"):
            GameLogManager.log_service_debug("点击属性UI")
            return

        if game_ui.get_surface_show("角色技能"):
            skill_sur = game_ui.get_surface_ui("角色技能")
            GameLogManager.log_service_debug("点击角色技能")
            return

    def __click_map(self, **args):
        """点击小地图打开中地图."""
        self.__show_medium_map()
        return False

    def __show_medium_map(self):
        game_ui: GameUI = GameManager.get("游戏UI")
        surface = self.__create_medium_map_surface()
        if game_ui.get_surface_sprite(self.MEDIUM_MAP_UI_NAME) is None:
            game_ui.load_system_ui(
                surface,
                loc="middle",
                options={
                    "name": self.MEDIUM_MAP_UI_NAME,
                    "show": False,
                    "mouse_down": self.__medium_map_mouse_down,
                    "mouse_move": self.__medium_map_mouse_move,
                    "mouse_scroll_wheel_down": self.__medium_map_scroll_down,
                    "mouse_scroll_wheel_up": self.__medium_map_scroll_up,
                    "drag": True,
                    "event_layer": 5,
                    "drag_rect": ["auto", "auto", 590, 38],
                    "update_blit": self.__update_medium_map,
                    "un_allow": False,
                },
                sort=True
            )
        else:
            game_ui.set_surface_ui(self.MEDIUM_MAP_UI_NAME, surface)
        game_ui.change_ui_layer(self.MEDIUM_MAP_UI_NAME, center=True)

    def __medium_map_mouse_down(self, **args):
        event = args.get("event", {})
        game_ui: GameUI = GameManager.get("游戏UI")
        sprite = game_ui.get_surface_sprite(self.MEDIUM_MAP_UI_NAME)
        if sprite is None:
            return False

        mouse_pos = event.get("mouse_pos", pygame.mouse.get_pos())
        rect = sprite.get("rect")
        local_x = mouse_pos[0] - rect.x
        local_y = mouse_pos[1] - rect.y

        if self.MEDIUM_MAP_CLOSE_RECT.collidepoint(local_x, local_y):
            game_ui.close_surface_ui(self.MEDIUM_MAP_UI_NAME)
            return False

        for row in self.__medium_map_target_rows:
            if row.get("rect").collidepoint(local_x, local_y):
                self.__walk_to_map_target(row.get("target"), near=True)
                return False

        if not self.MEDIUM_MAP_VIEW_RECT.collidepoint(local_x, local_y):
            return False

        target_world = self.__medium_map_local_to_world(local_x, local_y)
        if target_world is None:
            return False

        world_x, world_y = target_world
        self.__walk_to_world_pos(world_x, world_y)
        return False

    def __medium_map_mouse_move(self, **args):
        event = args.get("event", {})
        game_ui: GameUI = GameManager.get("游戏UI")
        sprite = game_ui.get_surface_sprite(self.MEDIUM_MAP_UI_NAME)
        if sprite is None:
            return False

        mouse_pos = event.get("mouse_pos", pygame.mouse.get_pos())
        rect = sprite.get("rect")
        local_x = mouse_pos[0] - rect.x
        local_y = mouse_pos[1] - rect.y
        hover_text = ""
        if self.MEDIUM_MAP_VIEW_RECT.collidepoint(local_x, local_y):
            hover_target = self.__get_medium_map_hover_target(local_x, local_y)
            if hover_target is not None:
                hover_text = str(getattr(hover_target, "name", "未知"))
            else:
                target_world = self.__medium_map_local_to_world(local_x, local_y)
                if target_world is not None:
                    hover_text = f"坐标: {target_world[0] // GameManager.game_box_size}, {target_world[1] // GameManager.game_box_size}"
        elif self.MEDIUM_MAP_LIST_RECT.collidepoint(local_x, local_y):
            for row in self.__medium_map_target_rows:
                if row.get("rect").collidepoint(local_x, local_y):
                    hover_text = str(getattr(row.get("target"), "name", "未知"))
                    break

        if hover_text != self.__medium_map_hover_text:
            self.__medium_map_hover_text = hover_text
            self.__update_medium_map()
        return False

    def __medium_map_scroll_down(self):
        return self.__medium_map_scroll_target_list(1)

    def __medium_map_scroll_up(self):
        return self.__medium_map_scroll_target_list(-1)

    def __medium_map_scroll_target_list(self, direction: int):
        game_ui: GameUI = GameManager.get("游戏UI")
        sprite = game_ui.get_surface_sprite(self.MEDIUM_MAP_UI_NAME)
        if sprite is None or not sprite.get("show"):
            return False

        mouse_pos = pygame.mouse.get_pos()
        rect = sprite.get("rect")
        local_x = mouse_pos[0] - rect.x
        local_y = mouse_pos[1] - rect.y
        if not self.MEDIUM_MAP_LIST_RECT.collidepoint(local_x, local_y):
            return True

        old_scroll = self.__medium_map_target_scroll
        self.__medium_map_target_scroll = max(
            0,
            min(self.__medium_map_target_scroll + direction * 32, self.__medium_map_target_scroll_max)
        )
        if old_scroll != self.__medium_map_target_scroll:
            self.__update_medium_map()
        return False

    def __walk_to_map_target(self, target, near: bool = False):
        if target is None:
            return False
        world_x = int(target.transform.x)
        world_y = int(target.transform.y)
        if near:
            grid = self.__find_near_target_grid(target)
            if grid is not None:
                world_x = grid[0] * GameManager.game_box_size
                world_y = grid[1] * GameManager.game_box_size
        return self.__walk_to_world_pos(world_x, world_y)

    def __walk_to_world_pos(self, world_x: int, world_y: int):
        target_grid = [
            int(world_x // GameManager.game_box_size),
            int(world_y // GameManager.game_box_size)
        ]
        find_path = GameManager.find_path(target_grid, GameMapManager.game_map_passable())
        if find_path:
            click_effect = GameManager.get("点击特效系统")
            if click_effect:
                click_effect.add_world(world_x, world_y)
            self.update_blit_map = True
            self.__update_medium_map()
        return bool(find_path)

    def __find_near_target_grid(self, target):
        passable = GameMapManager.game_map_passable()
        if not passable:
            return None
        gx = int(target.transform.x // GameManager.game_box_size)
        gy = int(target.transform.y // GameManager.game_box_size)
        candidates = []
        for radius in range(1, 5):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if max(abs(dx), abs(dy)) != radius:
                        continue
                    nx, ny = gx + dx, gy + dy
                    if self.__is_passable_cell(passable, nx, ny):
                        candidates.append((nx, ny))
            if candidates:
                px, py = self.scene_pos
                return min(candidates, key=lambda p: (p[0] - px) ** 2 + (p[1] - py) ** 2)
        return (gx, gy)

    @staticmethod
    def __is_passable_cell(passable: list, x: int, y: int) -> bool:
        if not passable or y < 0 or y >= len(passable):
            return False
        if x < 0 or x >= len(passable[y]):
            return False
        return str(passable[y][x]) != "0"

    def __medium_map_local_to_world(self, local_x: int, local_y: int):
        world_w, world_h = self.__current_map_world_size()
        if world_w <= 0 or world_h <= 0:
            return None
        view_rect = self.MEDIUM_MAP_VIEW_RECT
        world_x = (local_x - view_rect.x) * world_w / view_rect.width
        world_y = (local_y - view_rect.y) * world_h / view_rect.height
        return (
            max(0, min(int(world_x), world_w - 1)),
            max(0, min(int(world_y), world_h - 1))
        )

    def __get_medium_map_hover_target(self, local_x: int, local_y: int):
        world_w, world_h = self.__current_map_world_size()
        if world_w <= 0 or world_h <= 0:
            return None
        view_rect = self.MEDIUM_MAP_VIEW_RECT
        hit_radius = 8
        best = None
        best_dist = None
        for npc in GameMapManager.game_map_npcs():
            if getattr(npc, "battle_state", False) or npc.is_dead():
                continue
            point = self.__world_to_map_point(npc.transform.x, npc.transform.y, view_rect, (0, 0, world_w, world_h))
            if point is None:
                continue
            dist = math.hypot(local_x - point[0], local_y - point[1])
            if dist <= hit_radius and (best_dist is None or dist < best_dist):
                best = npc
                best_dist = dist
        return best

    def __update_medium_map(self):
        game_ui: GameUI = GameManager.get("游戏UI")
        if not game_ui.get_surface_show(self.MEDIUM_MAP_UI_NAME):
            return
        game_ui.set_surface_ui(self.MEDIUM_MAP_UI_NAME, self.__create_medium_map_surface())

    def __create_medium_map_surface(self):
        width, height = self.MEDIUM_MAP_SIZE
        view_rect = self.MEDIUM_MAP_VIEW_RECT
        list_rect = self.MEDIUM_MAP_LIST_RECT
        sur = pygame.Surface((width, height), pygame.SRCALPHA)
        sur.fill((0, 0, 0, 0))

        shadow = pygame.Surface((width, height), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 62))
        sur.blit(shadow, (4, 5))

        pygame.draw.rect(sur, (4, 14, 16, 218), (0, 0, width, height))
        pygame.draw.rect(sur, (34, 139, 34), (0, 0, width, height), 1)
        pygame.draw.rect(sur, (18, 66, 62), (3, 3, width - 6, height - 6), 1)

        title_bar = pygame.Surface((width - 8, 30), pygame.SRCALPHA)
        title_bar.fill((9, 31, 35, 224))
        sur.blit(title_bar, (4, 4))

        scene_name = GameMapManager.map_scene_name()
        title = GameFont.get_text_surface_line(scene_name, True, 15, "#8AD7FF", bolder=True)
        sur.blit(title, (18, 11))
        coord_text = f"当前坐标: {self.scene_pos[0]}, {self.scene_pos[1]}"
        coord = GameFont.get_text_surface_line(coord_text, True, 12, "#FFE08A", bolder=True)
        sur.blit(coord, (454, 14))

        sur.blit(self.__get_medium_map_close_surface(), self.MEDIUM_MAP_CLOSE_RECT.topleft)

        pygame.draw.rect(sur, (2, 10, 12, 208), view_rect.inflate(4, 4))
        sur.blit(self.__create_medium_map_view(view_rect.size), view_rect.topleft)
        self.__draw_medium_map_path(sur, view_rect)
        self.__draw_map_points(sur, view_rect, label=True)
        pygame.draw.rect(sur, (34, 139, 34), view_rect.inflate(2, 2), 1)
        pygame.draw.rect(sur, (53, 94, 91), view_rect, 1)
        self.__draw_medium_map_target_list(sur, list_rect)
        self.__draw_medium_map_hover_tip(sur)
        return sur

    def __get_medium_map_close_surface(self):
        if self.__medium_map_close_surface is None:
            self.__medium_map_close_surface = SourceManager.load(
                f"{SourceManager.ui_system_path}/btn_close_down.png",
                [self.MEDIUM_MAP_CLOSE_RECT.width, self.MEDIUM_MAP_CLOSE_RECT.height]
            ).copy()
        return self.__medium_map_close_surface.copy()

    def __draw_medium_map_hover_tip(self, sur: pygame.Surface):
        if not self.__medium_map_hover_text:
            return
        text = GameFont.get_text_surface_line(self.__medium_map_hover_text, True, 12, "#E8FFFF", bolder=True)
        padding_x = 8
        padding_y = 4
        bg = pygame.Surface((text.width + padding_x * 2, text.height + padding_y * 2), pygame.SRCALPHA)
        bg.fill((0, 14, 16, 186))
        pygame.draw.rect(bg, (34, 139, 34), bg.get_rect(), 1)
        pos = (self.MEDIUM_MAP_VIEW_RECT.x + 8, self.MEDIUM_MAP_VIEW_RECT.bottom - bg.height - 8)
        sur.blit(bg, pos)
        sur.blit(text, (pos[0] + padding_x, pos[1] + padding_y))

    def __draw_medium_map_target_list(self, sur: pygame.Surface, list_rect: pygame.Rect):
        self.__medium_map_target_rows = []
        pygame.draw.rect(sur, (2, 10, 12, 196), list_rect)
        pygame.draw.rect(sur, (34, 139, 34), list_rect, 1)
        pygame.draw.rect(sur, (16, 52, 53), list_rect.inflate(-6, -6), 1)

        header = GameFont.get_text_surface_line("场景目标", True, 14, "#8AD7FF", bolder=True)
        sur.blit(header, (list_rect.x + 10, list_rect.y + 8))

        content_rect = pygame.Rect(list_rect.x + 9, list_rect.y + 36, list_rect.width - 18, list_rect.height - 45)
        targets = self.__get_medium_map_targets()
        content_height = self.__medium_map_target_group_height(targets["npc"]) + 8 + \
                         self.__medium_map_target_group_height(targets["monster"])
        self.__medium_map_target_scroll_max = max(0, content_height - content_rect.height)
        self.__medium_map_target_scroll = max(
            0,
            min(self.__medium_map_target_scroll, self.__medium_map_target_scroll_max)
        )

        old_clip = sur.get_clip()
        sur.set_clip(content_rect.clip(old_clip))
        y = content_rect.y - self.__medium_map_target_scroll
        y = self.__draw_medium_map_target_group(sur, content_rect, "NPC", targets["npc"], y, (58, 235, 105))
        self.__draw_medium_map_target_group(sur, content_rect, "怪物", targets["monster"], y + 8, (255, 66, 66))
        sur.set_clip(old_clip)

        if self.__medium_map_target_scroll_max > 0:
            rail_rect = pygame.Rect(list_rect.right - 8, content_rect.y, 3, content_rect.height)
            pygame.draw.rect(sur, (8, 28, 30), rail_rect)
            bar_h = max(26, int(content_rect.height * content_rect.height / (content_height + 1)))
            bar_y = content_rect.y + int(
                self.__medium_map_target_scroll / self.__medium_map_target_scroll_max *
                max(1, content_rect.height - bar_h)
            )
            pygame.draw.rect(sur, (138, 224, 207), (rail_rect.x, bar_y, rail_rect.width, bar_h))

    @staticmethod
    def __medium_map_target_group_height(targets: list):
        return 20 + (22 if not targets else len(targets) * 27)

    def __draw_medium_map_target_group(self, sur: pygame.Surface, list_rect: pygame.Rect, title: str,
                                       targets: list, y: int, color: tuple[int, int, int]):
        title_sur = GameFont.get_text_surface_line(title, True, 12, "#FFE08A", bolder=True)
        if y + title_sur.height >= list_rect.top and y <= list_rect.bottom:
            sur.blit(title_sur, (list_rect.x + 2, y))
        y += 20
        if not targets:
            empty = GameFont.get_text_surface_line("暂无", True, 11, "#9AA6A8")
            if y + empty.height >= list_rect.top and y <= list_rect.bottom:
                sur.blit(empty, (list_rect.x + 12, y))
            return y + 22

        for target in targets:
            row_rect = pygame.Rect(list_rect.x, y, list_rect.width - 8, 23)
            if row_rect.bottom >= list_rect.top and row_rect.y <= list_rect.bottom:
                pygame.draw.rect(sur, (8, 23, 26, 220), row_rect)
                pygame.draw.rect(sur, (24, 72, 70), row_rect, 1)
                pygame.draw.circle(sur, (4, 4, 4), (row_rect.x + 12, row_rect.centery), 4)
                pygame.draw.circle(sur, color, (row_rect.x + 12, row_rect.centery), 3)

                name = str(getattr(target, "name", "未知"))
                if len(name) > 7:
                    name = name[:7] + "."
                name_sur = GameFont.get_text_surface_line(name, True, 11, "#FFFFFF", bolder=True)
                sur.blit(name_sur, (row_rect.x + 22, row_rect.y + 4))

                gx = int(target.transform.x // GameManager.game_box_size)
                gy = int(target.transform.y // GameManager.game_box_size)
                pos_sur = GameFont.get_text_surface_line(f"{gx},{gy}", True, 10, "#B8C7C9", bolder=True)
                sur.blit(pos_sur, (row_rect.right - pos_sur.width - 5, row_rect.y + 5))
                self.__medium_map_target_rows.append({"rect": row_rect, "target": target})
            y += 27
        return y

    def __get_medium_map_targets(self):
        targets = {"npc": [], "monster": []}
        for npc in GameMapManager.game_map_npcs():
            if getattr(npc, "battle_state", False) or npc.is_dead():
                continue
            if int(getattr(npc, "type", 1) or 1) == 2:
                targets["monster"].append(npc)
            else:
                targets["npc"].append(npc)

        for key in targets:
            targets[key].sort(key=lambda item: (
                str(getattr(item, "name", "")),
                int(item.transform.x // GameManager.game_box_size),
                int(item.transform.y // GameManager.game_box_size)
            ))
        return targets

    def __create_medium_map_view(self, size: tuple[int, int]):
        cache_key = (
            GameMapManager.map_id,
            tuple(GameManager.game_map_size or []),
            tuple(GameMapManager.game_map_column_row_size()),
            tuple(GameMapManager.game_map_tile_size()),
            size
        )
        if self.__medium_map_cache_key == cache_key and self.__medium_map_cache_surface is not None:
            return self.__medium_map_cache_surface.copy()

        view_w, view_h = size
        view = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        view.fill((18, 28, 30, 230))

        map_paths = GameMapManager.game_map_surface_path()
        tile_cols, tile_rows = GameMapManager.game_map_column_row_size()
        tile_w, tile_h = GameMapManager.game_map_tile_size()
        world_w, world_h = self.__current_map_world_size()
        if not map_paths or tile_cols <= 0 or tile_rows <= 0 or tile_w <= 0 or tile_h <= 0 or world_w <= 0 or world_h <= 0:
            return view

        for tile_y in range(tile_rows):
            for tile_x in range(tile_cols):
                tile_index = tile_y * tile_cols + tile_x
                if tile_index >= len(map_paths):
                    continue
                tile_surface = SourceManager.load(map_paths[tile_index])
                dest_rect = pygame.Rect(
                    int(tile_x * tile_w * view_w / world_w),
                    int(tile_y * tile_h * view_h / world_h),
                    max(1, math.ceil(tile_w * view_w / world_w)),
                    max(1, math.ceil(tile_h * view_h / world_h))
                )
                view.blit(pygame.transform.smoothscale(tile_surface, dest_rect.size), dest_rect)

        overlay = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 42))
        view.blit(overlay, (0, 0))
        self.__medium_map_cache_key = cache_key
        self.__medium_map_cache_surface = view.copy()
        return view

    def __draw_medium_map_path(self, sur: pygame.Surface, view_rect: pygame.Rect):
        """在中地图上绘制当前自动寻路路线。"""
        if not self.current_path or self.current_path_index >= len(self.current_path):
            return
        world_w, world_h = self.__current_map_world_size()
        if world_w <= 0 or world_h <= 0:
            return

        route_world = [(int(self.transform.x), int(self.transform.y))]
        route_world.extend([
            (int(pos[0]), int(pos[1]))
            for pos in self.current_path[self.current_path_index:]
        ])
        if len(route_world) < 2:
            return

        points = [
            self.__world_to_medium_map_point(wx, wy, view_rect, world_w, world_h)
            for wx, wy in route_world
        ]
        points = [point for point in points if point is not None]
        if len(points) < 2:
            return

        for idx in range(len(points) - 1):
            pygame.draw.line(sur, (13, 30, 34), points[idx], points[idx + 1], 6)
            pygame.draw.line(sur, (36, 220, 255), points[idx], points[idx + 1], 3)
            pygame.draw.line(sur, (255, 255, 255), points[idx], points[idx + 1], 1)
        for point in points[1:]:
            pygame.draw.circle(sur, (13, 30, 34), point, 5)
            pygame.draw.circle(sur, (36, 220, 255), point, 3)

    @staticmethod
    def __world_to_medium_map_point(wx, wy, view_rect: pygame.Rect, world_w: int, world_h: int):
        world_w = max(1, world_w)
        world_h = max(1, world_h)
        wx = max(0, min(int(wx), world_w - 1))
        wy = max(0, min(int(wy), world_h - 1))
        return (
            view_rect.x + int(wx * view_rect.width / world_w),
            view_rect.y + int(wy * view_rect.height / world_h)
        )

    def __current_map_world_size(self):
        tile_cols, tile_rows = GameMapManager.game_map_column_row_size()
        tile_w, tile_h = GameMapManager.game_map_tile_size()
        world_w = GameManager.game_map_size[0] if GameManager.game_map_size else tile_cols * tile_w
        world_h = GameManager.game_map_size[1] if GameManager.game_map_size else tile_rows * tile_h
        return max(0, int(world_w or 0)), max(0, int(world_h or 0))

    def __get_minimap_bg_surface(self):
        """加载小地图外框背景图, 资源缺失时降级为手绘背景."""
        if self.__mini_map_bg_surface is not None:
            return self.__mini_map_bg_surface.copy()

        width, height = self.MINI_MAP_SIZE
        try:
            self.__mini_map_bg_surface = SourceManager.load(
                f"{SourceManager.ui_system_path}/window_smap.png", [width, height]
            ).copy()
        except Exception as e:
            GameLogManager.log_service_error(f"小地图背景加载失败: {e}")
            bg = pygame.Surface((width, height), pygame.SRCALPHA)
            bg.fill((12, 18, 22, 218))
            pygame.draw.rect(bg, (218, 176, 85), (0, 0, width, height), 2)
            self.__mini_map_bg_surface = bg
        return self.__mini_map_bg_surface.copy()

    def __create_minimap_surface(self):
        """创建当前小地图面板."""
        width, height = self.MINI_MAP_SIZE
        view_rect = self.MINI_MAP_VIEW_RECT
        sur = self.__get_minimap_bg_surface()

        pygame.draw.rect(sur, (6, 12, 16, 135), (6, 3, width - 12, 17))
        pygame.draw.rect(sur, (6, 12, 16, 145), (6, 106, width - 12, 18))
        pygame.draw.rect(sur, (15, 25, 28), view_rect.inflate(2, 2), 1)

        map_view = self.__create_minimap_view(view_rect.size)
        sur.blit(map_view, view_rect.topleft)
        self.__draw_minimap_points(sur, view_rect)

        scene_name = GameMapManager.map_scene_name()
        title = GameFont.get_text_surface_line(scene_name, True, 12, "#FFE08A", bolder=True)
        sur.blit(title, (10, 5))

        coord_text = f"坐标: {self.scene_pos[0]}, {self.scene_pos[1]}"
        coord = GameFont.get_text_surface_line(coord_text, True, 11, "#FFFFFF", bolder=True)
        sur.blit(coord, (10, 108))

        return sur

    def __create_minimap_view(self, size: tuple[int, int]):
        """从当前地图块里裁出角色附近区域, 作为小地图底图."""
        view_w, view_h = size
        view = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        view.fill((18, 28, 30, 230))

        map_paths = GameMapManager.game_map_surface_path()
        tile_cols, tile_rows = GameMapManager.game_map_column_row_size()
        tile_w, tile_h = GameMapManager.game_map_tile_size()
        if not map_paths or tile_cols <= 0 or tile_rows <= 0 or tile_w <= 0 or tile_h <= 0:
            return view

        left, top, range_w, range_h = self.__get_minimap_world_rect(view_w, view_h)

        for tile_y in range(tile_rows):
            for tile_x in range(tile_cols):
                tile_left = tile_x * tile_w
                tile_top = tile_y * tile_h
                tile_rect = pygame.Rect(tile_left, tile_top, tile_w, tile_h)
                crop_rect = pygame.Rect(left, top, range_w, range_h).clip(tile_rect)
                if crop_rect.width <= 0 or crop_rect.height <= 0:
                    continue

                tile_index = tile_y * tile_cols + tile_x
                if tile_index >= len(map_paths):
                    continue
                tile_surface = SourceManager.load(map_paths[tile_index])
                local_crop = pygame.Rect(
                    crop_rect.x - tile_left,
                    crop_rect.y - tile_top,
                    crop_rect.width,
                    crop_rect.height
                )
                piece = tile_surface.subsurface(local_crop).copy()
                dest_rect = pygame.Rect(
                    int((crop_rect.x - left) * view_w / range_w),
                    int((crop_rect.y - top) * view_h / range_h),
                    max(1, math.ceil(crop_rect.width * view_w / range_w)),
                    max(1, math.ceil(crop_rect.height * view_h / range_h))
                )
                view.blit(pygame.transform.smoothscale(piece, dest_rect.size), dest_rect)

        overlay = pygame.Surface((view_w, view_h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 54))
        view.blit(overlay, (0, 0))
        return view

    def __draw_minimap_points(self, sur: pygame.Surface, view_rect: pygame.Rect):
        """绘制玩家、NPC和怪物点位."""
        world_rect = self.__get_minimap_world_rect(view_rect.width, view_rect.height)
        self.__draw_map_points(sur, view_rect, world_rect)

    def __get_minimap_world_rect(self, view_w: int, view_h: int):
        world_w, world_h = self.__current_map_world_size()
        if world_w <= 0 or world_h <= 0 or view_w <= 0 or view_h <= 0:
            return 0, 0, 1, 1
        range_w = min(self.MINI_MAP_WORLD_RANGE, world_w)
        range_h = min(int(self.MINI_MAP_WORLD_RANGE * view_h / view_w), world_h)
        center_x = max(0, min(self.transform.x, world_w))
        center_y = max(0, min(self.transform.y, world_h))
        left = max(0, min(int(center_x - range_w / 2), max(0, world_w - range_w)))
        top = max(0, min(int(center_y - range_h / 2), max(0, world_h - range_h)))
        return left, top, max(1, range_w), max(1, range_h)

    def __draw_map_points(self, sur: pygame.Surface, view_rect: pygame.Rect, world_rect=None, label: bool = False):
        """按给定世界矩形绘制玩家、NPC和怪物点位."""
        world_w, world_h = self.__current_map_world_size()
        if world_w <= 0 or world_h <= 0:
            return
        if world_rect is None:
            world_rect = (0, 0, world_w, world_h)
        left, top, range_w, range_h = world_rect
        range_w = max(1, range_w)
        range_h = max(1, range_h)

        for npc in GameMapManager.game_map_npcs():
            if getattr(npc, "battle_state", False) or npc.is_dead():
                continue
            point = self.__world_to_map_point(npc.transform.x, npc.transform.y, view_rect, world_rect)
            if point is None:
                continue
            color = (255, 66, 66) if int(getattr(npc, "type", 1) or 1) == 2 else (58, 235, 105)
            pygame.draw.circle(sur, (12, 12, 12), point, 4)
            pygame.draw.circle(sur, color, point, 3)

        player_point = self.__world_to_map_point(self.transform.x, self.transform.y, view_rect, world_rect)
        if player_point is None:
            return
        self.__draw_player_map_arrow(sur, player_point)
        if label:
            text = GameFont.get_text_surface_line("我", True, 11, "#FFFFFF", bolder=True)
            sur.blit(text, (player_point[0] + 6, player_point[1] - 6))

    def __world_to_map_point(self, wx, wy, view_rect: pygame.Rect, world_rect):
        left, top, range_w, range_h = world_rect
        range_w = max(1, range_w)
        range_h = max(1, range_h)
        mx = view_rect.x + int((wx - left) * view_rect.width / range_w)
        my = view_rect.y + int((wy - top) * view_rect.height / range_h)
        max_x = view_rect.right - 1
        max_y = view_rect.bottom - 1
        if mx < view_rect.left or mx > max_x or my < view_rect.top or my > max_y:
            return None
        return max(view_rect.left, min(mx, max_x)), max(view_rect.top, min(my, max_y))

    def __draw_player_map_arrow(self, sur: pygame.Surface, point: tuple[int, int]):
        cursor = self.__mini_map_cursor_surface or self.__load_map_cursor_surface([18, 18])
        # map_cursor.png 原图默认朝上；raw_angle 的 0 度是向右，所以要先补一个 -90 度基准偏移。
        rotated_cursor = pygame.transform.rotate(cursor, -90 - self.raw_angle)
        rect = rotated_cursor.get_rect(center=point)
        sur.blit(rotated_cursor, rect)

    def __load_map_cursor_surface(self, size: list[int]):
        try:
            return SourceManager.load(f"{SourceManager.ui_system_path}/map_cursor.png", size).copy()
        except Exception:
            return SourceManager.load(
                f"{SourceManager.ui_system_path}/UI_JX/系统框架UI/exp_5-63232.png", size
            ).copy()

    def __update_blit(self):
        """用于提供给游戏UI进行重绘的方法"""
        if not self.update_blit:
            return
        self.update_blit = False

        game_ui: GameUI = GameManager.get("游戏UI")
        sur = game_ui.get_surface_ui("角色属性")
        fun_tool_sur = game_ui.get_surface_ui("功能区")

        if game_ui.get_surface_show("角色属性"):
            for k in STATUS_POS.keys():
                if hasattr(self, k):
                    if k == "healthy":
                        sur.blit(GameFont.get_text_surface_line(f"{self.healthy} / {self.max_healthy}", True),
                                 STATUS_POS[k])
                        continue
                    sur.blit(GameFont.get_text_surface_line(str(getattr(self, k)), True), STATUS_POS[k])
                else:
                    sur.blit(GameFont.get_text_surface_line("0", True), STATUS_POS[k])
            game_ui.set_surface_ui("角色属性", sur)

        # if game_ui.get_surface_show("角色技能"):
            # 频率控制：假设游戏 60 帧，每 5 帧更新一次 GIF（约 12FPS）
            # self.skill_anim_timer += 1
            # if self.skill_anim_timer >= 5:
            #     self.skill_anim_timer = 0
            #     self.skill_bg_gif_idx = (self.skill_bg_gif_idx + 1) % self.skill_bg_gif.get("len")

            # skill_sur = game_ui.get_surface_ui("角色技能")
            # curr_rect = self.skill_bg_gif.get("rects")[self.skill_bg_gif_idx]
            #
            # # 关键修复：subsurface 之前确保不越界（上面 SourceManager 修复后这里通常没问题）
            # curr_skill_bg = self.skill_bg_gif.get("surface").subsurface(curr_rect)
            #
            # skill_sur.blit(curr_skill_bg, (0, 20))
            #
            # # 这一行很重要：保持 update_blit 为 True 才能形成连续动画
            # self.update_blit = True
            # game_ui.set_surface_ui("角色技能", skill_sur)

        game_ui.set_surface_ui("功能区", fun_tool_sur)

    def __update_blit_map(self):
        """绘制小地图"""
        if not self.update_blit_map:
            return
        self.update_blit_map = False

        game_ui: GameUI = GameManager.get("游戏UI")
        game_ui.set_surface_ui("小地图", self.__create_minimap_surface())
        self.__update_medium_map()

    def get_pos(self):
        """
        返回当前角色的世界格子坐标
        :return:
        """
        return tuple(self.scene_pos)

    def set_pos(self, x: int, y: int):
        """设置角色位置"""
        self.transform.set_pos(x, y)
        # 更新全局格子坐标
        self.scene_pos = [
            int(self.transform.x // GameManager.game_box_size),
            int(self.transform.y // GameManager.game_box_size)
        ]
        self.stop_moving()
        self.update_blit_map = True

    def start_battle(self):
        """隐藏一些ui"""
        game_ui: GameUI = GameManager.get("游戏UI")
        tool_sur = game_ui.get_surface_sprite("功能区")
        map_sur = game_ui.get_surface_sprite("小地图")
        map_cursor_sur = game_ui.get_surface_sprite("地图光标")
        tool_sur["show"] = False
        map_sur["show"] = False
        map_cursor_sur["show"] = False
        for b in self.btn_s:
            a = game_ui.get_surface_sprite(f"__u_tool_{b["name"]}")
            a["show"] = False
        game_ui.close_surface_ui("角色背包")
        game_ui.close_surface_ui("角色属性")

    def end_battle(self):
        game_ui: GameUI = GameManager.get("游戏UI")
        tool_sur = game_ui.get_surface_sprite("功能区")
        map_sur = game_ui.get_surface_sprite("小地图")
        map_cursor_sur = game_ui.get_surface_sprite("地图光标")
        tool_sur["show"] = True
        map_sur["show"] = True
        if map_cursor_sur:
            map_cursor_sur["show"] = False
        for b in self.btn_s:
            a = game_ui.get_surface_sprite(f"__u_tool_{b["name"]}")
            a["show"] = True

    def _tool_btn(self, **args):
        game_ui: GameUI = GameManager.get("游戏UI")
        cbk_name = args.get("cbk_name")
        match cbk_name:
            case "属性":
                game_ui.change_ui_layer("角色属性")
                return
            case "背包":
                # 唤出背包的时候才需要读取背包数据
                if not game_ui.get_surface_show("角色背包"):
                    w_server: "GameWorldServer" = GameManager.get_manager("w_server")
                    # 有服务器.那么就通知服务器获取背包数据
                    if w_server:
                        pass
                    else:
                        # 从数据库获取到背包数据
                        items = GameManager.game_local_db.fetch_on("SELECT items from fso WHERE account_id = (SELECT ID FROM accounts WHERE username = ?)", (self.acc_name,))
                        if items:
                            self.bag.refresh_bag(items.get("items"))
                game_ui.change_ui_layer("角色背包")
                return
            case "退出":
                w_server: "GameWorldServer" = GameManager.get_manager("w_server")
                if w_server:
                    w_server.disconnect()
                else:
                    GameManager.logout()
            case "技能":
                self.__show_skill_tree()
                # if self.skill_bg_gif is None:
                #     skill_bg = SourceManager.load(f"{SourceManager.ui_system_path}/none_window.png", [600, 400])
                #     game_ui.load_system_ui(skill_bg,
                #                            [600, 400],
                #                            "middle",
                #                            options=
                #                            {
                #                                "name": "角色技能",
                #                                "mouse_down": self.__click_status_ui,
                #                                "drag": True,
                #                                "event_layer": 5,
                #                                "drag_rect": ["auto", "auto", "auto", "20"],
                #                                "update_blit": self.__update_blit,
                #                                "listen_keyboard": lambda: game_ui.get_surface_show("角色技能")
                #                            }, sort=True)
                #     _rect = list(skill_bg.get_rect().size)
                #     _rect[1] -= 20
                #     self.skill_bg_gif = SourceManager.load(f"{SourceManager.ui_system_path}/dt_bg.gif", _rect)
                # game_ui.change_ui_layer("角色技能")
                # if not game_ui.get_surface_show("角色技能"):
                #     self.skill_bg_gif = None
                # return
            case _:
                GameLogManager.log_service_error(f"无法识别的指令: {cbk_name}")

        self.update_blit = True

    def __show_skill_tree(self):
        if self.__skill_tree_dialog is None:
            self.__skill_tree_dialog = GameDialog(GameManager, "角色技能树")
        self.__skill_tree_dialog.show_dialog(
            SkillSystem.write_skill_tree_dialog(self),
            render_x=0,
            render_y=0,
            overwrite_path=True,
            loc="middle",
            hover_callback=True,
            dialog_callback=self.__skill_tree_dialog_callback,
        )

    def __skill_tree_dialog_callback(self, node):
        node_type = node.get("__type")
        if node_type in ("hover", "hover_move"):
            skill = self.__get_skill_from_dialog_node(node.get("node") or {})
            if skill:
                SkillSystem.show_skill_hover(GameManager, skill, node.get("mouse_pos") or pygame.mouse.get_pos())
            else:
                SkillSystem.hide_skill_hover(GameManager)
            return
        if node_type in ("hover_out", "close"):
            SkillSystem.hide_skill_hover(GameManager)
            if node_type == "close":
                game_ui: GameUI = GameManager.get("游戏UI")
                game_ui.close_surface_ui("技能详情UI")
            return

        target_node = node.get("node") if node_type == "double_click" else node
        skill = self.__get_skill_from_dialog_node(target_node or {})
        if skill is None:
            return
        if node_type == "double_click":
            self.__upgrade_skill(skill)
            return
        self.__show_skill_detail(skill)

    @staticmethod
    def __get_skill_from_dialog_node(node):
        attrs = node.get("attrs", {})
        skill_id = attrs.get("data-skill-id")
        if not skill_id:
            return None
        return SkillSystem.get(skill_id=skill_id)

    def __show_skill_detail(self, skill):
        if skill is None:
            return
        self.__selected_skill = SkillSystem.get_current_skill(self, skill.group_id) or skill
        game_ui: GameUI = GameManager.get("游戏UI")
        SkillSystem.hide_skill_hover(GameManager)
        self.__skill_detail_dialog = GameDialog(GameManager, "技能详情UI")
        self.__skill_detail_dialog.show_dialog(
            SkillSystem.write_skill_detail_dialog(self.__selected_skill, self),
            render_x=0,
            render_y=0,
            overwrite_path=True,
            loc="right_center",
            always_on_top=True,
            dialog_event_dict={
                "skill_upgrade": self.__upgrade_selected_skill
            }
        )

    def __upgrade_selected_skill(self):
        if self.__selected_skill is None:
            return
        self.__upgrade_skill(self.__selected_skill)

    def __upgrade_skill(self, skill):
        if skill is None:
            return False
        success, message, new_skill = SkillSystem.upgrade_skill(self, skill)
        GameDialogBoxManager.dialog(message)
        if not success:
            return False
        self.__selected_skill = new_skill
        self.__refresh_skill_tree_ui()
        self.__show_skill_detail(new_skill)
        return False

    def __refresh_skill_tree_ui(self):
        if self.__skill_tree_dialog is None or not self.__skill_tree_dialog.visible():
            return
        self.__skill_tree_dialog.show_dialog(
            SkillSystem.write_skill_tree_dialog(self),
            render_x=0,
            render_y=0,
            overwrite_path=True,
            loc="middle",
            hover_callback=True,
            dialog_callback=self.__skill_tree_dialog_callback,
        )

    # def change_status(self, status: dict, add: bool = True):
        # for k in status.keys():
        #     val = int(status.get(k))
        #     if not add:
        #         val = -val
        #     if k == "伤害":
        #         self.attack += val
        #         continue
        #     if k == "最大生命值":
        #         self.max_healthy += val
        #         continue
        #     if k == "最大魔法值":
        #         self.mana += val
        #         continue
        #     if k == "攻击速度":
        #         self.attack_speed += val
        #         continue
        #     if k == "防御":
        #         self.defense += val
        #         continue
        #     if k == "闪躲":
        #         self.miss += val
        #         continue
        # self.update_blit = True

    def change_status_Deprecate(self, status: dict, add: bool = True):
        """
        修改角色属性
        :param status: 属性字典，例如 {'力量': 10, '伤害': 5.5}
        :param add: True 为穿装备（加属性），False 为脱装备（减属性）
        """
        for k, raw_val in status.items():
            try:
                # 向下取整并转为整数
                val = math.floor(float(raw_val))
                if not add:
                    val = -val

                # 属性映射逻辑
                if k == "伤害" or k == "attack":
                    self.attack += val
                elif k == "最大生命值" or k == "hp":
                    self.max_healthy += val
                elif k == "最大魔法值" or k == "mp":
                    self.mana += val
                elif k == "攻击速度" or k == "attack_speed":
                    self.attack_speed += val
                elif k == "防御" or k == "defense":
                    self.defense += val
                elif k == "闪躲" or k == "miss":
                    self.miss += val
                # 如果你有其他属性如 力量、敏捷等，继续在这里补充
                elif hasattr(self, k):
                    # 尝试通过反射直接修改同名属性（如果存在）
                    current_attr = getattr(self, k)
                    setattr(self, k, current_attr + val)
                else:
                    # 暂不支持的属性
                    print(f"[属性系统] 暂不支持的属性类型: {k} (值: {val})")

            except (ValueError, TypeError):
                print(f"[属性系统] 属性值格式错误: {k} = {raw_val}")

        self.update_blit = True  # 触发 UI 重绘


    def change_status(self, status: dict = None, add: bool = True):
        """
        现在这个方法主要作为一个触发器。
        无论传入什么，我们都直接根据当前装备栏的所有装备重新刷新最终属性。
        """
        self.refresh_final_status()
        self.update_blit = True


    def refresh_final_status(self):
        """
        核心计算逻辑：基于裸体属性计算百分比
        公式：最终值 = int(基础值 + 装备固定值 + (基础值 * 装备百分比总和) + 强度转化)
        """
        # 1. 汇总所有穿戴装备提供的三种加成
        total_fixed = {}
        total_ratio = {}
        total_points = {}

        # 注意：这里确保 self.bag.equips 对应的是你的装备栏字典
        for key, slot in self.bag.equips.items():
            item = slot.get("item")
            if not item:
                continue

            # 获取 Item.py 返回的结构化字典: {"fixed": {}, "ratio": {}, "points": {}}
            attr_pack = item.get_attr()

            # 累计固定值 (Flat)
            for k, v in attr_pack.get("fixed", {}).items():
                total_fixed[k] = total_fixed.get(k, 0) + v
            # 累计百分比 (Ratio)
            for k, v in attr_pack.get("ratio", {}).items():
                total_ratio[k] = total_ratio.get(k, 0.0) + v
            # 累计强度点数 (Points)
            for k, v in attr_pack.get("points", {}).items():
                total_points[k] = total_points.get(k, 0) + v

        # --- A. 更新面板五围属性 (STATUS_POS 中对应的强度值) ---
        # 最终力量 = 裸体力量 + 装备提供的力量强度点数
        self.strength = self.base_strength + int(total_points.get("力量强度", 0))
        self.constitution = self.base_constitution + int(total_points.get("体质强度", 0))
        self.intelligence = self.base_intelligence + int(total_points.get("智力强度", 0))
        self.agile = self.base_agile + int(total_points.get("敏捷强度", 0))
        self.endurance = self.base_endurance + int(total_points.get("精准强度", 0))

        # --- B. 计算二级属性转换 (强度 -> 固定值追加) ---
        # 力量强度 -> 伤害 (2:1)
        total_fixed["伤害"] = total_fixed.get("伤害", 0) + (int(total_points.get("力量强度", 0)) // 2)
        # 体质强度 -> HP (2:3)
        total_fixed["MaxHp"] = total_fixed.get("MaxHp", 0) + (int(total_points.get("体质强度", 0) * 3) // 2)
        # 智力强度 -> MP (2:1)
        total_fixed["MaxMp"] = total_fixed.get("MaxMp", 0) + (int(total_points.get("智力强度", 0)) // 2)
        # 敏捷强度 -> 闪躲 (3:1)
        total_fixed["闪躲"] = total_fixed.get("闪躲", 0) + (int(total_points.get("敏捷强度", 0)) // 3)

        # --- C. 执行最终公式计算 (所有结果向下取整) ---
        # 计算攻击力 (Attack)
        self.attack = int(math.floor(
            self.base_attack + total_fixed.get("伤害", 0) + (self.base_attack * total_ratio.get("伤害", 0.0))
        ))

        # 计算最大生命 (Max HP)
        self.max_healthy = int(math.floor(
            self.base_max_hp + total_fixed.get("MaxHp", 0) + (self.base_max_hp * total_ratio.get("hp", 0.0))
        ))

        # 计算最大魔法 (Max MP)
        self.mana = int(math.floor(
            self.base_base_mp + total_fixed.get("MaxMp", 0) + (self.base_base_mp * total_ratio.get("mp", 0.0))
        ))

        # 计算防御 (Defense)
        self.defense = int(math.floor(
            self.base_defense + total_fixed.get("防御", 0) + (self.base_defense * total_ratio.get("防御", 0.0))
        ))

        # 计算闪躲 (Miss/Dodge)
        self.miss = int(math.floor(
            self.base_miss + total_fixed.get("闪躲", 0) + (self.base_miss * total_ratio.get("闪躲", 0.0))
        ))

        # 计算速度 (Attack Speed)
        self.attack_speed = int(math.floor(
            self.base_attack_speed + total_fixed.get("攻击速度", 0) + (
                        self.base_attack_speed * total_ratio.get("攻击速度", 0.0))
        ))

        # --- D. 状态修正与通知 ---
        # 如果上限变小了，当前值不能超过上限
        if self.healthy > self.max_healthy:
            self.healthy = self.max_healthy

        # 标记需要重绘 UI 面板
        self.update_blit = True



    def level_up(self):
        """ 玩家升级时的逻辑示例 """
        # 提升裸体基础属性
        self.base_attack += 5
        self.base_max_hp += 50

        # 升级后必须调用一次刷新，让装备的百分比加成应用到新的基础值上
        self.refresh_final_status()
