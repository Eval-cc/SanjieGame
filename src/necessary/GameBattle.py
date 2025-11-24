#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : GameBattle.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/09/24 19:54
@Desc    : 战斗场景
"""
import random
import uuid
from dataclasses import field, dataclass
from typing import TYPE_CHECKING, Dict, Optional
import pygame

from src.code.Enums import SpriteState, BattleState
from src.code.SpriteBase import SpriteBase
from src.manager.GameEvent import GameEvent
from src.manager.GameFont import GameFont
from src.manager.GameLogManger import GameLogManager
from src.manager.GameMapManager import GameMapManager
from src.manager.SourceManager import SourceManager
from src.system.GameToast import GameToastManager

if TYPE_CHECKING:
    from src.manager.GameManager import GameManager
    from src.render.GameUI import GameUI


@dataclass
class Action:
    """
    表示游戏中一个动作的数据类，包含动作的执行者、类型、目标以及相关动画信息等。
    """
    actor: SpriteBase  # 执行动作的角色或精灵对象
    type: str  # "move", "attack", "magic", "item", "capture"
    targets: list[SpriteBase] = field(default_factory=list)
    back: list[int] = field(default_factory=list)  # 返回的坐标
    animation_start: bool = False  # 标记动作是否开始
    animation_name: str = ""  # 需要执行播放的动画名称
    animation_loop: bool = False  # 标记动画是否需要重复播放
    animation_pos: Optional[list] = field(default_factory=list)  # 动画播放位置
    hit_animation_name: str = ""  # 目标--需要执行播放的受击动画名称
    hit_animation_loop: bool = False  # 目标--标记动画是否需要重复播放
    hit_animation_pos: Optional[list] = field(default_factory=list)  # 受击动画播放位置
    animation_parallel: bool = False  # 动画是否并行
    uid: uuid.uuid4() = field(default_factory=uuid.uuid4)  # 唯一标识符
    move_speed: int = 5  # 移动速度
    timer: int = 0  # 动作持续时间
    # data: dict = field(default_factory=dict)  # 添加默认值
    animation_complete: bool = False  # 标记动画是否完成
    # action_event: Dict[int, Optional["Action"]] = field(default_factory=dict)  # 帧事件


@dataclass
class ActionBuff:
    """
    表示游戏中一个动作的数据信息等。
    """
    actor: SpriteBase  # 执行动作的角色或精灵对象
    target: SpriteBase
    type: str  # "buff", "debuff", "info"
    uid: uuid.uuid4() = field(default_factory=uuid.uuid4)  # 唯一标识符
    timer: int = 100


class _CompositeAction:
    """
    把一组 Action 打包成一个复合动作。
    - 只有当内部所有子动作完成时，CompositeAction 才算完成。
    - 子动作可以包含串行和并行的混合。
    """

    def __init__(self, actions: list, actor: SpriteBase):
        self.sub_queue = actions[:]  # 串行动作队列
        self.parallel_queue = []  # 内部并行动作池
        self.uid = actor.UID

    def tick(self, create_action_handlers, log):
        """每帧调用，返回 True 表示整套动作完成"""
        if not self.sub_queue and not self.parallel_queue:
            return True  # 全部完成

        # 1. tick 并行动作
        for pa in self.parallel_queue[:]:
            action_fun = create_action_handlers(pa)
            if action_fun is None:
                log(f"[Composite] 无效并行动作: {pa.type}")
                self.parallel_queue.remove(pa)
                continue

            if not getattr(pa, "animation_start", False):
                pa.animation_start = True

            over = action_fun()
            if over:
                self.parallel_queue.remove(pa)

        # 2. 处理串行动作（只看队头）
        if self.sub_queue:
            head = self.sub_queue[0]
            if head.animation_parallel:
                # 并行动作：移入并行池，并立即 tick 一次
                if head not in self.parallel_queue:
                    self.parallel_queue.append(head)
                self.sub_queue.pop(0)

                action_fun = create_action_handlers(head)
                if action_fun:
                    if not head.animation_start:
                        head.animation_start = True
                    over = action_fun()
                    if over and head in self.parallel_queue:
                        self.parallel_queue.remove(head)
                return False  # Composite 还没结束

            # 串行动作：tick
            action_fun = create_action_handlers(head)
            if action_fun is None:
                log(f"[Composite] 无效串行动作: {head.type}")
                self.sub_queue.pop(0)
                return False

            if not head.animation_start:
                head.animation_start = True

            over = action_fun()
            if over:
                self.sub_queue.pop(0)
                head.animation_start = False

        return False  # 还没完成


class _Battle(SpriteBase):
    def __init__(self, gm: "GameManager"):
        super().__init__([[f"战斗场景点击事件"], [1]])
        self.gm: "GameManager" = gm
        self.battle_bg = SourceManager.load(
            f"{SourceManager.ui_system_path}/battle_background.png",
            [gm.game_win_rect.width, gm.game_win_rect.height]
        )
        self.battle_bg.set_alpha(200)
        self.player: SpriteBase = None
        self.enemy_list: list[SpriteBase] = []
        self.__GUI_rect_list = []
        self.update_blit = True

        self.rect = pygame.Rect(0, 0, gm.game_win_rect.width, gm.game_win_rect.height)
        # 存放主角进入战斗前的坐标, 结束之后恢复, exec_battle 初始化
        self.play_old_pos = [0, 0]

        # 缓存一些状态
        self.player_cache = {
        }
        self.__load_ui()

        self.action_queue: list[_CompositeAction] = []  # 存放所有行动

        # 战斗受损surface, 显示被打击的伤害 或者增益的伤害文本
        self._hit_content_queue: list[ActionBuff] = []

        self.battle_sta: BattleState = BattleState.START  # 当前战斗状态的步骤
        """ 对应战斗状态枚举
        START. 战斗开始 → 初始化
                   玩家与敌人进入指令阶段（可同时）
                       按速度排序逐一执行行动
                       - 执行前检查状态（死亡/封印/晕眩）
                       - 执行行动
                       - 执行后触发效果（反击/连击/死亡判定）
        CMD_ATTACK.      攻击指令
        CMD_MAGIC.       法术指令
        CMD_ITEM.        使用道具指令
        ACTION. 所有行动执行完毕 → 回合结束
                         - 处理 buff/debuff 回合数
                         - 判定战斗是否结束
        REPEAT.  如果未结束 → 进入下一轮（回到步骤1）
        OVER.    战斗结束 → 结算
        """

        self.cmd_tip = GameFont.get_text_surface_line("开始选择目标", True, font_color="#FFFF00")

        self.cmd_tip_bg = SourceManager.load(
            f"{SourceManager.ui_system_path}/message-header.png",
            [self.cmd_tip.width + 20, self.cmd_tip.height + 15]
        )
        self.cmd_tip_bg.blit(self.cmd_tip, (self.cmd_tip.width // 2 - self.cmd_tip.get_width() // 2 + 10, 6))
        # 释放技能的队列
        self.skill_data_queue = {}

    def __load_ui(self):
        """初始化UI"""
        game_ui: "GameUI" = self.gm.get("游戏UI")
        if game_ui.get_surface_ui("指令框_人物"):
            game_ui.change_ui_layer("指令框_人物")
            return
        [cmd_bg, cmd_rect, cmd_params] = game_ui.load_system_ui(
            rf"{SourceManager.ui_system_path}\battle\指令框_人物.png",
            loc="top_right_center",
            options=
            {
                "name": "指令框_人物",
                "mouse_down": self.mouse_down_ui,
                "mouse_up": self.mouse_up_ui,
                "mouse_move": self.mouse_move_ui,
                "mouse_out": self.mouse_out_ui,
                "drag": True,
                "drag_rect": ["auto", "auto", "auto", "20"],
                "contents": [],
                "show": True,
                "update_blit": self.__update_blit
            }, sort=True)

        btn_add = [
            {
                "name": "battle_attack",
                "label": "攻击",
            },
            {
                "name": "battle_magic",
                "label": "法术",
            },
            {
                "name": "battle_item",
                "label": "道具",
            },
            {
                "name": "battle_catch",
                "label": "捕捉",
            },
            {
                "name": "battle_break",
                "label": "撤退",
            }
        ]
        btn_sur = SourceManager.load(f"{SourceManager.ui_system_path}/ui-button-mini.png",
                                     scale=[cmd_rect.width - 15, 20])
        btn_mask = btn_sur.copy()
        btn_mask.fill((30, 144, 255, 200))
        btn_mask.set_alpha(200)
        btn_form_sur = pygame.Surface([btn_sur.width * 2, btn_sur.height])
        btn_form_sur.blit(btn_sur, (0, 0))
        btn_form_sur.blit(btn_mask, (btn_sur.width, 0))
        for index, btn in enumerate(btn_add):
            [_, cr, cp] = game_ui.load_system_ui(btn_form_sur,
                                                 # [cmd_rect.width - 15, 20],
                                                 options=
                                                 {
                                                     "name": btn.get("name"),
                                                     # "show": True,
                                                     "frame": {
                                                         "play": False,
                                                         "size": cmd_rect.width - 15,
                                                         "count": 2,
                                                         "index": 0,
                                                         "loc": (8, 25 + 25 * index),
                                                     },
                                                     "label": {
                                                         "text": btn.get("label"),
                                                         "size": 11
                                                     },
                                                     "parent": [cmd_bg, cmd_rect, cmd_params],
                                                     "mouse_down": lambda cmd=btn.get("label"): self.ui_cmd_click(cmd),
                                                     "is_share": True
                                                 }, sort=True)
            self.__GUI_rect_list.append([cr, cp])

    def exec_battle(self, player: SpriteBase, enemy_list: list[SpriteBase]):
        """
        执行战斗准备
        """
        player.stop_moving()
        self.play_old_pos = player.transform.get_pos_list()
        # self.__load_ui()
        self.gm.game_camera.unmounted()
        player.direction = player.animator.get_dir("左上")
        # player.sprite_state = SpriteState.ATTACK
        player.animator.play(f"stand_{player.direction}", speed=0.15)
        player.battle_dict["default_dir"] = f"左上"

        self.player = player
        player.start_battle()
        self.enemy_list = [npc for npc in enemy_list]

        # 初始化战斗单位
        self.active_units = [self.player] + enemy_list
        self.active_units.sort(key=lambda u: u.attack_speed, reverse=True)  # 速度排序

        # 设置战斗位置
        # 玩家固定在右下角
        _g_pos = self.gm.scene_to_global_pos(
            self.gm.game_win_rect.width - 200,
            self.gm.game_win_rect.height - 80
        )
        self.player.transform.set_pos(_g_pos[0], _g_pos[1])
        self.player.rect.x = self.player.transform.x
        self.player.rect.y = self.player.transform.y

        # 敌人排列在左上角
        enemy_start_x = 100  # 左上角起点 X
        enemy_start_y = 150  # 左上角起点 Y
        enemy_spacing_x = 100  # 敌人之间的水平间距
        enemy_spacing_y = 80  # 每一行的纵向间距
        row_offset_x = 40  # 每一行向右偏移的量（模拟倾斜感）
        max_enemies_in_first_row = 4  # 第一行敌人数

        current_index = 0
        row = 0

        while current_index < len(enemy_list):
            enemies_in_row = max(max_enemies_in_first_row - row, 1)  # 每行人数递减
            row_start_x = enemy_start_x + row * row_offset_x
            row_y = enemy_start_y + row * enemy_spacing_y

            for col in range(enemies_in_row):
                if current_index >= len(enemy_list):
                    break

                enemy = enemy_list[current_index]
                enemy.direction = enemy.animator.get_dir("右下")
                enemy.animator.play(f"stand_{enemy.direction}")
                enemy.battle_dict["default_dir"] = f"右下"
                enemy.start_battle()
                x = row_start_x + col * enemy_spacing_x + current_index * 15
                y = row_y - col * 10

                _g_pos = self.gm.scene_to_global_pos(x, y)
                enemy.transform.set_pos(_g_pos[0], _g_pos[1])
                enemy.rect.x = enemy.transform.x
                enemy.rect.y = enemy.transform.y
                current_index += 1

            row += 1

    def render_floor(self):
        """渲染战斗场景
        具体的NPC渲染在NPC类中这里仅渲染战斗相关的精灵
        """
        self.gm.game_win.blit(self.battle_bg, (0, 0))

        self._process_next_action()

    def render_mask(self):
        if self.battle_sta == BattleState.CMD_ATTACK or \
                self.battle_sta == BattleState.CMD_MAGIC:
            self.gm.game_win.blit(self.cmd_tip_bg, (self.gm.game_win_rect.width // 2 - self.cmd_tip_bg.width // 2,
                                                    self.gm.game_win_rect.height // 2 - self.cmd_tip_bg.height // 2))

    def log(self, msg: str):
        GameToastManager.add_message(msg)
        GameLogManager.log_service_debug("[BattleLog]", msg)

    def ui_cmd_click(self, cmd: str):
        """处理UI指令点击事件"""
        self.log(f"收到指令:{cmd}")
        game_ui: "GameUI" = self.gm.get("游戏UI")
        match cmd:
            case "攻击":
                if self.battle_sta == BattleState.ACTION or self.battle_sta == BattleState.OVER:
                    return
                self.battle_sta: BattleState = BattleState.CMD_ATTACK
                return

            case "法术":
                if self.battle_sta == BattleState.ACTION or self.battle_sta == BattleState.OVER:
                    return
                game_ui.close_surface_ui("指令框_人物")
                self.gm.game_dialog.show_dialog("skill_choose", render_x=0, render_y=5,
                                                dialog_callback=self.__dialog_callback)
                return

            case "道具":
                if self.battle_sta == BattleState.ACTION or self.battle_sta == BattleState.OVER:
                    return
                self.battle_sta: BattleState = BattleState.CMD_ITEM

                def __cbk():
                    game_ui.close_surface_ui("角色背包")
                    self.__active_enemy()  # 开始到敌人执行动作
                    self.battle_sta = BattleState.ACTION  # 开始行动

                game_ui.set_surface_cbk("角色背包", __cbk)
                game_ui.change_ui_layer("角色背包")
                return

            case "捕捉":
                if self.battle_sta == BattleState.ACTION or self.battle_sta == BattleState.OVER:
                    return
                return

            case "撤退":
                if self.battle_sta == BattleState.ACTION:
                    return
                BattleManager.battle_end(True)

            case "战斗结束":
                if self.battle_sta == BattleState.ACTION:
                    return
                BattleManager.battle_end()

    def __update_blit(self):
        """用于提供给游戏UI进行重绘的方法"""
        if not self.update_blit:
            return

        self.update_blit = False
        game_ui: GameUI = self.gm.get("游戏UI")
        bag_sur = game_ui.get_surface_ui("指令框_人物")

        # 渲染按钮
        for [rect, params] in self.__GUI_rect_list:
            btn_sort_frame_size = params.get("frame").get("size")
            btn_sort_frame_index = params.get("frame").get("index")

            bag_sur.blit(params.get("surface"), params.get("frame").get("loc"),
                         (btn_sort_frame_index * btn_sort_frame_size, 0, btn_sort_frame_size, btn_sort_frame_size))

            if params.get("label"):
                # 计算文本坐标,确保文件处于ui的中间
                width = len(params.get("label").get("text")) * params.get("label").get("size")
                lab_left = 0 if rect.width < width else (rect.width - width) // 2
                lab_top = 0 if rect.height < params.get("label").get("size") else (rect.height - params.get(
                    "label").get("size")) // 2
                bag_sur.blit(self.gm.game_font.get_text_surface_line(params.get("label").get("text"), True,
                                                                     params.get("label").get("size"),
                                                                     font_color="#000000"),
                             (
                                 params.get("frame").get("loc")[0] + lab_left,
                                 params.get("frame").get("loc")[1] + lab_top))

        game_ui.set_surface_ui("指令框_人物", bag_sur)

    def mouse_down_ui(self):
        """鼠标按下事件-UI"""
        if not self.__GUI_rect_list:
            return
        mouse_pos = pygame.mouse.get_pos()
        game_ui: GameUI = self.gm.get("游戏UI")
        ui_sprite = game_ui.get_surface_sprite("指令框_人物")  # 需要加上背包的偏移
        for [gui_rect, gui_params] in self.__GUI_rect_list:
            if gui_rect.collidepoint(mouse_pos[0] - ui_sprite.get("rect").x, mouse_pos[1] - ui_sprite.get("rect").y):
                gui_fun = gui_params.get("mouse_down")
                if gui_fun:
                    gui_fun()
                gui_params.get("frame")["index"] = 1 if gui_params.get("frame").get(
                    "target_index") is None else gui_params.get("frame").get("target_index")
                self.update_blit = True
                return

    def mouse_up_ui(self):
        """鼠标抬起事件-UI"""
        for [_, gui_params] in self.__GUI_rect_list:
            gui_params.get("frame")["index"] = 0

        self.update_blit = True

    def mouse_move_ui(self):
        """鼠标移动事件-UI"""
        mouse_pos = pygame.mouse.get_pos()
        game_ui: GameUI = self.gm.get("游戏UI")
        ui_sprite = game_ui.get_surface_sprite("指令框_人物")  # 需要加上背包的偏移
        for [gui_rect, gui_params] in self.__GUI_rect_list:
            if gui_rect.collidepoint(mouse_pos[0] - ui_sprite.get("rect").x, mouse_pos[1] - ui_sprite.get("rect").y):
                gui_params.get("frame")["index"] = 1
                continue

            gui_params.get("frame")["index"] = 0
        self.update_blit = True

    def mouse_out_ui(self):
        """鼠标移出事件-UI"""
        for [_, gui_params] in self.__GUI_rect_list:
            gui_params.get("frame")["index"] = 0

        self.update_blit = True

    def mouse_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        if self.battle_sta == BattleState.CMD_ATTACK or \
                self.battle_sta == BattleState.CMD_MAGIC:
            for en in self.enemy_list:
                # 已经阵亡的就跳过
                if en.sprite_state == SpriteState.DEAD:
                    continue
                if en.has_clicked_condition():
                    action_queue = []
                    if self.battle_sta == BattleState.CMD_ATTACK:
                        action_queue.append(Action(self.player, "move", [en]))

                        action_queue.append(Action(self.player, "attack_animation", [en],
                                                   animation_name="战斗_攻击2",
                                                   animation_parallel=False))
                        action_queue.append(
                            Action(self.player, "hurt", targets=[en], animation_parallel=True, timer=15))

                        tar_pos = self.player.transform.get_pos()
                        action_queue.append(Action(self.player, "back", back=[tar_pos.x, tar_pos.y]))


                    elif self.battle_sta == BattleState.CMD_MAGIC:
                        # 排除已经死亡的
                        __en_list = [e for e in self.enemy_list if e.sprite_state != SpriteState.DEAD]
                        action_queue.append(Action(self.player, "attack_animation", __en_list,
                                                   # action_event={5: Action(target, "hurt_animation", actor, {})},
                                                   animation_name="战斗_施法",
                                                   animation_pos=self.player.transform.get_pos_list(),
                                                   # animation_parallel=True,
                                                   # animation_loop=False
                                                   ))
                        action_queue.append(
                            Action(self.player, "magic_mult", targets=__en_list,
                                   animation_name=self.skill_data_queue.get("player"),
                                   animation_pos=[self.gm.global_to_scene_pos(en.transform.x, en.transform.y)],
                                   hit_animation_name="战斗_挨打" if random.random() < 0.5 else "战斗_击飞",
                                   animation_parallel=True))
                        action_queue.append(
                            Action(self.player, "hurt", targets=__en_list, animation_parallel=True, timer=15))

                    # 确保主角释放动作之后, 恢复idle
                    direction = self.player.animator.get_dir("左上")
                    action_queue.append(
                        Action(self.player, "change_anim", animation_name=f"stand_{direction}", animation_loop=True))
                    self.action_queue.append(_CompositeAction(action_queue, self.player))

                    self.__active_enemy()  # 开始到敌人执行动作
                    self.battle_sta = BattleState.ACTION  # 开始行动
                    break

    def __active_enemy(self):
        for en in self.enemy_list:
            if en.sprite_state == SpriteState.DEAD:
                continue
            actions = []
            actions.append(Action(en, "attack_animation",
                                  animation_name="战斗_施法",
                                  animation_pos=[
                                      self.gm.global_to_scene_pos(self.player.transform.x,
                                                                  self.player.transform.y)],
                                  # animation_parallel=True,
                                  # animation_loop=False
                                  ))
            actions.append(Action(en, "magic", targets=[self.player],
                                  animation_name="魔浪滔天",
                                  animation_pos=[
                                      self.gm.global_to_scene_pos(self.player.transform.x,
                                                                  self.player.transform.y)],
                                  hit_animation_name="战斗_挨打" if random.random() < 0.5 else "战斗_击飞",
                                  animation_parallel=True
                                  ))

            actions.append(Action(en, "hurt", targets=[self.player], timer=15))
            actions.append(Action(en, "back", back=en.transform.get_pos_list()))
            #
            direction = en.animator.get_dir("右下")
            actions.append(
                Action(en, "change_anim", animation_name=f"stand_{direction}", animation_loop=True))

            # 用 CompositeAction 打包
            self.action_queue.append(_CompositeAction(actions, en))

    def _create_action_handlers(self, action: Action):
        """创建动作类型与处理方法的映射"""
        return {
            "move": lambda: self._process_move_action(action),
            "back": lambda: self._process_move_action(action),
            "change_anim": lambda: self._process_change_action(action),
            "hurt": lambda: self._process_hurt_action(action),
            "magic": lambda: self._process_magic_action(action),
            "magic_mult": lambda: self._process_magic_action_mult(action),
            "attack_animation": lambda: self._process_attack_animation(action)
        }.get(action.type, None)

    def _process_next_action(self):
        """处理 action_queue 中的顶层 CompositeAction"""
        # 还没到开始行动阶段, 直接撤回所有操作
        if self.battle_sta != BattleState.ACTION:
            self.action_queue.clear()
            return

        if not self.action_queue:
            if len(self.action_queue) == 0 and self.battle_sta != BattleState.OVER:
                """触发结算逻辑"""
                battle_over = (self.player.healthy <= 0) or all(
                    en.sprite_state == SpriteState.DEAD for en in self.enemy_list)
                if battle_over:
                    # 关闭所有动画展示
                    for en in self.enemy_list:
                        en.eff_animator_floor.stop()
                        en.eff_animator_stick.stop()
                    self.battle_sta = BattleState.OVER
                    self.log("战斗结束")
                    self.ui_cmd_click("战斗结束")
                else:
                    self.battle_sta = BattleState.START
            return
        head = self.action_queue[0]

        # --- 如果是 CompositeAction ---
        if isinstance(head, _CompositeAction):
            over = head.tick(self._create_action_handlers, self.log)
            if over:
                self.action_queue.pop(0)
            return
        else:
            self.log(f"非法的动作类型, 请传入:_CompositeAction")

    def _process_move_action(self, action: Action):
        """处理移动动作（支持在目标点附近停止，避免完全贴脸）"""
        target = action.back if action.type == "back" else action.targets[0].transform.get_pos_list()
        actor = action.actor
        dest_x, dest_y = target
        cur_x, cur_y = actor.transform.get_pos_list()
        step = max(action.move_speed, 5)  # 每帧移动距离

        # 根据动作类型设置停止距离：
        # - 后退动作（back）：必须完全到达目标点
        # - 普通移动：距离目标 10 像素时即停止
        stop_distance = 0 if action.type == "back" else action.actor.rect.width

        # 计算到目标的距离和方向
        dx = dest_x - cur_x
        dy = dest_y - cur_y
        distance = (dx ** 2 + dy ** 2) ** 0.5

        # 提前计算单位方向向量（避免重复计算）
        if distance > 0:  # 防止除以零
            dir_x = dx / distance
            dir_y = dy / distance
        else:
            dir_x, dir_y = 0, 0

        # 判断是否到达停止范围
        if distance > stop_distance + step:
            # 按步长移动
            new_x = cur_x + dir_x * step
            new_y = cur_y + dir_y * step
            actor.transform.set_pos(new_x, new_y)

            # 更新方向动画
            dir_name = "右下" if dx > 0 else "左上"
            actor.direction = actor.animator.get_dir(dir_name)
            if not actor.animator.is_playing(f"move_{actor.direction}"):
                actor.animator.play(f"move_{actor.direction}")
            return False
        else:
            # 到达停止范围
            if distance > stop_distance:
                # 精确停在 stop_distance 距离处
                actor.transform.set_pos(
                    dest_x - dir_x * stop_distance,
                    dest_y - dir_y * stop_distance
                )
            else:
                actor.transform.set_pos(dest_x, dest_y)
            return True

    def _process_hurt_action(self, action: Action):
        """
        播放受击动画
        :param action:
        :return:
        """
        anim_name = action.hit_animation_name or "战斗_挨打"
        if action.animation_complete:
            if action.timer > 0:
                action.timer -= 1
            if action.timer == 0:
                # 恢复敌人因为受击之后需要恢复的动画
                for target in action.targets:
                    if target.sprite_state == SpriteState.DEAD:
                        target.animator.play("战斗_死亡", False)
                        continue  # 死亡了就不要播放其他动画了
                    target.direction = target.animator.get_dir(target.battle_dict["default_dir"])
                    target.animator.play(f"stand_{target.direction}")
                    self.log(f"{target.name}播放动画: stand_{target.direction}")
            return action.timer == 0

        total = 0
        for target in action.targets:
            if target.animator.current == anim_name:
                if target.animator.is_playing(anim_name) and target.animator.finished:
                    action.animation_complete = True
                    total += 1
                    _hurt = target.take_damage(action.actor.attack)
                    if target.sprite_state == SpriteState.DEAD:
                        # target.animator.play("战斗_死亡", False)
                        # 从事件队列移除 ,但是暂时不从总的列表移除. 需要播放一些动画
                        for ac in self.action_queue:
                            if ac.uid == target.UID:
                                self.action_queue.remove(ac)
                                break
                    continue

            if not target.animator.is_playing(anim_name):
                try:
                    target.animator.play(anim_name, loop=False)
                except ValueError as ve:
                    self.log(f"受击动画 {anim_name} 未找到. {ve}")
                    # 找不到动画也还是要执行受伤的
                    _hurt = target.take_damage(action.actor.attack)
                    if target.sprite_state == SpriteState.DEAD:
                        try:
                            target.animator.play("战斗_死亡", False)
                        except ValueError as ve:
                            self.log(f"死亡动画 {anim_name} 未找到. {ve}")
                            target.animator.stop()  # 连待机都给停掉吧
                        # 从事件队列移除 ,但是暂时不从总的列表移除. 需要播放一些动画
                        for ac in self.action_queue:
                            if ac.uid == target.UID:
                                self.action_queue.remove(ac)
                                break
                    return True  # 没有动画还说啥, 直接执行完成吧
        return False

    def _process_magic_action(self, action: Action):
        """
        播放施法动画
        :param action:
        :return:
        """
        actor = action.actor

        if not actor.eff_animator_stick.is_playing(action.animation_name):
            actor.eff_animator_stick.play(action.animation_name, loop=action.animation_loop,
                                          render_pos=action.animation_pos, speed=0.5)
            return False

        if actor.eff_animator_stick.finished:
            # 停止播放技能特效
            actor.eff_animator_stick.stop()
            # 本轮事件结束
            action.animation_complete = True

            return True
        return False

    def _process_magic_action_mult(self, action: Action):
        """
        播放施法动画--批量（每个目标独立播放动画）
        :param action: 包含目标和动画信息的动作
        :return: 是否所有目标的动画均已完成
        """
        # 检查是否已经有目标在播放动画
        is_any_playing = any(
            target.eff_animator_stick.is_playing(action.animation_name)
            for target in action.targets
        )

        # 如果没有目标在播放动画，则对所有目标播放动画
        if not is_any_playing:
            hit_anim = action.actor.eff_animator_stick.expose_clip(action.animation_name)
            for target in action.targets:
                target.eff_animator_stick.add_clip(hit_anim)
                target.eff_animator_stick.play(
                    action.animation_name,
                    loop=action.animation_loop,
                    render_pos=[self.gm.global_to_scene_pos(target.transform.x, target.transform.y)],  # 使用目标自身的位置
                    speed=0.5
                )
            return False

        # 检查是否所有目标的动画均已完成
        is_all_finished = all(
            target.eff_animator_stick.finished
            for target in action.targets
        )

        if is_all_finished:
            # 停止所有目标的动画
            for target in action.targets:
                target.eff_animator_stick.stop()
            action.animation_complete = True
            return True

        return False

    def _process_change_action(self, action: Action):
        """
        切换动作, 不需要等待执行完成
        :param action:
        :return:
        """
        action.actor.animator.play(action.animation_name, speed=0.15, loop=action.animation_loop)
        return True

    def _process_attack_animation(self, action: Action):
        """播放攻击动画"""
        try:
            animator = action.actor.animator
            # 初始化动画播放
            if not animator.is_playing(action.animation_name):
                animator.play(action.animation_name, loop=False)
                return False  # 第一次播放先返回，避免后续逻辑立即执行
            if animator.finished:
                # 本轮事件结束
                action.animation_complete = True

            return animator.finished
        except ValueError as e:
            return True
        except Exception as e:
            return True

    def __dialog_callback(self, node):
        if node.get("__type") == "close":
            game_ui: GameUI = self.gm.get("游戏UI")
            game_ui.change_ui_layer("指令框_人物")
            return
        # self.change_state(BattleState.PLAYER_CHOOSE)

        skill_name = node.get("text")
        if skill_name is None:
            for el in node.get("children"):
                if el.get("tag") == "p" and el.get("text"):
                    skill_name = el.get("text")
        if skill_name is None:
            GameToastManager.add_message("无法释放技能,没有找到当前技能的信息")
            game_ui: GameUI = self.gm.get("游戏UI")
            game_ui.change_ui_layer("指令框_人物")
            return

        self.skill_data_queue["player"] = skill_name
        self.battle_sta: BattleState = BattleState.CMD_MAGIC

        self.gm.game_dialog.close_dialog()

    def destroy(self):
        """卸载战斗场景"""
        game_ui: "GameUI" = self.gm.get("游戏UI")
        game_ui.remove_surface_ui("指令框_人物")  # 移除ui引用
        GameEvent.remove(f"战斗场景点击事件_{self.UID}")
        self.gm.game_camera.mounted(self.player)  # 需要重新挂载相机
        # self.gm.remove(self)
        self.player.transform.set_pos(self.play_old_pos[0], self.play_old_pos[1])
        self.player.end_battle()
        # 这里仅销毁生成的敌人副本, 主体仅在战斗胜利之后才执行销毁
        for enemy in self.enemy_list:
            enemy.end_battle()
            enemy.destroy()

        self.enemy_list.clear()
        self.gm = None
        self.battle_bg = None
        self.__GUI_rect_list.clear()
        self.player = None


class BattleManager:
    """是否开始战斗"""
    _start_battle = False
    """战斗场景"""
    _battle_scene: _Battle = None
    """游戏管理对象"""
    _gm: "GameManager" = None

    @classmethod
    def Awake(cls, gm):
        cls._gm = gm

    @classmethod
    def battle_start(cls, player: SpriteBase, enemy_list: list[SpriteBase]):
        """
        开始战斗, 初始化战斗场景
        :param player:
        :param enemy_list:
        :return:
        """
        BattleManager._start_battle = True
        BattleManager._battle_scene = _Battle(BattleManager._gm)
        BattleManager._battle_scene.player = player
        BattleManager._battle_scene.enemy_list = enemy_list

        BattleManager._gm.add("战斗场景", BattleManager._battle_scene)
        BattleManager._start_battle = True

        BattleManager._battle_scene.exec_battle(player, enemy_list)

    @staticmethod
    def battle_end(retreat: bool = False):
        # 结束战斗场景
        # 把场景中这个死亡的敌人主体给移除掉
        if not retreat:
            [GameMapManager.remove_map_npc(nid) for nid in GameMapManager.CURR_BATTLE_NPC_UID]
        BattleManager._battle_scene.destroy()
        BattleManager._battle_scene = None
        BattleManager._gm.remove("战斗场景")
        BattleManager._start_battle = False

    @staticmethod
    def battle_sta():
        """是否处于战斗中"""
        return BattleManager._start_battle
