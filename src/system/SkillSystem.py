#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : SkillSystem.py
@Desc    : 技能配置与战斗技能辅助
"""
import csv
import os
import re
from dataclasses import dataclass
from html import escape
from typing import Optional

import pygame

from src.manager.GameFont import GameFont
from src.manager.GameLogManger import GameLogManager
from src.manager.SourceManager import SourceManager


@dataclass
class SkillConfig:
    skill_id: str
    name: str
    icon: str = "101.jpg"
    group_id: str = ""
    parent_id: str = ""
    tree_row: int = 0
    tree_col: int = 0
    order: int = 0
    skill_level: int = 1
    required_level: int = 1
    mp_cost: int = 0
    description: str = ""
    effect_name: str = "魔浪滔天"
    effect_file: str = "##魔浪滔天.png"
    frame_column: int = 5
    frame_total: int = 38
    damage: int = 0
    target_count: int = 0
    is_area: bool = True
    effect_type: str = "damage"
    target_side: str = "enemy"
    hit_times: int = 1
    upgrade_exp: int = 0
    sp_cost: int = 0
    raw: dict = None


class SkillSystem:
    """技能系统入口.

    目前只接战斗主动技能：读取 skills.csv，生成技能选择 UI，并提供伤害/动画配置。
    """

    _skills: dict[str, SkillConfig] = {}
    _skill_name_index: dict[str, SkillConfig] = {}
    _skill_group_index: dict[str, list[SkillConfig]] = {}
    _loaded = False
    _hover_ui_name = "__技能悬浮说明"
    _hover_skill_id = None

    _manual_skills = [
        SkillConfig("manual_1", "化生唧唧歪歪", "101.jpg", "化生唧唧歪歪", "", 0, 0, 1, 1, 1, 10, "对多个目标造成法术伤害", "化生唧唧歪歪", "化生唧唧歪歪.png", 5, 20, 36, 5, True),
        SkillConfig("manual_2", "漫天花雨", "102.jpg", "漫天花雨", "", 0, 1, 2, 1, 1, 10, "花雨飞落, 对多个目标造成伤害", "漫天花雨", "@@@漫天花雨.png", 5, 19, 135, 5, True),
        SkillConfig("manual_3", "龙卷雨击", "103.jpg", "龙卷雨击", "", 0, 2, 3, 1, 1, 10, "召唤龙卷攻击多个目标", "龙卷雨击", "龙宫龙卷雨击.png", 2, 30, 120, 4, True),
        SkillConfig("manual_4", "地府判官令", "104.jpg", "地府判官令", "", 1, 0, 4, 1, 1, 10, "判官令落, 对目标造成伤害", "地府判官令", "地府判官令.png", 5, 15, 100, 1, False),
        SkillConfig("manual_5", "兔几", "105.jpg", "兔几", "", 1, 1, 5, 1, 1, 10, "兔几特效, 对目标造成伤害", "兔几", "####兔子特效.png", 5, 20, 80, 1, False),
        SkillConfig("manual_6", "呼风唤雨", "106.jpg", "呼风唤雨", "", 1, 2, 6, 1, 1, 10, "呼风唤雨, 攻击多个目标", "呼风唤雨", "##呼风唤雨.png", 5, 25, 160, 5, True),
        SkillConfig("manual_7", "魔浪滔天", "107.jpg", "魔浪滔天", "", 2, 0, 7, 1, 1, 10, "魔浪滔天, 攻击多个目标", "魔浪滔天", "##魔浪滔天.png", 5, 38, 180, 5, True),
        SkillConfig("manual_8", "菩提", "108.jpg", "菩提", "", 2, 1, 8, 1, 1, 10, "菩提特技, 对目标造成伤害", "菩提", "##特技-菩提.png", 5, 15, 60, 1, False),
        SkillConfig("manual_9", "紫气东来", "109.jpg", "紫气东来", "", 2, 2, 9, 1, 1, 10, "紫气东来, 对目标造成伤害", "紫气东来", "化生紫气东来.png", 5, 22, 90, 1, False),
        SkillConfig("manual_10", "情天恨海", "110.png", "情天恨海", "", 3, 1, 10, 1, 1, 10, "情天恨海, 对目标造成伤害", "情天恨海", "女儿情天恨海.png", 5, 15, 140, 1, False),
    ]

    @classmethod
    def load(cls, force: bool = False):
        if cls._loaded and not force:
            return

        cls._skills.clear()
        cls._skill_name_index.clear()
        cls._skill_group_index.clear()
        for skill in cls._manual_skills:
            cls._register(skill)

        csv_path = os.path.join(SourceManager.cfg_csv_path, "skills.csv")
        if not os.path.exists(csv_path):
            cls._loaded = True
            return

        try:
            with open(csv_path, "r", encoding="gb2312", newline="") as f:
                rows = list(csv.reader(f))
        except Exception as e:
            GameLogManager.log_service_error(f"技能表读取失败: {e}")
            cls._loaded = True
            return

        header = None
        data_rows = []
        for row in rows:
            if not row:
                continue
            if cls._clean_key(row[0]) in ("编号", "ID"):
                header = [cls._clean_key(k) for k in row]
                continue
            if header:
                data_rows.append(row)

        if not header:
            cls._loaded = True
            return

        for row in data_rows:
            record = {header[i]: row[i] if i < len(row) else "" for i in range(len(header))}
            skill = cls._skill_from_record(record)
            if skill:
                cls._register(skill)

        cls._loaded = True

    @classmethod
    def get_all(cls) -> list[SkillConfig]:
        cls.load()
        return list(cls._skills.values())

    @classmethod
    def get_current_skills(cls, actor=None) -> list[SkillConfig]:
        cls.load()
        result = []
        for group_skills in cls._skill_group_index.values():
            candidates = cls._sort_group_skills(group_skills)
            group_id = candidates[0].group_id
            result.append(cls.get_current_skill(actor, group_id) or candidates[0])
        return sorted(result, key=lambda s: (s.tree_row, s.tree_col, s.order, s.name))

    @classmethod
    def get_current_skill(cls, actor, group_id: str) -> Optional[SkillConfig]:
        cls.load()
        candidates = cls._sort_group_skills(cls._skill_group_index.get(group_id, []))
        if not candidates:
            return None
        learned_level = cls.get_actor_skill_level(actor, group_id)
        current = candidates[0]
        for skill in candidates:
            if skill.skill_level <= learned_level:
                current = skill
            else:
                break
        return current

    @classmethod
    def get_next_skill(cls, actor, skill: SkillConfig) -> Optional[SkillConfig]:
        cls.load()
        if skill is None:
            return None
        learned_level = cls.get_actor_skill_level(actor, skill.group_id)
        for candidate in cls._sort_group_skills(cls._skill_group_index.get(skill.group_id, [])):
            if candidate.skill_level > learned_level:
                return candidate
        return None

    @classmethod
    def get_actor_skill_level(cls, actor, group_id: str) -> int:
        candidates = cls._sort_group_skills(cls._skill_group_index.get(group_id, []))
        base_level = candidates[0].skill_level if candidates else 1
        if actor is None:
            return base_level
        levels = cls.ensure_actor_skill_levels(actor)
        return cls._to_int(levels.get(group_id), base_level)

    @classmethod
    def ensure_actor_skill_levels(cls, actor) -> dict:
        if actor is None:
            return {}
        levels = getattr(actor, "skill_levels", None)
        if not isinstance(levels, dict):
            levels = cls.parse_actor_skill_levels(levels)
            setattr(actor, "skill_levels", levels)
        return levels

    @staticmethod
    def parse_actor_skill_levels(raw) -> dict:
        if isinstance(raw, dict):
            return {str(k): int(v) for k, v in raw.items() if str(k)}
        if not raw:
            return {}
        result = {}
        for item in re.split(r"[|;]", str(raw)):
            if not item.strip():
                continue
            if ":" in item:
                key, value = item.split(":", 1)
            elif "=" in item:
                key, value = item.split("=", 1)
            else:
                continue
            try:
                result[str(key).strip()] = int(float(str(value).strip()))
            except Exception:
                continue
        return result

    @classmethod
    def can_upgrade(cls, actor, skill: SkillConfig) -> tuple[bool, str, Optional[SkillConfig]]:
        next_skill = cls.get_next_skill(actor, skill)
        if next_skill is None:
            return False, "技能已经达到最高等级", None
        actor_level = int(getattr(actor, "level", 1) or 1)
        if actor_level < next_skill.required_level:
            return False, f"角色等级不足, 需要 {next_skill.required_level} 级", next_skill
        sp_value = cls._get_actor_resource(actor, ("skill_points", "skill_point", "sp"))
        if sp_value is not None and sp_value < next_skill.sp_cost:
            return False, f"技能点不足, 需要 {next_skill.sp_cost}", next_skill
        exp_value = cls._get_actor_resource(actor, ("curr_exp", "exp", "experience"))
        if exp_value is not None and exp_value < next_skill.upgrade_exp:
            return False, f"经验不足, 需要 {next_skill.upgrade_exp}", next_skill
        return True, "可以升级", next_skill

    @classmethod
    def upgrade_skill(cls, actor, skill: SkillConfig) -> tuple[bool, str, Optional[SkillConfig]]:
        can_upgrade, message, next_skill = cls.can_upgrade(actor, skill)
        if not can_upgrade:
            return False, message, next_skill
        cls._consume_actor_resource(actor, ("skill_points", "skill_point", "sp"), next_skill.sp_cost)
        cls._consume_actor_resource(actor, ("curr_exp", "exp", "experience"), next_skill.upgrade_exp)
        levels = cls.ensure_actor_skill_levels(actor)
        levels[next_skill.group_id] = next_skill.skill_level
        return True, f"{next_skill.name} 升级到 Lv.{next_skill.skill_level}", next_skill

    @classmethod
    def get(cls, skill_id: str = None, name: str = None) -> Optional[SkillConfig]:
        cls.load()
        if skill_id and skill_id in cls._skills:
            return cls._skills[skill_id]
        if name and name in cls._skill_name_index:
            return cls._skill_name_index[name]
        return None

    @classmethod
    def calc_damage(cls, actor, skill: SkillConfig) -> int:
        base = skill.damage if skill and skill.damage > 0 else getattr(actor, "attack", 1)
        return max(1, int(base + getattr(actor, "attack", 0)))

    @classmethod
    def can_cast(cls, actor, skill: SkillConfig) -> bool:
        return getattr(actor, "mana", 0) >= skill.mp_cost

    @classmethod
    def consume_mp(cls, actor, skill: SkillConfig):
        actor.mana = max(0, getattr(actor, "mana", 0) - skill.mp_cost)

    @classmethod
    def show_skill_hover(cls, gm, skill: SkillConfig, mouse_pos=None):
        if gm is None or skill is None:
            cls.hide_skill_hover(gm)
            return
        game_ui = gm.get("游戏UI")
        if game_ui is None:
            return
        mouse_pos = mouse_pos or pygame.mouse.get_pos()
        surface = cls._build_skill_hover_surface(skill)
        x, y = cls._calc_hover_pos(gm, surface, mouse_pos)
        sprite = game_ui.get_surface_sprite(cls._hover_ui_name)
        if sprite is None:
            game_ui.load_system_ui(
                surface,
                pos=[x, y],
                options={
                    "name": cls._hover_ui_name,
                    "show": True,
                    "always_on_top": True,
                    "ignore_event": True,
                    "event_layer": 9999,
                    "render_layer": 9999,
                },
                sort=True
            )
        else:
            if cls._hover_skill_id != skill.skill_id:
                game_ui.set_surface_ui(cls._hover_ui_name, surface, show=True)
                sprite = game_ui.get_surface_sprite(cls._hover_ui_name)
            sprite["rect"].x = x
            sprite["rect"].y = y
            sprite["show"] = True
            sprite["always_on_top"] = True
            sprite["event_layer"] = 9999
            sprite["render_layer"] = 9999
        cls._hover_skill_id = skill.skill_id

    @classmethod
    def hide_skill_hover(cls, gm=None):
        cls._hover_skill_id = None
        if gm is None:
            return
        game_ui = gm.get("游戏UI")
        if game_ui:
            game_ui.close_surface_ui(cls._hover_ui_name)

    @classmethod
    def _calc_hover_pos(cls, gm, surface: pygame.Surface, mouse_pos):
        margin = 12
        mouse_x, mouse_y = mouse_pos
        x = mouse_x + 16
        y = mouse_y + 18
        width = surface.get_width()
        height = surface.get_height()
        if x + width + margin > gm.game_win_rect.width:
            x = mouse_x - width - 16
        if y + height + margin > gm.game_win_rect.height:
            y = mouse_y - height - 12
        x = max(margin, min(x, gm.game_win_rect.width - width - margin))
        y = max(margin, min(y, gm.game_win_rect.height - height - margin))
        return x, y

    @classmethod
    def _build_skill_hover_surface(cls, skill: SkillConfig) -> pygame.Surface:
        target_label = "群体" if skill.is_area else "单体"
        side_label = {
            "enemy": "敌方",
            "ally": "友方",
            "self": "自身",
        }.get(skill.target_side, skill.target_side or "敌方")
        lines = [
            (f"{skill.name} Lv.{skill.skill_level}", 14, "#FFE08A"),
            (f"消耗 MP: {skill.mp_cost}", 12, "#E8E0C8"),
            (f"目标: {side_label} {target_label} x{skill.target_count or 1}", 12, "#E8E0C8"),
            (f"打击回合: {skill.hit_times}", 12, "#E8E0C8"),
            (f"基础伤害: {skill.damage}", 12, "#E8E0C8"),
        ]
        description = skill.description or "暂无技能说明"
        for text in cls._wrap_hover_text(description, 18):
            lines.append((text, 12, "#CFC7B0"))

        padding_x = 10
        padding_y = 8
        line_surfaces = [
            GameFont.get_text_surface_line(text, True, font_size, color)
            for text, font_size, color in lines
        ]
        width = max([sur.get_width() for sur in line_surfaces] + [120]) + padding_x * 2
        height = sum(sur.get_height() + 3 for sur in line_surfaces) + padding_y * 2
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(surface, (28, 24, 18, 235), (0, 0, width, height), border_radius=4)
        pygame.draw.rect(surface, (218, 178, 92, 245), (0, 0, width, height), 1, border_radius=4)

        y = padding_y
        for index, text_surface in enumerate(line_surfaces):
            surface.blit(text_surface, (padding_x, y))
            y += text_surface.get_height() + 3
            if index == 0:
                pygame.draw.line(surface, (140, 112, 64, 200), (padding_x, y), (width - padding_x, y), 1)
                y += 3
        return surface

    @staticmethod
    def _wrap_hover_text(text: str, max_chars: int) -> list[str]:
        if len(text) <= max_chars:
            return [text]
        lines = []
        current = ""
        for char in text:
            current += char
            if len(current) >= max_chars:
                lines.append(current)
                current = ""
        if current:
            lines.append(current)
        return lines[:3]

    @classmethod
    def ensure_effect_clip(cls, animator, skill: SkillConfig) -> str:
        if animator.expose_clip(skill.effect_name):
            return skill.effect_name

        effect_path = os.path.join(SourceManager.ui_animation_path, skill.effect_file)
        try:
            animator.surface_to_animation_row(
                SourceManager.load(effect_path),
                skill.effect_name,
                max(skill.frame_column, 1),
                max(skill.frame_total, 1),
            )
            return skill.effect_name
        except Exception as e:
            GameLogManager.log_service_error(f"技能特效加载失败[{skill.name}]: {e}")

        fallback = cls.get(name="魔浪滔天") or cls._manual_skills[6]
        if not animator.expose_clip(fallback.effect_name):
            animator.surface_to_animation_row(
                SourceManager.load(os.path.join(SourceManager.ui_animation_path, fallback.effect_file)),
                fallback.effect_name,
                fallback.frame_column,
                fallback.frame_total,
            )
        return fallback.effect_name

    @classmethod
    def write_battle_skill_dialog(cls, actor=None) -> str:
        skills = cls.get_current_skills(actor)
        path = os.path.join(SourceManager.cfg_task_path, "__skill_choose_generated.html")
        items = []
        for skill in skills:
            items.append(cls._skill_icon_li(skill, 44, 6, "#ece4d0"))
        cls._write_dialog(path, 235, 260, "\n".join(items), close="true")
        return path

    @classmethod
    def write_skill_tree_dialog(cls, actor=None) -> str:
        skills = cls.get_current_skills(actor)
        path = os.path.join(SourceManager.cfg_task_path, "__skill_tree_generated.html")
        rows: dict[int, dict[int, SkillConfig]] = {}

        for skill in skills:
            row = max(0, int(skill.tree_row or 0))
            col = max(0, int(skill.tree_col or 0))
            row_slots = rows.setdefault(row, {})
            while col in row_slots:
                col += 1
            row_slots[col] = skill

        body = ['<p color="#f3e6bf" font-size="15">角色技能</p>']
        if not rows:
            body.append('<p color="#d8c188">暂无技能</p>')

        for row in sorted(rows.keys()):
            row_slots = rows[row]
            max_col = max(row_slots.keys()) if row_slots else -1
            items = []
            for col in range(max_col + 1):
                skill = row_slots.get(col)
                if skill is None:
                    items.append('<li width="46" height="46" margin="10" align-items="center"></li>')
                    continue
                can_upgrade, _, _ = cls.can_upgrade(actor, skill)
                bg_color = "#f0d28a" if can_upgrade else "#efe6d6"
                items.append(cls._skill_icon_li(skill, 46, 10, bg_color))
            body.append(f'<ul width="405" margin="6">\n{"".join(items)}\n</ul>')

        cls._write_dialog(path, 455, 360, "\n".join(body), close="true", wrap_body=False)
        return path

    @classmethod
    def write_skill_book_dialog(cls, actor=None) -> str:
        skills = cls.get_current_skills(actor)
        path = os.path.join(SourceManager.cfg_task_path, "__skill_book_generated.html")
        items = []
        for skill in skills:
            items.append(cls._skill_icon_li(skill, 54, 8, "#efe6d6"))
        cls._write_dialog(path, 390, 330, "\n".join(items), close="true")
        return path

    @classmethod
    def write_skill_detail_dialog(cls, skill: SkillConfig, actor=None) -> str:
        path = os.path.join(SourceManager.cfg_task_path, "__skill_detail_generated.html")
        icon_html = cls._icon_html(skill.icon, placeholder=True)
        area_label = "群体" if skill.is_area else "单体"
        next_skill = cls.get_next_skill(actor, skill)
        can_upgrade, upgrade_tip, _ = cls.can_upgrade(actor, skill)
        skill_name = escape(str(skill.name))
        description = escape(skill.description or "暂无技能说明")
        upgrade_tip = escape(upgrade_tip)
        if next_skill:
            upgrade_body = (
                f'<p>下一等级: Lv.{next_skill.skill_level}    需求等级: {next_skill.required_level}</p>'
                f'<p>升级消耗: 经验 {next_skill.upgrade_exp}    SP {next_skill.sp_cost}</p>'
                f'<p>{upgrade_tip}</p>'
                f'<button id="skill_upgrade_btn" width="92" height="26" @click="skill_upgrade">'
                f'{"升级" if can_upgrade else "无法升级"}</button>'
            )
        else:
            upgrade_body = '<p>已经达到最高等级</p>'
        body = (
            f'<ul width="320" margin="5">'
            f'<li width="300" height="56" margin="5" padding="4" align-items="center" background-color="#efe6d6">'
            f'{icon_html}<p>{skill_name} Lv.{skill.skill_level}</p>'
            f'</li>'
            f'</ul>'
            f'<p>需求等级: {skill.required_level}    消耗MP: {skill.mp_cost}</p>'
            f'<p>目标类型: {area_label}    目标数量: {skill.target_count or 1}</p>'
            f'<p>打击次数: {skill.hit_times}</p>'
            f'<p>基础伤害: {skill.damage}</p>'
            f'<p>{description}</p>'
            f'{upgrade_body}'
        )
        cls._write_dialog(path, 350, 330, body, close="true", wrap_body=False)
        return path

    @classmethod
    def _register(cls, skill: SkillConfig):
        if not skill.group_id:
            skill.group_id = skill.name
        cls._skills[skill.skill_id] = skill
        cls._skill_name_index[skill.name] = skill
        cls._skill_group_index.setdefault(skill.group_id, []).append(skill)

    @classmethod
    def _sort_group_skills(cls, group_skills: list[SkillConfig]) -> list[SkillConfig]:
        return sorted(
            group_skills or [],
            key=lambda s: (s.skill_level, s.required_level, s.order, cls._to_int(s.skill_id, 0)),
        )

    @staticmethod
    def _get_actor_resource(actor, names: tuple[str, ...]) -> Optional[int]:
        if actor is None:
            return None
        for name in names:
            if hasattr(actor, name):
                try:
                    return int(getattr(actor, name) or 0)
                except Exception:
                    return 0
        return None

    @staticmethod
    def _consume_actor_resource(actor, names: tuple[str, ...], amount: int):
        if actor is None or amount <= 0:
            return
        for name in names:
            if hasattr(actor, name):
                try:
                    setattr(actor, name, max(0, int(getattr(actor, name) or 0) - amount))
                except Exception:
                    setattr(actor, name, 0)
                return

    @classmethod
    def _skill_from_record(cls, record: dict) -> Optional[SkillConfig]:
        skill_id = cls._pick(record, "编号", "ID")
        name = cls._pick(record, "名称", "名字")
        if not skill_id or not name:
            return None

        formula = cls._pick(record, "公式", "伤害公式")
        damage = cls._parse_formula_number(formula, "attack")
        mp_cost = cls._to_int(cls._pick(record, "消耗MP", "MP"), 0)
        target_count = cls._to_int(cls._pick(record, "攻击目标个数", "目标个数"), 0)
        hit_times = max(1, cls._to_int(cls._pick(record, "打击回合", "打击次数", "攻击次数", "连击次数"), 1))
        upgrade_exp = cls._to_int(cls._pick(record, "升级经验", "升级消耗经验", "经验消耗"), 0)
        sp_cost = cls._to_int(cls._pick(record, "消耗sp", "消耗SP", "升级SP", "技能点消耗"), 0)
        is_area = cls._pick(record, "是否范围法术", "范围法术") not in ("0", "false", "False")
        effect_type = cls._normalize_effect_type(cls._pick(record, "效果类型", "技能效果", "作用类型"))
        target_side = cls._normalize_target_side(cls._pick(record, "目标阵营", "目标类型", "作用目标"))
        effect_name = cls._pick(record, "施法特效", "施放特效", "特效") or name
        effect_file = cls._find_effect_file(effect_name, name)
        icon = cls._normalize_icon(cls._pick(record, "图标"))
        skill_level = cls._to_int(cls._pick(record, "技能等级", "等级"), 1)
        required_level = cls._to_int(cls._pick(record, "角色等级", "需求等级", "学习等级"), 0)
        if required_level <= 0:
            required_level = cls._parse_formula_number(cls._pick(record, "学习条件", "使用条件"), "Level") or 1
        group_id = cls._pick(record, "技能树ID", "技能组ID", "分组", "树ID") or name

        return SkillConfig(
            skill_id=str(skill_id),
            name=name,
            icon=icon,
            group_id=group_id,
            parent_id=cls._pick(record, "父技能ID", "前置技能ID"),
            tree_row=cls._to_int(cls._pick(record, "树行", "行"), 0),
            tree_col=cls._to_int(cls._pick(record, "树列", "列"), 0),
            order=cls._to_int(cls._pick(record, "排序", "显示排序"), cls._to_int(skill_id, 0)),
            skill_level=skill_level,
            required_level=required_level,
            mp_cost=mp_cost,
            description=cls._pick(record, "详细说明", "说明", "简要说明"),
            effect_name=name if effect_file else effect_name,
            effect_file=effect_file or "##魔浪滔天.png",
            frame_column=cls._to_int(cls._pick(record, "列帧"), 5),
            frame_total=cls._to_int(cls._pick(record, "总帧"), 20),
            damage=damage,
            target_count=target_count,
            is_area=is_area or target_count > 1,
            effect_type=effect_type,
            target_side=target_side,
            hit_times=hit_times,
            upgrade_exp=upgrade_exp,
            sp_cost=sp_cost,
            raw=record,
        )

    @staticmethod
    def _write_dialog(path: str, width: int, height: int, body: str, close: str = "true", wrap_body: bool = True):
        content = f'<ul width="{width - 15}" margin="5">\n{body}\n</ul>' if wrap_body else body
        html = (
            '<!DOCTYPE html>\n<html lang="en">\n<head><meta charset="UTF-8"><title>skills</title></head>\n<body>\n'
            f'<div id="app" width="{width}" height="{height}" color="#2f210d" close="{close}" '
            'background-image="#ROOT_S\\none_window_no_title.png">\n'
            f'{content}\n'
            '</div>\n</body>\n</html>\n'
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    @staticmethod
    def _clean_key(key: str) -> str:
        return re.sub(r"\s+", "", str(key or ""))

    @classmethod
    def _pick(cls, record: dict, *keys: str) -> str:
        for key in keys:
            val = record.get(cls._clean_key(key))
            if val not in (None, ""):
                return str(val).strip()
        return ""

    @staticmethod
    def _to_int(value: str, default: int = 0) -> int:
        try:
            return int(float(str(value).strip()))
        except Exception:
            return default

    @staticmethod
    def _parse_formula_number(formula: str, key: str) -> int:
        match = re.search(rf"{key}\s*(?:=|>=|>|<=|<)\s*(-?\d+)", formula or "")
        if not match:
            return 0
        return int(match.group(1))

    @classmethod
    def _normalize_icon(cls, icon: str) -> str:
        icon = str(icon or "").strip()
        if icon:
            if icon.lower().endswith((".png", ".jpg", ".jpeg")):
                if os.path.exists(os.path.join(SourceManager.ui_skill_path, icon)):
                    return icon
                return ""
            for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
                candidate = icon + ext
                if os.path.exists(os.path.join(SourceManager.ui_skill_path, candidate)):
                    return candidate
        return ""

    @staticmethod
    def _normalize_effect_type(value: str) -> str:
        value = str(value or "").strip().lower()
        if value in ("heal", "治疗", "恢复", "加血"):
            return "heal"
        if value in ("mana", "mp", "回蓝", "法力"):
            return "mana"
        if value in ("buff", "增益"):
            return "buff"
        return "damage"

    @staticmethod
    def _normalize_target_side(value: str) -> str:
        value = str(value or "").strip().lower()
        if value in ("self", "自己", "自身"):
            return "self"
        if value in ("ally", "friend", "友方", "己方", "队友"):
            return "ally"
        return "enemy"

    @classmethod
    def _icon_html(cls, icon: str, placeholder: bool = False) -> str:
        if icon and os.path.exists(os.path.join(SourceManager.ui_skill_path, icon)):
            return f'<img src="#ROOT_SKILL\\{icon}" width="36" height="36" />'
        if placeholder:
            return '<img width="36" height="36" />'
        return ""

    @classmethod
    def _skill_icon_li(cls, skill: SkillConfig, size: int, margin: int, bg_color: str) -> str:
        icon_html = cls._icon_html(skill.icon, placeholder=True)
        skill_id = escape(str(skill.skill_id), quote=True)
        return (
            f'<li width="{size}" height="{size}" margin="{margin}" align-items="center" '
            f'background-color="{bg_color}" data-skill-id="{skill_id}">'
            f'{icon_html}'
            f'</li>'
        )

    @staticmethod
    def _find_effect_file(effect_name: str, skill_name: str) -> str:
        candidates = [
            f"{effect_name}.png",
            f"{skill_name}.png",
            f"##{effect_name}.png",
            f"@@@{effect_name}.png",
            f"化生{effect_name}.png",
            f"女儿{effect_name}.png",
            f"龙宫{effect_name}.png",
        ]
        for candidate in candidates:
            if os.path.exists(os.path.join(SourceManager.ui_animation_path, candidate)):
                return candidate
        return ""
