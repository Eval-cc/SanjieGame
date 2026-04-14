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
import webbrowser
import sys
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
from src.system.GameDialog import GameDialog
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

        # 获取本地保存的配置信息
        bgm_cfg = self.gm.game_local_db.fetch_on("SELECT * FROM 'main'.'system_settings' WHERE key = 'bgm'")
        if bgm_cfg:
            if bgm_cfg.get("value") == "1":
                GameMusicManager.play_bgm("login_bg")
        else:
            GameMusicManager.play_bgm("login_bg")

        GameMusicManager.set_sound_enabled(True)
        # 获取本地保存的配置信息
        scfg = self.gm.game_local_db.fetch_all("SELECT * FROM 'main'.'system_settings'")
        if scfg:
            for c in scfg:
                if c.get("key") == "sound_volume":
                    # 获取原始值
                    raw_volume = float(c.get("value"))
                    normalized_volume = raw_volume / 100.0
                    volume = max(0.0, min(normalized_volume, 1.0))
                    GameMusicManager.set_sound_volume(volume)
                    continue
                elif c.get("key") == "bgm_volume":
                    raw_volume = float(c.get("value"))
                    normalized_volume = raw_volume / 100.0
                    volume = max(0.0, min(normalized_volume, 1.0))
                    GameMusicManager.set_bgm_volume(volume)
                    continue
                elif c.get("key") == "sound":
                    GameMusicManager.set_sound_enabled(c.get("value") == "1")
                    continue
                elif c.get("key") == "bgm":
                    GameMusicManager.set_bgm_enabled(c.get("value") == "1")
                    continue

        GameMusicManager.play_bgm("login_bg")

        self.dialog_list: dict[str, "GameDialog"] = {}

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

    def _load_login_ui(self, **args):
        """
        加载UI 比如选区 和输入账号
        :return:
        """

        self.__components: List[Union["GameComponentBase"]] = []

        # 1. 提取公共参数（减少重复赋值）
        common_props = {
            "font_size": 10,
            "text_color": "#FFFFFF",
            "hover_color": "#2980b9",
            "press_color": "#1a5276",
            "bg_image": SourceManager.ui_system_path + "/gw_b1.png",
            "bg_press_image": SourceManager.ui_system_path + "/gw_b2.png"
        }

        # 2. 定义差异化配置 (文字, 垂直偏移量, 回调函数)
        btn_configs = [
            ("system_setting", "系统设置", self._show_setting_ui),
            ("game_website", "游戏官网", lambda: webbrowser.open("www.sjdlzfs.com")),
            ("game_exit", "退出游戏", lambda: (pygame.quit(), sys.exit())),  # 注意退出逻辑需根据实际框架调整
            ("game_create_acc", "创建账号", None)
        ]

        right_x = self.gm.game_win.get_rect().right - 90
        bottom_y = self.gm.game_win.get_rect().bottom
        _start_y = 150

        # 3. 循环批量创建
        for attr_name, text, callback in btn_configs:
            rect = pygame.Rect(right_x, bottom_y - _start_y, 60, 25)
            # 创建按钮对象
            button = GameButton(self.gm.game_win, rect, text, **common_props)
            # 存入组件列表
            if callback:
                button.set_on_click(callback)
            self.__components.append(button)
            _start_y -= 32

        # game_ui.set_surface_ui("登录账号UI", dialog_sur)

        def __entrance_game(acc_name, data):
            self.gm.game_dialog.close_dialog()
            for dl in self.dialog_list.values():
                dl.close_dialog()
                dl = None
            # 先把角色挂载上
            self.gm.add("主角", Player(acc_name, data))
            GameMapManager.change_map(data.get("scene_id"))
            # game_ui.remove_surface_ui("登录账号UI")
            self.gm.shop_system = ShopSystem(self.gm)
            self.gm.add("地图", RenderMap())

        # 设置点击回调
        def on_button_click():
            """
            点击登录
            :return:
            """
            dl = self.dialog_list.get("游戏登录UI")
            user_name = dl.get_val("account")
            password = dl.get_val("password")
            if len(user_name) == 0 or len(password) == 0:
                GameDialogBoxManager.dialog("账号密码不能为空")
                return
            login = LoginServer("http://169.254.249.130:8089/")

            # login = LoginServer()

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
                w_server = GameWorldServer(self.gm.get("主角"), self.gm, "http://169.254.249.130:8089/")
                ser_sta = w_server.connect_sync(GameMapManager.map_id)
                if not ser_sta:
                    raise Exception("服务器连接失败")
                # 追加事件
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
            login.login(user_name, password)

        def on_button_click_offline():
            """
            离线模式
            :return:
            """
            self._load_static_background()
            self.playing = False
            self.show_static_bg = True
            test_user = "eval"
            db = self.gm.game_local_db
            # 1. 检查或创建账号
            acc_res = db.fetch_all("SELECT id FROM accounts WHERE username = ?", (test_user,))
            if not acc_res:
                # 创建账号
                db.insert_row("accounts", {
                    "username": test_user,
                    "password": "123",  # 离线模式默认密码
                    "is_lock": 0
                })
                acc_res = db.fetch_all("SELECT id FROM accounts WHERE username = ?", (test_user,))

            acc_id = acc_res[0]['id']

            # 2. 更新最后登录时间
            db.update_row("accounts",
                          {"latest_time": time.strftime('%Y-%m-%d %H:%M:%S')},
                          "id = ?", (acc_id,))

            # 3. 查询该账号下的角色列表
            characters = db.fetch_all("SELECT * FROM fso WHERE account_id = ?", (acc_id,))

            if characters:
                # 如果有多个角色，这里可以弹出个简单的 UI 让玩家选
                # 这里演示直接取第一个角色
                player_data = characters[0]
            else:
                # 4. 如果没角色，创建初始角色
                player_data = {
                    "account_id": acc_id,
                    "avatar": "105进阶幽莹娃娃",
                    "name": "Eval",
                    "scene_id": "1042",
                    "sx": 995,
                    "sy": 1200,
                    "healthy": 500,
                    "mana": 100,
                    "attack": 10,
                    "defense": 10,
                    "attack_speed": 5,
                    "anim_model": "3",
                    "items": "1,0,0,1,1|1,0,3,2,3|1,1,3,3,3|1,2,3,4,3|1,3,3,2,3|1,3,3,3,3",
                }
                db.insert_row("fso", player_data)
                # 重新获取完整数据（包含自增ID等）
                player_data = db.fetch_all("SELECT * FROM fso WHERE account_id = ?", (acc_id,))[0]

            def run_async():
                # 清理所有组件
                self.cleanup(False)
                # 可以尝试用sqlite或者其他的什么技术进行离线数据的存储
                __entrance_game("eval", player_data)
                time.sleep(1)
                self.cleanup()

            threading.Thread(target=run_async, daemon=True).start()

        dl = GameDialog(self.gm, "游戏登录UI")
        dl.show_dialog(SourceManager.cfg_ui_path + "/game_login.html",
                       render_x=0,
                       render_y=0,
                       overwrite_path=True,
                       dialog_event_dict={
                           "login": on_button_click,
                           "unline": on_button_click_offline
                       },
                       loc="right_center"
                       )

        dl1 = GameDialog(self.gm, "健康游戏公告10086")
        dl1.show_dialog(SourceManager.cfg_ui_path + "/game_HGA.html",
                        render_x=0,
                        render_y=0,
                        overwrite_path=True,
                        loc="top_left")
        self.dialog_list.setdefault(dl.dialog_key, dl)
        self.dialog_list.setdefault(dl1.dialog_key, dl1)

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
        pygame_surface = pygame.surfarray.make_surface(np.transpose(frame_rgb, (1, 0, 2))).convert()
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
        # 1. 缩小 OpenCV 原始帧的大小（在转换为 Surface 前缩放效率更高）
        frame = cv2.resize(frame, (self.gm.game_win_rect.width, self.gm.game_win_rect.height))
        # 2. 转换颜色空间
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # 3. 交换维度并创建 Surface
        # 注意：使用 swapaxes 通常比 np.transpose 在某些版本上更快
        # return pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))

        surface = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
        return surface.convert()  # 这一步至关重要

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

    def render_mask(self):
        pass

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
            if _com.parent_id:
                _com.update_pos(rect.x, rect.y)

    def _show_setting_ui(self):
        if self.gm.game_dialog.visible():
            self.gm.game_dialog.close_dialog()
            return

        def on_music_volume_changed(value):
            GameMusicManager.set_bgm_volume(round(value / 100, 2))

        def on_change_music(e):
            GameMusicManager.bgm_enabled = e
            if e:
                if not GameMusicManager.resume_bgm():
                    GameMusicManager.play_bgm("login_bg")
            else:
                GameMusicManager.pause_bgm()

        self.gm.game_dialog.show_dialog(SourceManager.cfg_ui_path + "/game_setting.html",
                                        render_x=0,
                                        render_y=0,
                                        overwrite_path=True,
                                        dialog_event_dict={
                                            "confirm": self._set_confirm,
                                            "cancel": lambda: (GameToastManager.add_message(f"取消"),
                                                               self.gm.game_dialog.close_dialog()),
                                            "bgm_change": lambda val: on_music_volume_changed(val),
                                            "sound_change": lambda val: GameMusicManager.set_sound_volume(val),
                                            "bgm_change_cbk": lambda val: on_change_music(val),
                                            "sound_change_cbk": lambda val: GameMusicManager.set_sound_enabled(val),
                                        },
                                        load_val={
                                            "sound-volume": GameMusicManager.sound_volume * 100,
                                            "bgm-volume": GameMusicManager.bgm_volume * 100,
                                            "game-bgm": GameMusicManager.bgm_enabled,
                                            "game-sound": GameMusicManager.sound_enabled
                                        })

    def _set_confirm(self):
        bgm_enable = "1" if self.gm.game_dialog.get_val("game-bgm") else "0"
        sound_enable = "1" if self.gm.game_dialog.get_val("game-sound") else "0"
        sound_volume = round(self.gm.game_dialog.get_val("sound-volume"))
        bgm_volume = round(self.gm.game_dialog.get_val("bgm-volume"))

        # 构造需要更新的数据列表
        settings_to_update = [
            {"key": "bgm", "value": bgm_enable},
            {"key": "sound", "value": sound_enable},
            {"key": "sound_volume", "value": str(sound_volume)},
            {"key": "bgm_volume", "value": str(bgm_volume)}
        ]
        self.gm.game_local_db.update_batch("system_settings", settings_to_update, condition_key="key")
        self.gm.game_dialog.close_dialog()
