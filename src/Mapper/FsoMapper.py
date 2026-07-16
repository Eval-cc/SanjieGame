#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : FsoMapper.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2026/02/03 15:14
@Desc    : 角色相关的数据操作
"""
from typing import TYPE_CHECKING

from src.manager.GameLogManger import GameLogManager
from src.manager.GameMapManager import GameMapManager
from src.manager.DungeonManager import DungeonManager
from src.system.SkillSystem import SkillSystem

if TYPE_CHECKING:
    from src.manager.GameManager import GameManager
    from src.character.Player import Player


class FsoMapper:
    gm: "GameManager"

    @classmethod
    def Awake(cls, gm):
        cls.gm = gm

    @classmethod
    def update_pos(cls):
        """更新角色数据"""
        u_player: "Player" = cls.gm.get("主角")
        save_map_id, save_x, save_y = DungeonManager.get_persistent_save_location(GameMapManager.map_id, u_player)
        # 将变量直接打包成元组，通过参数化查询防止注入
        sql = '''
              UPDATE fso
              SET scene_id=?,
                  sx=?,
                  sy=?,
                  healthy=?,
                  mana=?,
                  attack=?,
                  defense=?,
                  attack_speed=?,
                  items=?,
                  level=?,
                  curr_exp=?,
                  upgrade_exp=?,
                  skill_points=?,
                  skill_levels=?
              WHERE id = ?;
              '''

        params = (
            save_map_id, save_x, save_y, u_player.healthy, u_player.mana,
            u_player.attack, u_player.defense, u_player.attack_speed,
            u_player.bag.get_full_save_data(), getattr(u_player, "level", 1),
            getattr(u_player, "curr_exp", 0), getattr(u_player, "upgrade_exp", 0),
            getattr(u_player, "skill_points", 0), SkillSystem.serialize_actor_skill_levels(u_player),
            u_player.fso_id
        )

        cls.gm.game_local_db.execute_non_query(sql, params)
        GameLogManager.log_service_debug("update fso data")

    @classmethod
    def save_skill_data(cls, u_player: "Player" = None):
        if u_player is None:
            u_player = cls.gm.get("主角")
        if u_player is None:
            return
        sql = '''
              UPDATE fso
              SET curr_exp=?,
                  skill_points=?,
                  skill_levels=?
              WHERE id = ?;
              '''
        params = (
            getattr(u_player, "curr_exp", 0),
            getattr(u_player, "skill_points", 0),
            SkillSystem.serialize_actor_skill_levels(u_player),
            u_player.fso_id
        )
        cls.gm.game_local_db.execute_non_query(sql, params)
        GameLogManager.log_service_debug("update fso skill data")
