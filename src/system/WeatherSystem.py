#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : WeatherSystem.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2026/04/14 14:00
@Desc    : 天气系统
"""
import random

import pygame
from src.code.SpriteBase import SpriteBase

class WeatherSystem(SpriteBase):
    def __init__(self, gm):
        super().__init__()
        self.__gm = gm
        self.__weather_type = None
        self.particles = []
        # 预创建大雾遮罩层
        self.fog_overlay = pygame.Surface((self.__gm.game_win.get_width(), self.__gm.game_win.get_height()),
                                          pygame.SRCALPHA)
        self.view_rect = self.__gm.game_win.get_rect()

    def setWeather(self, weather_type):
        """设置当前天气并初始化粒子库"""
        if self.__weather_type == weather_type:
            return

        self.__weather_type = weather_type
        self.particles = []

        if not weather_type:
            return

        if weather_type == "rain":
            # 初始化雨滴：[x, y, speed, length]
            self.particles = [[random.randint(0, self.view_rect.width),
                               random.randint(0, self.view_rect.height),
                               random.randint(10, 15),
                               random.randint(5, 12)] for _ in range(100)]
        elif weather_type == "snow":
            # 初始化雪花：[x, y, speed, radius]
            self.particles = [[random.randint(0, self.view_rect.width),
                               random.randint(0, self.view_rect.height),
                               random.uniform(1, 3),
                               random.randint(2, 4)] for _ in range(80)]
        elif weather_type == "fog":
            # 大雾使用半透明 Surface 遮罩
            self.fog_surface = pygame.Surface((self.view_rect.width, self.view_rect.height))
            self.fog_surface.set_alpha(120)  # 雾的浓度
            self.fog_surface.fill((200, 200, 200))  # 灰白色雾

    def clear(self):
        """清空当前天气效果。"""
        self.setWeather(None)

    def render_sticky(self):
        """置顶渲染"""
        if not self.__weather_type:
            return

        screen = self.__gm.game_win

        if self.__weather_type == "fog":
            self.__render_fog_with_hole(screen)

        elif self.__weather_type == "rain":
            for p in self.particles:
                # 绘制斜雨丝
                pygame.draw.line(screen, (150, 150, 255), (p[0], p[1]), (p[0] - 2, p[1] + p[3]), 1)
                p[1] += p[2]  # 下落
                p[0] -= 1  # 随风微偏
                if p[1] > self.view_rect.height: p[1] = -10; p[0] = random.randint(0, self.view_rect.width)

        elif self.__weather_type == "snow":
            for p in self.particles:
                # 绘制圆点雪花
                pygame.draw.circle(screen, (255, 255, 255), (int(p[0]), int(p[1])), p[3])
                p[1] += p[2]
                p[0] += random.uniform(-0.5, 0.5)  # 左右晃动
                if p[1] > self.view_rect.height: p[1] = -5; p[0] = random.randint(0, self.view_rect.width)

    def __render_fog_with_hole(self, screen):
        """渲染带有主角避让区域的大雾"""
        # 1. 填充基础雾色 (R, G, B, Alpha)
        self.fog_overlay.fill((200, 200, 200, 200))

        # 2. 获取主角位置
        player = self.__gm.get("主角")
        if player:
            # 将世界坐标转换为屏幕像素坐标
            # 注意：这里需要是主角在屏幕上的中心点
            p_pos = player.get_pos_world()  # [x, y, w, h]
            screen_pos = self.__gm.global_to_scene_pos(p_pos[0], p_pos[1])

            # 计算圆心（角色脚底或中心）
            center_x = screen_pos[0]
            center_y = screen_pos[1] - (p_pos[3] / 2)  # 向上偏移半个身位

            # 3. 在遮罩上“挖洞”
            # 使用透明色 (0,0,0,0) 和特殊混合模式来清除该区域的 Alpha
            # 这里的 150 是避让半径
            pygame.draw.circle(self.fog_overlay, (0, 0, 0, 0), (int(center_x), int(center_y)), 150)

            # 可选：绘制一个带羽化效果的渐变圆（需要多次绘制不同半径且带有不同 alpha 的圆）
            for r in range(150, 180, 5):
                alpha = int(200 * (r - 150) / 30)
                pygame.draw.circle(self.fog_overlay, (200, 200, 200, alpha), (int(center_x), int(center_y)), r, 5)

        # 4. 绘制到主屏幕
        screen.blit(self.fog_overlay, (0, 0))
