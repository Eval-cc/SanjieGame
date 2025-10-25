#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：SpriteBase.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/2/14 下午2:05 
@Describe: 所有的精灵基类
"""
import math
import random
import time
from pathlib import Path
from typing import Dict, TYPE_CHECKING
from uuid import uuid4

import pygame
from pygame.key import ScancodeWrapper

from src.code.Enums import SpriteState, SpriteLayer
from src.manager.GameLogManger import GameLogManager
from src.manager.SourceManager import SourceManager

if TYPE_CHECKING:
    from src.system.Animator import Animator


class SpriteBase:
    def __init__(self, event_name: list = None):
        self.UID = uuid4().hex[:8]  # 当前NPC的唯一id
        self.clsName = self.__class__.__name__
        # 坐标系
        self.position = [0, 0]
        # 每个精灵最原始的坐标
        self.origin_pos = [0, 0]
        self.width = 0
        self.height = 0
        self.image: pygame.Surface = None
        """精灵图"""
        self.rect: pygame.Rect = None
        """精灵尺寸"""
        self.mask: pygame.Mask = None
        self.rect_list = []
        """单个精灵的触发 多尺寸"""
        self.__rect_list_curr = -1
        """多区域触发的时候,保存触发的区域索引"""
        self.anim_index = 0
        """初始动画帧"""
        self.name = f'未定义的精灵_{random.randint(1, 99)}'
        self.active_click = True
        """是否激活点击事件"""
        self.mouse_tap = False
        """是否被点击"""
        self.mouse_pos = [0, 0]
        self.mask = None
        self.key_status = False
        """是否处于按下键盘状态"""
        self.is_dragging = False
        """是否正在推拽"""
        self.drag_first_pos = [0, 0]
        """保存推拽ui时候的坐标"""
        self.drag_offset_pos = [0, 0]
        self.layer: SpriteLayer = SpriteLayer.DEFAULT
        """精灵的图层"""
        self.layer_order: int = 1
        """精灵的渲染层级"""

        self.healthy: int = 10
        self.max_healthy: int = 10
        self.mana: int = 0
        self.attack: int = 0
        self.defense: int = 0
        self.attack_speed: int = 0
        self.level: int = 1  # 等级
        self.miss: int = 0  # 闪避
        self.strength: int = 1  # 力量
        self.intelligence: int = 1  # 智力
        self.constitution: int = 1  # 体质
        self.agile: int = 1  # 敏捷
        self.endurance: int = 1  # 耐力

        self.move_speed = 2  # 移动速度

        # 上一次点击的时间
        self.__last_click_time: float = 0
        self.__max_click_timer: float = 0.3

        # 默认精灵是 4方向的
        self.supported_directions = [1, 2, 3, 4]
        self.direction: int = 0  # 默认朝向

        self.buffs = []  # 当前身上的buff效果
        self.sprite_state = SpriteState.IDLE
        """精灵状态"""
        self.battle_state = False
        """是否处于战斗选中状态"""
        self.current_path: list = []
        self.current_path_index = 0
        self.animator: Animator = None
        """精灵的动画组件"""
        self.eff_animator_floor: Animator = None
        """特效动画组件_脚底特效"""
        self.eff_animator_stick: Animator = None
        """特效动画组件_头部特效"""
        self.battle_dict: dict = {}
        """存放战斗相关的配置"""
        self.raw_angle: int = 0  # 保存原始计算角度（0-360度）
        """原始计算角度"""

        self.stand_model: list = [0, 0]
        self.move_model: list = [0, 0]
        self.stand_direction: list = [1, 2, 3, 4]
        self.move_direction: list = [1, 2, 3, 4]
        self.stand_texture: str = ""
        self.move_texture: str = ""
        # 单帧宽度
        self.frame_width: int = 0
        self.frame_timer: int = 0
        self.frame_delay: int = 2  # 每 2 帧更新一次

        # 4方向映射（配置编号 → 角度）
        self.direction_map_4 = {
            1: 45,  # 右下 ↘
            2: 135,  # 左下 ↙
            3: 225,  # 左上 ↖
            4: 315,  # 右上 ↗
        }

        # 8方向映射（配置编号 → 角度）
        self.direction_map_8 = {
            1: 90,  # 下 ↓
            2: 180,  # 左 ←
            3: 0,  # 右 →
            4: 270,  # 上 ↑
            5: 135,  # 左下 ↙
            6: 45,  # 右下 ↘
            7: 225,  # 左上 ↖
            8: 315,  # 右上 ↗
        }

        self.__register = []
        """ 获取到自动注册的事件列表 """

        # 如果传递了事件, 那么就自动注册事件
        if event_name is not None:
            from src.manager.GameEvent import GameEvent
            """是否需要自动注册键鼠事件"""
            # 保存自动注册的事件名称
            self.__register = [f"{event_name}_{self.UID}" for event_name in event_name[0]]
            GameEvent.add([f"{event_name}_{self.UID}" for event_name in event_name[0]], event_name[1], self)

    def get_register(self):
        """返回当前自动注册的事件列表"""
        return self.__register

    def get_status(self):
        """返回当前精灵的属性"""
        return {
            "name": self.name,
            "healthy": self.healthy,
            "mana": self.mana,
            "attack": self.attack,
            "defense": self.defense,
            "attack_speed": self.attack_speed,
            "level": self.level,
            "miss": self.miss,
            "strength": self.strength,
            "intelligence": self.intelligence,
            "constitution": self.constitution,
            "agile": self.agile,
            "endurance": self.endurance,
        }

    def render_floor(self):
        """背景层"""
        pass

    def render(self):
        """逻辑层"""
        pass

    def render_mask(self):
        """遮罩层"""
        pass

    def render_sticky(self):
        """置顶层"""
        pass

    def has_clicked_condition(self, target=None):
        """判断是否被点击的额外拓展,默认返回当前的 active_click 类属性状态, 需要拓展判定的由子类自行实现,, 适用于单精灵的多区域判断"""
        return self.active_click

    def is_clicked(self, mouse_x: int, mouse_y: int):
        """精灵是否被点击, 不需要子类实现"""
        try:
            if not self.active_click:
                return False

            if len(self.rect_list) > 0:
                for e_index in range(len(self.rect_list)):
                    rect_e = self.rect_list[e_index]
                    rect: pygame.Rect = rect_e.get("rect")
                    mask: pygame.Mask = rect_e.get("mask")
                    # 有mask就优先使用mask检测
                    if mask is not None:
                        mask_rect = mask.get_rect()
                        if rect is not None:
                            mask_rect.x = rect.x
                            mask_rect.y = rect.y
                        # 检查坐标是否在 mask 范围内
                        if (mask_rect.collidepoint(mouse_x, mouse_y) and
                                mask.get_at((mouse_x - mask_rect.x, mouse_y - mask_rect.y))
                                and self.has_clicked_condition(rect_e)):
                            # if rect_e.get("mouse_down") is None:
                            #     GameLogManager.log_service_debug(f"已命中[{rect_e.get('name')}], 但是没有对应的mouse_down实现")
                            self.__rect_list_curr = e_index
                            self.is_dragging = True
                            return True

                    if rect is not None and rect.collidepoint(mouse_x, mouse_y) and rect_e.get("mouse_down") is not None \
                            and self.has_clicked_condition(rect_e):
                        self.__rect_list_curr = e_index
                        self.is_dragging = True
                        return True
                return False
            if self.mask is not None:
                mask_rect = self.mask.get_rect()
                if self.rect is not None:
                    mask_rect.x = self.rect.x
                    mask_rect.y = self.rect.y
                # 检查坐标是否在 mask 范围内
                if mask_rect.collidepoint(mouse_x, mouse_y) and self.has_clicked_condition(mask_rect):
                    # 1. 获取鼠标坐标（全局）
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    # 2. 计算鼠标在 mask 中的局部坐标
                    local_x = mouse_x - mask_rect.x
                    local_y = mouse_y - mask_rect.y
                    # 3. 检查坐标是否在 mask 范围内
                    if 0 <= local_x < mask_rect.width and 0 <= local_y < mask_rect.height:
                        # 4. 获取该像素的 alpha 值
                        alpha = self.mask.get_at((local_x, local_y))
                        # 5. 如果 alpha > 0，说明点击了有效像素
                        if alpha > 0:
                            self.is_dragging = True
                            return True
            # 检测矩形
            if self.rect and self.rect.collidepoint(mouse_x, mouse_y) and self.has_clicked_condition():
                self.is_dragging = True
                return True
            return False
        except AttributeError as e:
            GameLogManager.log_service_error(f"无法触发点击事件,当前实现的子类并未初始化rect属性,错误:{e}")
            return False
        except Exception as e:
            GameLogManager.log_service_error(f"监听点击事件出错=>>{e}")
            return False

    def listen_keyboard(self):
        return True

    def get_click_sprite_index(self):
        """获取多区域点击的索引元素"""
        return self.__rect_list_curr

    def mouse_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """鼠标按下事件
        @:return 返回 False 就结束,  如果返回True就说明允许向下穿透
        """
        self.mouse_tap = True
        self.mouse_pos = event["mouse_pos"]
        if self.__last_click_time == 0:
            self.__last_click_time = time.time()
        else:
            if time.time() - self.__last_click_time < self.__max_click_timer:
                self.__last_click_time = 0
                self.mouse_double_click(event)
                return False
            else:
                self.__last_click_time = time.time()
        return False

    def mouse_double_click(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """鼠标双击事件
        @:return 返回 False 就结束,  如果返回True就说明允许向下穿透
        """
        self.mouse_tap = True
        self.mouse_pos = event["mouse_pos"]
        return False

    def mouse_up(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """鼠标抬起事件
        @:return 返回 False 就结束,  如果返回True就说明允许向下穿透
        """
        self.mouse_tap = False
        self.is_dragging = False
        return True

    def mouse_move(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """鼠标移动事件
        @:return 返回 False 就结束,  如果返回True就说明允许向下穿透
        """
        return True

    def mouse_enter(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """鼠标进入事件
        @:return 返回 False 就结束,  如果返回True就说明允许向下穿透
        """
        return True

    def mouse_out(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """鼠标离开事件"""
        return True

    def mouse_scroll_wheel_up(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """滚轮向上事件
        @:return 返回 False 就结束,  如果返回True就说明允许向下穿透
        """
        return True

    def mouse_scroll_wheel_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """滚轮向下事件
        @:return 返回 False 就结束,  如果返回True就说明允许向下穿透
        """
        return True

    def key_down(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """键盘按下事件"""
        self.key_status = True

    def key_up(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """键盘抬起事件"""
        self.key_status = False

    def keyboard_pressed(self, event: Dict[str, ScancodeWrapper] | pygame.event.EventType):
        """触发键盘长按事件"""
        pass

    def key_text(self, event: Dict[str, pygame.event.EventType] | pygame.event.EventType):
        """
        接收输入的中文候选字事件
        :param event:
        :return: {
            dict:{
                text:"xxxx",
                window:None
            },
            text:"xxx",
            type:"771",
            window:None
        }
        """
        pass

    def get_size(self):
        """获取精灵的宽高"""
        if self.rect is None:
            return [0, 0]
        return [self.rect.width, self.rect.height]

    def get_pos_world(self):
        """返回当前角色的真实世界坐标
        rect(x,y,w,h)
        """
        if self.rect is None:
            return [self.position[0], self.position[1], 0, 0]
        return [self.position[0], self.position[1], self.rect.width, self.rect.height]

    def is_dead(self):
        """ 是否死亡状态? """
        return self.sprite_state == SpriteState.DEAD

    def take_damage(self, base_damage: float) -> float:
        """
        接收伤害处理逻辑（支持暴击、浮动伤害）

        Args:
            base_damage: 基础伤害值（未计算防御、暴击等）

        Returns:
            实际造成的伤害值
        """
        # 1. 计算是否暴击（默认暴击率15%，暴击伤害150%）
        is_critical = random.random() < 0.15  # 15% 暴击概率
        critical_multiplier = 1.5 if is_critical else 1.0

        # 2. 伤害浮动（±10%随机波动）
        damage_fluctuation = random.uniform(0.9, 1.1)

        # 3. 最终伤害计算（至少造成1点伤害）
        final_damage = max(math.ceil(1 * critical_multiplier), int(
            (base_damage - self.defense) * critical_multiplier * damage_fluctuation
        ))

        # 4. 应用伤害
        self.healthy -= final_damage

        # 5. 战斗日志（显示暴击和浮动效果）
        log_msg = (
            f"{self.name} 受到 {final_damage} 点伤害"
            f"{'（暴击！）' if is_critical else ''}"
            f"，剩余HP: {self.healthy}"
        )
        GameLogManager.log_service_debug(log_msg)

        # 6. 死亡判定
        if self.healthy <= 0:
            self.healthy = 0
            self.sprite_state = SpriteState.DEAD
            self.on_death()

        return final_damage

    def on_death(self):
        """角色死亡时的处理逻辑，可由子类复写"""
        pass

    def apply_buff(self, buff):
        """
        添加buff效果（如中毒、封印、加攻击）
        """
        self.buffs.append(buff)
        print(f"{self.name} 获得效果：{buff.name}")

    def update_buffs(self):
        """
        更新所有buff效果，每个回合调用一次
        """
        for buff in self.buffs[:]:
            buff.on_turn(self)
            if buff.duration <= 0:
                self.buffs.remove(buff)
                print(f"{self.name} 的效果 {buff.name} 消失了")

    def update_direction(self, dx: float, dy: float):
        """根据偏移量更新朝向（支持4方向和8方向，按配置编号匹配）"""
        if dx == 0 and dy == 0:
            return

        angle = math.degrees(math.atan2(dy, dx))
        self.raw_angle = angle
        if angle < 0:
            angle += 360

        # 选择当前方向表
        if len(self.supported_directions) == 4:
            direction_map = self.direction_map_4
        else:
            direction_map = self.direction_map_8

        # 找到与角度最接近的方向编号
        min_diff = 360
        best_dir = self.direction
        for dir_id in self.supported_directions:
            dir_angle = direction_map.get(dir_id)
            if dir_angle is None:
                continue
            diff = abs((angle - dir_angle + 360) % 360)
            if diff > 180:
                diff = 360 - diff
            if diff < min_diff:
                min_diff = diff
                best_dir = dir_id

        self.direction = best_dir - 1

    def stop_moving(self):
        """停止移动"""
        self.current_path = []
        self.current_path_index = 0
        self.animator.play(f"stand_{self.direction}")
        self.sprite_state = SpriteState.IDLE

    def load_battle_anim(self, target: str, ani_name: str, npc_data: dict):
        """加载精灵的战斗动画序列"""
        if target != "enemy" and target != "actor":
            GameLogManager.log_service_debug(f"非法阵营:{target}")
            return
        # 定义战斗动作类型列表
        battle_actions = [
            (f"战斗_攻击1", f"attack1"),
            (f"战斗_攻击2", f"attack2"),
            (f"战斗_击飞", "fly"),
            (f"战斗_施法", f"magic"),
            (f"战斗_死亡", f"die"),
            (f"战斗_上移", f"up"),
            (f"战斗_下移", f"down"),
            (f"战斗_挨打", f"hit")
        ]
        # 批量初始化战斗动作索引和动画
        for action, action_key in battle_actions:
            index = int(npc_data.get(action, "0") or "0")
            # 加载对应动画资源
            if index >= 0:
                # 确定动画类型对应的文件夹名称
                folder_name = {
                    # "idle": "待机",
                    f"attack1": f"攻击/{target}",
                    f"attack2": f"攻击二/{target}",
                    f"fly": "击飞",
                    f"magic": f"施法/{target}",
                    f"die": f"死亡/{target}",
                    f"up": "移动",
                    f"down": "返回",
                    f"hit": f"挨打/{target}",
                }.get(action_key, action_key)

                # 构建基础路径
                base_path = Path(f"{SourceManager.ui_battle_path}/{ani_name}/{folder_name}/")

                # 检查基础目录是否存在
                if not base_path.exists():
                    GameLogManager.log_service_debug(f"警告：动画目录不存在: {base_path}")
                    continue

                # 收集有效的动画帧
                valid_frames = []
                missing_frames = []

                for i in range(index + 1):
                    frame_path = base_path / f"{str(i).zfill(2)}.png"
                    if frame_path.exists():
                        try:
                            first_frame = SourceManager.load(str(frame_path))
                            rect = first_frame.get_bounding_rect()
                            first_frame = first_frame.subsurface(rect)
                            # 尝试加载图片资源
                            valid_frames.append(first_frame)
                        except Exception as e:
                            GameLogManager.log_service_debug(f"警告：加载动画帧失败 {frame_path}: {str(e)}")
                            missing_frames.append(str(frame_path))
                    else:
                        missing_frames.append(str(frame_path))

                # 如果有缺失的帧，打印警告
                if missing_frames:
                    GameLogManager.log_service_debug(
                        f"警告：动画 {action} 缺失 {len(missing_frames)} 帧: {', '.join(missing_frames)}")

                # 如果有有效的帧，添加动画
                if valid_frames:
                    self.animator.add_animation(
                        action,
                        len(valid_frames),  # 使用实际有效的帧数
                        3,  # 默认帧率设为3，可根据需要调整
                        valid_frames
                    )
                    GameLogManager.log_service_debug(
                        f"[{self.name}] 添加战斗动画 {action} 完成! 共[{len(valid_frames)}]帧")
                else:
                    GameLogManager.log_service_debug(f"错误：动画 {action} 没有可用的帧，跳过添加")

            # GameLogManager.log_service_debug(f"[{self.name}] 添加战斗动画 {action} 结束")

    def destroy(self):
        """由每个子精灵自己实现的销毁方法"""
        from src.manager.GameEvent import GameEvent
        for event_name in self.__register:
            GameEvent.remove(event_name)

    def start_battle(self):
        """开始触发战斗"""
        pass

    def end_battle(self):
        """结束战斗"""
        pass

    def set_direction(self, angle: int):
        """根据角度设置方向"""
        pass

    def __str__(self):
        return "[class SpriteBase]"
