import pygame
import math
from collections import defaultdict
from typing import Dict, List, Optional, Callable

from typing import TYPE_CHECKING

from src.manager.GameFont import GameFont
from src.manager.GameLogManger import GameLogManager
from src.manager.SourceManager import SourceManager

if TYPE_CHECKING:
    from src.manager.GameManager import GameManager

# 4方向映射（配置编号 → 角度）
direction_map_4 = {
    "右下": 1,
    "左下": 2,
    "左上": 3,
    "右上": 4,
}

# 8方向映射（配置编号 → 角度）
direction_map_8 = {
    "下": 1,
    "左": 2,
    "右": 3,
    "上": 4,
    "左下": 5,
    "右下": 6,
    "左上": 7,
    "右上": 8,
}


class BoneTransform:
    # 初始化函数，设置位置、旋转和缩放
    def __init__(self, pos=(0, 0), rot=0, scale=(1, 1)):
        self.position = pygame.Vector2(pos)  # 设置位置
        self.rotation = rot  # 设置旋转
        self.scale = pygame.Vector2(scale)  # 设置缩放

    # 插值函数，根据目标值和插值因子t计算插值结果
    def lerp(self, target, t):
        return BoneTransform(
            self.position.lerp(target.position, t),  # 插值位置
            self.rotation + (target.rotation - self.rotation) * t,  # 插值旋转
            (
                self.scale.x + (target.scale.x - self.scale.x) * t,  # 插值缩放
                self.scale.y + (target.scale.y - self.scale.y) * t
            )
        )


class AnimationClip:
    def __init__(self, name: str, length: float, fps: int):
        """ 初始化动画剪辑类 """
        self.name = name
        """动画剪辑的名称"""
        self.length = length
        """动画剪辑的长度"""
        self.fps = fps
        """动画剪辑的帧率"""
        self.frames: List[pygame.Surface] = []
        """动画剪辑的帧列表"""
        self.bones: Dict[str, List[BoneTransform]] = defaultdict(list)
        """动画剪辑的骨骼列表"""
        self.events: Dict[int, List[Callable]] = defaultdict(list)
        """动画剪辑的事件列表"""
        self.paused = False
        """是否暂停"""

    def add_frame(self, surface: pygame.Surface):
        """
        添加一帧到动画剪辑中
        :param surface:
        :return:
        """
        self.frames.append(surface)

    def add_event(self, frame_index: int, callback: Callable):
        """
        追加事件到指定的帧
        :param frame_index:
        :param callback:
        :return:
        """
        # 添加一个事件到动画剪辑中
        if frame_index >= len(self.frames):
            GameLogManager.log_service_debug(f"索引:{frame_index} 超过了当前动画集的长度,帧事件不生效")
            return
        self.events[frame_index].append(callback)


