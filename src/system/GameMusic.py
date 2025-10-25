#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : GameMusic.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/25 13:08
@Desc    : 游戏音效
"""
import os
import pygame
from typing import Dict, Optional

from src.manager.SourceManager import SourceManager


class GameMusicManager:
    # 类变量存储资源路径和配置
    _bgm_paths: Dict[str, str] = {}  # 背景音乐路径字典
    _sound_paths: Dict[str, str] = {}  # 音效路径字典

    # 音量控制 (0.0 ~ 1.0)
    bgm_volume: float = 0.2
    sound_volume: float = 0.3

    # 开关控制
    bgm_enabled: bool = True
    sound_enabled: bool = True

    # 当前播放的BGM
    _current_bgm: Optional[pygame.mixer.Sound] = None
    _current_bgm_name: Optional[str] = None

    @classmethod
    def Awake(cls):
        """初始化音频系统"""
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        cls._bgm_channel = pygame.mixer.Channel(0)  # 专用BGM通道
        cls._sound_channel = pygame.mixer.Channel(1)  # 专用音效通道
        cls.load_resources()

    @classmethod
    def load_resources(cls):
        """预加载音频资源"""
        # 加载BGM (只加载目录下的.mp3和.ogg文件)
        for pa in [SourceManager.audio_dream_bgm_path,SourceManager.audio_zfs_bgm_path]:
            for file in os.listdir(pa):
                if file.endswith(('.mp3', '.ogg', '.wav')):
                    name = os.path.splitext(file)[0]
                    cls._bgm_paths[name] = os.path.join(pa, file)

        # 加载音效
        for se in [SourceManager.audio_dream_source_path,SourceManager.audio_zfs_source_path]:
            for file in os.listdir(se):
                if file.endswith(('.mp3', '.ogg', '.wav')):
                    name = os.path.splitext(file)[0]
                    cls._sound_paths[name] = os.path.join(se, file)

    @classmethod
    def play_bgm(cls, bgm_name: str, fade_in: int = 1000):
        """
        播放背景音乐（自动循环）
        :param bgm_name: 音乐名称
        :param fade_in: 淡入时间(毫秒)
        """
        if not cls.bgm_enabled:
            return

        # 如果已经在播放相同的BGM，则不做处理
        if cls._current_bgm_name == bgm_name:
            return

        # 停止当前BGM
        if cls._current_bgm is not None:
            cls._bgm_channel.fadeout(fade_in)

        # 加载并播放新BGM
        if bgm_name in cls._bgm_paths:
            try:
                cls._current_bgm = pygame.mixer.Sound(cls._bgm_paths[bgm_name])
                cls._current_bgm.set_volume(cls.bgm_volume)
                cls._bgm_channel.play(cls._current_bgm, loops=-1, fade_ms=fade_in)
                cls._current_bgm_name = bgm_name
            except pygame.error as e:
                print(f"BGM播放失败: {e}")

    @classmethod
    def play_sound(cls, sound_name: str):
        """
        播放音效（单次）
        :param sound_name: 音效名称
        """
        if not cls.sound_enabled:
            return

        if sound_name in cls._sound_paths:
            try:
                sound = pygame.mixer.Sound(cls._sound_paths[sound_name])
                sound.set_volume(cls.sound_volume)
                cls._sound_channel.play(sound)
            except pygame.error as e:
                print(f"音效播放失败: {e}")

    @classmethod
    def pause_bgm(cls):
        """暂停背景音乐"""
        cls._bgm_channel.pause()

    @classmethod
    def resume_bgm(cls, fade_in: int = 500):
        """恢复背景音乐"""
        if cls._current_bgm is not None and cls.bgm_enabled:
            cls._bgm_channel.unpause()
            cls._bgm_channel.set_volume(cls.bgm_volume)

    @classmethod
    def stop_bgm(cls, fade_out: int = 1000):
        """停止背景音乐"""
        cls._bgm_channel.fadeout(fade_out)
        cls._current_bgm = None
        cls._current_bgm_name = None

    @classmethod
    def set_bgm_volume(cls, volume: float):
        """设置BGM音量"""
        cls.bgm_volume = max(0.0, min(1.0, volume))
        if cls._current_bgm is not None:
            cls._current_bgm.set_volume(cls.bgm_volume)

    @classmethod
    def set_sound_volume(cls, volume: float):
        """设置音效音量"""
        cls.sound_volume = max(0.0, min(1.0, volume))