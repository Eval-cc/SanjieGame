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
import time
from functools import partial
from typing import List, TYPE_CHECKING

import pygame

from src.Mapper.FsoMapper import FsoMapper
from src.code.GameBag import GameBag
from src.manager.GameLogManger import GameLogManager
from src.manager.GameWorldManager import GameWorldManager
from src.necessary.GameBattle import BattleManager
from src.system.Animator import Animator
from src.code.SpriteBase import SpriteBase
from src.manager.GameFont import GameFont
from src.manager.GameManager import GameManager
from src.manager.SourceManager import SourceManager
from src.code.Enums import SpriteState
from src.system.GameTipDialog import GameDialogBoxManager

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
                "frames": [215, 0, 30, 40],
                "frames1": [230, 0, 30, 40]
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
        game_tool = SourceManager.ssurface_scale(game_tool, [120, 120])
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
        _game_map = SourceManager.ssurface_scale(ui1_1.subsurface((0, 0, 150, 150)), [100, 100])
        game_ui.load_system_ui(_game_map,
                               pos=[0, 0],
                               options=
                               {
                                   "name": "小地图",
                                   "show": True,
                                   "update_blit": self.__update_blit_map,
                                   "mouse_down": self.__click_map,
                               })
        __game_cursor = SourceManager.load(f"{SourceManager.ui_system_path}/UI_JX/系统框架UI/exp_5-63232.png", [15, 15])
        game_ui.load_system_ui(__game_cursor,
                               pos=[_game_map.width // 2 - __game_cursor.width // 2,
                                    _game_map.height // 2 - __game_cursor.height // 2],
                               options={
                                   "name": "地图光标",
                                   "show": True,
                                   # "has_draw": True
                               })

        skill_bg = SourceManager.load(f"{SourceManager.ui_system_path}/none_window.png", [600, 400])
        game_ui.load_system_ui(skill_bg,
                               [600, 400],
                               "middle",
                               options=
                               {
                                   "name": "角色技能",
                                   "mouse_down": self.__click_status_ui,
                                   "drag": True,
                                   "event_layer": 5,
                                   "drag_rect": ["auto", "auto", "auto", "20"],
                                   "update_blit": self.__update_blit,
                                   "listen_keyboard": lambda: game_ui.get_surface_show("角色技能")
                               }, sort=True)
        self.skill_bg_gif = SourceManager.load(f"{SourceManager.ui_system_path}/dt_bg.gif", skill_bg.get_rect().size)
        self.skill_bg_gif_idx = 0

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
            # self.rect.x, self.rect.y = x, y
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
            btn_sur = SourceManager.ssurface_scale(sprite_sheet.subsurface(frame_coords), [_size, _size])
            new_surface.blit(btn_sur, (0, 0))
            if frame_coords_1:
                btn_sur1 = SourceManager.ssurface_scale(sprite_sheet.subsurface(frame_coords_1), [_size, _size])
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
                image = SourceManager.load(f"{SourceManager.ui_npc_path}/{texture}.png").convert_alpha()
                cols, rows = model
                fw, fh = image.get_width() // cols, image.get_height() // rows
                # 模型是否有缩放
                if self.scale_texture != 1:
                    image = SourceManager.ssurface_scale(image, [image.get_width() * self.scale_texture,
                                                                 image.get_height() * self.scale_texture])
                    fw *= self.scale_texture
                    fh *= self.scale_texture

                first_frame = image.subsurface((0, 0, fw, fh))
                self.rect = first_frame.get_bounding_rect()
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
                    # self.rect = first_frame.get_bounding_rect()
                    # base_offset_x = self.rect.x
                    # base_offset_y = self.rect.y
                    #
                    # # 遍历每一列
                    # frames_by_dir[d_idx] = [
                    #     image.subsurface((
                    #         col * fw + base_offset_x,  # 使用基准偏移量
                    #         d_idx * fh + base_offset_y,  # 使用基准偏移量
                    #         self.rect.width,  # 使用bounding rect的宽度
                    #         self.rect.height  # 使用bounding rect的高度
                    #     ))
                    #     for col in range(cols)
                    # ]
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
        camera_pos = GameManager.game_camera.get_position()

        render_x = self.transform.x - camera_pos.x - self.rect.width / 2  # - (self.rect.width / 2)
        render_y = self.transform.y - camera_pos.y - self.rect.height  # - (self.rect.height / 2)
        self.rect.x = render_x
        self.rect.y = render_y

        if self.eff_animator_floor:
            self.eff_animator_floor.update(0.5, True)
        # 更新动画
        self.animator.update(0.5)  # 以 60fps 作为基准

        # 使用Animator获取当前帧
        current_frame = self.animator.get_frame()
        if current_frame:
            # 使用统一的偏移量进行渲染
            GameManager.game_win.blit(current_frame, (render_x + self.stand_offset[0], render_y + self.stand_offset[1]))

        if GameManager.has_debug_render:
            pygame.draw.rect(GameManager.game_win, (220, 220, 220), (
                render_x, render_y,
                self.rect.width, self.rect.height
            ), 1)

    def render_mask(self):
        camera_pos = GameManager.game_camera.get_position()
        render_x = self.transform.x - camera_pos.x - (self.width / 2)
        render_y = self.transform.y - camera_pos.y - (self.height / 2)
        # 渲染人物名字
        GameFont.render_line_text(self.name,
                                  int(self.rect.x + self.stand_offset[0] + self.rect.width / 2 -
                                      self.name_width / 2),
                                  self.rect.y - 10 + self.stand_offset[1], True)

        if self.eff_animator_stick:
            self.eff_animator_stick.update(0.3, True)

        if GameManager.has_debug_render:
            # 绘制路径点和连接线
            previous_pos = None
            for pos in self.current_path:
                local_x, local_y = GameManager.global_to_scene_pos(pos[0], pos[1])
                # 画点
                pygame.draw.rect(GameManager.game_win, (250, 250, 250), (local_x, local_y, 10, 10), 0)
                # 画线（连接前一个点到当前点）
                if previous_pos is not None:
                    pygame.draw.line(GameManager.game_win, (100, 255, 100), previous_pos, (local_x + 5, local_y + 5), 2)
                previous_pos = (local_x + 5, local_y + 5)

            # 绘制人物的边框
            pygame.draw.rect(GameManager.game_win, (255, 255, 250), (render_x, render_y, self.width, self.height), 1)
            # 脚底的红点
            pygame.draw.rect(GameManager.game_win, (200, 20, 20), [int(render_x + self.width / 2),
                                                                   render_y + (self.height / 2), 10, 10], 0,
                             border_radius=5)
        # 渲染血条
        if BattleManager.battle_sta():
            pygame.draw.rect(GameManager.game_win, (100, 220, 100),
                             (self.rect.x + self.rect.width // 2 - 25, self.rect.y + 10, 50, 5), 1)
            pygame.draw.rect(GameManager.game_win, (255, 10, 10),
                             (self.rect.x + self.rect.width // 2 - 25, self.rect.y + 11,
                              int(50 * self.healthy / self.max_healthy), 3), 0)

    def move(self):
        if self.sprite_state == SpriteState.ATTACK or BattleManager.battle_sta():
            return
        """根据路径数组移动角色（修复坐标体系 + 播放动画）"""
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
        # 更新全局格子坐标
        self.scene_pos = [
            int(self.transform.x // GameManager.game_box_size),
            int(self.transform.y // GameManager.game_box_size)
        ]
        # 通知服务器. 我停止了
        w_server: "GameWorldServer" = GameManager.get_manager("w_server")
        if w_server:
            w_server.send_stop()

    def set_path(self, path: List[tuple]):
        """设置移动路径(网格坐标)"""
        if not path or self.sprite_state == SpriteState.ATTACK:
            self.stop_moving()
            return

        # 如果已经在移动，则停止当前移动
        # if self.sprite_state == SpriteState.WALK:
        #     self.stop_moving()

        # 将网格坐标转换为世界坐标
        self.current_path = [(x * GameManager.game_box_size, y * GameManager.game_box_size) for x, y in path]
        self.current_path_index = 0
        self.sprite_state = SpriteState.WALK

        # 立即更新方向（指向第一个目标点）
        if self.current_path:
            dx = self.current_path[0][0] - self.transform.x
            dy = self.current_path[0][1] - self.transform.y
            self.update_direction(dx, dy)

        # 通知服务器. 我移动了
        w_server: "GameWorldServer" = GameManager.get_manager("w_server")
        if w_server:
            w_server.send_move()

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
        """点击小地图"""
        print("点击小地图")

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

        if game_ui.get_surface_show("角色技能"):
            self.skill_bg_gif_idx = (self.skill_bg_gif_idx + 1) % self.skill_bg_gif.get("len")
            if self.skill_bg_gif_idx == 0:
                self.skill_bg_gif_idx = 0
            skill_sur = game_ui.get_surface_ui("角色技能")

            curr_rect = self.skill_bg_gif.get("rects")[self.skill_bg_gif_idx]
            curr_skill_bg = self.skill_bg_gif.get("surface").subsurface(curr_rect)
            skill_sur.blit(curr_skill_bg, (0, 0))
            self.update_blit = True
            game_ui.set_surface_ui("角色技能", skill_sur)

        game_ui.set_surface_ui("功能区", fun_tool_sur)

    def __update_blit_map(self):
        """绘制小地图"""
        if not self.update_blit_map:
            return
        self.update_blit_map = False

        game_ui: GameUI = GameManager.get("游戏UI")
        cursor_sur = game_ui.get_surface_ui("地图光标")
        rotated_cursor = pygame.transform.rotate(cursor_sur, - self.raw_angle + 230)
        game_ui.set_surface_ui("地图光标", rotated_cursor)

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
        map_cursor_sur["show"] = True
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
                game_ui.change_ui_layer("角色技能")
                return
            case _:
                GameLogManager.log_service_error(f"无法识别的指令: {cbk_name}")

        self.update_blit = True

    def change_status(self, status: dict, add: bool = True):
        for k in status.keys():
            val = int(status.get(k))
            if not add:
                val = -val
            if k == "伤害":
                self.attack += val
                continue
            if k == "最大生命值":
                self.max_healthy += val
                continue
            if k == "最大魔法值":
                self.mana += val
                continue
            if k == "攻击速度":
                self.attack_speed += val
                continue
            if k == "防御":
                self.defense += val
                continue
            if k == "闪躲":
                self.miss += val
                continue
        self.update_blit = True