class Animator:
    def __init__(self, gm=None):
        # 动画片段字典
        self.clips: Dict[str, AnimationClip] = {}
        # 当前播放的动画片段名称
        self.current: Optional[str] = None
        # 当前播放时间
        self.time = 0.0
        # 播放速度
        self.speed = 1.0
        # 是否循环播放
        self.loop = True
        # 是否暂停
        self.paused = False
        # 动画是否结束
        self.finished = False
        # 动画开始时的回调函数
        self.on_start: Optional[Callable[[str], None]] = None
        # 动画结束时的回调函数
        self.on_end: Optional[Callable[[str], None]] = None
        # 上一次播放的帧索引
        self._last_frame_index = -1
        # 当前动画是 4x4 还是 8x8
        self.supported_directions = 4
        # 游戏管理器
        self.gm: GameManager = gm
        self.delay_timer = 0.0  # 延时计时器
        self.pending_animation = None  # 待播放的动画信息
        self.render_pos = []  # 渲染位置

        self.show_frame_text = False # 是否显示帧的调试文本

    def get_dir(self, anim_dir: str = None):
        """
        根据方向获取对应的朝向索引
        """
        if self.supported_directions == 4:
            return direction_map_4[anim_dir] - 1
        else:
            return direction_map_8[anim_dir] - 1

    # --------- 动画管理 ---------
    def add_clip(self, clip: AnimationClip):
        """
        添加动画片段
        :param clip: 动画片段
        :return:
        """
        # 将动画片段添加到clips字典中，键为动画片段的名称，值为动画片段
        self.clips[clip.name] = clip

    def expose_clip(self, name: str)->AnimationClip:
        """
        导出动画片段
        :param name: 动画片段名称
        :return:
        """
        return self.clips.get(name)

    def surface_to_animation_row(self, surface: pygame.Surface, name: str, frame_column: int,
                                 frame_total: int, fps: int = 2):
        """
        将Surface对象转换为动画片段, 针对单图片存在不分方向的帧, 需要把所有的行的帧都加载为一个动画
        :param surface:
        :param name:
        :param frame_column:
        :param frame_total:
        :param fps:
        :return:
        """
        surface_rect = surface.get_rect()
        frame_w = surface_rect.width // frame_column
        frame_h = surface_rect.height // math.ceil(frame_total / frame_column)
        frames = []
        calc_x = 0
        calc_y = 0

        for frame_index in range(frame_total):
            if frame_index > 0 and frame_index % frame_column == 0:
                calc_x = 0
                calc_y += frame_h
            frame = surface.subsurface((calc_x, calc_y, frame_w, frame_h))

            rect = frame.get_bounding_rect()
            base_offset_x = rect.x
            base_offset_y = rect.y
            frames.append(
                surface.subsurface((
                    calc_x + base_offset_x,  # 使用基准偏移量
                    calc_y + base_offset_y,  # 使用基准偏移量
                    rect.width,  # 使用bounding rect的宽度
                    rect.height  # 使用bounding rect的高度
                ))
            )
            calc_x += frame_w

        self.add_animation(name, len(frames), fps, frames)

    def add_animation(self, name: str, length: float, fps: int,
                      frames: List[pygame.Surface],
                      events: Optional[Dict[int, Callable]] = None) -> AnimationClip:
        """
        添加动画片段
        :param name: 动画片段名称
        :param length: 动画片段长度
        :param fps: 每秒帧数
        :param frames: 动画片段帧列表
        :param events: 动画片段事件字典，键为帧索引，值为回调函数
        :return: 返回动画片段对象
        """
        clip = AnimationClip(name, length, fps)
        for surf in frames:
            clip.add_frame(surf)
        if events:
            for frame_idx, callback in events.items():
                clip.add_event(frame_idx, callback)
        self.add_clip(clip)
        return clip

    # --------- 播放控制 ---------
    def play(self, name: str, loop: bool = True, speed: float = None, restart: bool = True, anim_dir: str = None,
             delay: float = 0, render_pos: list[list] = None):
        """
        播放动画（restart=False 时，重复播放同一动画不会重置进度）
        :param render_pos: 传入的格式为 二维数组 [[x,y],[x1,y1],...]
        :param anim_dir:
        :param name: 动画名称
        :param loop: 是否循环播放
        :param speed: 播放速度
        :param restart: 是否重置进度
        :param delay: 是否延时执行播放
        :return:
        """
        if anim_dir:
            if self.supported_directions == 4:
                name = f"{name}_{direction_map_4[anim_dir] - 1}"
            else:
                name = f"{name}_{direction_map_8[anim_dir] - 1}"
        if name not in self.clips:
            raise ValueError(f"Animation {name} not found")

        if not restart and self.current == name:
            return  # 跳过重复播放

        if delay > 0:
            # 如果有延时，保存动画信息
            self.pending_animation = {
                'name': name,
                'loop': loop,
                'speed': speed,
                'restart': restart,
                'anim_dir': anim_dir
            }
            self.delay_timer = delay
            return
        self.current = name
        self.loop = loop
        if speed is not None:  # 只有明确传入时才覆盖
            self.speed = speed
        # self.speed = speed
        self.time = 0.0
        self._last_frame_index = -1
        self.paused = False
        self.finished = False
        if render_pos:
            self.render_pos = render_pos
        if self.on_start:
            self.on_start(name)

    def cross_fade(self, name: str, duration: float = 0.2, restart: bool = True):
        """
        淡入淡出播放动画
        :param name: 动画名称
        :param duration: 动画持续时间，默认为0.2秒
        :param restart: 是否重新播放动画，默认为True
        :return:
        """
        self.play(name, restart=restart)

    def pause(self, clip_name: str = None, anim_dir: str = None):
        """
        暂停动画
        :param anim_dir:
        :param clip_name: 可选，指定要暂停的动画片段名称。如果为None，则暂停整个动画器
        """
        if clip_name is None:
            self.paused = True
        elif clip_name in self.clips:
            if anim_dir:
                if self.supported_directions == 4:
                    clip_name = f"{clip_name}_{direction_map_4[anim_dir] - 1}"
                else:
                    clip_name = f"{clip_name}_{direction_map_8[anim_dir] - 1}"
            self.clips[clip_name].paused = True

    def resume(self, clip_name: str = None, anim_dir: str = None):
        """
        恢复动画
        :param anim_dir:
        :param clip_name: 可选，指定要恢复的动画片段名称。如果为None，则恢复整个动画器
        """
        if clip_name is None:
            self.paused = False
        elif clip_name in self.clips:
            if anim_dir:
                if self.supported_directions == 4:
                    clip_name = f"{clip_name}_{direction_map_4[anim_dir] - 1}"
                else:
                    clip_name = f"{clip_name}_{direction_map_8[anim_dir] - 1}"
            self.clips[clip_name].paused = False

    def stop(self):
        """ 停止动画 """
        self.current = None
        self.time = 0.0
        self.paused = False
        self._last_frame_index = -1
        self.finished = True

    # --------- 更新与渲染 ---------
    def update(self, dt: float = 1.0, render: bool = False):
        """ 更新动画 """
        # 如果当前没有动画或者动画暂停，则直接返回
        if not self.current or self.paused:
            return
        # 获取当前动画的clip
        clip = self.clips[self.current]
        # 检查动画器或当前动画片段是否暂停
        if self.paused or clip.paused:
            return

        # 处理延时播放
        if self.delay_timer > 0:
            self.delay_timer -= dt
            if self.delay_timer <= 0 and self.pending_animation:
                # 延时结束，执行待播放的动画
                anim_info = self.pending_animation
                self.pending_animation = None
                self.play(
                    anim_info['name'],
                    loop=anim_info['loop'],
                    speed=anim_info['speed'],
                    restart=anim_info['restart'],
                    anim_dir=anim_info['anim_dir']
                )
            return

        # 更新动画的时间
        self.time += dt * self.speed

        # 如果动画时间超过clip的长度，则进行循环或者停止
        if self.time >= clip.length or self.is_last_index():
            if self.loop:
                # 如果循环，则将动画时间重置为clip的长度
                self.time %= clip.length
            else:
                # 如果不循环，则将动画时间设置为clip的长度减去一个非常小的数，以保证动画停止
                self.time = clip.length - 1e-4
                self.finished = True
                if self.on_end:
                    self.on_end(self.current)

        # 计算当前帧的索引
        frame_idx = int(self.time * clip.fps) % len(clip.frames)
        # 如果当前帧的索引和上一次的索引不同，则更新帧
        if frame_idx != self._last_frame_index:
            self._last_frame_index = frame_idx
            # 如果当前帧有事件，则执行事件
            if frame_idx in clip.events:
                for callback in clip.events[frame_idx]:
                    callback()
        if render:
            # 渲染函数
            self.render(int(self.render_pos[0][0]), int(self.render_pos[0][1]) + 20, center=True)

    def render(self, render_x, render_y, target_surface: pygame.Surface = None, center: bool = False):
        if target_surface is None:
            if self.gm is None:
                return
            target_surface = self.gm.game_win
        eff_frame = self.get_frame()
        if eff_frame:
            if len(self.render_pos):
                for pos in self.render_pos:
                    if center:
                        target_surface.blit(eff_frame,
                                            (pos[0] - eff_frame.width // 2, pos[1] - eff_frame.height // 2))
                    else:
                        target_surface.blit(eff_frame, pos)
            else:
                # 使用统一的偏移量进行渲染
                target_surface.blit(eff_frame, (render_x, render_y))
            if self.show_frame_text:
                GameFont.render_line_text(self.current + str(self.get_frame_index()),render_x, render_y - 20, True)

    def get_frame(self) -> Optional[pygame.Surface]:
        """ 获取当前帧 """
        clip = self.clips.get(self.current)
        frame_idx = self.get_frame_index()
        if frame_idx is None:
            return frame_idx
        return clip.frames[frame_idx]

    def get_frame_index(self) -> Optional[int]:
        """ 获取当前帧索引 """
        if not self.current:
            return None
        clip = self.clips[self.current]
        return int(self.time * clip.fps) % len(clip.frames)

    def is_last_index(self) -> Optional[int]:
        """ 是否是最后一帧 """
        if not self.current:
            return None
        clip = self.clips[self.current]
        current_frame = int(self.time * clip.fps) % len(clip.frames)
        return current_frame == len(clip.frames) - 1

    def draw(self, surface: pygame.Surface, pos):
        """
        绘制到指定表面
        :param surface:
        :param pos:
        :return:
        """
        frame = self.get_frame()
        if frame:
            surface.blit(frame, pos)

    def is_playing(self, name: str) -> bool:
        """
        当前是否正播放着指定名称的动画
        :param name: 动画名称
        :return: 如果正在播放返回True，否则返回False
        """
        return name == self.current

    def is_paused(self, name: str = None) -> bool:
        """
        检查指定动画是否暂停
        :param name: 动画名称
        :return: 如果暂停返回True，否则返回False
        """
        if name is None:
            return self.paused
        if name in self.clips:
            return self.clips[name].paused
        return False

# if __name__ == "__main__":
#     pygame.init()
#     screen = pygame.display.set_mode((800, 600))
#     clock = pygame.time.Clock()
#
#     animator1 = Animator()
#     animator2 = Animator()  # 用于测试共享 Clip
#
#     # --- 创建动画帧 ---
#     frames = []
#     for i in range(4):
#         surf = pygame.Surface((50, 50))
#         surf.fill((50 * i, 100, 200))
#         frames.append(surf)
#
#     # --- 快速创建动画（返回 Clip 以便共享） ---
#     clip_run = animator1.add_animation(
#         name="Run",
#         length=1.0,
#         fps=8,
#         frames=frames,
#         events={2: lambda: print("Run 动画触发第2帧事件")}
#     )
#
#     # --- 共享 Clip 给另一个 Animator ---
#     animator2.add_clip(clip_run)
#
#     # 回调
#     animator1.on_start = lambda name: print(f"[A1] Animation {name} started")
#     animator1.on_end = lambda name: print(f"[A1] Animation {name} ended")
#     animator2.on_start = lambda name: print(f"[A2] Animation {name} started")
#
#     animator1.play("Run", loop=True,restart=False)
#     animator1.play("Run", loop=True)
#     animator2.play("Run", loop=True)
#
#     running = True
#     while running:
#         dt = clock.tick(60) / 1000
#         for event in pygame.event.get():
#             if event.type == pygame.QUIT:
#                 running = False
#             elif event.type == pygame.KEYDOWN:
#                 if event.key == pygame.K_1:
#                     animator1.play("Run", loop=True)
#                 if event.key == pygame.K_p:
#                     animator1.pause()
#                 elif event.key == pygame.K_r:
#                     animator1.resume()
#                 elif event.key == pygame.K_s:
#                     animator1.stop()
#
#         animator1.update(dt)
#         animator2.update(dt)
#
#         screen.fill((30, 30, 30))
#         animator1.draw(screen, (300, 275))
#         animator2.draw(screen, (400, 275))
#         pygame.display.flip()
#
#     pygame.quit()
