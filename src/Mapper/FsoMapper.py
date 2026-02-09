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
        upos = u_player.get_pos_world()
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
                  items=?
              WHERE id = ?;
              '''

        params = (
            GameMapManager.map_id, upos[0], upos[1], u_player.healthy, u_player.mana,
            u_player.attack, u_player.defense, u_player.attack_speed,
            u_player.bag.get_full_save_data(), u_player.fso_id
        )

        cls.gm.game_local_db.execute_non_query(sql, params)
        GameLogManager.log_service_debug("update fso data")
