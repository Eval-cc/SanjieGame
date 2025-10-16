#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：GameLogger.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/6/16 12:41 
@Describe: 日志管理类--此为基础日志类,请勿直接在逻辑层使用
"""

import logging
import os
import sys
from datetime import datetime
from colorama import init, Fore, Back, Style

# 初始化 colorama（自动处理 Windows 的颜色支持）
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """自定义带颜色的日志格式化器"""
    def format(self, record):
        # 先让父类格式化日志记录
        message = super().format(record)

        # 根据日志级别添加颜色
        if record.levelno == logging.DEBUG:
            return f"{Fore.BLUE}{message}{Style.RESET_ALL}"
        elif record.levelno == logging.INFO:
            return f"{Fore.GREEN}{message}{Style.RESET_ALL}"
        elif record.levelno == logging.WARNING:
            return f"{Fore.YELLOW}{message}{Style.RESET_ALL}"
        elif record.levelno == logging.ERROR:
            return f"{Fore.RED}{message}{Style.RESET_ALL}"
        elif record.levelno == logging.CRITICAL:
            return f"{Fore.RED}{Back.WHITE}{message}{Style.RESET_ALL}"
        else:
            return message


class GameLogger:
    """
    不建议在业务层调用此类, 请使用封装的GameLogManager.py
    """
    def __init__(self, name='GameLogger', log_name=None, log_level=logging.DEBUG):
        """
        初始化日志类

        :param name: 日志名称
        :param log_name: 日志文件名称，如果为None则不写入文件
        :param log_level: 日志级别，默认为DEBUG
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

        # 清除已有的handler，避免重复添加
        self.logger.handlers.clear()

        # 创建控制台handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # 创建带颜色的格式化器
        formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(formatter)

        # 添加控制台handler
        self.logger.addHandler(console_handler)

        # 如果指定了日志文件，则添加文件handler（文件不需要颜色）
        if log_name is not None:
            # 生成日期格式的日志文件名（如 2525_06_16_info.log）
            today = datetime.now()
            date_str = today.strftime("%y%m%d")  # （年_月_日）
            # 定义不同日志级别的文件名（可选）
            if log_level == logging.DEBUG:
                log_filename = f"DEBUG/{date_str}_debug_{log_name}.log"
            elif log_level == logging.INFO:
                log_filename = f"INFO/{date_str}_info_{log_name}.log"
            elif log_level == logging.WARNING:
                log_filename = f"WARN/{date_str}_warning_{log_name}.log"
            elif log_level == logging.ERROR:
                log_filename = f"ERROR/{date_str}_error_{log_name}.log"
            elif log_level == logging.CRITICAL:
                log_filename = f"CRITICAL/{date_str}_critical_{log_name}.log"
            else:
                log_filename = f"LOG/{date_str}_log_{log_name}.log"  # 默认

            root_path = os.path.dirname(os.path.abspath(sys.argv[0]))
            log_file = os.path.join(root_path,f"logs/{log_filename}")
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(log_level)

            # 文件使用普通格式化器（无颜色）
            file_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

        # 关键点: 设置propagate为False，避免日志向上传播到root logger
        self.logger.propagate = False


    def debug(self, *args, sep=' ', end='\n'):
        """支持sep和end参数的调试日志"""
        msg = sep.join(str(arg) for arg in args) + end
        self.logger.debug(msg.rstrip('\n'), stacklevel=2)


    def info(self, *args, sep=' ', end='\n'):
        """普通信息"""
        msg = sep.join(str(arg) for arg in args) + end
        self.logger.info(msg.rstrip('\n'), stacklevel=2)

    def warning(self, *args, sep=' ', end='\n'):
        """警告信息"""
        msg = sep.join(str(arg) for arg in args) + end
        self.logger.warning(msg.rstrip('\n'), stacklevel=2)

    def error(self, *args, sep=' ', end='\n'):
        """错误信息"""
        msg = sep.join(str(arg) for arg in args) + end
        self.logger.error(msg.rstrip('\n'), stacklevel=2)

    def critical(self, *args, sep=' ', end='\n'):
        """严重错误信息"""
        msg = sep.join(str(arg) for arg in args) + end
        self.logger.critical(msg.rstrip('\n'), stacklevel=2)


# 使用示例
# if __name__ == '__main__':
#     # 示例1: 只输出到控制台（带颜色）
#     console_logger = GameLogger('ConsoleLogger')
#     console_logger.debug('这是一条调试信息(蓝色)')
#     console_logger.info('这是一条普通信息(绿色)')
#     console_logger.warning('这是一条警告信息(黄色)')
#     console_logger.error('这是一条错误信息(红色)')
#     console_logger.critical('这是一条严重错误信息(红底白字)')
#
#     # 示例2: 输出到控制台和文件（控制台带颜色，文件无颜色）
#     file_logger = GameLogger('FileLogger', log_name='app')
#     file_logger.warning('这是一条警告信息(控制台彩色，文件无色)')
#     file_logger.error('这是一条错误信息(控制台彩色，文件无色)')