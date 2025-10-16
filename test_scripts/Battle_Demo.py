#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : Battle_depre.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/8/7
@Desc    : 修复卡死问题的战斗系统
"""
import random

import pygame
import sys

# 初始化pygame
pygame.init()
WIDTH = 1000
HEIGHT = 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("三界奇谈 - 战斗系统(测试)")
clock = pygame.time.Clock()

scene_bg = pygame.image.load(
    r"E:\Project Code\Python Code\a_pygame\三界奇谈\Graphics\Parallaxes\1234.jpg").convert_alpha()
battle_bg = pygame.image.load(
    r"E:\Project Code\Python Code\a_pygame\三界奇谈\Graphics\System\battle_background.png").convert_alpha()
battle_bg.set_alpha(150)
battle_bg = pygame.transform.smoothscale(battle_bg, (WIDTH, HEIGHT))

battle_size = 50

pygame.font.init()

font = pygame.font.Font(
    r"E:\Project Code\Python Code\a_pygame\三界奇谈\resources\fonts\AaBanRuoKaiShuJiaCu（JianFan）-2.ttf", 16)

cmd_bg = pygame.image.load(
    r"E:\Project Code\Python Code\a_pygame\三界奇谈\Graphics\System\battle\指令框.png").convert_alpha()
cmd_bg_rect = cmd_bg.get_rect()
cmd_bg_rect.x = WIDTH - cmd_bg_rect.width
cmd_bg_rect.y = HEIGHT - cmd_bg_rect.height * 2
battle_box = [[760, 565], [370, 220], [180, 220]]

cmd_btns = ["法术", "道具", "逃跑", "捕捉"]

effect_1 = pygame.image.load(
    r"E:\Project Code\Python Code\a_pygame\三界奇谈\Graphics\Animations\状态-如花解语.png").convert_alpha()
# 特效
hit_effect_1 = [
    effect_1.subsurface(pygame.Rect(column * 960 // 5, row * 768 // 4, 960 // 5, 768 // 4))
    for column in range(5)
    for row in range(4)
]

effect_2 = pygame.image.load(
    r"E:\Project Code\Python Code\a_pygame\三界奇谈\Graphics\Animations\五庄-生命之泉.png").convert_alpha()
# 特效
hit_effect_2 = [
    effect_2.subsurface(pygame.Rect(column * 960 // 5, row * 768 // 4, 960 // 5, 768 // 4))
    for column in range(5)
    for row in range(4)
]
hit_effect_2.pop() # 弹出最后一个

effect_3 = pygame.image.load(
    r"E:\Project Code\Python Code\a_pygame\三界奇谈\Graphics\Animations\新琴女.png").convert_alpha()
# 特效
hit_effect_3 = [
    effect_3.subsurface(pygame.Rect(column * 1152 // 6, row * 384 // 2, 1152 // 6, 384 // 2))
    for column in range(6)
    for row in range(2)
]

class AnimationPlayer:
    def __init__(self, frames, speed=50):
        self.frames = frames
        self.speed = speed
        self.current_frame = 0
        self.last_update = 0
        self.is_playing = False
        self.target_pos = None

    def start_animation(self, pos):
        """开始播放一次动画"""
        if not self.is_playing:
            self.target_pos = pos
            self.current_frame = 0
            self.last_update = pygame.time.get_ticks()
            self.is_playing = True

    def update(self):
        """更新动画状态，返回是否完成"""
        if not self.is_playing:
            return False

        # 播放当前帧
        screen.blit(self.frames[self.current_frame], self.target_pos)

        # 检查是否需要更新帧
        now = pygame.time.get_ticks()
        if now - self.last_update > self.speed:
            self.last_update = now
            self.current_frame += 1
            if self.current_frame >= len(self.frames):
                self.is_playing = False
                return True  # 动画完成

        return False  # 动画未完成


# 初始化
hit_animation_player = AnimationPlayer(hit_effect_1, speed=50)
hit_animation_player_skill = AnimationPlayer(hit_effect_2, speed=50)
hit_animation_player_skill_1 = AnimationPlayer(hit_effect_3, speed=50)
#


# 扣减的方法组
diminish_fun = []

# 存放敌人的回合
enemy_fun = []

# 战斗情况, 0. 选择目标  , 1. 玩家攻击  , 2 怪物攻击 , 3. 战斗结束 | 0 选择目标
battle_sta = 0


class Character:
    def __init__(self, name, hp, mp, attack, defense, speed, pos, texture, has_btn: bool = False, frame: int = 0):
        self.name = name
        self.hp = hp
        self.hp_max = hp
        self.mp = mp
        self.attack = attack
        self.defense = defense
        self.speed = speed
        self.texture = texture
        self.image = pygame.image.load(texture).convert_alpha()
        self.has_btn = has_btn

        self.take_hit = 0

        self.frame_index = -1

        self.wait = 15

        self.is_hover = False

        self.is_battle_over = False
        self.is_attacking = False  # 是否正在攻击（新增）
        self.attack_finished = False  # 攻击是否完成（新增）
        # 受击伤害文字
        self.hit_tip_text = []
        self.tip_text_time = 2

        self.attack_type = "attack"  # skill

        if not has_btn:
            self.pos_index = pos
            self.pos = battle_box[pos]
            self.pos_raw = self.pos
            self.rect = self.image.get_rect(center=self.pos)
            self.name_sur = font.render(self.name, True, (200, 200, 200))

            self.start_battle = False
            self.target = []
            self.original_pos = self.pos.copy()  # 保存原始位置
            self.moving_to_target = False  # 是否正在向目标移动
            self.moving_back = False  # 是否正在返回原位置
            self.run_battle = False # 是否正在战斗
        else:
            self.frame = frame
            self.frame_index = 0
            self.rect = self.image.get_rect()
            self.rect.x = pos[0]
            self.rect.y = pos[1]

    def render(self):
        global  battle_sta
        if not self.has_btn:
            if self.hp - self.take_hit <= 0:
                return
            # 渲染血条
            pygame.draw.rect(screen, (200, 50, 50) if self.is_hover else (200,200,200), (self.rect.x, self.rect.y, battle_size, battle_size), 1)
            screen.blit(self.image, self.rect)
            screen.blit(self.name_sur, (self.pos[0], self.pos[1] - self.image.height // 2))

            if self.start_battle:
                if self.moving_to_target:
                    if self.attack_type == "attack":
                        hit_animation_player.update()
                        if self.move(self.target, self.speed):
                            hit_animation_player.start_animation(self.target)
                            for f in diminish_fun:
                                f()
                            self.moving_to_target = False
                    elif self.attack_type == "skill":
                        skill_sta = hit_animation_player_skill.update()
                        if skill_sta:
                            for f in diminish_fun:
                                f()
                            self.moving_to_target = False
                        else:
                            hit_animation_player_skill.start_animation(self.target)
                    elif self.attack_type == "skill_2":
                        skill_sta = hit_animation_player_skill_1.update()
                        if skill_sta:
                            for f in diminish_fun:
                                f()
                            self.moving_to_target = False
                        else:
                            hit_animation_player_skill_1.start_animation(self.target)


                elif not self.moving_back:
                    self.moving_back = True


                elif self.moving_back:
                    if self.move(self.original_pos, self.speed):
                        self.die()
                        diminish_fun.clear()
                        if battle_sta == 1:
                            battle_sta = 2


            # # 在游戏循环中
            hit_animation_player.update()

            pygame.draw.rect(screen, (255, 0, 0),
                             (self.pos[0] - self.image.width // 2, self.pos[1] - self.image.height // 2,
                              100 * (self.hp / self.hp_max), 5))
            pygame.draw.rect(screen, (0, 255, 0),
                             (self.pos[0] - self.image.width // 2, self.pos[1] - self.image.height // 2,
                              100, 5), 1)
            if self.take_hit > 0:
                self.hp -= 1
                self.take_hit -= 1
                self.hit_tip_text.insert(0, font.render(str(self.take_hit), True, (255, 200, 200)))

            if len(self.hit_tip_text) > 0:
                self.tip_text_time -= 1
                if self.tip_text_time <= 0:
                    self.hit_tip_text.pop(0)
                    self.tip_text_time = 3

        else:
            screen.blit(self.image, self.rect,
                        (self.rect.width // self.frame * self.frame_index, 0, self.rect.width // self.frame,
                         self.rect.height))

        if len(self.hit_tip_text) > 0:
            for ti,t in enumerate(self.hit_tip_text):
                screen.blit(t,(self.pos[0] - self.image.width // 2, self.pos[1] - self.image.height // 2 - ti * 5))

    def die(self):
        self.moving_back = False
        self.start_battle = False
        self.target = []
        self.attack_finished = True  # 关键：标记攻击完成

    def distance(self, target_pos: list[int]) -> float:
        """计算当前位置与目标位置的直线距离"""
        dx = target_pos[0] - self.pos[0]
        dy = target_pos[1] - self.pos[1]
        return (dx ** 2 + dy ** 2) ** 0.5

    def move(self, target_pos: list[int], speed: int = 5) -> bool:
        """
        平滑移动到目标位置
        :param target_pos: 目标坐标 [x, y]
        :param speed: 移动速度(像素/帧)
        :return: 是否到达目标位置
        """
        # 计算方向向量
        dx = target_pos[0] - self.pos[0]
        dy = target_pos[1] - self.pos[1]
        distance = self.distance(target_pos)  # (dx ** 2 + dy ** 2) ** 0.5

        # 如果已经到达目标位置
        if distance < speed:
            self.pos = list(target_pos)
            self.rect.center = self.pos
            return True

        # 标准化方向向量并计算移动步长
        dx /= distance
        dy /= distance

        # 更新位置
        self.pos[0] += dx * speed
        self.pos[1] += dy * speed

        self.rect.center = self.pos

        return False

    def tap(self, pos):
        if self.has_btn:
            frame_w = self.image.width // self.frame
            hit = self.rect.x <= pos[0] <= self.rect.x + frame_w and self.rect.y <= pos[
                1] <= self.rect.y + self.rect.height
            if hit and self.frame_index != -1:
                self.frame_index = 2
            return hit

        return self.rect.x <= pos[0] <= self.rect.x + battle_size and self.rect.y <= pos[
            1] <= self.rect.y + battle_size

    def hover(self, pos):
        self.is_hover = False
        if pos is None:
            self.frame_index = 0
            return False
        if self.frame_index == 1 and self.tap(pos):
            self.is_hover = True
            return True
        if self.frame_index == 0 and self.tap(pos):
            self.is_hover = True
            self.frame_index = 1
            return True
        self.frame_index = 0
        return False


    def hit(self, target: 'Character', atk_type="attack"):
        """攻击"""
        self.target = pygame.Rect(target.rect.x,target.rect.y,battle_size,battle_size).midtop
        self.moving_to_target = True
        self.start_battle = True
        self.is_attacking = True  # 标记当前正在攻击
        self.attack_finished = False  # 重置攻击完成状态
        self.attack_type = atk_type
        diminish_fun.append(lambda: target.takedamage(self.attack if atk_type == "attack" else self.attack * 1.5))

    def takedamage(self, attk):
        self.take_hit = attk


player = [
    Character("剑侠客", 200, 100, 30, 15, 10, 0,
              r"E:\Project Code\Python Code\a_pygame\三界奇谈\Graphics\Battlers\二郎神\待机\actor\00.png")
]

# # 创建敌人（使用随机位置）
enemies = [
    Character("强盗", 80, 0, 15, 8, 12, 1,
              r"E:\Project Code\Python Code\a_pygame\三界奇谈\Graphics\Battlers\凤凰\待机\enemy\00.png"),
    Character("山贼", 120, 0, 20, 12, 10, 2,
              r"E:\Project Code\Python Code\a_pygame\三界奇谈\Graphics\Battlers\地狱战神\待机\enemy\00.png"),
]

cmd_btn_sur = [Character(sur, 0, 0, 0, 0, 0, (cmd_bg_rect.x + 3, 2 + cmd_bg_rect.y + sindex * 30),
                         rf"E:\Project Code\Python Code\a_pygame\三界奇谈\Graphics\System\battle\{sur}.png", True, 3)
               for
               sindex, sur in enumerate(cmd_btns)]



def event_fun():
    global  battle_sta
    pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if battle_sta == 0:
                for en in enemies:
                    if en.tap(pos):
                        battle_sta = 1
                        print(f"点击了敌人:{en.name}")
                        for play in player:
                            play.hit(en,"attack")

                            # 修改 event_fun() 中的敌人攻击函数创建方式
                            for ei in enemies:
                                enemy_fun.append({
                                    "en": ei,
                                    "cbk": lambda eei=ei, p=play: eei.hit(p, "attack" if random.random() < 0.2 else "skill")  # 显式绑定参数
                                })
                        return

                for btn in cmd_btn_sur:
                    if btn.tap(pos):
                        print(f"点击按钮:{btn.name}")
                        if btn.name == "法术":
                            battle_sta = 1
                            for play in player:
                                en = enemies[random.randint(0,len(enemies)-1)]
                                play.hit(en, "skill_2")

                                # 修改 event_fun() 中的敌人攻击函数创建方式
                                for ei in enemies:
                                    enemy_fun.append({
                                        "en": ei,
                                        "cbk": lambda eei=ei, p=play: eei.hit(p, "attack" if random.random() < 0.2 else "skill")
                                        # 显式绑定参数
                                    })
                        return

        elif event.type == pygame.MOUSEBUTTONUP:
            for btn in cmd_btn_sur:
                btn.hover(None)

        elif event.type == pygame.MOUSEMOTION:
            for btn in cmd_btn_sur:
                if btn.hover(pos):
                    # print(f"悬浮按钮:{btn.name}")
                    return


def draw():
    screen.blit(scene_bg, (0, 0))
    screen.blit(battle_bg, (0, 0))

    screen.blit(cmd_bg, cmd_bg_rect)
    pygame.draw.rect(screen, (255, 0, 255), cmd_bg_rect, 1)

    for enemy in enemies:
        enemy.render()

    for user in player:
        user.render()

    for btn in cmd_btn_sur:
        btn.render()

    pygame.display.update()


def battle_main():
    global battle_sta

    if battle_sta == 1:
        pass  # 玩家攻击阶段（已在 Character.render() 处理）
    elif battle_sta == 2:
        if len(enemy_fun) > 0:
            current_enemy_data = enemy_fun[0]
            current_enemy:Character = current_enemy_data["en"]
            callback = current_enemy_data["cbk"]

            if not current_enemy.is_attacking and not current_enemy.attack_finished:
                if current_enemy.hp - current_enemy.take_hit <= 0:
                    current_enemy.die()
                    enemy_fun.pop(0)  # 移除已死亡的敌人
                    enemies.remove(current_enemy) # 从总的列表移除
                    return
                callback()  # 执行攻击
                current_enemy.is_attacking = True
                print(f'{current_enemy.name}开始攻击')
            elif current_enemy.attack_finished:
                enemy_fun.pop(0)  # 移除当前敌人
                current_enemy.is_attacking = False
                current_enemy.attack_finished = False
                print(f'{current_enemy.name}攻击完成')

                # 如果还有敌人，立即开始下一个敌人的攻击
                if len(enemy_fun) > 0:
                    next_enemy = enemy_fun[0]["en"]
                    if not next_enemy.is_attacking:
                        battle_main()  # 递归调用处理下一个敌人
            # else:
            #     print(f"{current_enemy.name} 状态")
        else:
            battle_sta = 0  # 所有敌人攻击完毕
            print("所有敌人攻击完成")

def main():
    while True:
        clock.tick(60)
        event_fun()
        draw()
        battle_main()


if __name__ == "__main__":
    main()
