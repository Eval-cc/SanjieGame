#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : LoadGIF.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/08/13 12:17
@Desc    : 测试pygame加载gif文件
"""

import pygame
import imageio
import numpy as np


def load_gif_frames(gif_path):
    gif = imageio.mimread(gif_path)
    frames = []

    for frame in gif:
        # 检查通道数（灰度图需转RGB）
        if len(frame.shape) == 2:
            frame = np.stack([frame] * 3, axis=-1)  # 灰度转RGB
        elif frame.shape[2] == 4:
            frame = frame[:, :, :3]  # 丢弃Alpha通道（可选）

        # 调整维度顺序为 (width, height, channels)
        frame = np.transpose(frame, (1, 0, 2))

        # 转换为Pygame Surface
        pygame_frame = pygame.surfarray.make_surface(frame)
        frames.append(pygame_frame)

    return frames


# 初始化 Pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

# 加载 GIF 所有帧
gif_frames = load_gif_frames(r"E:\Project Code\Python Code\a_pygame\三界奇谈\Graphics\Icons\items\1.gif")
current_frame = 0

if __name__ == "__main__":
    # 主循环
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 显示当前帧
        screen.fill((0, 0, 0))
        screen.blit(gif_frames[current_frame], (100, 100))

        # 切换到下一帧
        current_frame = (current_frame + 1) % len(gif_frames)

        pygame.display.flip()
        clock.tick(30)  # 30 FPS

    pygame.quit()
