#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：win.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/2/13 下午8:23 
@Describe: 
"""
import pygame
import sys
from src.manager.GameLogManger import GameLogManager
from src.manager.GameLuaManager import GameLuaManager
from src.manager.GameMapManager import GameMapManager
from src.network.GameWorldServer import GameWorldServer
from src.render.GameLogin import GameLogin
from src.render.GameUI import GameUI
from src.render.RenderMap import RenderMap
from src.manager.GameManager import GameManager
from src.manager.GameEvent import GameEvent
from src.manager.GameFont import GameFont
from src.system.ShopSystem import ShopSystem
from src.system.TaskSystem import TaskTracker


class GameWin:
    def __init__(self, width: int, height: int, title: str, fps: int = 60):
        self.width = width
        self.height = height
        self.title = title
        self.fps = fps
        self.clock = pygame.Clock()
        self.__init_win()

    def __init_win(self):
        """初始化游戏窗口"""
        # 初始化 pygame
        pygame.init()
        GameManager.game_win = pygame.display.set_mode((self.width, self.height))
        GameManager.clock = self.clock
        pygame.display.set_caption(self.title)
        GameLogManager.Awake()
        GameLuaManager.Awake()
        GameManager.Awake()
        # 初始化字体管理类
        GameFont.load(GameManager.game_win)
        GameManager.add("游戏UI", GameUI(GameManager))
        GameManager.add("任务追踪", TaskTracker(GameManager))
        GameManager.add("登录页面", GameLogin(GameManager))

        if sys.argv and len(sys.argv) > 1:
            GameManager.has_debug_render = sys.argv[1].lower() == "true"  # 如果传的是字符串 "true"/"false"
        self.renderer()

    def renderer(self):
        while True:
            GameManager.game_win.fill((10, 10, 10))
            GameEvent.listen_event()
            self.clock.tick(self.fps)

            GameManager.render()
            pygame.display.update()
            GameMapManager.loop()
