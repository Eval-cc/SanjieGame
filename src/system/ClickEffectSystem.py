#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : ClickEffectSystem.py
@Desc    : 地图点击反馈动画
"""
import os

import pygame

from src.code.SpriteBase import SpriteBase
from src.manager.SourceManager import SourceManager


class ClickEffectSystem(SpriteBase):
    def __init__(self, gm):
        super().__init__()
        self.gm = gm
        self.layer_order = 2
        self.frames: list[pygame.Surface] = []
        self.effects: list[dict] = []
        self.__dedupe_frames = 6
        self.__load_frames()

    def __load_frames(self):
        path = os.path.join(SourceManager.ui_system_path, "transfer.png")
        surface = SourceManager.load(path)
        frame_count = 8
        frame_w = surface.get_width() // frame_count
        frame_h = surface.get_height()
        self.frames = [
            surface.subsurface((i * frame_w, 0, frame_w, frame_h)).convert_alpha()
            for i in range(frame_count)
        ]

    def add_world(self, world_x: int, world_y: int):
        if not self.frames:
            return
        world_x = int(world_x)
        world_y = int(world_y)
        dedupe_radius = max(1, getattr(self.gm, "game_box_size", 20) * 3)
        dedupe_radius_sq = dedupe_radius * dedupe_radius
        for effect in self.effects:
            if effect.get("frame", 0) > self.__dedupe_frames:
                continue
            dx = effect["x"] - world_x
            dy = effect["y"] - world_y
            if dx * dx + dy * dy <= dedupe_radius_sq:
                return
        self.effects.append({
            "x": world_x,
            "y": world_y,
            "frame": 0,
            "timer": 0,
            "delay": 3,
        })

    def render_floor(self):
        if not self.effects:
            return

        camera_pos = self.gm.game_camera.get_position()
        alive = []
        for effect in self.effects:
            frame = self.frames[effect["frame"]]
            rect = frame.get_rect()
            rect.center = (effect["x"] - camera_pos.x, effect["y"] - camera_pos.y)
            self.gm.game_win.blit(frame, rect)

            effect["timer"] += 1
            if effect["timer"] >= effect["delay"]:
                effect["timer"] = 0
                effect["frame"] += 1

            if effect["frame"] < len(self.frames):
                alive.append(effect)
        self.effects = alive
