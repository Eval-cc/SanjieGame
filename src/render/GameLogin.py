# !/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : GameLogin.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/17 13:10
@Desc    : 游戏登录界面（快速显示Logo+异步视频加载优化版）
"""

import os.path
import threading
import time
from random import choice
from typing import TYPE_CHECKING, Any, List, Union
import pygame
import cv2
import numpy as np
from functools import partial

from src.character.Player import Player
from src.code.SpriteBase import SpriteBase
from src.components.GameButton import GameButton
from src.components.GameCheckBox import GameCheckBox
from src.components.GameComponentBase import GameComponentBase
from src.components.GameInput import GameInput
from src.components.GameSlider import GameSlider
from src.manager.GameFont import GameFont
from src.manager.GameMapManager import GameMapManager
from src.manager.SourceManager import SourceManager
from src.network.GameWorldServer import GameWorldServer
from src.network.LoginServer import LoginServer

from src.render.RenderMap import RenderMap
from src.system.GameMusic import GameMusicManager
from src.system.GameTipDialog import GameDialogBoxManager
from src.system.GameToast import GameToastManager
from src.system.ShopSystem import ShopSystem

if TYPE_CHECKING:
    from src.manager.GameManager import GameManager
    from src.render.GameUI import GameUI


class GameLogin(SpriteBase):
    def __init__(self, gm: Any):
        """
        初始化登录界面
        :param gm: self.gm实例
        """
        super().__init__()
        self.gm: "GameManager" = gm
        self.rect = pygame.Rect(self.gm.game_win_rect)

        GameMusicManager.play_bgm("login_bg")
        # ========== 第一阶段：立即加载静态背景 ==========
        self._load_static_background()
        self._load_login_ui()

        # ========== 第二阶段：初始化视频参数 ==========
        self._init_video_params()

        # ========== 第三阶段：启动异步加载 ==========
        self._start_async_loading()

    def _load_static_background(self):
        """立即加载静态背景图"""
        __rand_bg = [f"zfs_bg{i}.png" for i in range(1, 13)]  # 随机静态背景
        selected_bg = choice(__rand_bg)
        self.static_bg = SourceManager.load(
            os.path.join(SourceManager.ui_root_path, "Pictures", selected_bg),
            [self.gm.game_win_rect.width, self.gm.game_win_rect.height]
        )
        self.show_static_bg = True
        self.last_frame_time = pygame.time.get_ticks() / 1000.0
        self.accumulated_time = 0

    def _init_video_params(self):
        """初始化视频参数"""
        self.video_path = os.path.join(SourceManager.ui_root_path, "LoginCG", "login_video.mp4")
        self.cap = None
        self.video_ready = False
        self.original_fps = 30
        self.total_frames = 0
        self.current_frame_pos = 0

        # 播放控制参数
        self.playing = False
        self.loop = True
        self.playback_speed = 1.0  # 默认正常速度
        self.frame_duration = 0

        # 状态标志
        self.load_progress = 0
        self.current_frame = None  # 当前显示的帧

    def _start_async_loading(self):
        """启动后台加载线程"""
        self.loading_thread = threading.Thread(target=self._load_video_resource, daemon=True)
        self.loading_thread.start()

    def _load_video_resource(self):
        """加载视频资源"""
        try:
            self.video_ready = False
            self.cap = cv2.VideoCapture(self.video_path)

            if not self.cap.isOpened():
                raise IOError(f"无法打开CG文件: {self.video_path}")

            # 获取视频信息
            self.original_fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self._update_frame_duration()

            # print(f"视频加载成功: {self.total_frames}帧 @ {self.original_fps}fps")

            # 预加载第一帧
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = self._convert_frame(frame)
                self.current_frame_pos = 1
                self.load_progress = 1 / self.total_frames

            self.video_ready = True
            time.sleep(1)
            self.playing = True
            self.last_frame_time = pygame.time.get_ticks() / 1000.0

        except Exception as e:
            print(f"视频加载错误: {e}")
            self.video_ready = False
            self.playing = False

    def _load_login_ui(self):
        """
        加载UI 比如选区 和输入账号
        :return:
        """

        game_ui: "GameUI" = self.gm.get("游戏UI")
        _width = 200
        _height = 230
        dialog_title = SourceManager.surface_cale(
            SourceManager.load(f"{SourceManager.ui_system_path}/dialog_title.png"),
            [_width, 32]).convert_alpha()

        dialog_bg = pygame.Surface((_width, _height - 30), pygame.SRCALPHA)
        dialog_bg.fill(self.gm.game_font.hex_color_to_rgb("#000000"))
        dialog_bg.set_alpha(170)

        dialog_sur = pygame.Surface((_width, _height), pygame.SRCALPHA)
        dialog_sur.fill((0, 0, 0, 0))
        dialog_sur.blit(dialog_title, (2, 0))
        dialog_sur.blit(dialog_bg, (0, 30))
        pygame.draw.rect(dialog_sur, (self.gm.game_font.hex_color_to_rgb("#228B22")),
                         (0, 30, _width, _height - 30), 1)

        [_, login_ui_rect, _] = game_ui.load_system_ui(dialog_sur,
                                                       [_width, _height],
                                                       "top_right_center",
                                                       {
                                                           "name": "登录账号UI",
                                                           "drag": True,
                                                           "drag_rect": ["auto", "auto", "-25px", 30],
                                                           "move_callback": self.login_ui_move,
                                                           "mouse_move": lambda: True,
                                                           "show": True,
                                                           "bubble": True
                                                       }, sort=True)

        self.__components: List[Union["GameComponentBase"]] = []

        self.user_name = GameInput(self.gm.game_win, pygame.Rect([login_ui_rect.x, login_ui_rect.y, 170, 30]),
                                   placeholder="请输入账号", offset=(10, 50), bg_color="#000000", text_color="#FFFFFF",
                                   field="账号")
        self.user_pwd = GameInput(self.gm.game_win, pygame.Rect([login_ui_rect.x, login_ui_rect.y, 170, 30]),
                                  placeholder="请输入密码", is_password=True, offset=(10, 90), bg_color="#000000",
                                  text_color="#FFFFFF", field="密码")

        self.enter_game = GameButton(
            self.gm.game_win,  # 渲染表面
            pygame.Rect(login_ui_rect.x, login_ui_rect.y, 60, 25),  # 位置和大小
            "进入游戏",
            font_size=10,
            text_color="#FFFFFF",
            # bg_color="#3498db",
            border_color="#2980b9",
            hover_color="#2980b9",
            press_color="#1a5276",
            bg_image=SourceManager.ui_system_path + "/gw_b1.png",
            bg_press_image=SourceManager.ui_system_path + "/gw_b2.png",
            offset=(20, 140)
        )
        self.enter_game_offline = GameButton(
            self.gm.game_win,  # 渲染表面
            pygame.Rect(login_ui_rect.x, login_ui_rect.y, 60, 25),  # 位置和大小
            "离线模式",
            font_size=10,
            text_color="#FFFFFF",
            # bg_color="#3498db",
            border_color="#2980b9",
            hover_color="#2980b9",
            press_color="#1a5276",
            bg_image=SourceManager.ui_system_path + "/gw_b1.png",
            bg_press_image=SourceManager.ui_system_path + "/gw_b2.png",
            offset=(110, 140)
        )
        # 创建滑块实例
        self.music_slider = GameSlider(
            self.gm.game_win,  # 渲染表面
            pygame.Rect(login_ui_rect.x, login_ui_rect.y, 150, 30),  # 位置和大小
            # rect=pygame.Rect(100, 100, 200, 30),  # 滑块轨道的位置和大小 (x, y, width, height)
            min_value=0,  # 最小值
            max_value=100,  # 最大值
            initial_value=round(GameMusicManager.bgm_volume * 100),  # 初始值
            bg_color="#CCCCCC",  # 轨道背景颜色
            slider_color="#666666",  # 滑块颜色
            active_slider_color="#333333",  # 滑块激活时的颜色
            border_color="#000000",  # 边框颜色
            value_color="#FFFFFF",
            border_width=1,  # 边框宽度
            slider_width=20,  # 滑块宽度
            slider_height=30,  # 滑块高度
            show_value=True,  # 是否显示当前值
            value_format="{:.0f}%",  # 值显示格式
            offset=(0, login_ui_rect.height - 60)  # 位置偏移量
        )
        self.custom_toggle = GameCheckBox(
            self.gm.game_win,  # 渲染表面
            # rect=pygame.Rect(100, 200, 200, 30),
            pygame.Rect(login_ui_rect.x, login_ui_rect.y, 120, 30),  # 位置和大小
            text="是否播放音乐",
            is_checked=True,
            is_radio=True,
            font_size=12,
            text_color="#FF0000",  # 红色文本
            bg_color="#FFFFFF",  # 白色背景
            border_color="#00FF00",  # 绿色边框
            check_color="#0000FF",  # 蓝色选中标记
            hover_color="#FFFF00",  # 黄色悬停背景
            border_width=2,
            check_width=3,
            bg_image=SourceManager.load(fr"{SourceManager.ui_system_path}/checkbox.png").subsurface((0, 0, 28, 28)),
            bg_check_image=SourceManager.load(fr"{SourceManager.ui_system_path}/checkbox.png").subsurface(
                (56, 0, 28, 28)),
            offset=(0, login_ui_rect.height - 30)
        )
        self.__components.append(self.user_name)
        self.__components.append(self.user_pwd)
        self.__components.append(self.enter_game)
        self.__components.append(self.enter_game_offline)
        self.__components.append(self.music_slider)
        self.__components.append(self.custom_toggle)

        game_ui.set_surface_ui("登录账号UI", dialog_sur)

        def __entrance_game(acc_name, data):
            GameMapManager.change_map(data.get("scene_id"))
            game_ui.remove_surface_ui("登录账号UI")
            self.gm.shop_system = ShopSystem(self.gm)
            self.gm.add("地图", RenderMap())
            self.gm.add("主角", Player(acc_name, data))

        # 设置点击回调
        def on_button_click():
            """
            点击登录
            :return:
            """
            if len(self.user_name.text) == 0 or len(self.user_pwd.text) == 0:
                GameDialogBoxManager.dialog("账号密码不能为空")
                return
            login = LoginServer()

            def _on_login_success(data: dict):
                nonlocal login
                login = None  # 释放请求内存
                self._load_static_background()
                username = data.get("username")
                GameToastManager.add_message(f"登录成功: {username}")

                self.playing = False
                __entrance_game(data.get("username"), data.get("user"))

                # 实例化服务器连接
                # w_server = GameWorldServer(self.gm.get("主角"),self.gm,"http://llzfs.online:8089/")
                w_server = GameWorldServer(self.gm.get("主角"), self.gm)
                ser_sta = w_server.connect_sync(GameMapManager.map_id)
                if not ser_sta:
                    raise Exception("服务器连接失败")

                self.gm.add_manager("w_server", w_server)
                self.cleanup(False)
                time.sleep(1)
                self.cleanup()

            def _on_login_failed(error_msg: str):
                GameDialogBoxManager.dialog(error_msg)
                # GameToastManager.add_message(f"登录失败: {error_msg}")
                # 显示错误消息或允许用户重试

            login.on_login_success = _on_login_success
            login.on_login_failed = _on_login_failed
            login.login(self.user_name.text, self.user_pwd.text)

        self.enter_game.set_on_click(on_button_click)

        def on_button_click_offline():
            """
            离线模式
            :return:
            """
            self._load_static_background()
            self.playing = False
            self.show_static_bg = True

            def run_async():
                # 清理所有组件
                self.cleanup(False)
                __entrance_game("eval", {
                    "avatar": "105进阶幽莹娃娃",
                    "name": "Eval",
                    "scene_id": "1042",
                    "sx": 995,
                    "sy": 240,
                    "stand_texture": "NPC国子监祭酒",
                    "move_texture": "NPC国子监祭酒_move",
                    "stand_model": [8, 4],
                    "move_model": [8, 4],
                    "stand_direction": [1, 2, 3, 4],
                    "move_direction": [1, 2, 3, 4],
                    "max_healthy": 500,
                    "mana": 100,
                    "attack": 10,
                    "defense": 10,
                    "attack_speed": 5,
                    "anim_name": "进阶夜罗刹",
                    "npc_data": {
                        "战斗_攻击2": "13",
                        "战斗_击飞": "4",
                        "战斗_施法": "16",
                        "战斗_死亡": "12",
                        "战斗_挨打": "1",
                    },
                    "items": ["1"],
                })
                time.sleep(1)
                self.cleanup()

            threading.Thread(target=run_async, daemon=True).start()

        self.enter_game_offline.set_on_click(on_button_click_offline)

        # 设置值改变时的回调函数
        def on_music_volume_changed(value):
            GameMusicManager.set_bgm_volume(round(value / 100, 2))

        self.music_slider.set_on_value_changed(on_music_volume_changed)

        def on_change_music(e):
            if e:
                GameMusicManager.resume_bgm()
            else:
                GameMusicManager.pause_bgm()

        self.custom_toggle.set_on_toggle(on_change_music)

    def _update_frame_duration(self):
        """更新帧持续时间"""
        self.frame_duration = 1.0 / (self.original_fps * self.playback_speed)

    def _get_video_frame(self):
        """获取当前视频帧"""
        if not self.cap or not self.video_ready:
            return None

        ret, frame = self.cap.read()
        if not ret:
            if self.loop:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    return None
            else:
                return None

        self.current_frame_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self.load_progress = self.current_frame_pos / self.total_frames

        # 转换图像格式
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pygame_surface = pygame.surfarray.make_surface(np.transpose(frame_rgb, (1, 0, 2)))
        return pygame.transform.scale(
            pygame_surface,
            (self.gm.game_win_rect.width, self.gm.game_win_rect.height)
        )

    def update(self, delta_time: float):
        """
        更新动画状态
        :param delta_time: 距离上次更新的时间(秒)
        """
        if not self.playing or not self.video_ready:
            return

        # 累积时间
        self.accumulated_time += delta_time

        # 处理帧更新
        while self.accumulated_time >= self.frame_duration:
            self.accumulated_time -= self.frame_duration

            # 获取新帧
            ret, frame = self.cap.read()
            if not ret:
                if self.loop:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()
                    if not ret:
                        break
                else:
                    self.playing = False
                    break

            self.current_frame = self._convert_frame(frame)
            self.current_frame_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.load_progress = self.current_frame_pos / self.total_frames

    def _convert_frame(self, frame):
        """
        转换OpenCV帧为Pygame Surface
        :param frame:
        :return:
        """
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pygame_surface = pygame.surfarray.make_surface(np.transpose(frame_rgb, (1, 0, 2)))
        return pygame.transform.scale(
            pygame_surface,
            (self.gm.game_win_rect.width, self.gm.game_win_rect.height)
        )

    def render(self):
        """渲染当前帧"""
        current_time = pygame.time.get_ticks() / 1000.0
        delta_time = current_time - self.last_frame_time
        self.last_frame_time = current_time

        self.update(delta_time)

        if self.video_ready and self.playing and self.current_frame is not None:
            # 显示视频帧
            self.gm.game_win.blit(self.current_frame, (0, 0))
            self.show_static_bg = False

    def render_sticky(self):
        if not self.playing and self.static_bg is not None:
            self.gm.game_win.blit(self.static_bg, (0, 0))
        else:
            for _com in self.__components:
                _com.render()

    def _render_loading_status(self, delta_time: float):
        """渲染加载状态"""
        if not self.video_ready:
            # 模拟加载进度动画
            self.load_progress = (self.load_progress + delta_time * 0.5) % 1.0

            # 绘制进度条
            bar_width = int(self.gm.game_win_rect.width * 0.6)
            bar_height = 15
            bar_x = (self.gm.game_win_rect.width - bar_width) // 2
            bar_y = self.gm.game_win_rect.height - 120

            # 进度条背景
            pygame.draw.rect(self.gm.game_win, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height))
            # 进度条前景
            pygame.draw.rect(self.gm.game_win, (0, 200, 100),
                             (bar_x, bar_y, int(bar_width * self.load_progress), bar_height))

            # 加载文本
            text = GameFont.get_text_surface_line("加载中...", True, 16, "#FFFFFF")
            self.gm.game_win.blit(text, (bar_x, bar_y - 30))

    def handle_event(self, event):
        """处理用户输入事件"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.video_ready:
                print("点击登录界面")
                # 这里可以添加跳过动画的逻辑
                self.playing = False
            else:
                print("资源加载中，请稍候...")

    def set_playback_speed(self, speed: float):
        """设置播放速度 (0.5-2.0)"""
        if 0.5 <= speed <= 2.0:
            self.playback_speed = speed
            self._update_frame_duration()
            print(f"播放速度设置为: {speed}x")

    def skip_animation(self):
        """跳过动画"""
        self.playing = False
        self.show_static_bg = True

    def restart_animation(self):
        """重新播放动画"""
        if self.video_ready:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.playing = True
            self.show_static_bg = False

    def cleanup(self, clear_bg: bool = True):
        """清理资源"""
        if self.cap:
            self.cap.release()
            self.cap = None

        # 清理所有组件
        for component in self.__components:
            if hasattr(component, 'destroy'):
                component.destroy()
        self.__components.clear()

        if clear_bg:
            # 清理引用
            self.static_bg = None
            self.current_frame = None

            callback = partial(self.gm.remove, "登录页面")
            pygame.event.post(pygame.event.Event(
                pygame.USEREVENT,
                {"callback": callback}
            ))

    def login_ui_move(self, rect: pygame.Rect):
        """
        拖动UI之后 更新组件位置
        :param rect:
        :return:
        """
        for _com in self.__components:
            _com.update_pos(rect.x, rect.y)
