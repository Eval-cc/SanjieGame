#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : LoginServer.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/18 22:33
@Desc    : 异步登录服务
"""
import threading
from typing import Callable, Optional
from src.manager.GameLogManger import GameLogManager
from src.system.GameToast import GameToastManager


class LoginServer:
    """异步登录管理器 - 使用多线程避免阻塞主进程"""

    def __init__(self, server_url: str = "http://localhost:2169"):
        self.server_url = server_url
        self.token = None
        self.username = None
        self.logged_in = False
        self.on_login_success: Optional[Callable] = None
        self.on_login_failed: Optional[Callable] = None
        self.on_register_success: Optional[Callable] = None
        self.on_register_failed: Optional[Callable] = None

    def _run_in_thread(self, target: Callable, args: tuple = (), kwargs: dict = None):
        """在后台线程中运行函数"""
        if kwargs is None:
            kwargs = {}
        thread = threading.Thread(target=target, args=args, kwargs=kwargs)
        thread.daemon = True  # 设置为守护线程，主线程退出时自动结束
        thread.start()

    def register(self, username: str, password: str, callback: Optional[Callable] = None) -> None:
        """异步注册新用户"""
        if not username or not password:
            GameToastManager.add_message("账号密码不能为空")
            if self.on_register_failed:
                self.on_register_failed("账号密码不能为空")
            return

        def _register_task():
            try:
                import requests
                response = requests.post(
                    f"{self.server_url}/register",
                    json={"username": username, "password": password},
                    timeout=5  # 设置5秒超时
                )

                if response.status_code == 201:
                    GameToastManager.add_message("注册成功")
                    if callback:
                        callback(True, None)
                    if self.on_register_success:
                        self.on_register_success(username)
                else:
                    error_msg = response.json().get("error", "注册失败")
                    GameToastManager.add_message(f"注册失败: {error_msg}")
                    if callback:
                        callback(False, error_msg)
                    if self.on_register_failed:
                        self.on_register_failed(error_msg)
            except requests.exceptions.Timeout:
                error_msg = "连接超时"
                GameLogManager.log_service_error(f"注册请求超时")
                GameToastManager.add_message("连接服务器超时")
                if callback:
                    callback(False, error_msg)
                if self.on_register_failed:
                    self.on_register_failed(error_msg)
            except Exception as e:
                error_msg = str(e)
                GameLogManager.log_service_error(f"注册请求失败: {e}")
                GameToastManager.add_message("无法连接到服务器")
                if callback:
                    callback(False, error_msg)
                if self.on_register_failed:
                    self.on_register_failed(error_msg)

        self._run_in_thread(_register_task)

    def login(self, username: str, password: str, callback: Optional[Callable] = None) -> None:
        """异步用户登录"""
        if not username or not password:
            GameToastManager.add_message("账号密码不能为空")
            if self.on_login_failed:
                self.on_login_failed("账号密码不能为空")
            return

        def _login_task():
            try:
                import requests
                response = requests.post(
                    f"{self.server_url}/login",
                    json={"username": username, "password": password},
                    timeout=5  # 设置5秒超时
                )

                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("token")
                    self.username = username
                    self.logged_in = True
                    if callback:
                        callback(True, None)
                    if self.on_login_success:
                        self.on_login_success(data)
                    else:
                        GameToastManager.add_message(f"欢迎回来, {username}")
                else:
                    error_msg = response.json().get("error", "登录失败")
                    if callback:
                        callback(False, error_msg)
                    if self.on_login_failed:
                        self.on_login_failed(error_msg)
                    else:
                        GameToastManager.add_message(f"登录失败: {error_msg}")
            except requests.exceptions.Timeout:
                error_msg = "连接超时"
                if callback:
                    callback(False, error_msg)
                if self.on_login_failed:
                    self.on_login_failed(error_msg)
                else:
                    GameLogManager.log_service_error(f"登录请求超时")
                    GameToastManager.add_message("连接服务器超时")
            except Exception as e:
                error_msg = str(e)
                GameLogManager.log_service_error(f"登录请求失败: {e}")
                GameToastManager.add_message("无法连接到服务器")
                if callback:
                    callback(False, error_msg)
                if self.on_login_failed:
                    self.on_login_failed(error_msg)

        self._run_in_thread(_login_task)

    def online_limit(self, username: str, client_id: str, callback: Optional[Callable] = None) -> None:
        """推送在线状态"""
        if not username:
            if self.on_login_failed:
                self.on_login_failed("用户名不能为空")
            else:
                GameToastManager.add_message("用户名不能为空")
            return

        def _online_limit():
            try:
                import requests
                response = requests.post(
                    f"{self.server_url}/online_limit",
                    json={"username": username, "clientID": client_id},
                    timeout=5  # 设置5秒超时
                )

                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("token")
                    self.username = username
                    self.logged_in = True
                    if callback:
                        callback(True, None)
                    if self.on_login_success:
                        self.on_login_success(data)
                    else:
                        GameToastManager.add_message(f"欢迎回来, {username}")
                else:
                    error_msg = response.json().get("error", "操作失败")
                    if callback:
                        callback(False, error_msg)
                    if self.on_login_failed:
                        self.on_login_failed(error_msg)
                    else:
                        GameToastManager.add_message(f"操作失败: {error_msg}")
            except requests.exceptions.Timeout:
                error_msg = "连接超时"
                if callback:
                    callback(False, error_msg)
                if self.on_login_failed:
                    self.on_login_failed(error_msg)
                else:
                    GameLogManager.log_service_error(f"登录请求超时")
                    GameToastManager.add_message("连接服务器超时")
            except Exception as e:
                error_msg = str(e)
                GameLogManager.log_service_error(f"登录请求失败: {e}")
                GameToastManager.add_message("无法连接到服务器")
                if callback:
                    callback(False, error_msg)
                if self.on_login_failed:
                    self.on_login_failed(error_msg)

        self._run_in_thread(_online_limit)

    def logout(self):
        """用户登出"""
        self.token = None
        self.username = None
        self.logged_in = False
        GameToastManager.add_message("已登出")

    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return self.logged_in and self.token is not None