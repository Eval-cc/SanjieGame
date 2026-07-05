#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : SkillTreePanel.py
@Desc    : 角色技能树面板
"""
import os
from typing import Callable

import pygame

from src.manager.GameFont import GameFont
from src.manager.SourceManager import SourceManager
from src.system.SkillSystem import SkillConfig, SkillSystem


class SkillTreePanel:
    WIDTH = 430
    HEIGHT = 340
    NODE_SIZE = 46
    ICON_SIZE = 36
    X_GAP = 88
    Y_GAP = 72
    LEFT = 42
    TOP = 54

    def __init__(self, actor, on_select: Callable[[SkillConfig], None], on_upgrade: Callable[[SkillConfig], None] = None):
        self.actor = actor
        self.on_select = on_select
        self.on_upgrade = on_upgrade
        self.skills: list[SkillConfig] = []
        self.node_rects: list[tuple[SkillConfig, pygame.Rect]] = []
        self.surface = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        self.refresh()

    def refresh(self) -> pygame.Surface:
        self.skills = SkillSystem.get_current_skills(self.actor)
        self.node_rects.clear()
        self.surface.fill((0, 0, 0, 0))

        bg = SourceManager.load(f"{SourceManager.ui_system_path}/none_window_no_title.png")
        bg = SourceManager.surface_scale(bg, [self.WIDTH, self.HEIGHT])
        self.surface.blit(bg, (0, 0))

        title = GameFont.get_text_surface_line("技能树", True, 16, "#fff3c4")
        self.surface.blit(title, (18, 10))

        positions = self._calc_positions()
        self._draw_links(positions)

        for skill in self.skills:
            rect = pygame.Rect(*positions[skill.skill_id], self.NODE_SIZE, self.NODE_SIZE)
            self.node_rects.append((skill, rect))
            self._draw_node(skill, rect)

        return self.surface

    def mouse_down(self, event=None):
        if event is None:
            return False
        mouse_pos = event.get("mouse_pos", pygame.mouse.get_pos())
        for skill, rect in self.node_rects:
            if rect.collidepoint(mouse_pos):
                self.on_select(skill)
                return False
        return False

    def mouse_double_click(self, event=None):
        if event is None:
            return False
        mouse_pos = event.get("mouse_pos", pygame.mouse.get_pos())
        for skill, rect in self.node_rects:
            if rect.collidepoint(mouse_pos):
                if self.on_upgrade:
                    self.on_upgrade(skill)
                return False
        return False

    def get_hover_skill(self, local_pos) -> SkillConfig | None:
        for skill, rect in self.node_rects:
            if rect.collidepoint(local_pos):
                return skill
        return None

    def _calc_positions(self) -> dict[str, tuple[int, int]]:
        positions = {}
        for idx, skill in enumerate(self.skills):
            row = skill.tree_row if skill.tree_row >= 0 else idx // 5
            col = skill.tree_col if skill.tree_col >= 0 else idx % 5
            if row == 0 and col == 0 and idx > 0:
                row = idx // 5
                col = idx % 5
            x = self.LEFT + col * self.X_GAP
            y = self.TOP + row * self.Y_GAP
            positions[skill.skill_id] = (x, y)
        return positions

    def _draw_links(self, positions: dict[str, tuple[int, int]]):
        group_positions = {
            skill.group_id: positions[skill.skill_id]
            for skill in self.skills
            if skill.group_id
        }
        name_positions = {
            skill.name: positions[skill.skill_id]
            for skill in self.skills
            if skill.name
        }
        for skill in self.skills:
            parent_pos = self._resolve_parent_position(skill.parent_id, positions, group_positions, name_positions)
            if parent_pos is None:
                continue
            sx, sy = parent_pos
            tx, ty = positions[skill.skill_id]
            start = (sx + self.NODE_SIZE // 2, sy + self.NODE_SIZE // 2)
            end = (tx + self.NODE_SIZE // 2, ty + self.NODE_SIZE // 2)
            pygame.draw.line(self.surface, (158, 126, 67), start, end, 2)

    @staticmethod
    def _resolve_parent_position(
            parent_id: str,
            positions: dict[str, tuple[int, int]],
            group_positions: dict[str, tuple[int, int]],
            name_positions: dict[str, tuple[int, int]]
    ) -> tuple[int, int] | None:
        if not parent_id:
            return None
        if parent_id in positions:
            return positions[parent_id]
        if parent_id in group_positions:
            return group_positions[parent_id]
        if parent_id in name_positions:
            return name_positions[parent_id]

        parent_skill = SkillSystem.get(skill_id=parent_id) or SkillSystem.get(name=parent_id)
        if parent_skill and parent_skill.group_id in group_positions:
            return group_positions[parent_skill.group_id]
        return None

    def _draw_node(self, skill: SkillConfig, rect: pygame.Rect):
        actor_level = int(getattr(self.actor, "level", 1) or 1)
        unlocked = skill.required_level <= actor_level
        bg_color = (83, 61, 35) if unlocked else (48, 48, 48)
        border_color = (238, 190, 91) if unlocked else (112, 112, 112)
        pygame.draw.rect(self.surface, bg_color, rect, border_radius=4)
        pygame.draw.rect(self.surface, border_color, rect, 2, border_radius=4)

        icon_rect = pygame.Rect(0, 0, self.ICON_SIZE, self.ICON_SIZE)
        icon_rect.center = rect.center
        if skill.icon:
            icon_path = os.path.join(SourceManager.ui_skill_path, skill.icon)
            if os.path.exists(icon_path):
                icon = SourceManager.load(icon_path, [self.ICON_SIZE, self.ICON_SIZE]).copy()
                if not unlocked:
                    icon.set_alpha(100)
                self.surface.blit(icon, icon_rect)

        lvl = GameFont.get_text_surface_line(str(skill.skill_level), True, 10, "#ffffff")
        self.surface.blit(lvl, (rect.right - lvl.width - 3, rect.bottom - lvl.height - 2))
        if SkillSystem.get_next_skill(self.actor, skill):
            marker = GameFont.get_text_surface_line("+", True, 12, "#66ff66")
            self.surface.blit(marker, (rect.x + 3, rect.y + 1))
