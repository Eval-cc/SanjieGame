# !/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈
@File    ：NPC.py
@IDE     ：PyCharm
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/6/14 20:49
@Describe:
"""
import random
import time
from typing import List, Dict

import pygame

from src.manager.GameEvent import GameEvent
from src.manager.GameLogManger import GameLogManager
from src.manager.GameMapManager import GameMapManager
from src.necessary.GameBattle import BattleManager
from src.system.Animator import Animator
from src.code.SpriteBase import SpriteBase
from src.manager.GameManager import GameManager
from src.manager.SourceManager import SourceManager
from src.code.Enums import SpriteState, SpriteLayer


class NpcSprite(SpriteBase):
    def __init__(self, npc_data: dict, gx: int, gy: int, direction):
        super().__init__([[f"NPC_点击事件"], [1]])
        if npc_data is None:
            self.destroy()
            return
        self.layer = SpriteLayer.ENEMY
        # 添加Animator组件
        self.animator = Animator()
        # 特效动画组件
        self.eff_animator_floor = Animator(GameManager)
        self.eff_animator_stick = Animator(GameManager)
        # 保存当前NPC的副本,用于在复活的时候重新初始化
        self.__npc_data = npc_data
        self.__g_pos = [gx, gy]

        self.__return_origin = 0  # 用于标志NPC最大移动步数, 超过了这个移动次数, , 为0 则不限制
        self.__return_origin_curr = 0  # 当前移动步数

        self.current_path = []  # 存储当前路径
        self.current_path_index = 0  # 当前路径索引
        self.direction = direction  # 朝向的初始值，默认为右下方向
        self.scene_pos = [0, 0]
        self.has_behind = False

        self.mandatory = False
        # 重置下一次移动的时间
        self.random_move_timer = 0

        # 单帧宽度
        self.frame_width = 0
        self.frame_timer = 0
        self.frame_delay = 2  # 每 2 帧更新一次

        self.has_dialog = False

        self.__init_status()
        # 加载动画
        self.load_animations()

    def __init_status(self):
        self.ID = self.__npc_data.get("ID")
        self.name = self.__npc_data.get("名称")
        self.type = int(self.__npc_data.get("类型"))

        user_actor_data = SourceManager.get_csv("user_actor", self.__npc_data.get("模型ID"))
        super().loading_model(user_actor_data)

        self.script = self.__npc_data.get("脚本")
        self.shop_item = [item for item in self.__npc_data.get("出售道具").split(",") if item]
        self.recv_task = self.__npc_data.get("可接受任务")
        self.submit_task = self.__npc_data.get("可完成任务")
        self.ai = self.__npc_data.get("AI类型")

        avatar_name = self.__npc_data.get("头像", "")
        self.avatar = None if not avatar_name else SourceManager.load(f"{SourceManager.ui_face_path}/{avatar_name}.png")
        self.restart_time = int(self.__npc_data.get("重生周期", "0"))
        self.re_curr_time = 0
        """当前的重生计时"""
        self.default_dialog = self.__npc_data.get("默认对话")

        self.healthy = int(self.__npc_data.get("生命"))
        self.max_healthy = self.healthy
        self.mana = int(self.__npc_data.get("法力"))
        self.attack = int(self.__npc_data.get("伤害"))
        self.defense = int(self.__npc_data.get("防御"))
        self.attack_speed = int(self.__npc_data.get("攻速"))
        self.level = int(self.__npc_data.get("等级"))
        self.miss = int(self.__npc_data.get("闪避"))
        self.strength = int(self.__npc_data.get("力量"))
        self.intelligence = int(self.__npc_data.get("智力"))
        self.constitution = int(self.__npc_data.get("体质"))
        self.agile = int(self.__npc_data.get("敏捷"))
        self.endurance = int(self.__npc_data.get("耐力"))
        self.random_move_radius = int(self.__npc_data.get("巡逻范围", "0") or "0")  # 以当前坐标为中心，最大移动格数
        self.__return_origin = self.random_move_radius  # 定为和巡逻距离一样吧, 后续有改动再说

        self.current_path.clear()  # 清空当前路径
        self.current_path_index = 0  # 当前路径索引
        # 是否触发了对话
        self.has_dialog = False

        x, y = GameManager.scene_to_global_pos_box(self.__g_pos[0], self.__g_pos[1])
        # self.rect.x, self.rect.y = x, y
        self.transform.set_pos(x * GameManager.game_box_size, y * GameManager.game_box_size)  # 实际的像素坐标，乘以32格子大小
        # 保存最原始的坐标,方便移动的太远之后,重新给移动回来, 避免NPC移动超过了它应该存在的范围
        self.origin_pos = [x, y]
        self.scene_pos = [x, y]
        self.has_behind = False
        # 随机移动相关
        self.random_move_timer = time.time() + random.uniform(2, 5)  # 首次延迟
        self.mandatory = False  # 允许强制寻路
        self.sprite_state = SpriteState.IDLE

        # self.has_updated_size = False  # 标志位，标记是否更新过尺寸

        # 设置方向表，用于后续方向匹配（合并站立/移动方向，以保证完整性）
        self.supported_directions = sorted(set(self.stand_direction + self.move_direction))

    def load_animations(self):
        """一次性加载NPC的站立和移动动画（不做偏移量计算）"""

        # 加载每一帧的图像
        def load_frames(texture, model, directions):
            frames_by_dir = {}
            if not texture:
                return frames_by_dir
            image = SourceManager.load(texture)
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

            for _dir_idx, dir_val in enumerate(directions):
                d_idx = dir_val - 1
                if d_idx >= rows:
                    continue
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
        stand_frames = load_frames(f"{SourceManager.ui_npc_path}/{self.stand_texture}.png", self.stand_model,
                                   self.stand_direction)
        move_frames = load_frames(f"{SourceManager.ui_npc_path}/{self.move_texture}.png", self.move_model,
                                  self.move_direction)

        self.eff_animator_floor.surface_to_animation_row(
            SourceManager.load(f"{SourceManager.ui_animation_path}/##特技-水清.png"),
            "battle_effect", 5, 13
        )

        self.eff_animator_stick.surface_to_animation_row(
            SourceManager.load(f"{SourceManager.ui_animation_path}/##魔浪滔天.png"),
            "魔浪滔天", 5, 38
        )
        # 添加到 Animator
        for dir_idx, frames in stand_frames.items():
            self.animator.add_animation(f"stand_{dir_idx}", len(frames), 2, frames)
        for dir_idx, frames in move_frames.items():
            self.animator.add_animation(f"move_{dir_idx}", len(frames), 3, frames)

        # 默认播放站立动画
        self.animator.play(f"stand_{self.direction}", speed=0.15)

    def __str__(self):
        return f"NPC:{self.name}"

    def render(self):
        self.move()
        camera_pos = GameManager.game_camera.get_position()
        render_x = self.transform.x - camera_pos.x
        render_y = self.transform.y - camera_pos.y
        # ui相关的坐标, 如:名称
        self.rect.x = render_x
        self.rect.y = render_y
        # 如果当前有挑战的NPC
        if BattleManager.battle_sta() and self.sprite_state != SpriteState.ATTACK and self.sprite_state != SpriteState.DEAD:
            return

        # 随机移动-- 允许不再视野内的时候也移动, 增加真实性
        self.update_random_move()
        # 超过视图区域的就不显示了
        if self.rect.x + self.rect.width < 0 or self.rect.y + self.rect.height < 0:
            return
        view_width = GameManager.game_win_rect.width
        view_height = GameManager.game_win_rect.height
        if self.rect.x + self.rect.width // 2 < 0 or self.rect.y + self.rect.height // 2 < 0 or self.rect.x > view_width or self.rect.y > view_height:
            return

        self.update_sprite()
        # 更新动画
        self.animator.update(0.5)
        self.eff_animator_floor.update(0.5, True)
        #
        # # 使用Animator获取当前帧
        # cpos = self.rect.center
        # # 渲染背景特效
        # self.eff_animator_floor.render(cpos[0], cpos[1] + 20, center=True)
        #

        x_off = -(self.rect.width / 2)
        y_off = - self.rect.height
        if len(self.stand_offset) > 0:
            ani_idx = self.animator.get_current_frame_absolute_index()
            if len(self.stand_offset) > ani_idx:
                x_off = self.stand_offset[ani_idx]["offX"]
                y_off = self.stand_offset[ani_idx]["offY"]
        # 渲染精灵
        current_frame = self.animator.get_frame()
        if current_frame and not self.has_behind:
            GameManager.game_win.blit(current_frame, (render_x + x_off, render_y + y_off))

        if GameManager.has_debug_render:
            # pygame.draw.rect(GameManager.game_win, (100, 220, 100), (
            #     render_x + x_off, render_y + y_off,
            #     self.rect.width, self.rect.height
            # ), 1)
            pygame.draw.rect(GameManager.game_win, (100, 220, 100),
                             (
                                 self.rect.x - self.rect.width // 2, render_y - self.rect.height,
                                 self.rect.width, self.rect.height
                             )
                             , 1)

    # def render_mask(self):
    #     self.eff_animator_stick.update(0.5, True)
    #     # 如果当前有挑战的NPC
    #     if BattleManager.battle_sta() and not self.battle_state:
    #         return
    #
    #     if self.rect.x < 0 or self.rect.y < 0:
    #         return
    #
    #     view_width = GameManager.game_win_rect.width
    #     view_height = GameManager.game_win_rect.height
    #     if self.rect.x > view_width or self.rect.y > view_height:
    #         return
    #     render_x = self.rect.x
    #     render_y = self.rect.y
    #
    #     # 使用统一的偏移量进行渲染
    #     x_off = -(self.rect.width / 2)
    #     y_off = - self.rect.height
    #     if len(self.stand_offset) > 0:
    #         ani_idx = self.animator.get_current_frame_absolute_index()
    #         if len(self.stand_offset) > ani_idx:
    #             x_off = int(self.stand_offset[ani_idx]["offX"])
    #             y_off = int(self.stand_offset[ani_idx]["offY"])
    #     if self.has_behind:
    #         # 渲染精灵
    #         current_frame = self.animator.get_frame()
    #         if current_frame:
    #             a = current_frame.copy()
    #             a.set_alpha(150)
    #             GameManager.game_win.blit(a, (render_x + x_off, render_y + y_off))
    #
    #     # 绘制路径点和连接线
    #     if GameManager.has_debug_render:
    #         previous_pos = None
    #         for pos in self.current_path:
    #             local_x, local_y = GameManager.global_to_scene_pos(pos[0], pos[1])
    #             # 画点
    #             pygame.draw.rect(GameManager.game_win, (250, 250, 250), (local_x, local_y, 10, 10), 0)
    #             # 画线（连接前一个点到当前点）
    #             if previous_pos is not None:
    #                 pygame.draw.line(GameManager.game_win, (100, 255, 100), previous_pos, (local_x + 5, local_y + 5), 2)
    #             previous_pos = (local_x + 5, local_y + 5)
    #
    #         # 基点
    #         pygame.draw.rect(GameManager.game_win, (250, 0, 0), (render_x, render_y, 10, 10), 0)
    #
    #     # 绘制名称
    #     GameFont.render_line_text(f"{self.name}",
    #                               max(
    #                                   10,
    #                                   int(render_x + self.rect.width / 2 - GameFont.get_text_size(f"{self.name}")[
    #                                       0] / 2)
    #                               ),
    #                               max(
    #                                   10,
    #                                   render_y - 10
    #                               ), True,
    #                               font_color="#FF7F24")
    #
    #     # 渲染血条
    #     if self.battle_state and self.sprite_state != SpriteState.DEAD:
    #         pygame.draw.rect(GameManager.game_win, (100, 220, 100),
    #                          (self.rect.x + self.rect.width // 2 - 25, render_y + 4, 50, 5), 1)
    #         pygame.draw.rect(GameManager.game_win, (255, 10, 10),
    #                          (self.rect.x + self.rect.width // 2 - 25, render_y + 5,
    #                           int(50 * self.healthy / self.max_healthy), 3), 0)

    def move(self):
        """根据路径数组移动角色"""
        if self.battle_state:
            return

        if self.sprite_state == SpriteState.IDLE or not self.current_path:
            # 如果当前没移动，确保播放站立动画
            if not self.animator.is_playing(f"stand_{self.direction}"):
                self.animator.play(f"stand_{self.direction}")
                self.sprite_state = SpriteState.IDLE
            return

        if self.current_path_index >= len(self.current_path) or self.has_dialog:
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

    def stop_moving(self):
        """停止移动"""
        self.current_path = []
        self.current_path_index = 0
        self.animator.play(f"stand_{self.direction}")
        self.sprite_state = SpriteState.IDLE

    def set_path(self, path: List[tuple]):
        """设置移动路径(网格坐标)"""
        if not path:
            self.current_path = []
            self.stop_moving()
            return

        # 如果已经在移动，则停止当前移动
        if self.sprite_state == SpriteState.WALK:
            self.stop_moving()

        # 将网格坐标转换为世界坐标
        self.current_path = [(x * GameManager.game_box_size, y * GameManager.game_box_size) for x, y in path]
        self.current_path_index = 0
        self.sprite_state = SpriteState.WALK

        # 立即更新方向（指向第一个目标点）
        if self.current_path:
            dx = self.current_path[0][0] - self.transform.x
            dy = self.current_path[0][1] - self.transform.y
            self.update_direction(dx, dy)

    def update_sprite(self):
        """
        判断是否需要检查超距离之后关闭对话UI
        """
        u_player: SpriteBase = GameManager.get("主角")
        if u_player:
            play_pos = u_player.get_pos_world()
            camera_pos = GameManager.game_camera.get_position()
            px = play_pos[0] - camera_pos.x
            py = play_pos[1] - camera_pos.y
            if self.rect.collidepoint(px, py):
                # print(f"碰到了:{self.name}")
                # 获取玩家脚部位置（通常是玩家坐标的底部）
                player_foot_y = play_pos[1] + play_pos[3]  # 假设height是精灵高度

                # 获取NPC的中心位置
                npc_center_y = self.transform.y + self.height / 2
                self.has_behind = player_foot_y > npc_center_y
                # 如果玩家的脚在NPC中心的下方，视为在背面
                # if self.has_behind:
                #     print(f"玩家在NPC背面:{self.name}")
            else:
                self.has_behind = False

            if not self.has_dialog:
                return
            npc_pos = self.get_pos_world()
            diff_distance = 200
            # 距离太远的不触发点击事件
            if (abs(play_pos[0] - npc_pos[0]) > diff_distance or abs(play_pos[1] - npc_pos[1]) > diff_distance) \
                    or play_pos[0] > npc_pos[0] + npc_pos[2] + diff_distance \
                    or play_pos[0] < npc_pos[0] - diff_distance \
                    or play_pos[1] > npc_pos[1] + npc_pos[3] + diff_distance \
                    or play_pos[1] < npc_pos[1] - diff_distance:
                GameManager.game_dialog.close_dialog()

    def has_clicked_condition(self, target=None):
        if BattleManager.battle_sta() and self.sprite_state == SpriteState.ATTACK:
            # 如果是攻击状态, 那就判断鼠标是否位于这个位置
            _x, _y = pygame.mouse.get_pos()
            if self.rect.collidepoint(_x, _y):
                return True
            return False

        # 计算实际交互距离
        return self.rect.colliderect(GameManager.get("主角").rect)

    def mouse_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        if BattleManager.battle_sta():
            return
        GameManager.get("主角").stop_moving()
        if len(self.default_dialog) > 0:
            # 修改当前NPC的朝向 面对主角
            next_target = GameManager.get("主角").get_pos_world()
            self.update_direction(next_target[0] - self.transform.x,
                                  next_target[1] - self.transform.y)
            self.has_dialog = True
            GameManager.game_dialog.show_dialog(self.default_dialog, self)
            return

    def update_random_move(self):
        """检测是否需要随机移动"""
        if self.random_move_radius == 0:
            if not self.mandatory:
                return  # 此NPC未指定巡逻范围- 且不允许强制移动
        if self.sprite_state == SpriteState.WALK or self.has_dialog or self.battle_state:
            return  # 正在移动/或者战斗 就不打断

        now = time.time()
        if now >= self.random_move_timer or self.mandatory:
            self.mandatory = False
            # 随机目标点（在范围内）
            dx = random.randint(-self.random_move_radius, self.random_move_radius)
            dy = random.randint(-self.random_move_radius, self.random_move_radius)
            target_x = max(self.scene_pos[0] - 1, self.scene_pos[0] + dx)
            target_y = max(self.scene_pos[1] - 1, self.scene_pos[1] + dy)

            if self.__return_origin > 0:
                # 开始回家---移动的太远了
                if self.__return_origin_curr > self.__return_origin:
                    target_x = self.origin_pos[0]
                    target_y = self.origin_pos[1]
                    self.__return_origin_curr = 0

                self.__return_origin_curr += 1  # 步数+ 1

            find_path = GameManager.find_path([target_x, target_y], GameMapManager.game_map_passable(), self.scene_pos,
                                              True)
            self.set_path(find_path)

            # 重置下一次移动的时间
            self.random_move_timer = now + random.uniform(1, 2)

    def hide_dialog(self):
        self.has_dialog = False

    def battle(self):
        """
        触发NPC战斗
        :return:
        """
        # 关闭开窗
        GameManager.game_dialog.close_dialog()
        # 修改状态为攻击--源NPC暂时不修改状态
        # self.sprite_state = SpriteState.ATTACK
        GameLogManager.log_service_debug("开始战斗吧!!!!!")
        GameMapManager.CURR_BATTLE_NPC_UID.append(self.UID)
        arr = []
        # 创建战斗用的NPC副本
        for i in range(3):  # 创建3个副本
            battle_npc = GameMapManager.add_npc(self.ID, self.__g_pos[0], self.__g_pos[1], self.direction)
            battle_npc.load_battle_anim("enemy", self.battle_texture, self.__npc_data)
            battle_npc.sprite_state = SpriteState.ATTACK
            battle_npc.battle_state = True
            arr.append(battle_npc)
        # 触发战斗场景
        BattleManager.battle_start(GameManager.get("主角"), arr)
        arr.clear()

    def destroy(self):
        GameManager.remove(self.UID)  # 从游戏管理器中移除敌人
        GameEvent.remove(f"NPC_点击事件_{self.UID}")  # 移除敌人的点击事件
        GameEvent.remove(f"NPC_键盘事件_{self.UID}")  # 移除敌人的键盘事件
