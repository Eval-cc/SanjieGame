#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：GameLogManger.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/6/16 13:18 
@Describe: 
"""
from src.lib.GameLogger import GameLogger

class GameLogManager:
    log_service_main_game:GameLogger = None
    """游戏主日志,输出到控制台和本地log文件, 可选择"""
    log_service_debug:GameLogger.debug = None
    """游戏调试日志, 仅输出控制台"""
    log_service_error:GameLogger.error = None
    """游戏异常日志, 输出到控制台和本地log文件"""


    @staticmethod
    def Awake():
        GameLogManager.log_service_main_game = GameLogger("GameMainLog","main_game")
        GameLogManager.log_service_debug = GameLogger("GameDebugLog").debug
        GameLogManager.log_service_error = GameLogger("GameErrorLog","main_error").error
