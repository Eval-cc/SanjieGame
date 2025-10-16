#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : PickableItem.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/13 18:46
@Desc    : 世界场景中 待拾取的道具
"""
from typing import Dict, TYPE_CHECKING

import pygame
import random
import uuid
import math
from typing import List, Tuple

from src.code.Enums import SpriteLayer
from src.code.SpriteBase import SpriteBase
from src.manager.GameEvent import GameEvent
from src.manager.GameFont import GameFont
from src.manager.GameManager import GameManager
from src.manager.SourceManager import SourceManager
from src.system.Animator import Animator

if TYPE_CHECKING:
    from src.code.Item import Item


class PickableItem(SpriteBase):
    def __init__(self, item: "Item", world_x: int, world_y: int):
        super().__init__([[f"pick_item_点击事件"], [1]])
        self.item = item

        rand_name = "pick_item1" if item.count > 30 else "pick_item2" if item.type != 1 else "pickable_item"
        self.image = SourceManager.load(fr"Graphics\System\{rand_name}.png", [32, 32]).convert_alpha()
        self.rect = self.image.get_rect()
        # self.mask = SourceManager.create_surface_mask(self.image)
        self.layer = SpriteLayer.PICK_ITEM
        # 动画控制参数
        self.animation_start_time = pygame.time.get_ticks()
        self.is_animating = True

        GameManager.add(f"pick_item_{self.UID}", self)

        self.item_name_sur = GameFont.get_text_surface_line(self.item.name, True, 12, "#7FFF00", True)
        self.rotation_angle = 0  # 动画旋转角

        # 优化动画参数
        self.animation_duration = 1000  # 延长动画时间至1000ms
        self.rotation_progress = 0  # 单独控制旋转进度
        self.bounce_count = 0  # 弹跳次数计数器

        # 贝塞尔曲线参数优化
        start_pos = (world_x, world_y - 70)  # 从更高处掉落
        control_point = (world_x + random.randint(-30, 30), world_y - 80)
        end_pos = (world_x + random.randint(-20, 20), world_y + random.randint(-20, 20))
        self.bezier_points = [start_pos, control_point, end_pos]
        self.render_pos = list(start_pos)

        self.eff_animator_stick = Animator(GameManager)

        # anim_frame = [SourceManager.load(f"{SourceManager.ui_animation_path}/files/{sf}.png", [50, 50]).convert_alpha()
        #               for sf in
        #               range(1, 17)]
        # self.eff_animator_stick.add_animation("pickable_item", len(anim_frame), 30, anim_frame)

        self.eff_animator_stick.surface_to_animation_row(
            SourceManager.load(f"{SourceManager.ui_animation_path}/pickitem.png", [245, 245]),
            "pickable_item", 2, 10
        )
        self.eff_animator_stick.play("pickable_item", speed=0.05, loop=True)

    def calculate_bezier_point(self, t: float, points: List[Tuple[float, float]]) -> List[float]:
        """优化后的二次贝塞尔曲线计算（带子采样抗锯齿）
        Args:
            t: 进度 [0, 1]
            points: 三个控制点 [(x0,y0), (x1,y1), (x2,y2)]
        Returns:
            当前t值对应的平滑坐标[x, y]
        """
        # 基础贝塞尔公式（二次）
        mt = 1 - t
        x = mt * mt * points[0][0] + 2 * mt * t * points[1][0] + t * t * points[2][0]
        y = mt * mt * points[0][1] + 2 * mt * t * points[1][1] + t * t * points[2][1]

        # --- 新增优化部分 ---
        # 1. 子采样抗锯齿（计算前后两点取平均）
        sample_offset = 0.02  # 采样间隔
        t_prev = max(t - sample_offset, 0)
        t_next = min(t + sample_offset, 1)

        mt_prev = 1 - t_prev
        x_prev = mt_prev * mt_prev * points[0][0] + 2 * mt_prev * t_prev * points[1][0] + t_prev * t_prev * points[2][0]
        y_prev = mt_prev * mt_prev * points[0][1] + 2 * mt_prev * t_prev * points[1][1] + t_prev * t_prev * points[2][1]

        mt_next = 1 - t_next
        x_next = mt_next * mt_next * points[0][0] + 2 * mt_next * t_next * points[1][0] + t_next * t_next * points[2][0]
        y_next = mt_next * mt_next * points[0][1] + 2 * mt_next * t_next * points[1][1] + t_next * t_next * points[2][1]

        # 2. 动态权重平滑（根据速度调整）
        velocity = math.sqrt((x_next - x_prev) ** 2 + (y_next - y_prev) ** 2)
        smooth_factor = min(0.5, 10 / velocity) if velocity > 0 else 0.5

        # 3. 返回平滑后的坐标
        return [
            x * smooth_factor + (x_prev + x_next) * (1 - smooth_factor) / 2,
            y * smooth_factor + (y_prev + y_next) * (1 - smooth_factor) / 2
        ]

    def __str__(self):
        return f"可拾取_{self.item.name}"

    def update_animation(self):
        """优化后的动画更新方法"""
        if not self.is_animating:
            return

        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.animation_start_time
        progress = min(elapsed / self.animation_duration, 1.0)

        # 使用缓动函数使运动更自然
        ease_progress = self.ease_out_quad(progress)

        # 计算贝塞尔曲线位置
        self.render_pos = self.calculate_bezier_point(ease_progress, self.bezier_points)

        # 优化弹跳效果 (3次弹跳)
        if progress < 0.8:
            if progress < 0.3:
                self.bounce_count = 0
            elif progress < 0.5 and self.bounce_count < 1:
                self.bounce_count = 1
            elif progress < 0.7 and self.bounce_count < 2:
                self.bounce_count = 2

            bounce_height = math.sin(progress * math.pi * (3 + self.bounce_count)) * (30 - self.bounce_count * 10)
            self.render_pos[1] -= bounce_height

        # 控制旋转进度 (先快后慢)
        self.rotation_progress = min(progress * 1.2, 1.0)

        if progress >= 1.0:
            self.is_animating = False

    def ease_out_quad(self, t: float) -> float:
        """二次缓出函数，使动画结尾更平滑"""
        return t * (2 - t)

    def render_floor(self):
        """优化后的渲染方法"""
        self.update_animation()

        camera_pos = GameManager.game_camera.get_position()
        render_x = self.render_pos[0] - camera_pos[0]
        render_y = self.render_pos[1] - camera_pos[1]
        self.rect.x = render_x
        self.rect.y = render_y

        # 优化旋转效果
        if self.is_animating:
            # 使用缓动旋转 (先快后慢)
            angle = 360 * self.ease_out_quad(self.rotation_progress)
            rotated_img = pygame.transform.rotate(self.image, angle)
            new_rect = rotated_img.get_rect(center=self.rect.center)
            GameManager.game_win.blit(rotated_img, new_rect.topleft)
        else:
            self.eff_animator_stick.update()
            self.eff_animator_stick.render(render_x - 50, render_y)
            GameManager.game_win.blit(self.image, (render_x, render_y))

    def render_mask(self):
        if not self.is_animating:
            camera_pos = GameManager.game_camera.get_position()
            render_x = self.render_pos[0] - camera_pos[0] - self.item_name_sur.width // 2
            render_y = self.render_pos[1] - camera_pos[1] - 10
            GameManager.game_win.blit(self.item_name_sur, (render_x + self.image.width // 2, render_y))

    def mouse_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        u_player = GameManager.get("主角")
        u_player.bag.add_item_exist(self.item)
        self.destroy()


    def destroy(self):
        GameManager.remove(f"pick_item_{self.UID}")  # 从游戏管理器中移除
        GameEvent.remove(f"pick_item_点击事件_{self.UID}")  # 移除点击事件
