#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : ChatSystem.py
@Desc    : 左下角聊天框与后续GM/联网聊天入口
"""

import html
import os
import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import uuid4

import pygame

from src.manager.GameLogManger import GameLogManager
from src.manager.SourceManager import SourceManager
from src.system.GameDialog import GameDialog
from src.system.GameToast import GameToastManager

if TYPE_CHECKING:
    from src.manager.GameManager import GameManager


@dataclass
class ChatMessage:
    channel: str
    sender: str
    content: str
    color: str = "#FFFFFF"
    item_links: list[dict] = field(default_factory=list)


class ChatSystem:
    dialog_key = "游戏聊天框"
    input_id = "chat_input"
    max_messages = 80
    visible_messages = 4

    quality_names = {"white", "green", "blue", "gold", "purple"}

    channel_colors = {
        "系统": "#FFE08A",
        "一般": "#FFFFFF",
        "本地": "#FFFFFF",
        "队伍": "#7DFF9A",
        "诸侯": "#D7A8FF",
        "世界": "#8AD7FF",
        "GM": "#FF9B9B",
    }
    channel_order = ["一般", "队伍", "诸侯", "世界", "系统"]
    channel_labels = {
        "一般": "一般频道",
        "队伍": "队伍频道",
        "诸侯": "诸侯频道",
        "世界": "世界频道",
        "系统": "系统频道",
    }
    face_token_pattern = re.compile(r"\[微笑([1-9]\d?)\]|\[f([1-9]\d?)\]")
    face_cols = 13
    face_rows = 13
    face_size = 32
    face_display_size = 20
    face_panel_display_size = 32

    def __init__(self, gm: "GameManager"):
        self.gm = gm
        self.dialog = GameDialog(gm, self.dialog_key)
        self.face_dialog = GameDialog(gm, "聊天表情面板")
        self.item_detail_dialog = GameDialog(gm, "聊天道具信息")
        self.messages: list[ChatMessage] = []
        self.pending_item_links: list[dict] = []
        self.item_snapshots: dict[str, dict] = {}
        self.input_history: list[str] = []
        self.history_index: int | None = None
        self.history_draft = ""
        self.message_scroll = 0
        self.current_channel = "一般"
        self.show_face_panel = False
        self.face_cache_name = f"chat_faces_{self.face_cols}x{self.face_rows}_{self.face_size}"
        self.face_cache_dir = os.path.join(SourceManager.cfg_task_path, self.face_cache_name)
        self.__faces_ready = False
        self.template_path = os.path.join(SourceManager.cfg_ui_path, "game_chat.html")
        self.generated_path = os.path.join(SourceManager.cfg_task_path, "__game_chat_generated.html")
        self.face_panel_path = os.path.join(SourceManager.cfg_task_path, "__chat_face_panel_generated.html")
        self.item_detail_path = os.path.join(SourceManager.cfg_task_path, "__chat_item_detail_generated.html")

    def show(self):
        if not os.path.exists(self.template_path):
            GameToastManager.add_message(f"聊天框模板不存在:{self.template_path}")
            GameLogManager.log_service_error(f"聊天框模板不存在:{self.template_path}")
            return

        if not self.messages:
            _msg = ["抵制不良游戏，拒绝盗版游戏。","注意自我保护，谨防受骗上当。","适度游戏益脑，沉迷游戏伤身。","合理安排时间，享受健康生活。"]
            for m in _msg:
                self.add_message( "系统","", m, render=False)
        self.render()

    def close(self):
        self.dialog.close_dialog()
        self.face_dialog.close_dialog()

    def render(self):
        current_input_state = ""
        had_focus = False
        if self.dialog.visible():
            current_input_state = self.dialog.get_component_state(self.input_id) or self.dialog.get_val(self.input_id) or ""
            had_focus = self.dialog.has_focus()

        with open(self.template_path, "r", encoding="utf-8") as f:
            template = f.read()

        message_html = self.__build_messages_html()
        channel_html = self.__build_channel_tabs_html()
        face_button_src = self.__face_img_src(1)
        channel_label = html.escape(self.channel_labels.get(self.current_channel, self.current_channel))
        with open(self.generated_path, "w", encoding="utf-8") as f:
            f.write(
                template
                .replace("{{CHAT_MESSAGES}}", message_html)
                .replace("{{CHANNEL_TABS}}", channel_html)
                .replace("{{FACE_BUTTON_SRC}}", face_button_src)
                .replace("{{FACE_PANEL}}", "")
                .replace("{{CURRENT_CHANNEL}}", channel_label)
            )

        event_dict = self.__build_dialog_events()
        self.dialog.show_dialog(
            self.generated_path,
            render_x=8,
            render_y=35,
            overwrite_path=True,
            dialog_event_dict=event_dict,
            loc="bottom_left",
            load_val={self.input_id: current_input_state},
            listen_keyboard=lambda: self.dialog.has_focus(),
            esc_close=False,
        )
        if had_focus:
            self.dialog.focus(self.input_id)

    def send_current_text(self):
        self.send_text(self.dialog.get_val(self.input_id) or "")

    def send_text(self, text: str):
        text = (text or "").strip()
        if not text:
            return

        self.__push_input_history(text)
        self.dialog.set_val(self.input_id, "")
        if text.startswith("-"):
            self.pending_item_links.clear()
            self.__handle_command(text[1:].strip())
            self.dialog.focus(self.input_id)
            return

        player = self.gm.get("主角")
        sender = getattr(player, "name", "") or "我"
        item_links = self.__consume_pending_item_links(text)
        self.add_message(self.current_channel, sender, text, item_links=item_links)
        self.__send_network_message(text, item_links)
        self.dialog.focus(self.input_id)

    def switch_input_history(self, direction: str, current_text: str):
        if not self.input_history:
            return None

        if self.history_index is None:
            self.history_draft = current_text or ""
            self.history_index = len(self.input_history)

        if direction == "up":
            self.history_index = max(0, self.history_index - 1)
            return self.input_history[self.history_index]

        self.history_index = min(len(self.input_history), self.history_index + 1)
        if self.history_index >= len(self.input_history):
            self.history_index = None
            return self.history_draft
        return self.input_history[self.history_index]

    def __push_input_history(self, text: str):
        text = (text or "").strip()
        if not text:
            return
        if not self.input_history or self.input_history[-1] != text:
            self.input_history.append(text)
        self.input_history = self.input_history[-50:]
        self.history_index = None
        self.history_draft = ""

    def scroll_messages_up(self):
        max_scroll = self.__max_message_scroll()
        if self.message_scroll >= max_scroll:
            return False
        self.message_scroll = min(max_scroll, self.message_scroll + 1)
        self.render()
        return False

    def scroll_messages_down(self):
        if self.message_scroll <= 0:
            return False
        self.message_scroll = max(0, self.message_scroll - 1)
        self.render()
        return False

    def add_message(self, channel: str, sender: str, content: str, render: bool = True,
                    item_links: list[dict] | None = None):
        color = self.channel_colors.get(channel, "#FFFFFF")
        message = ChatMessage(channel, sender, content, color, item_links or [])
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
        if self.message_scroll > 0:
            self.message_scroll = min(self.message_scroll + 1, self.__max_message_scroll())
        self.__remember_item_snapshots(message.item_links)
        self.__prune_item_snapshots()
        if render:
            self.render()

    def receive_network_message(self, sender: str, content: str, channel: str = "世界",
                                item_links: list[dict] | None = None):
        self.add_message(channel, sender, content, item_links=item_links)

    def __send_network_message(self, text: str, item_links: list[dict]):
        network_client = self.gm.get("network_client") if hasattr(self.gm, "get") else None
        if network_client is None or not getattr(network_client, "connected", False):
            return
        if not hasattr(network_client, "send_chat"):
            return
        try:
            network_client.send_chat(text, channel=self.current_channel, item_links=item_links)
        except TypeError:
            network_client.send_chat(text)
        except Exception as exc:
            GameLogManager.log_service_error(f"发送聊天消息失败:{exc}")

    def switch_channel(self, channel: str):
        if channel not in self.channel_order:
            return False
        self.current_channel = channel
        self.show_face_panel = False
        self.render()
        self.dialog.focus(self.input_id)
        return False

    def toggle_face_panel(self):
        input_had_focus = self.dialog.has_focus()
        self.show_face_panel = not self.show_face_panel
        if self.show_face_panel:
            self.render_face_panel()
        else:
            self.face_dialog.close_dialog()
        self.dialog.focus(self.input_id, move_cursor_to_end=not input_had_focus)
        return False

    def insert_face(self, face_index: int):
        if face_index < 1 or face_index > self.face_cols * self.face_rows:
            return False
        if not self.dialog.visible():
            self.show()
        if not self.dialog.has_focus():
            self.dialog.focus(self.input_id, move_cursor_to_end=True)
        self.dialog.insert_text(self.input_id, self.__face_token(face_index))
        self.show_face_panel = False
        self.face_dialog.close_dialog()
        self.dialog.focus(self.input_id)
        return False

    def render_face_panel(self):
        with open(self.face_panel_path, "w", encoding="utf-8") as f:
            f.write(self.__build_face_panel_html())

        self.face_dialog.show_dialog(
            self.face_panel_path,
            render_x=10,
            render_y=35,
            overwrite_path=True,
            dialog_event_dict=self.__build_dialog_events(),
            loc="bottom_left",
            listen_keyboard=False,
            esc_close=True,
        )

    def insert_item_link(self, item):
        """把背包道具插入聊天输入框, 发送时再生成快照."""
        if item is None:
            return False
        if not self.dialog.visible():
            self.show()

        item_name = getattr(item, "name", "") or "未知道具"
        label = f"[{item_name}]"
        self.pending_item_links.append({
            "label": label,
            "item": item,
            "uid": getattr(item, "UID", ""),
        })

        current_input = self.dialog.get_val(self.input_id) or ""
        separator = "" if not current_input or current_input.endswith((" ", "　")) else " "
        self.dialog.insert_text(self.input_id, f"{separator}{label}")
        self.dialog.focus(self.input_id)
        GameToastManager.add_message(f"已插入道具:{item_name}")
        return True

    def __handle_command(self, command: str):
        if not command:
            self.add_message("系统", "GM", "请输入命令, -help 查看帮助")
            return

        args = command.split()
        cmd = args[0].lower()
        if cmd in ("help", "?"):
            self.add_message("系统", "GM", "-add money 数量 | -add item ID [数量] [强化] [品质] [秒] | -moveto [地图ID] 格子X,格子Y")
            return

        if cmd == "clear":
            self.messages.clear()
            self.add_message("系统", "GM", "聊天记录已清空")
            return

        if cmd == "add":
            self.__gm_add(args[1:])
            return

        if cmd == "moveto":
            self.__gm_moveto(args[1:])
            return

        self.add_message("系统", "GM", f"未知命令: -{command}")

    def __gm_add(self, args: list[str]):
        if not args:
            self.add_message("系统", "GM", "用法: -add money 999 或 -add item 3 [数量] [强化] [品质] [秒]")
            return

        add_type = args[0].lower()
        if add_type in ("money", "gold"):
            self.__gm_add_money(args)
            return

        if add_type == "item":
            self.__gm_add_item(args)
            return

        self.add_message("系统", "GM", f"未知添加类型: {args[0]}")

    def __gm_add_money(self, args: list[str]):
        if len(args) < 2:
            self.add_message("系统", "GM", "用法: -add money 999")
            return
        try:
            amount = int(args[1])
        except ValueError:
            self.add_message("系统", "GM", "金币数量必须是整数")
            return

        player = self.gm.get("主角")
        if not player or not getattr(player, "bag", None):
            self.add_message("系统", "GM", "当前没有可操作的角色")
            return
        player.bag.money = max(0, player.bag.money + amount)
        player.bag.update_blit = True
        self.add_message("系统", "GM", f"金币变化 {amount:+d}, 当前金币 {player.bag.money}")

    def __gm_add_item(self, args: list[str]):
        if len(args) < 2:
            self.add_message("系统", "GM", "用法: -add item 3 [数量] [强化等级] [white|green|blue|gold|purple] [有效秒数]")
            return

        item_id = args[1]
        extras = args[2:]
        if len(extras) > 4:
            self.add_message("系统", "GM", "参数过多, 用法: -add item ID [数量] [强化等级] [品质] [有效秒数]")
            return

        count = self.__parse_optional_int(extras, 0, 1, "道具数量必须是整数")
        if count is None:
            return
        if count <= 0:
            self.add_message("系统", "GM", "道具数量必须大于 0")
            return

        enhance_level = self.__parse_optional_int(extras, 1, 0, "强化等级必须是整数")
        if enhance_level is None:
            return
        if enhance_level < 0:
            self.add_message("系统", "GM", "强化等级不能小于 0")
            return

        quality = "white"
        if len(extras) >= 3:
            quality = extras[2].lower()
            if quality not in self.quality_names:
                self.add_message("系统", "GM", "品质必须是 white/green/blue/gold/purple")
                return
        duration = self.__parse_optional_int(extras, 3, 0, "有效期必须是秒数")
        if duration is None:
            return
        if duration < 0:
            self.add_message("系统", "GM", "有效期不能小于 0")
            return

        player = self.gm.get("主角")
        if not player or not getattr(player, "bag", None):
            self.add_message("系统", "GM", "当前没有可操作的角色")
            return

        expire_time = int(time.time()) + duration if duration > 0 else 0
        if not player.bag.get_target_item_count(item_id, count, quality, enhance_level, expire_time):
            self.add_message("系统", "GM", f"添加失败: 背包空间不足或道具 {item_id} 不存在")
            return

        item_data = SourceManager.get_csv("items", str(item_id))
        if item_data is None:
            self.add_message("系统", "GM", f"添加失败: 道具 {item_id} 不存在")
            return

        before_count = self.__count_bag_item(player.bag, item_id)
        self.__add_item_to_bag(player.bag, item_data, item_id, count, expire_time, quality, enhance_level)
        player.bag.update_blit = True
        after_count = self.__count_bag_item(player.bag, item_id)

        if after_count <= before_count:
            self.add_message("系统", "GM", f"添加失败: 道具 {item_id} 未写入背包")
            return

        expire_text = f", 有效期 {duration} 秒" if duration > 0 else ""
        enhance_text = f", 强化 +{enhance_level}" if enhance_level > 0 else ""
        self.add_message("系统", "GM", f"已添加道具 {item_id} x{after_count - before_count}{enhance_text}, 品质 {quality}{expire_text}")

    def __gm_moveto(self, args: list[str]):
        if not args:
            self.add_message("系统", "GM", "用法: -moveto 格子X,格子Y 或 -moveto 地图ID 格子X,格子Y")
            return

        from src.manager.GameMapManager import GameMapManager

        map_id = None
        coord_text = ""
        if len(args) == 1:
            coord_text = args[0]
        elif "," in args[1]:
            map_id = args[0]
            coord_text = args[1]
        elif len(args) >= 3:
            map_id = args[0]
            coord_text = f"{args[1]},{args[2]}"
        else:
            self.add_message("系统", "GM", "坐标格式错误, 示例: -moveto 1024 92,78")
            return

        pos = self.__parse_coord(coord_text)
        if pos is None:
            self.add_message("系统", "GM", "坐标格式错误, 请使用 x,y")
            return

        grid_x, grid_y = pos
        world_x, world_y = self.__grid_to_world_pos(grid_x, grid_y)
        player = self.gm.get("主角")
        if not player:
            self.add_message("系统", "GM", "当前没有可移动的角色")
            return

        try:
            move_result = GameMapManager.move_player_to(map_id, world_x, world_y)
            result_map_id = move_result.get("map_id") or GameMapManager.map_id
            result_grid_x = move_result.get("grid_x", grid_x)
            result_grid_y = move_result.get("grid_y", grid_y)
            if move_result.get("mode") == "network":
                prefix = "已通知服务端移动到"
            elif move_result.get("mode") == "map_changed":
                prefix = "已移动到地图"
            else:
                prefix = "已移动到当前地图"
            adjusted_text = " (已避开障碍点)" if move_result.get("adjusted") else ""
            self.add_message("系统", "GM", f"{prefix} {result_map_id}: {result_grid_x},{result_grid_y}{adjusted_text}")
        except Exception as exc:
            self.add_message("系统", "GM", f"移动失败: {exc}")

    @staticmethod
    def __parse_coord(coord_text: str):
        parts = coord_text.split(",", 1)
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None

    @staticmethod
    def __grid_to_world_pos(grid_x: int, grid_y: int):
        from src.manager.GameManager import GameManager

        return grid_x * GameManager.game_box_size, grid_y * GameManager.game_box_size

    def __parse_optional_int(self, args: list[str], index: int, default: int, error_message: str):
        if len(args) <= index:
            return default
        try:
            return int(args[index])
        except ValueError:
            self.add_message("系统", "GM", error_message)
            return None

    @staticmethod
    def __count_bag_item(bag, item_id: str):
        return sum(int(item.count or 0) for item in bag.get_item_by_id(item_id))

    @staticmethod
    def __add_item_to_bag(bag, item_data: dict, item_id: str, count: int, expire_time: int, quality: str,
                          enhance_level: int):
        if item_data.get("可重叠摆放") != "1":
            bag.add_item(item_id, count, expire_time=expire_time, quality=quality, enhance_level=enhance_level)
            return

        try:
            max_count = int(item_data.get("最大使用次数", count) or count)
        except (TypeError, ValueError):
            max_count = count
        max_count = max(1, max_count)
        remaining = count
        while remaining > 0:
            add_count = min(remaining, max_count)
            bag.add_item(item_id, add_count, expire_time=expire_time, quality=quality, enhance_level=enhance_level)
            remaining -= add_count

    def __build_messages_html(self):
        if not self.messages:
            return '<p color="#888888" font-size="12">暂无消息</p>'

        lines = []
        for msg in self.__visible_messages():
            if msg.item_links:
                lines.append(self.__build_rich_message_html(msg))
                continue
            lines.append(self.__build_rich_message_html(msg))
        return "\n            ".join(lines)

    def __build_dialog_events(self):
        event_dict = {
            "chat_send": self.send_current_text,
            "chat_submit": self.send_text,
            "chat_history": self.switch_input_history,
            "chat_faces_toggle": self.toggle_face_panel,
            "__scroll_up": self.scroll_messages_up,
            "__scroll_down": self.scroll_messages_down,
        }
        for channel in self.channel_order:
            event_dict[f"chat_channel_{channel}"] = lambda ch=channel: self.switch_channel(ch)
        for face_index in range(1, self.face_cols * self.face_rows + 1):
            event_dict[f"chat_face_{face_index}"] = lambda idx=face_index: self.insert_face(idx)
        for msg in self.__visible_messages():
            for link in msg.item_links:
                snapshot = link.get("snapshot") or self.item_snapshots.get(link.get("snapshot_id"))
                if not snapshot:
                    continue
                event_key = self.__item_event_key(link)
                event_dict[event_key] = lambda snap=snapshot: self.show_item_snapshot(snap)
        return event_dict

    def __visible_messages(self):
        if len(self.messages) <= self.visible_messages:
            return self.messages
        max_scroll = self.__max_message_scroll()
        self.message_scroll = max(0, min(self.message_scroll, max_scroll))
        end = len(self.messages) - self.message_scroll
        start = max(0, end - self.visible_messages)
        return self.messages[start:end]

    def __max_message_scroll(self):
        return max(0, len(self.messages) - self.visible_messages)

    def __consume_pending_item_links(self, text: str):
        if not self.pending_item_links:
            return []

        item_links = []
        remaining_text = text
        for pending in self.pending_item_links:
            label = pending.get("label", "")
            if not label or label not in remaining_text:
                continue
            snapshot = self.__snapshot_item(pending.get("item"))
            snapshot_id = uuid4().hex[:10]
            snapshot["snapshot_id"] = snapshot_id
            self.item_snapshots[snapshot_id] = snapshot
            item_links.append({
                "label": label,
                "snapshot_id": snapshot_id,
                "snapshot": snapshot,
            })
            remaining_text = remaining_text.replace(label, "", 1)

        self.pending_item_links.clear()
        return item_links

    def __build_rich_message_html(self, msg: ChatMessage):
        segments = [("text", f"[{msg.channel}] {msg.sender}:", None)]
        content = msg.content or ""
        cursor = 0
        for link in msg.item_links:
            label = link.get("label", "")
            if not label:
                continue
            link_pos = content.find(label, cursor)
            if link_pos < 0:
                continue
            if link_pos > cursor:
                segments.append(("text", content[cursor:link_pos], None))
            segments.append(("link", label, link))
            cursor = link_pos + len(label)
        if cursor < len(content):
            segments.append(("text", content[cursor:], None))

        segments = self.__expand_face_segments(segments)
        children = []
        for kind, text, link in segments:
            if not text:
                continue
            if kind == "face":
                face_src = self.__face_img_src(int(text))
                if face_src:
                    children.append(
                        f'<img src="{face_src}" width="{self.face_display_size}" height="{self.face_display_size}" img-size="{self.face_display_size},{self.face_display_size}" />'
                    )
                else:
                    children.append(
                        f'<p width="48" color="{msg.color}" font-size="12">{html.escape(self.__face_token(int(text)))}</p>'
                    )
            elif kind == "link" and link:
                safe_text = html.escape(str(text))
                width = self.__chat_segment_width(str(text))
                event_key = self.__item_event_key(link)
                children.append(
                    f'<a width="{width}" color="#64C8FF" font-size="12" @click="{event_key}">{safe_text}</a>'
                )
            else:
                safe_text = html.escape(str(text))
                width = self.__chat_segment_width(str(text))
                children.append(f'<p width="{width}" color="{msg.color}" font-size="12">{safe_text}</p>')

        if not children:
            return f'<p color="{msg.color}" font-size="12">{html.escape(content)}</p>'
        return f'<row>{"".join(children)}</row>'

    def __expand_face_segments(self, segments: list[tuple[str, str, dict | None]]):
        expanded = []
        for kind, text, link in segments:
            if kind != "text":
                expanded.append((kind, text, link))
                continue
            cursor = 0
            for match in self.face_token_pattern.finditer(str(text)):
                face_index = int(match.group(1) or match.group(2))
                if face_index > self.face_cols * self.face_rows:
                    continue
                if match.start() > cursor:
                    expanded.append(("text", str(text)[cursor:match.start()], None))
                expanded.append(("face", str(face_index), None))
                cursor = match.end()
            if cursor < len(str(text)):
                expanded.append(("text", str(text)[cursor:], None))
        return expanded

    def __build_channel_tabs_html(self):
        buttons = []
        for channel in self.channel_order:
            label = self.channel_labels.get(channel, channel)
            state = "active" if channel == self.current_channel else "idle"
            if channel == self.current_channel:
                label = f">{label}"
            color = "#FFE08A" if channel == self.current_channel else "#FFFFFF"
            buttons.append(
                f'<button id="chat_channel_{channel}_{state}" width="68" height="24" color="{color}" @click="chat_channel_{channel}">{html.escape(label)}</button>'
            )
        return "\n        ".join(buttons)

    def __build_face_panel_html(self):
        self.__ensure_face_assets()
        cells = []
        for face_index in range(1, self.face_cols * self.face_rows + 1):
            face_src = self.__face_img_src(face_index)
            cells.append(
                f'<li id="chat_face_{face_index}" width="{self.face_panel_display_size}" height="{self.face_panel_display_size}" margin="2" padding="0" tight="true" background-color="#050505" @click="chat_face_{face_index}">'
                f'<img src="{face_src}" width="{self.face_panel_display_size}" height="{self.face_panel_display_size}" img-size="{self.face_panel_display_size},{self.face_panel_display_size}" />'
                '</li>'
            )

        return "\n".join([
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head><meta charset="UTF-8"><title>Faces</title></head>',
            '<body>',
            '<div id="app" width="306" height="462" close="false" padding="8 8 8 8" background-color="#050505">',
            # '<div id="app" width="256" height="256" close="false" padding="8 8 8 8" background-color="#050505">',
            '<ul width="256" margin="2">',
            *cells,
            '</ul>',
            '</div>',
            '</body>',
            '</html>',
        ])

    def __ensure_face_assets(self):
        if self.__faces_ready:
            return
        face_path = os.path.join(SourceManager.ui_system_path, "faces.png")
        if not os.path.exists(face_path):
            GameLogManager.log_service_error(f"聊天表情图不存在:{face_path}")
            self.__faces_ready = True
            return

        os.makedirs(self.face_cache_dir, exist_ok=True)
        try:
            sheet = SourceManager.load(face_path)
            target_sheet_size = (self.face_cols * self.face_size, self.face_rows * self.face_size)
            if sheet.get_size() != target_sheet_size:
                sheet = pygame.transform.smoothscale(sheet, target_sheet_size)
            for face_index in range(1, self.face_cols * self.face_rows + 1):
                target = os.path.join(self.face_cache_dir, f"face_{face_index}.png")
                if os.path.exists(target) and pygame.image.load(target).get_size() == (self.face_size, self.face_size):
                    continue
                col = (face_index - 1) % self.face_cols
                row = (face_index - 1) // self.face_cols
                rect = pygame.Rect(col * self.face_size, row * self.face_size, self.face_size, self.face_size)
                pygame.image.save(sheet.subsurface(rect), target)
            self.__faces_ready = True
        except Exception as exc:
            self.__faces_ready = True
            GameLogManager.log_service_error(f"生成聊天表情缓存失败:{exc}")

    def __face_img_src(self, face_index: int):
        if face_index < 1 or face_index > self.face_cols * self.face_rows:
            return ""
        self.__ensure_face_assets()
        rel_path = f"{self.face_cache_name}/face_{face_index}.png"
        if not os.path.exists(os.path.join(SourceManager.cfg_task_path, rel_path)):
            return ""
        return rel_path

    @staticmethod
    def __face_meaning(face_index: int):
        return "微笑"

    def __face_token(self, face_index: int):
        return f"[{self.__face_meaning(face_index)}{face_index}]"

    @staticmethod
    def __chat_segment_width(text: str):
        width = 8
        for ch in text:
            width += 12 if ord(ch) > 127 else 7
        return max(18, min(width, 300))

    @staticmethod
    def __item_event_key(link: dict):
        return f"chat_item_{link.get('snapshot_id', '')}"

    def __snapshot_item(self, item):
        item_id = str(getattr(item, "ID", "") or "")
        item_cfg = SourceManager.get_csv("items", item_id) if item_id else {}
        item_cfg = item_cfg or {}
        display_attrs = []
        if item is not None and hasattr(item, "get_display_attrs"):
            try:
                display_attrs = [{"text": text, "color": color} for text, color in item.get_display_attrs()]
            except Exception as exc:
                GameLogManager.log_service_debug(f"生成聊天道具属性快照失败:{exc}")

        return {
            "item_id": item_id,
            "uid": str(getattr(item, "UID", "") or ""),
            "name": str(item.get_display_name() if hasattr(item, "get_display_name") else getattr(item, "name", "") or "未知道具"),
            "count": int(getattr(item, "count", 1) or 1),
            "quality": str(getattr(item, "quality", "") or "white"),
            "enhance_level": int(getattr(item, "enhance_level", 0) or 0),
            "type_name": self.__get_item_type_name(item),
            "level": int(getattr(item, "level_requirement", getattr(item, "level", 1)) or 0),
            "bind": bool(getattr(item, "bind", False)),
            "can_trade": bool(getattr(item, "can_trade", False)),
            "can_stack": bool(getattr(item, "can_stack", False)),
            "money": int(getattr(item, "money", 0) or 0),
            "points": int(getattr(item, "points", 0) or 0),
            "expire_time": int(getattr(item, "expire_time", 0) or 0),
            "description": str(getattr(item, "description", "") or "暂无说明"),
            "display_attrs": display_attrs,
            "icon": str(item_cfg.get("Icon", "") or ""),
            "created_at": int(time.time()),
        }

    def __get_item_type_name(self, item):
        player = self.gm.get("主角")
        bag = getattr(player, "bag", None)
        if bag is not None and hasattr(bag, "get_item_type") and item is not None:
            try:
                return bag.get_item_type(item)
            except Exception:
                pass
        item_type = getattr(item, "type", "")
        sub_type = getattr(item, "sub_type", "")
        return f"{item_type}/{sub_type}" if item_type or sub_type else "未知类型"

    def show_item_snapshot(self, snapshot: dict | str):
        if isinstance(snapshot, str):
            snapshot = self.item_snapshots.get(snapshot)
        if not snapshot:
            GameToastManager.add_message("道具信息已失效")
            return

        with open(self.item_detail_path, "w", encoding="utf-8") as f:
            f.write(self.__build_item_detail_html(snapshot))

        self.item_detail_dialog.show_dialog(
            self.item_detail_path,
            render_x=10,
            render_y=38,
            overwrite_path=True,
            loc="middle",
            always_on_top=True,
            esc_close=True,
            listen_keyboard=False,
        )
        if self.dialog.visible():
            self.dialog.focus(self.input_id)

    def __build_item_detail_html(self, snapshot: dict):
        quality = str(snapshot.get("quality", "white") or "white")
        quality_color = self.__quality_color(quality)
        name = html.escape(str(snapshot.get("name", "未知道具")))
        item_id = html.escape(str(snapshot.get("item_id", "")))
        type_name = html.escape(str(snapshot.get("type_name", "未知类型")))
        description = html.escape(str(snapshot.get("description", "暂无说明")))
        expire_text = html.escape(self.__format_expire_time(int(snapshot.get("expire_time", 0) or 0)))
        bind_text = "已绑定" if snapshot.get("bind") else "未绑定"
        trade_text = "可交易" if snapshot.get("can_trade") else "不可交易"
        count = int(snapshot.get("count", 1) or 1)
        level = int(snapshot.get("level", 0) or 0)
        money = int(snapshot.get("money", 0) or 0)
        points = int(snapshot.get("points", 0) or 0)
        icon_src = self.__chat_item_icon_src(snapshot)

        body = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head><meta charset="UTF-8"><title>Item</title></head>',
            '<body>',
            '<div id="app" width="300" height="390" color="#FFFFFF" close="true" padding="0 14 24 14">',
            '<row>',
            f'<img src="{icon_src}" width="55" height="55" img-size="55,55" />',
            '<div width="198" height="96" padding="0">',
            f'<p color="{quality_color}" font-size="15">{name}</p>',
            f'<p color="#40C8FF" font-size="12">ID:{item_id}    {type_name}</p>',
            f'<p color="#FFFFFF" font-size="12">使用等级:{level}</p>',
            f'<p color="#B8FFB8" font-size="12">{bind_text}    {trade_text}</p>',
            '</div>',
            '</row>',
            '<hr color="#6E5C3A" />',
            f'<p color="#FFFFFF" font-size="12">数量:{count}</p>',
            f'<p color="#FFFFFF" font-size="12">有效期:{expire_text}</p>',
        ]
        if money > 0:
            body.append(f'<p color="#FFE08A" font-size="12">价值:{money} 金币</p>')
        if points > 0:
            body.append(f'<p color="#FFE08A" font-size="12">点数:{points}</p>')
        for attr in snapshot.get("display_attrs", []):
            attr_text = html.escape(str(attr.get("text", "")))
            if attr_text:
                body.append(f'<p color="{quality_color}" font-size="12">{attr_text}</p>')
        body.extend([
            '<hr color="#6E5C3A" />',
            f'<p color="#3BFF6A" font-size="12">{description}</p>',
        ])
        body.extend(['</div>', '</body>', '</html>'])
        return "\n".join(body)

    @staticmethod
    def __chat_item_icon_src(snapshot: dict):
        icon = str(snapshot.get("icon", "") or "").strip()
        if not icon:
            return ""
        icon_file = icon if icon.lower().endswith(".png") else f"{icon}.png"
        icon_path = os.path.join(SourceManager.ui_item_path, "help", icon_file)
        if not os.path.exists(icon_path):
            return ""
        return f"#ROOT_ITEM\\help\\{html.escape(icon_file)}"

    @staticmethod
    def __quality_color(quality: str):
        return {
            "white": "#FFFFFF",
            "green": "#32CD32",
            "blue": "#4AA3FF",
            "gold": "#FFD700",
            "purple": "#C87BFF",
        }.get(quality, "#FFFFFF")

    @staticmethod
    def __format_expire_time(expire_time: int):
        if expire_time <= 0:
            return "永久"
        if expire_time < int(time.time()):
            return "已过期"
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire_time))

    def __remember_item_snapshots(self, item_links: list[dict]):
        for link in item_links:
            snapshot_id = link.get("snapshot_id")
            snapshot = link.get("snapshot")
            if snapshot_id and snapshot:
                self.item_snapshots[snapshot_id] = snapshot

    def __prune_item_snapshots(self):
        alive_ids = {
            link.get("snapshot_id")
            for msg in self.messages
            for link in msg.item_links
            if link.get("snapshot_id")
        }
        self.item_snapshots = {
            snapshot_id: snapshot
            for snapshot_id, snapshot in self.item_snapshots.items()
            if snapshot_id in alive_ids
        }
