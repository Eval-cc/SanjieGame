# #!/usr/bin/env python
# # -*- coding: UTF-8 -*-
# """
# @Project : 三界奇谈
# @File    : Battle_depre.py
# @IDE     : PyCharm
# @Author  : eval-
# @Email   : eval-email@qq.com
# @Date    : 2025/08/07 12:11
# @Desc    : 触发战斗
# """
# from src.code.Enums import BattleState, SpriteState
# from src.code.SpriteBase import SpriteBase
# import pygame
# from src.manager.GameLogManger import GameLogManager
# from src.manager.SourceManager import SourceManager
# from dataclasses import dataclass, field
# import random
# from typing import TYPE_CHECKING, Optional, Dict
#
# from src.render.GameUI import GameUI
#
# if TYPE_CHECKING:
#     from src.manager.GameManager import GameManager
#
#
# @dataclass
# class Action:
#     actor: SpriteBase
#     type: str  # "move", "attack", "magic", "item", "capture"
#     targets: list[SpriteBase] = field(default_factory=list)
#     data: dict = field(default_factory=dict)  # 添加默认值
#     animation_name: str = ""  # 需要执行播放的动画名称
#     animation_loop: bool = False  # 标记动画是否需要重复播放
#     animation_pos: Optional[list] = field(default_factory=list)  # 动画播放位置
#     hit_animation_name: str = ""  # 目标--需要执行播放的动画名称
#     hit_animation_loop: bool = False  # 目标--标记动画是否需要重复播放
#     hit_animation_pos: Optional[list] = field(default_factory=list)  # 动画播放位置
#     animation_complete: bool = False  # 标记动画是否完成
#     action_event: Dict[int, Optional["Action"]] = field(default_factory=dict)  # 帧事件
#     animation_parallel: bool = False  # 动画是否并行
#
#
# class Battle(SpriteBase):
#     def __init__(self, gm):
#         super().__init__()
#         self.gm: GameManager = gm
#         self.battle_bg = SourceManager.load(
#             f"{SourceManager.ui_system_path}/battle_background.png",
#             [gm.game_win_rect.width, gm.game_win_rect.height]
#         )
#         self.battle_bg.set_alpha(200)
#         self.player: SpriteBase = None
#         self.enemy_list: list[SpriteBase] = []
#
#         # 战斗状态
#         self.round = 0
#         self.battle_state = BattleState.START
#         self.active_units: list[SpriteBase] = []
#         self.current_unit_index = 0
#         self.battle_log: list[str] = []
#         self.finished = False
#         self.__GUI_rect_list = []
#         self.update_blit = True
#         # 战斗事件集
#         self.action_queue: list[Action] = []
#         # 动画计时器
#         self.animation_timer = 0.0
#         self.animation_duration = 0.5  # 动画持续时间
#         self.current_action = None  # 新增：当前行动类型
#         self.selected_target = []  # 新增：当前选中的目标数组
#
#         self.skill_data = {}
#
#     def __load_ui(self):
#         game_ui: GameUI = self.gm.get("游戏UI")
#         if game_ui.get_surface_ui("指令框_人物"):
#             game_ui.change_ui_layer("指令框_人物")
#             return
#         [cmd_bg, cmd_rect, cmd_params] = game_ui.load_system_ui(
#             rf"{SourceManager.ui_system_path}\battle\指令框_人物.png",
#             loc="top_right_center",
#             options=
#             {
#                 "name": "指令框_人物",
#                 "mouse_down": self.mouse_down_ui,
#                 "mouse_up": self.mouse_up_ui,
#                 "mouse_move": self.mouse_move_ui,
#                 "mouse_out": self.mouse_out_ui,
#                 "drag": True,
#                 "drag_rect": ["auto", "auto", "auto", "20"],
#                 "contents": [],
#                 "show": True,
#                 "update_blit": self.__update_blit
#             }, sort=True)
#
#         btn_add = [
#             {
#                 "name": "battle_attack",
#                 "label": "攻击",
#             },
#             {
#                 "name": "battle_magic",
#                 "label": "法术",
#             },
#             {
#                 "name": "battle_item",
#                 "label": "道具",
#             },
#             {
#                 "name": "battle_catch",
#                 "label": "捕捉",
#             },
#             {
#                 "name": "battle_break",
#                 "label": "撤退",
#             }
#         ]
#         btn_sur = SourceManager.load(f"{SourceManager.ui_system_path}/ui-button-mini.png",
#                                      scale=[cmd_rect.width - 15, 20])
#         btn_mask = btn_sur.copy()
#         btn_mask.fill((30, 144, 255, 200))
#         btn_mask.set_alpha(200)
#         btn_form_sur = pygame.Surface([btn_sur.width * 2, btn_sur.height])
#         btn_form_sur.blit(btn_sur, (0, 0))
#         btn_form_sur.blit(btn_mask, (btn_sur.width, 0))
#         for index, btn in enumerate(btn_add):
#             [_, cr, cp] = game_ui.load_system_ui(btn_form_sur,
#                                                  # [cmd_rect.width - 15, 20],
#                                                  options=
#                                                  {
#                                                      "name": btn.get("name"),
#                                                      # "show": True,
#                                                      "frame": {
#                                                          "play": False,
#                                                          "size": cmd_rect.width - 15,
#                                                          "count": 2,
#                                                          "index": 0,
#                                                          "loc": (8, 25 + 25 * index),
#                                                      },
#                                                      "label": {
#                                                          "text": btn.get("label"),
#                                                          "size": 11
#                                                      },
#                                                      "parent": [cmd_bg, cmd_rect, cmd_params],
#                                                      "mouse_down": lambda cmd=btn.get("label"): self.ui_cmd_click(cmd),
#                                                      "is_share": True
#                                                  }, sort=True)
#             self.__GUI_rect_list.append([cr, cp])
#
#     def render_floor(self):
#         """
#         战斗场景放在 mask层渲染
#         """
#         if not self.gm.battle_state:
#             return
#
#         self.gm.game_win.blit(self.battle_bg, (0, 0))
#
#         # 判断当前状态是否需要执行事件队列
#         # if self.battle_state == BattleState.ANIMATING:
#         #     self._process_next_action()
#
#     def exec_battle(self, player: SpriteBase, enemy_list: list[SpriteBase]):
#         """
#         执行战斗
#         """
#         player.stop_moving()
#         player.battle_pos = player.position
#         self.__load_ui()
#         self.gm.game_camera.unmounted()
#         player.direction = player.animator.get_dir("左上")
#         player.sprite_state = SpriteState.ATTACK
#         player.animator.play(f"stand_{player.direction}", speed=0.15)
#         player.battle_dict["default_dir"] = f"左上"
#         self.player = player
#         self.enemy_list = [npc for npc in enemy_list]
#
#         # 初始化战斗单位
#         self.active_units = [self.player] + enemy_list
#         self.active_units.sort(key=lambda u: u.attack_speed, reverse=True)  # 速度排序
#
#         # 设置战斗位置
#         # 玩家固定在右下角
#         self.player.position = self.gm.scene_to_global_pos(
#             self.gm.game_win_rect.width - 200,
#             self.gm.game_win_rect.height - 80
#         )
#
#         # 敌人排列在左上角
#         enemy_start_x = 100  # 左上角起点 X
#         enemy_start_y = 150  # 左上角起点 Y
#         enemy_spacing_x = 100  # 敌人之间的水平间距
#         enemy_spacing_y = 80  # 每一行的纵向间距
#         row_offset_x = 40  # 每一行向右偏移的量（模拟倾斜感）
#         max_enemies_in_first_row = 4  # 第一行敌人数
#
#         current_index = 0
#         row = 0
#
#         while current_index < len(enemy_list):
#             enemies_in_row = max(max_enemies_in_first_row - row, 1)  # 每行人数递减
#             row_start_x = enemy_start_x + row * row_offset_x
#             row_y = enemy_start_y + row * enemy_spacing_y
#
#             for col in range(enemies_in_row):
#                 if current_index >= len(enemy_list):
#                     break
#
#                 enemy = enemy_list[current_index]
#                 enemy.direction = enemy.animator.get_dir("右下")
#                 enemy.animator.play(f"stand_{enemy.direction}")
#                 enemy.battle_dict["default_dir"] = f"右下"
#                 x = row_start_x + col * enemy_spacing_x + current_index * 15
#                 y = row_y - col * 10
#
#                 enemy.position = self.gm.scene_to_global_pos(x, y)
#                 current_index += 1
#
#             row += 1
#
#         self.round = 1
#         self.current_unit_index = 0
#         self.finished = False
#         self.battle_log.clear()
#
#         self.log(f"第{self.round}回合开始")
#         self.gm.battle_state = True
#         self.gm.add("game_battle", self)
#
#     def update(self):
#         """战斗更新逻辑"""
#         if self.finished:
#             return
#
#         # 原有的更新逻辑
#         if self.action_queue:
#             self._process_next_action()
#             return
#
#         if self.current_unit_index >= len(self.active_units):
#             self.round += 1
#             self.log(f"第{self.round}回合开始")
#             self.current_unit_index = 0
#
#         current_unit = self.active_units[self.current_unit_index]
#         if current_unit.is_dead():
#             self.current_unit_index += 1
#             return
#
#     def execute_action(self, unit):
#         """
#         执行单位的操作，暂时默认攻击随机敌人
#         """
#         targets = [e for e in self.enemy_list if not e.is_dead()] if unit == self.player else [self.player]
#         if not targets:
#             return
#         target = targets[0]  # 暂时指向第一个
#         dmg = unit.task_damage(target)
#         self.log(f"{unit.name} 攻击 {target.name} ，造成 {dmg} 伤害")
#
#     def check_battle_end(self):
#         if self.player.is_dead():
#             self.log("玩家失败")
#             self.gm.remove("game_battle")
#             return True
#         if all(enemy.is_dead() for enemy in self.enemy_list):
#             self.log("敌人全部死亡")
#             self.gm.remove("game_battle")
#             return True
#         return False
#
#     def log(self, msg: str):
#         self.battle_log.append(msg)
#         GameLogManager.log_service_debug("[BattleLog]", msg)
#
#     def ui_cmd_click(self, cmd: str):
#         """处理UI指令点击事件"""
#         self.log(f"收到指令:{cmd}")
#         game_ui: GameUI = self.gm.get("游戏UI")
#         match cmd:
#             case "攻击":
#                 # 进入目标选择状态--普通攻击就直接让玩家状态切换到进攻
#                 self.change_state(BattleState.PLAYER_ACT)
#                 self.log("请选择需要攻击的目标")
#                 # 设置当前行动类型为攻击
#                 self.current_action = "attack"
#                 game_ui.close_surface_ui("指令框_人物")
#
#             case "法术":
#                 self.log("请选择法术和目标")
#                 game_ui.close_surface_ui("指令框_人物")
#                 self.gm.game_dialog.show_dialog("skill_choose", render_x=0, render_y=5,
#                                                 dialog_callback=self.__dialog_callback)
#
#             case "道具":
#                 self.log("请选择道具和目标")
#                 self.change_state(BattleState.PLAYER_CHOOSE)
#
#             case "捕捉":
#                 self.log("请选择要捕捉的目标")
#                 self.change_state(BattleState.PLAYER_CHOOSE)
#
#             case "撤退":
#                 self._escape_battle()
#
#     def mouse_down_ui(self):
#         mouse_pos = pygame.mouse.get_pos()
#         game_ui: GameUI = self.gm.get("游戏UI")
#         ui_sprite = game_ui.get_surface_sprite("指令框_人物")  # 需要加上背包的偏移
#         for [gui_rect, gui_params] in self.__GUI_rect_list:
#             if gui_rect.collidepoint(mouse_pos[0] - ui_sprite.get("rect").x, mouse_pos[1] - ui_sprite.get("rect").y):
#                 gui_fun = gui_params.get("mouse_down")
#                 if gui_fun:
#                     gui_fun()
#                 gui_params.get("frame")["index"] = 1 if gui_params.get("frame").get(
#                     "target_index") is None else gui_params.get("frame").get("target_index")
#                 self.update_blit = True
#                 return
#
#     def mouse_up_ui(self):
#         for [_, gui_params] in self.__GUI_rect_list:
#             gui_params.get("frame")["index"] = 0
#
#         self.update_blit = True
#
#     def mouse_move_ui(self):
#         pass
#
#     def mouse_out_ui(self):
#         for [_, gui_params] in self.__GUI_rect_list:
#             gui_params.get("frame")["index"] = 0
#
#         self.update_blit = True
#
#     def __update_blit(self):
#         """用于提供给游戏UI进行重绘的方法"""
#         if not self.update_blit:
#             return
#
#         self.update_blit = False
#         game_ui: GameUI = self.gm.get("游戏UI")
#         bag_sur = game_ui.get_surface_ui("指令框_人物")
#
#         # 渲染按钮
#         for [rect, params] in self.__GUI_rect_list:
#             btn_sort_frame_size = params.get("frame").get("size")
#             btn_sort_frame_index = params.get("frame").get("index")
#
#             bag_sur.blit(params.get("surface"), params.get("frame").get("loc"),
#                          (btn_sort_frame_index * btn_sort_frame_size, 0, btn_sort_frame_size, btn_sort_frame_size))
#
#             if params.get("label"):
#                 # 计算文本坐标,确保文件处于ui的中间
#                 width = len(params.get("label").get("text")) * params.get("label").get("size")
#                 lab_left = 0 if rect.width < width else (rect.width - width) // 2
#                 lab_top = 0 if rect.height < params.get("label").get("size") else (rect.height - params.get(
#                     "label").get("size")) // 2
#                 bag_sur.blit(self.gm.game_font.get_text_surface_line(params.get("label").get("text"), True,
#                                                                      params.get("label").get("size"),
#                                                                      font_color="#000000"),
#                              (
#                                  params.get("frame").get("loc")[0] + lab_left,
#                                  params.get("frame").get("loc")[1] + lab_top))
#
#         game_ui.set_surface_ui("指令框_人物", bag_sur)
#
#     def change_state(self, state: BattleState):
#         """更新战斗状态"""
#         self.battle_state = state
#
#     def _process_next_action(self, action: Action = None):
#         """处理事件队列中的一个动作"""
#         if not self.action_queue:
#             self.change_state(BattleState.START)
#             return
#         if action is None:
#             action = self.action_queue[0]
#         if action is None:
#             self.change_state(BattleState.START)
#             return
#         actor = action.actor
#         # target = action.target
#
#         if action.type == "move":
#             self._process_move_action(action)
#         elif action.type == "attack_animation":
#             self._process_attack_animation(action)
#         elif action.type == "hurt_animation":
#             self._process_hurt_animation(action)
#         elif action.type == "attack":
#             self._process_action_effect(action)
#         elif action.type == "magic":
#             self._process_magic_animation(action)
#         elif action.type in ["item", "capture"]:
#             action.animation_complete = True
#         elif action.type == "rotate":
#             actor.direction = actor.animator.get_dir(actor.battle_dict["default_dir"])
#             actor.animator.play(f"stand_{actor.direction}")
#             action.animation_complete = True
#
#         # # 如果动作完成，从队列中移除
#         if action.animation_complete or action.animation_parallel:
#             action.animation_parallel = False
#             self.action_queue.remove(action)
#             return
#         # 执行并行动画
#         # if action.animation_parallel:
#         #     action.animation_parallel = False
#         #     self._process_next_action()
#         #     self.action_queue.remove(action)
#
#     def _process_move_action(self, action: Action):
#         """处理移动动作"""
#         dest_x, dest_y = action.data["to"]
#         cur_x, cur_y = action.actor.position
#         step = 5  # 每帧移动距离
#
#         # 计算到目标的距离
#         dx = dest_x - cur_x
#         dy = dest_y - cur_y
#         distance = (dx ** 2 + dy ** 2) ** 0.5
#
#         # 判断是否到达目标
#         if distance > step:
#             # 计算单位向量
#             dir_x = dx / distance
#             dir_y = dy / distance
#
#             # 按步长移动
#             new_x = cur_x + dir_x * step
#             new_y = cur_y + dir_y * step
#             action.actor.position = (new_x, new_y)
#
#             dir_name = "右下" if dx > 0 else "左上"
#             action.actor.direction = action.actor.animator.get_dir(dir_name)
#             # 播放对应方向的移动动画
#             if not action.actor.animator.is_playing(f"move_{action.actor.direction}"):
#                 action.actor.animator.play(f"move_{action.actor.direction}")
#         else:
#             # 到达目标点
#             action.actor.position = (dest_x, dest_y)
#             action.animation_complete = True
#
#     def _process_attack_animation(self, action: Action):
#         """播放攻击动画"""
#         if action.actor.animator.current == action.animation_name:
#             if action.action_event.get(action.actor.animator.get_frame_index()):
#                 action.actor.animator.speed = 0.5
#                 # self._process_next_action(action)
#                 self._process_hurt_animation(action, False)
#
#             if action.actor.animator.is_playing(action.animation_name) and action.actor.animator.finished:
#                 action.animation_complete = True
#                 action.actor.animator.speed = 0.15
#
#                 for target in action.targets:
#                     target.direction = target.animator.get_dir(target.battle_dict["default_dir"])
#                     target.animator.play(f"stand_{target.direction}")
#                     if target in self.selected_target:
#                         target.battle_state = False
#                         target.eff_animator_floor.stop()
#                         self.selected_target.remove(target)
#                         # continue
#                 return
#
#         if not action.actor.animator.is_playing(action.animation_name):
#             action.actor.animator.play(action.animation_name, loop=False)
#
#     def _process_magic_animation(self, action: Action):
#         """
#         播放施法动画
#         :param action:
#         :return:
#         """
#         actor = action.actor
#         if actor.eff_animator_stick.current == action.animation_name:
#             for target in action.targets:
#                 if target.battle_state:
#                     # self._process_hurt_animation(action, False)
#                     target.animator.play(action.hit_animation_name, loop=False)
#                     target.battle_state = False
#
#             if actor.eff_animator_stick.is_playing(action.animation_name) and actor.eff_animator_stick.finished:
#                 # 停止播放技能特效
#                 actor.eff_animator_stick.stop()
#                 # 本轮事件结束
#                 action.animation_complete = True
#                 # 恢复敌人因为受击之后需要恢复的动画
#                 for target in action.targets:
#                     target.direction = target.eff_animator_floor.get_dir(target.battle_dict["default_dir"])
#                     target.animator.play(f"stand_{target.direction}")
#                     target.eff_animator_floor.stop()
#                     if target in self.selected_target:
#                         self.selected_target.remove(target)
#             return
#
#         if not actor.eff_animator_stick.is_playing(action.animation_name):
#             actor.eff_animator_stick.play(action.animation_name, loop=action.animation_loop,
#                                           render_pos=action.animation_pos, speed=0.5)
#
#     def _process_hurt_animation(self, action: Action, complete: bool = True):
#         """
#         播放受击动画
#         :param action:
#         :param complete: 控制是否允许切换: 动画是否播放完毕
#         :return:
#         """
#         anim_name = action.hit_animation_name or "战斗_挨打"
#         for target in action.targets:
#             if target.animator.current == anim_name:
#                 if target.animator.is_playing(anim_name) and target.animator.finished:
#                     target.direction = target.animator.get_dir(target.battle_dict["default_dir"])
#                     target.animator.play(f"stand_{target.direction}")
#                     action.animation_complete = complete
#                     continue
#
#             if not target.animator.is_playing(anim_name):
#                 target.animator.play(anim_name, loop=False)
#
#     def _process_action_effect(self, action: Action):
#         """处理动作效果"""
#         if action.type == "attack":
#             for en in action.targets:
#                 dmg = action.actor.task_damage(en.attack)
#                 self.log(f"{action.actor.name} 攻击 {en.name} 造成 {dmg} 伤害")
#         # elif action.type == "magic":
#         #     dmg = action.data.get("damage", 0)
#         #     self.log(f"{action.actor.name} 对 {action.target.name} 释放 {action.data['spell_name']} 造成 {dmg} 伤害")
#         # elif action.type == "item":
#         #     self.log(f"{action.actor.name} 使用了 {action.data['item_name']}")
#         # elif action.type == "capture":
#         #     self._try_capture(action.target)
#
#         action.animation_complete = True
#
#     def _move_attack_sequence(self, actor: SpriteBase, targets: list[SpriteBase], action_type: str, data: dict):
#         """生成移动-攻击-返回的事件序列"""
#         original_pos = actor.position
#         target = targets[0]
#         # 1. 计算攻击位置（靠近目标）
#         target_x, target_y = target.position
#         offset_x = -50 if actor == self.player else 50
#         attack_pos = (target_x + target.rect.width, target_y + target.rect.height)
#         # 2. 移动到攻击位置
#         self.action_queue.append(Action(actor, "move", targets, {"to": attack_pos}))
#         # 3. 播放攻击动画
#         self.action_queue.append(Action(actor, "attack_animation", targets, {},
#                                         action_event={5: Action(target, "hurt_animation", [actor], {})},
#                                         animation_name="战斗_攻击1"))
#         # # 4. 执行攻击
#         # self.action_queue.append(Action(actor, action_type, target, data,animation_name="三花聚顶",hit_animation_name="战斗_挨打"))
#         # # 5. 播放受击动画
#         # self.action_queue.append(Action(target, "hurt_animation", actor, {}))
#         # 6. 返回原位
#         self.action_queue.append(Action(actor, "move", targets, {"to": [original_pos[0], original_pos[1] + 5]}))
#         self.action_queue.append(Action(actor, "rotate", targets, {}))
#
#     def _move_magic_sequence(self, actor: SpriteBase, targets: list[SpriteBase], action_type: str, data: dict):
#         """
#         生成施法动画相关
#         :param actor:
#         :param targets:
#         :param action_type:
#         :param data:
#         :return:
#         """
#         # 3. 播放动画
#         self.action_queue.append(Action(actor, "attack_animation", targets, {},
#                                         # action_event={5: Action(target, "hurt_animation", actor, {})},
#                                         animation_name="战斗_施法",
#                                         animation_pos=actor.position,
#                                         animation_parallel=True,
#                                         animation_loop=False
#                                         ))
#
#         self.action_queue.append(Action(actor, "magic", targets, {},
#                                         action_event={
#                                             3: Action(actor, "hurt_animation", targets, {}),
#                                             4: Action(actor, "attack", targets, data)
#                                         },
#                                         animation_name=data.get("animation_name"),
#                                         animation_pos=data.get("animation_pos"),
#                                         animation_loop=False,
#                                         hit_animation_name=data.get("hit_animation_name"),
#                                         hit_animation_pos=data.get("hit_animation_pos")
#                                         ))
#         # self.action_queue.append(Action(actor, action_type, target, data,animation_name="三花聚顶",hit_animation_name="战斗_挨打"))
#         # original_pos = actor.position
#         # self.action_queue.append(Action(actor, "move", [], {"to": [original_pos[0], original_pos[1] + 5]}))
#         self.action_queue.append(Action(actor, "rotate", [], {}))
#
#     def _escape_battle(self):
#         """处理战斗的战略撤退"""
#         # 计算逃跑成功率
#         escape_chance = 0.7  # 基础成功率
#         if random.random() < escape_chance:
#             self.log("成功逃跑了！")
#             game_ui: GameUI = self.gm.get("游戏UI")
#             game_ui.close_surface_ui("指令框_人物")
#             # self.update_blit = True
#             self.player.position = self.player.battle_pos
#             self.gm.battle_state = False
#             self.gm.remove("game_battle")
#             for enemy in self.enemy_list:
#                 enemy.destroy()
#             self.enemy_list.clear()
#             self.gm.game_dialog.close_dialog()
#             self.gm.game_camera.mounted(self.player)
#             self.player = None
#         else:
#             self.log("逃跑失败！")
#             # 逃跑失败，敌人获得额外行动回合
#             self.current_unit_index += 1
#
#     def _try_capture(self, target: SpriteBase):
#         """尝试捕捉目标"""
#         pass
#         # capture_rate = 0.3  # 基础捕捉率30%
#         #
#         # # 根据目标生命值调整捕捉率
#         # hp_ratio = target.hp / target.max_hp
#         # capture_rate *= (1 - hp_ratio * 0.5)  # 生命值越低，捕捉率越高
#         #
#         # if random.random() < capture_rate:
#         #     self.log(f"成功捕捉了{target.name}！")
#         #     # 将目标添加到玩家队伍
#         #     self.gm.add_to_party(target)
#         #     # 从战斗中移除目标
#         #     self.enemy_list.remove(target)
#         # else:
#         #     self.log(f"捕捉{target.name}失败！")
#         #
#         # self.current_unit_index += 1
#
#     def trigger_battle(self, enemy: SpriteBase):
#         """
#         将NPC推送到选中列表,,由NPC调用
#         :param enemy:
#         :return:
#         """
#         if enemy in self.selected_target:
#             enemy.battle_state = False
#             enemy.eff_animator_floor.stop()
#             self.selected_target.remove(enemy)
#             return
#         # 还不是玩家的选中阶段, 那就直接跳出
#         if self.battle_state != BattleState.PLAYER_CHOOSE and self.battle_state != BattleState.PLAYER_ACT:
#             return
#
#         # # 渲染背景特效
#         if self.battle_state == BattleState.PLAYER_ACT:
#             enemy.battle_state = True
#             cpos = enemy.rect.center
#             enemy.eff_animator_floor.play("battle_effect", speed=0.1, render_pos=[[cpos[0], cpos[1] + 20]])
#             self.selected_target.append(enemy)
#             self.change_state(BattleState.ANIMATING)
#             self._move_attack_sequence(self.player, [enemy], "attack", {})
#             game_ui: GameUI = self.gm.get("游戏UI")
#             game_ui.change_ui_layer("指令框_人物")
#             return
#         elif self.battle_state == BattleState.PLAYER_CHOOSE:
#             random_enemies = random.sample(self.enemy_list, min(4, len(self.enemy_list)))
#             random_enemies.insert(0, enemy)
#             eff_pos = []
#             for e in random_enemies:
#                 e.battle_state = True
#                 cpos = e.rect.center
#                 e.eff_animator_floor.play("battle_effect", speed=0.1, render_pos=[[cpos[0], cpos[1] + 20]])
#                 self.selected_target.append(e)
#                 center_pos = [
#                     e.position[0],
#                     e.position[1] - e.rect.height // 2
#                 ]
#                 eff_pos.append(self.gm.global_to_scene_pos(center_pos[0], center_pos[1]))
#             self._move_magic_sequence(self.player, random_enemies,
#                                       "magic", {
#                                           "animation_name": self.skill_data.get("name"),
#                                           "hit_animation_name": "战斗_挨打" if random.random() < 0.5 else "战斗_击飞",
#                                           "animation_pos": eff_pos
#                                       })
#             self.change_state(BattleState.ANIMATING)
#             return
#
#     def __dialog_callback(self, node):
#         if node.get("__type") == "close":
#             game_ui: GameUI = self.gm.get("游戏UI")
#             game_ui.change_ui_layer("指令框_人物")
#             return
#         self.change_state(BattleState.PLAYER_CHOOSE)
#
#         skill_name = node.get("text")
#         if skill_name is None:
#             for el in node.get("children"):
#                 if el.get("tag") == "p" and el.get("text"):
#                     skill_name = el.get("text")
#         if skill_name is None:
#             GameLogManager.log_service_debug("无法释放技能,没有找到当前技能的信息")
#             game_ui: GameUI = self.gm.get("游戏UI")
#             game_ui.change_ui_layer("指令框_人物")
#             return
#
#         self.skill_data = {
#             "name": skill_name
#         }
#
#         self.gm.game_dialog.close_dialog()
