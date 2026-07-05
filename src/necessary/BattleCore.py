#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Pure battle rules for turn based combat.

This module intentionally avoids pygame/UI code. GameBattle converts these
serializable events into animations, and the same event stream is saved for
replay/debugging.
"""
import json
import math
import os
import random
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class BattleUnitSnapshot:
    uid: str
    name: str
    side: str
    hp: int
    max_hp: int
    mp: int
    max_mp: int
    attack: int
    defense: int
    speed: int
    level: int
    alive: bool = True


@dataclass
class BattleCommand:
    actor_uid: str
    command_type: str
    target_uid: str = ""
    skill_id: str = ""
    item_uid: str = ""
    item_id: str = ""
    item_name: str = ""


@dataclass
class BattleEffect:
    effect_type: str
    actor_uid: str
    actor_name: str
    target_uid: str = ""
    target_name: str = ""
    value: int = 0
    hp_before: int = 0
    hp_after: int = 0
    mp_before: int = 0
    mp_after: int = 0
    skill_id: str = ""
    skill_name: str = ""
    item_uid: str = ""
    item_id: str = ""
    item_name: str = ""
    success: bool = True
    message: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class BattleRoundRecord:
    round_no: int
    commands: list[dict[str, Any]] = field(default_factory=list)
    effects: list[dict[str, Any]] = field(default_factory=list)


class BattleReplayRecorder:
    def __init__(self, replay_dir: str):
        self.replay_dir = replay_dir
        self.battle_id = f"battle_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.started_at = time.strftime("%Y-%m-%d %H:%M:%S")
        self.seed = random.randint(1, 999999999)
        self.initial_units: list[dict[str, Any]] = []
        self.rounds: list[dict[str, Any]] = []
        self.result: dict[str, Any] = {}

    def start(self, units: list[BattleUnitSnapshot]):
        random.seed(self.seed)
        self.initial_units = [asdict(unit) for unit in units]

    def append_round(self, record: BattleRoundRecord):
        self.rounds.append(asdict(record))

    def finish(self, result: str, reason: str = "") -> str:
        self.result = {
            "result": result,
            "reason": reason,
            "ended_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        os.makedirs(self.replay_dir, exist_ok=True)
        path = os.path.join(self.replay_dir, f"{self.battle_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "battle_id": self.battle_id,
            "started_at": self.started_at,
            "seed": self.seed,
            "initial_units": self.initial_units,
            "rounds": self.rounds,
            "result": self.result,
        }


class BattleRules:
    @staticmethod
    def snapshot_unit(unit, side: str) -> BattleUnitSnapshot:
        return BattleUnitSnapshot(
            uid=str(getattr(unit, "UID", "")),
            name=str(getattr(unit, "name", "未命名单位")),
            side=side,
            hp=int(getattr(unit, "healthy", 0) or 0),
            max_hp=int(getattr(unit, "max_healthy", 0) or 0),
            mp=int(getattr(unit, "mana", 0) or 0),
            max_mp=int(getattr(unit, "max_mana", getattr(unit, "mana", 0)) or 0),
            attack=int(getattr(unit, "attack", 0) or 0),
            defense=int(getattr(unit, "defense", 0) or 0),
            speed=int(getattr(unit, "attack_speed", 0) or 0),
            level=int(getattr(unit, "level", 1) or 1),
            alive=not BattleRules.is_dead(unit),
        )

    @staticmethod
    def is_dead(unit) -> bool:
        return int(getattr(unit, "healthy", 0) or 0) <= 0

    @staticmethod
    def speed(unit) -> int:
        return int(getattr(unit, "attack_speed", 0) or 0)

    @staticmethod
    def calc_damage(actor, target, base_damage: int = 0, defending: bool = False) -> int:
        raw = int(base_damage or getattr(actor, "attack", 1) or 1)
        defense = int(getattr(target, "defense", 0) or 0)
        critical = random.random() < 0.12
        fluctuation = random.uniform(0.9, 1.1)
        damage = int(max(1, (raw - defense) * fluctuation))
        if defending:
            damage = max(1, math.ceil(damage * 0.45))
        return max(1, math.ceil(damage * (1.5 if critical else 1.0)))

    @staticmethod
    def apply_damage(actor, target, base_damage: int = 0, skill=None,
                     mutate: bool = True, defending: bool = False) -> BattleEffect:
        hp_before = int(getattr(target, "healthy", 0) or 0)
        damage = BattleRules.calc_damage(actor, target, base_damage, defending)
        hp_after = max(0, hp_before - damage)
        if mutate:
            target.healthy = hp_after
        if mutate and target.healthy <= 0:
            try:
                target.sprite_state = target.sprite_state.DEAD
            except Exception:
                pass
            if hasattr(target, "on_death"):
                target.on_death()
        return BattleEffect(
            effect_type="damage",
            actor_uid=str(getattr(actor, "UID", "")),
            actor_name=str(getattr(actor, "name", "")),
            target_uid=str(getattr(target, "UID", "")),
            target_name=str(getattr(target, "name", "")),
            value=damage,
            hp_before=hp_before,
            hp_after=hp_after,
            skill_id=str(getattr(skill, "skill_id", "") if skill else ""),
            skill_name=str(getattr(skill, "name", "") if skill else ""),
            extra={"defending": defending},
            message=f"{getattr(actor, 'name', '单位')} 对 {getattr(target, 'name', '目标')} 造成 {damage} 点伤害",
        )

    @staticmethod
    def apply_heal(actor, target, value: int, item=None) -> BattleEffect:
        hp_before = int(getattr(target, "healthy", 0) or 0)
        max_hp = int(getattr(target, "max_healthy", hp_before) or hp_before)
        heal_value = max(1, int(value or max_hp * 0.25))
        target.healthy = min(max_hp, hp_before + heal_value)
        return BattleEffect(
            effect_type="heal",
            actor_uid=str(getattr(actor, "UID", "")),
            actor_name=str(getattr(actor, "name", "")),
            target_uid=str(getattr(target, "UID", "")),
            target_name=str(getattr(target, "name", "")),
            value=int(getattr(target, "healthy", 0) or 0) - hp_before,
            hp_before=hp_before,
            hp_after=int(getattr(target, "healthy", 0) or 0),
            item_uid=str(getattr(item, "UID", "") if item else ""),
            item_id=str(getattr(item, "ID", "") if item else ""),
            item_name=str(getattr(item, "name", "") if item else ""),
            message=f"{getattr(actor, 'name', '单位')} 使用道具恢复 {int(getattr(target, 'healthy', 0) or 0) - hp_before} 点气血",
        )

    @staticmethod
    def apply_mana(actor, target, value: int, item=None) -> BattleEffect:
        mp_before = int(getattr(target, "mana", 0) or 0)
        max_mp = int(getattr(target, "max_mana", mp_before + value) or mp_before + value)
        mana_value = max(1, int(value or max_mp * 0.25))
        target.mana = min(max_mp, mp_before + mana_value)
        return BattleEffect(
            effect_type="mana",
            actor_uid=str(getattr(actor, "UID", "")),
            actor_name=str(getattr(actor, "name", "")),
            target_uid=str(getattr(target, "UID", "")),
            target_name=str(getattr(target, "name", "")),
            value=int(getattr(target, "mana", 0) or 0) - mp_before,
            mp_before=mp_before,
            mp_after=int(getattr(target, "mana", 0) or 0),
            item_uid=str(getattr(item, "UID", "") if item else ""),
            item_id=str(getattr(item, "ID", "") if item else ""),
            item_name=str(getattr(item, "name", "") if item else ""),
            message=f"{getattr(actor, 'name', '单位')} 使用道具恢复 {int(getattr(target, 'mana', 0) or 0) - mp_before} 点法力",
        )

    @staticmethod
    def apply_revive(actor, target, value: int, item=None) -> BattleEffect:
        hp_before = int(getattr(target, "healthy", 0) or 0)
        max_hp = int(getattr(target, "max_healthy", 1) or 1)
        revive_value = max(1, int(value or max_hp * 0.25))
        target.healthy = min(max_hp, revive_value)
        try:
            target.sprite_state = target.sprite_state.IDLE
        except Exception:
            pass
        return BattleEffect(
            effect_type="revive",
            actor_uid=str(getattr(actor, "UID", "")),
            actor_name=str(getattr(actor, "name", "")),
            target_uid=str(getattr(target, "UID", "")),
            target_name=str(getattr(target, "name", "")),
            value=int(getattr(target, "healthy", 0) or 0) - hp_before,
            hp_before=hp_before,
            hp_after=int(getattr(target, "healthy", 0) or 0),
            item_uid=str(getattr(item, "UID", "") if item else ""),
            item_id=str(getattr(item, "ID", "") if item else ""),
            item_name=str(getattr(item, "name", "") if item else ""),
            message=f"{getattr(actor, 'name', '单位')} 复活了 {getattr(target, 'name', '目标')}",
        )

    @staticmethod
    def capture_rate(actor, target) -> float:
        hp = max(0, int(getattr(target, "healthy", 0) or 0))
        max_hp = max(1, int(getattr(target, "max_healthy", 1) or 1))
        level_diff = int(getattr(actor, "level", 1) or 1) - int(getattr(target, "level", 1) or 1)
        hp_bonus = (1 - hp / max_hp) * 0.45
        level_bonus = max(-0.15, min(0.15, level_diff * 0.015))
        return max(0.05, min(0.85, 0.2 + hp_bonus + level_bonus))

    @staticmethod
    def apply_capture(actor, target, mutate: bool = True) -> BattleEffect:
        rate = BattleRules.capture_rate(actor, target)
        success = random.random() < rate
        if success and mutate:
            target.healthy = 0
            try:
                target.sprite_state = target.sprite_state.DEAD
            except Exception:
                pass
        return BattleEffect(
            effect_type="capture",
            actor_uid=str(getattr(actor, "UID", "")),
            actor_name=str(getattr(actor, "name", "")),
            target_uid=str(getattr(target, "UID", "")),
            target_name=str(getattr(target, "name", "")),
            success=success,
            message=f"{'捕捉成功' if success else '捕捉失败'}: {getattr(target, 'name', '目标')}",
            extra={"rate": round(rate, 4)},
        )

    @staticmethod
    def item_effect_type(item) -> str:
        text = f"{getattr(item, 'name', '')} {getattr(item, 'description', '')}"
        if "复活" in text or "还魂" in text:
            return "revive"
        if getattr(item, "max_mp", 0) or "法力" in text or "魔法" in text or "蓝" in text:
            return "mana"
        return "heal"

    @staticmethod
    def item_value(item, target, effect_type: str) -> int:
        if effect_type == "mana":
            return int(getattr(item, "max_mp", 0) or max(20, int(getattr(target, "mana", 0) or 0) // 3))
        return int(getattr(item, "max_hp", 0) or max(30, int(getattr(target, "max_healthy", 100) or 100) // 3))
