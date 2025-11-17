# """
# !/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : GameWorldServer.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/15 12:51
@Desc    : 后端通信模块 - 同步版本
"""
import os.path

import socketio  # 使用同步客户端
import time
import struct
from typing import Dict, Any, List, Optional, Callable, TYPE_CHECKING

from src.code.Enums import SpriteState
from src.code.Item import Item
from src.code.SpriteBase import SpriteBase
from src.manager.GameFont import GameFont
from src.manager.GameLogManger import GameLogManager
from src.manager.GameWorldManager import GameWorldManager

from src.manager.SourceManager import SourceManager
from src.network.LoginServer import LoginServer
from src.system.Animator import Animator
from src.system.GameTipDialog import GameDialogBoxManager
from src.system.GameToast import GameToastManager

if TYPE_CHECKING:
    from src.manager.GameManager import GameManager


class GameWorldServer(SpriteBase):
    """
    同步版本多人游戏客户端
    使用世界坐标系统
    """

    def __init__(self, user: SpriteBase, gm: Any, server_url: str = "http://localhost:2169"):
        """
        初始化多人游戏客户端
        Args:
            user: 玩家精灵对象
            gm: 游戏管理器
            server_url: 服务器地址
        """
        super().__init__()
        self.sio = socketio.Client()  # 同步客户端
        self.server_url = server_url
        self.room_id = None
        self.sprite = user
        self.player_sprite = self._serialize_sprite_data(user)

        # 存放远程用户
        self.remote_player: dict[str, RemotePlayerSprite] = {}

        self.gm: "GameManager" = gm
        self.gm.add("network_client", self)

        # 连接状态
        self.connected = False
        self.player_id = None

        # 玩家数据
        self.players: Dict[str, Dict[str, Any]] = {}
        self.chat_messages: List[str] = []

        # 性能优化
        self._last_sent_pos = None
        self._last_send_time = 0
        self.send_interval = 0.1  # 100ms 发送间隔
        self.send_count = 0

        # 回调函数
        self.on_player_joined: Optional[Callable] = None
        self.on_player_left: Optional[Callable] = None
        self.on_player_moved: Optional[Callable] = None
        self.on_chat_message: Optional[Callable] = None
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None

        # 设置事件处理器
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        """设置同步事件处理器"""

        @self.sio.event
        def connect():
            self.connected = True
            GameToastManager.add_message("成功连接服务器")

            # 发送加入房间请求
            self.send_msg('join_room', {
                'roomId': self.room_id,
                'playerData': self.player_sprite
            })

            if self.on_connected:
                self.on_connected()

        @self.sio.event
        def connect_error(data):
            self.connected = False
            GameLogManager.log_service_error(f"连接失败: {data}")

        @self.sio.event
        def disconnect():
            self.connected = False
            GameToastManager.add_message("断开连接")
            if self.on_disconnected:
                self.on_disconnected()

        @self.sio.event
        def join_success(data):
            """处理加入成功事件"""
            # self.players.clear()
            # for rk in self.remote_player.keys():
            #     self.remote_player[rk].destroy()
            # self.remote_player.clear()
            # 设置当前玩家
            if 'player' in data:
                self.player_id = data['player']['id']
                self.players[self.player_id] = data['player']
                self._update_local_sprite_from_data(data['player'])
                # 推送当前连接的客户端id到后台
                up_online = LoginServer()
                up_online.online_limit(self.sprite.acc_name, self.player_id)
                up_online.on_login_success = lambda data: GameLogManager.log_service_debug(f"成功:{data}")
                up_online.on_login_failed = lambda data: GameLogManager.log_service_error(f"失败:{data}")

            # 添加现有玩家
            if 'allPlayers' in data:
                for player_data in data['allPlayers']:
                    player_id = player_data.get('id')
                    if player_id and player_id != self.player_id:
                        self.players[player_id] = player_data
                        self._create_remote_player_sprite(player_id, player_data)

            GameLogManager.log_service_debug(f"加入房间成功! 玩家数: {len(self.players)}")

        @self.sio.event
        def player_joined(data):
            """新玩家加入"""
            if 'player' in data:
                player = data['player']
                self.players[player['id']] = player
                self._create_remote_player_sprite(player['id'], player)
                if self.on_player_joined:
                    self.on_player_joined(player)

        @self.sio.event
        def player_left(data):
            """玩家离开"""
            player_id = data.get('playerId')
            if player_id in self.remote_player:
                player = self.players[player_id]
                self._remove_remote_player_sprite(player_id)
                del self.players[player_id]
                if self.on_player_left:
                    self.on_player_left(player)

        @self.sio.event
        def force_logout(data):
            """
            被挤下线了
            :param data:
            :return:
            """
            self.disconnect()
            reason = data.get('reason')
            GameDialogBoxManager.dialog(reason)

        @self.sio.event
        def player_action(data):
            """
            收到玩家动作
            :param data:
            :return:
            """
            # 1 是扔道具
            if data.get('type') == "1":
                # 先判断这个丢弃的道具是否已经追加过了
                puid = data.get('itemData').get("puid")
                if not GameWorldManager.has_pick_item(puid):
                    world_x = data.get('itemData').get("world_x")
                    world_y = data.get('itemData').get("world_y")
                    item_data: dict[str, str] = SourceManager.get_csv("items", data.get('itemData').get("id"))
                    item_data["__pos"] = [0, 0, 0]
                    item = Item(item_data)
                    item.count = data.get('itemData').get("count")
                    GameWorldManager.add_pick_item(item, world_x, world_y, False, puid)
            # 2 是被人捡起来了. 或者过期了?
            elif data.get('type') == "2":
                GameWorldManager.remove_pick_item(data.get('itemData').get("puid"))

        # @self.sio.event
        # def player_moved(data):
        #     """玩家移动 明文格式--不推荐"""
        #     player_id = data.get('playerId')
        #     if player_id in self.remote_player:
        #         x, y, direction, sta = data.get('x'), data.get('y'), data.get("direction"), data.get("sta")
        #         current_path = data.get('current_path')
        #         self._update_remote_player_position(player_id, x, y, direction, sta, current_path)
        #         if self.on_player_moved:
        #             self.on_player_moved(self.players[player_id])
        #         if int(x) == -99:
        #             return
        #         self.players[player_id]['position'] = [x, y]

        @self.sio.event
        def player_moved(data):
            """
            解析收到的时间,  移动的数据比较频繁, 所以格式用的是二进制
            :param data:
            :return:
            """
            # 1. 解析 playerId（前 8 字节）
            player_id = data[:20].decode('utf-8').strip('\x00')

            # 2. 解析 x, y, direction, sta（接下来的 10 字节）
            x, y = struct.unpack_from('<ff', data, 20)  # 小端序浮点数
            direction = data[28]
            sta = data[29]

            # 3. 解析路径点数量（2 字节无符号整数）
            path_count = struct.unpack_from('<H', data, 30)[0]  # 小端序

            # 4. 解析路径数据（直接读取为二维数组）
            current_path = []
            offset = 32
            if path_count > 0:
                for _ in range(path_count):
                    px, py = struct.unpack_from('<ff', data, offset)  # 每个点 [x,y]
                    current_path.append([px, py])
                    offset += 8

            # 6. 构造 JSON 格式（保持原始结构）
            # json_data = {
            #     'playerId': player_id,
            #     'x': x,
            #     'y': y,
            #     'direction': direction,
            #     'sta': sta,
            #     'current_path': current_path,
            # }
            # 7. 调用原逻辑
            if player_id in self.remote_player:
                self._update_remote_player_position(
                    player_id, x, y, direction, sta, current_path
                )
                if self.on_player_moved:
                    self.on_player_moved(self.players[player_id])
                if int(x) == -99:
                    return
                self.players[player_id]['position'] = [x, y]

        # @self.sio.event
        # def player_updated(data):
        #     """玩家属性更新"""
        #     player_id = data.get('playerId')
        #     if player_id in self.players:
        #         self.players[player_id].update(data.get('attributes', {}))
        #         self._update_remote_player_attributes(player_id, data.get('attributes', {}))
        #         # GameLogManager.log_service_debug(f"玩家 {player_id} 属性已更新")

        @self.sio.event
        def chat_message(data):
            """聊天消息"""
            message = data.get('message')
            player_id = data.get('playerId')
            if message is None or player_id is None:
                GameToastManager.add_message("异常.无法接收服务器消息")
                return
            player_name = self.players.get(player_id, {}).get('name', '未知玩家')
            chat_text = f"{player_name}: {message}"

            self.chat_messages.append(chat_text)
            if len(self.chat_messages) > 10:
                self.chat_messages = self.chat_messages[-10:]

            if self.on_chat_message:
                self.on_chat_message(player_id, player_name, message)

    def _serialize_sprite_data(self, sprite: SpriteBase) -> Dict[str, Any]:
        """序列化精灵数据 - 只使用 user 的属性"""
        return {
            # 基本属性
            'UID': sprite.UID,
            'name': sprite.name,
            'position': sprite.position,  # 世界坐标

            # 核心属性
            'healthy': sprite.healthy,
            'max_healthy': sprite.max_healthy,
            'level': sprite.level,
            'direction': sprite.direction,

            # 战斗属性
            'attack': sprite.attack,
            'defense': sprite.defense,
            'attack_speed': sprite.attack_speed,
            'move_speed': sprite.move_speed,

            # 状态
            'sprite_state': sprite.sprite_state.value if hasattr(sprite.sprite_state, 'value') else sprite.sprite_state,
            'battle_state': sprite.battle_state,

            # 动画相关
            'anim_index': sprite.anim_index,
            'supported_directions': sprite.supported_directions,
            "frame_width": sprite.frame_width,
            "frame_timer": sprite.frame_timer,
            "frame_delay": sprite.frame_delay,
            "stand_model": sprite.stand_model,
            "move_model": sprite.move_model,
            "stand_direction": sprite.stand_direction,
            "move_direction": sprite.move_direction,
            "stand_texture": sprite.stand_texture,
            "move_texture": sprite.move_texture,
            "width": sprite.rect.width,
            "height": sprite.rect.height,

            "current_path": sprite.current_path
        }

    def _update_local_sprite_from_data(self, player_data: Dict[str, Any]):
        """从网络数据更新本地精灵"""
        self.player_sprite["position"] = player_data.get('position')

    def _create_remote_player_sprite(self, player_id: str, sprite_data: Dict[str, Any]):
        """创建远程玩家精灵"""
        # 创建远程玩家精灵实例
        remote_sprite = RemotePlayerSprite(sprite_data, self.gm)
        # GameLogManager.log_service_debug(f"👥 创建远程玩家精灵: {remote_sprite.name},{player_id}")
        self.remote_player[player_id] = remote_sprite
        GameToastManager.add_message(f"玩家:{remote_sprite.name} 加入游戏")

    def _remove_remote_player_sprite(self, player_id: str):
        """移除远程玩家精灵"""
        self.remote_player[player_id].destroy()
        del self.remote_player[player_id]

    def _update_remote_player_position(self, player_id: str, x: float, y: float, direction: int, sta: int,
                                       current_path: list):
        """更新远程玩家位置（世界坐标）"""
        if self.remote_player.get(player_id) and int(x) != -99:
            self.remote_player[player_id].position = [x, y]
            self.remote_player[player_id].current_path = current_path

        anim_name = f"move_{direction}" if int(sta) == 1 else f"stand_{direction}"
        if not self.remote_player[player_id].animator.is_playing(anim_name):
            self.remote_player[player_id].animator.play(anim_name)

    def _update_remote_player_attributes(self, player_id: str, attributes: Dict[str, Any]):
        """更新远程玩家属性"""
        sprite_key = f"remote_player_{player_id}"
        remote_sprite = getattr(self.gm, sprite_key, None)
        if remote_sprite:
            for attr, value in attributes.items():
                if hasattr(remote_sprite, attr):
                    setattr(remote_sprite, attr, value)

    def connect_sync(self, room_id: str = "game_room"):
        """
        同步连接
        Args:
            room_id: 房间ID，默认为 "game_room"
        """
        self.room_id = room_id
        try:
            GameLogManager.log_service_debug(f"连接到 {self.server_url}，房间: {room_id}...")
            self.sio.connect(self.server_url)
            return True
        except Exception as e:
            GameLogManager.log_service_error(f"连接失败: {e}")
            return False

    def disconnect(self, change_scene: bool = False):
        """断开连接"""
        if self.connected:
            self.sio.disconnect()
        if change_scene:
            return
        # 清空在线玩家列表
        for p_k in self.remote_player.keys():
            self.remote_player[p_k].destroy()
        self.remote_player.clear()

        # 重置一些数据
        self.room_id = None
        self.sprite = None
        self.player_sprite = None

        # 连接状态
        self.connected = False
        self.player_id = None
        # 玩家数据
        self.players: Dict[str, Dict[str, Any]] = {}
        self.chat_messages: List[str] = []
        # 性能优化
        self._last_sent_pos = None
        self._last_send_time = 0
        self.send_interval = 0.1  # 100ms 发送间隔
        self.send_count = 0
        # 回调函数
        self.on_player_joined: Optional[Callable] = None
        self.on_player_left: Optional[Callable] = None
        self.on_player_moved: Optional[Callable] = None
        self.on_chat_message: Optional[Callable] = None
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        if self.on_disconnected:
            self.on_disconnected()
        self.gm.remove(self)
        self.gm.logout()

    def send_msg(self, channel: str, data: dict):
        """
        推送服务器消息
        :param channel:
        :param data:
        :return:
        """
        if not self.connected:
            GameToastManager.add_message("已断开连接")
            return
        if data.get("roomId") is None:
            data["roomId"] = self.room_id
        self.sio.emit(channel, data)

    def send_move(self):
        """
        给服务器发送移动消息
        """
        current_time = time.time()

        # 频率限制：避免发送太频繁
        if current_time - self._last_send_time < self.send_interval:
            return

        if self.connected and self.room_id:
            try:
                start_time = time.time()
                self.send_msg('player_move', {
                    'roomId': self.room_id,
                    'x': self.sprite.position[0], # 当前位置
                    'y': self.sprite.position[1],
                    "direction": self.sprite.direction,
                    "sta": self.sprite.sprite_state.value,
                    "current_path": self.sprite.current_path # 寻路的路径
                })
                send_time = (time.time() - start_time) * 1000

                self.send_count += 1
                self._last_send_time = current_time

                # 每100次打印一次性能统计
                if self.send_count % 100 == 0:
                    GameToastManager.add_message(f"网络性能: {send_time:.2f}ms")

            except Exception as e:
                GameLogManager.log_service_error(f"发送移动消息失败: {e}")

    # def send_player_update(self):
    #     """发送玩家属性更新"""
    #     if self.connected and self.room_id and self.player_sprite:
    #         self.send_msg('player_update', {
    #             'roomId': self.room_id,
    #             'attributes': self.player_sprite
    #         })

    def send_chat(self, message: str):
        """发送聊天消息"""
        if self.connected and self.room_id and message.strip():
            self.send_msg('chat_message', {
                'roomId': self.room_id,
                'message': message.strip()
            })

    def change_room(self, new_room_id: str):
        """
        切换到新房间
        Args:
            new_room_id: 新房间ID
        """
        if self.connected:
            GameToastManager.add_message(f"正在切换到场景: {new_room_id}")
            self.disconnect(True)

        self.connect_sync(new_room_id)
        GameToastManager.add_message(f"已切换到场景: {new_room_id}")

    def get_player(self, player_id: str) -> Optional[Dict[str, Any]]:
        """获取指定玩家信息"""
        return self.players.get(player_id)

    def get_all_players(self) -> List[Dict[str, Any]]:
        """获取所有玩家列表"""
        return list(self.players.values())

    def get_player_count(self) -> int:
        """获取玩家数量"""
        return len(self.players)

    def is_self(self, player_id: str) -> bool:
        """判断是否是当前玩家"""
        return player_id == self.player_id

    def get_self(self) -> Optional[Dict[str, Any]]:
        """获取当前玩家信息"""
        return self.players.get(self.player_id) if self.player_id else None

    def render(self):
        """
        更新客户端状态（在游戏循环中调用）
        只在位置变化时发送移动消息
        """
        if self.connected and self.sprite:
            # current_pos = self.sprite.position

            # 检查位置是否变化，避免频繁发送
            # if self._last_sent_pos != current_pos:
            #     self.send_move(current_pos[0], current_pos[1])
            #     self._last_sent_pos = current_pos.copy()
            try:
                for re_user in self.remote_player.keys():
                    self.remote_player[re_user].render()

                for re_user in self.remote_player.keys():
                    self.remote_player[re_user].render_mask()
            except RuntimeError as re:
                pass

    def send_stop(self):
        """
        发送停止移动的指令到服务器
        如果连接断开会尝试重连，并在重连后返回
        如果发送过程中出现异常，会捕获并处理特定的异常情况
        """
        if not self.sio.connected:
            self.reconnect()  # 实现重连逻辑
            return

        try:
            # 构造并发送移动消息，使用特殊坐标(-99, -99)表示停止
            self.send_msg('player_move', {
                'roomId': self.room_id,  # 房间ID
                'x': -99,  # X坐标，使用-99表示停止
                'y': -99,  # Y坐标，使用-99表示停止
                "direction": self.sprite.direction,  # 角色朝向
                "sta": SpriteState.IDLE.value  # 角色状态，设置为空闲状态
            })
        except socketio.exceptions.BadNamespaceError:
            # 处理命名空间错误，通常是网络连接问题
            GameToastManager.add_message("网络连接异常，正在重连...")
            self.reconnect()
        except AttributeError as ae:
            # 处理属性错误，特别是当sprite对象不存在时
            if self.sprite is None:
                self.sprite = self.gm.get("主角")  # 尝试重新获取主角对象
            GameLogManager.log_service_error(ae)  # 记录错误信息

    def reconnect(self, max_retries=3):
        for _ in range(max_retries):
            try:
                self.sio.disconnect()
                self.connect_sync(self.room_id)
                return True
            except Exception as e:
                GameLogManager.log_service_error(f"重连失败: {e}")
                time.sleep(1)
        return False


class RemotePlayerSprite(SpriteBase):
    """远程玩家精灵类（使用世界坐标）"""
    def __init__(self, player_data: Dict[str, Any], gm: any):
        super().__init__()
        self.player_data = player_data
        self.client_id = player_data.get("id")
        self.gm: "GameManager" = gm
        self.is_remote = True  # 标记为远程玩家
        # 添加Animator组件
        self.animator = Animator(self.gm)

        # 从网络数据初始化
        self._init_from_network_data(player_data)
        self.load_animations()

    def _init_from_network_data(self, sprite_data: Dict[str, Any]):
        """从网络数据初始化"""
        self.UID = sprite_data.get('UID')
        self.name = sprite_data.get('name')
        # self.eff_animator_stick = Animator(GameManager)

        self.direction = sprite_data.get('direction')  # 朝向的初始值，默认为右下方向
        self.position = sprite_data.get('position')

        # 单帧宽度
        self.frame_width = sprite_data.get('frame_width')
        self.frame_timer = sprite_data.get('frame_timer')
        self.frame_delay = sprite_data.get('frame_delay')  # 每 2 帧更新一次

        self.stand_model = sprite_data.get("stand_model")
        self.move_model = sprite_data.get("move_model")
        self.stand_direction = sprite_data.get("stand_direction")
        self.move_direction = sprite_data.get("move_direction")
        self.stand_texture = sprite_data.get("stand_texture")
        self.move_texture = sprite_data.get("move_texture")
        self.level = sprite_data.get('level')

        self.width = sprite_data.get('width')
        self.height = sprite_data.get('height')
        self.current_path = sprite_data.get('current_path')
        self.current_path_index = 0  # 当前路径索引
        # 服务器传递的位置就是世界坐标. 这里不需要在进行转换. 直接用就行.  后续的移动传递的是寻路的路径. 就需要在当前客户端进行转换了
        self.__pos = self.position

    def update_from_network(self, sprite_data: Dict[str, Any]):
        """从网络数据更新"""
        self._init_from_network_data(sprite_data)

    def load_animations(self):
        """一次性加载NPC的站立和移动动画（不做偏移量计算）"""

        # 加载每一帧的图像
        def load_frames(texture, model, directions):
            frames_by_dir = {}
            if not texture:
                return frames_by_dir
            image = SourceManager.load(os.path.join(SourceManager.ui_npc_path, f"{texture}.png"))
            cols, rows = model
            fw, fh = image.get_width() // cols, image.get_height() // rows

            # 遍历每个方向
            for dir_val in directions:
                d_idx = dir_val - 1
                if d_idx >= rows:
                    continue
                # 自动忽略透明像素
                first_frame = image.subsurface((0, d_idx * fh, fw, fh))
                self.rect = first_frame.get_bounding_rect()
                base_offset_x = self.rect.x
                base_offset_y = self.rect.y

                # 遍历每一列
                frames_by_dir[d_idx] = [
                    image.subsurface((
                        col * fw + base_offset_x,  # 使用基准偏移量
                        d_idx * fh + base_offset_y,  # 使用基准偏移量
                        self.rect.width,  # 使用bounding rect的宽度
                        self.rect.height  # 使用bounding rect的高度
                    ))
                    for col in range(cols)
                ]
            return frames_by_dir

        # 一次性加载两种动画
        stand_frames = load_frames(self.stand_texture, self.stand_model, self.stand_direction)
        move_frames = load_frames(self.move_texture, self.move_model, self.move_direction)

        # 添加到 Animator
        for dir_idx, frames in stand_frames.items():
            self.animator.add_animation(f"stand_{dir_idx}", len(frames), 2, frames)
        for dir_idx, frames in move_frames.items():
            self.animator.add_animation(f"move_{dir_idx}", len(frames), 3, frames)

        # 默认播放站立动画
        self.animator.play(f"stand_{self.direction}", speed=0.15)

    def __str__(self):
        return f"网友:{self.name}"

    def render(self):
        self.move()
        camera_pos = self.gm.game_camera.get_position()
        render_x = self.__pos[0] - camera_pos[0] - self.width / 2
        render_y = self.__pos[1] - camera_pos[1] - self.height

        # 更新动画
        self.animator.update(0.5)  # 以 60fps 作为基准
        # 使用Animator获取当前帧
        current_frame = self.animator.get_frame()
        if current_frame:
            # 使用统一的偏移量进行渲染
            self.gm.game_win.blit(current_frame, (int(render_x), int(render_y)))

    def render_mask(self):
        camera_pos = self.gm.game_camera.get_position()
        render_x = self.__pos[0] - camera_pos[0] - self.width / 2
        render_y = self.__pos[1] - camera_pos[1] - self.height

        # 渲染人物名字
        GameFont.render_line_text(self.name,
                                  int(render_x + self.width / 2 -
                                      GameFont.get_text_size(f"{self.name}")[0] / 2),
                                  render_y - 10, True, font_color="#00CD00")

    # def destroy(self):
    #     pass
    #     # self.gm.remove(f"remote_player_{self.client_id}")

    def move(self):
        """根据路径数组移动角色"""
        # 检查是否有有效路径
        if not self.current_path or self.current_path_index >= len(self.current_path):
            self.current_path = None  # 清除已完成路径
            self.current_path_index = 0
            return

        # 当前目标点（世界像素坐标）
        target_x, target_y = self.current_path[self.current_path_index]

        # 计算x轴和y轴的移动距离
        dx = target_x - self.position[0]  # 使用世界坐标计算
        dy = target_y - self.position[1]

        # 计算当前位置到目标点的直线距离
        distance = (dx ** 2 + dy ** 2) ** 0.5

        # 防止除零错误
        if distance <= 0.1:  # 极小距离阈值
            self.position[0], self.position[1] = target_x, target_y
            self.current_path_index += 1
            self.__pos = [self.position[0], self.position[1]]  # 同步内部位置
            return

        # 如果角色已经到达或非常接近目标点
        if distance <= self.move_speed:
            self.position[0], self.position[1] = target_x, target_y
            self.__pos = [self.position[0], self.position[1]]  # 同步内部位置
            self.current_path_index += 1
            return

        # 按速度移动（归一化方向向量）
        move_x = (dx / distance) * self.move_speed
        move_y = (dy / distance) * self.move_speed

        # 更新世界坐标和渲染坐标
        self.position[0] += round(move_x)
        self.position[1] += round(move_y)
        self.__pos = [self.position[0], self.position[1]]  # 保持同步
