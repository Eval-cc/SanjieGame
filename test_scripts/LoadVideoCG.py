#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : LoadVideoCG.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/08/13 12:24
@Desc    : pygame加载视频流
"""

import pygame
import cv2
import numpy as np
import sys


class VideoStreamPlayer:
    def __init__(self, video_path, screen_width=1280, screen_height=720):
        """
        初始化视频流播放器
        :param video_path: 视频文件路径
        :param screen_width: 播放窗口宽度
        :param screen_height: 播放窗口高度
        """
        # 初始化Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("测试pygame加载视频")

        # 打开视频文件
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError("无法打开视频文件！")

        # 获取视频基本信息
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 控制参数
        self.clock = pygame.time.Clock()
        self.paused = False
        self.current_frame_pos = 0

    def get_next_frame(self):
        """动态获取下一帧（内存安全的核心）"""
        ret, frame = self.cap.read()
        self.current_frame_pos += 1

        if not ret:
            return None

        # OpenCV BGR → Pygame RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 转换为Pygame Surface
        return pygame.surfarray.make_surface(
            np.transpose(frame_rgb, (1, 0, 2))  # 调整维度顺序
        )

    def run(self):
        """主播放循环"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.paused = not self.paused  # 空格暂停/继续
                    elif event.key == pygame.K_ESCAPE:
                        running = False

            if not self.paused:
                # 获取并显示当前帧
                frame = self.get_next_frame()
                if frame is None:
                    break  # 视频结束

                # 缩放帧以适应窗口（可选）
                scaled_frame = pygame.transform.scale(frame, self.screen.get_size())
                self.screen.blit(scaled_frame, (0, 0))

                # 显示进度信息
                font = pygame.font.SysFont('Arial', 24)
                progress_text = f"Frame: {self.current_frame_pos}/{self.total_frames} | FPS: {self.clock.get_fps():.1f}"
                text_surface = font.render(progress_text, True, (100, 50, 50))
                self.screen.blit(text_surface, (10, 10))

                pygame.display.flip()
                self.clock.tick(self.fps)  # 按原视频帧率播放

        # 释放资源
        self.cap.release()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    # 使用示例（请替换为你的视频路径）
    player = VideoStreamPlayer(r"D:\Windows\Desktop\20251017_131355.mp4", screen_width=500, screen_height=500)
    player.run()