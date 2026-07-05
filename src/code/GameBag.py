#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：GameBag.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/6/17 10:55 
@Describe: 
"""
import copy
import pygame
from src.character.PickableItem import PickableItem
from src.code.Item import Item
from src.code.SpriteBase import SpriteBase
from src.manager.GameFont import GameFont
from src.manager.GameLogManger import GameLogManager
from src.manager.GameWorldManager import GameWorldManager
# from src.manager.GameLuaManager import GameLuaManager
from src.manager.SourceManager import SourceManager
from src.necessary.GameBattle import BattleManager
from src.render.GameUI import GameUI
from typing import TYPE_CHECKING, Any

from src.system.GameToast import GameToastManager

if TYPE_CHECKING:
    from src.manager.GameManager import GameManager
    from src.character.Player import Player


class GameBag:
    def __init__(self, gm):
        self.gm: GameManager = gm
        # 基础属性
        self.column = 5
        self.row = 4
        self.max_capacity = self.column * self.row  # 单页背包最大容量（格子数或重量上限）
        self.current_page = 1  # 当前背包的分页
        self.max_page = 3  # 最大分页数量
        self.update_blit = True
        # 道具类型配置
        self.__item_type = {}

        # 金币, 点卡
        self.money = 0
        self.point = 0

        self.items: list[list[list[Item | None]]] = [[[None for _ in range(self.column)] for _ in range(self.row)] for _
                                                     in range(self.max_page)]  # 存储物品对象或引用（列表形式）
        # 生成背包格子索引
        self.items_index_dict: dict[str, bool] = {
            f"{page}#{y}#{x}": False
            for page in range(self.max_page)
            for y in range(self.row)
            for x in range(self.column)
        }

        # 扩展功能属性
        # self.filterType = FilterType.ALL  # 当前物品分类筛选状态
        # self.sortOrder = SortOrder.ByID  # 物品排序规则

        game_ui: GameUI = self.gm.get("游戏UI")
        [_, rect, _] = game_ui.load_system_ui(f"{SourceManager.ui_system_path}/window_item.png",
                                              [250, 400],
                                              "middle",
                                              {
                                                  "name": "角色背包",
                                                  "mouse_down": self.mouse_down,
                                                  "right_mouse_down": self.right_mouse_down,
                                                  "mouse_up": self.mouse_up,
                                                  "mouse_move": self.mouse_move,
                                                  "mouse_double_click": self.mouse_double_click,
                                                  "mouse_out": self.mouse_out,
                                                  "update_event": self.render,
                                                  "drag": True,
                                                  "drag_rect": ["auto", "auto", "auto", "20"],
                                                  "bag_offset": pygame.Rect([25, 180, 200, 172]),
                                                  "bag_size": [45, 40],
                                                  "item_event": None,
                                                  "item_hover_event": None,
                                                  "update_blit": self.__update_blit,
                                                  "listen_keyboard": self.listen_keyboard
                                              })
        self.rect = rect
        # 加载 道具的 cursor 特效
        game_ui.load_system_ui(f"{SourceManager.ui_system_path}/item_cursor.png",
                               [80, 40],
                               "middle",
                               {
                                   "name": "item_cursor",
                                   "frame": {
                                       "size": 40,
                                       "count": 2,
                                       "index": 0,
                                       "time": 20,
                                       "timer": 15
                                   },
                               }, )
        # 选中道具的框
        game_ui.load_system_ui(f"{SourceManager.ui_system_path}/item_selected.png",
                               [40, 40],
                               "middle",
                               {
                                   "name": "item_selected",
                               }, sort=True)
        # 整理背包按钮
        [_, btn_sort_rect, btn_sort_params] = game_ui.load_system_ui(f"{SourceManager.ui_system_path}/button2.png",
                                                                     [240, 20],
                                                                     options=
                                                                     {
                                                                         "name": "button_sort",
                                                                         "mouse_down": self.sort_items,
                                                                         "frame": {
                                                                             "size": 60,
                                                                             "count": 2,
                                                                             "index": 0,
                                                                             "loc": (160, 363),
                                                                         },
                                                                         "label": {
                                                                             "text": "整理背包",
                                                                             "size": 11
                                                                         },
                                                                     }, )
        # 切换上一页背包
        [_, btn_prev_rect, btn_prev_params] = game_ui.load_system_ui(f"{SourceManager.ui_system_path}/btn_left.png",
                                                                     [72, 18],
                                                                     options=
                                                                     {
                                                                         "name": "button_prev",
                                                                         "mouse_down": self.prev_page,
                                                                         "frame": {
                                                                             "size": 18,
                                                                             "count": 2,
                                                                             "index": 0,
                                                                             "target_index": 2,
                                                                             "loc": (20, 360),
                                                                         },
                                                                     }, )
        # 切换下一页背包
        [_, btn_next_rect, btn_next_params] = game_ui.load_system_ui(f"{SourceManager.ui_system_path}/btn_right.png",
                                                                     [72, 18],
                                                                     options=
                                                                     {
                                                                         "name": "button_next",
                                                                         "mouse_down": self.next_page,
                                                                         "frame": {
                                                                             "size": 18,
                                                                             "count": 2,
                                                                             "index": 0,
                                                                             "target_index": 2,
                                                                             "loc": (60, 360),
                                                                         },
                                                                         "is_share": True
                                                                     }, pos=[90, 360])

        # 道具锁定框
        self.item_lock = SourceManager.surface_scale(SourceManager.load(f"{SourceManager.ui_system_path}/lock_1.png"),
                                                     [20, 20])
        # 道具描述UI的道具图片背景
        self.icon_item_bg = SourceManager.surface_scale(
            SourceManager.load(f"{SourceManager.ui_system_path}/icon_skill_bg.png"), [60, 60])

        self.__GUI_rect_list = [
            [btn_sort_rect, btn_sort_params],
            [btn_prev_rect, btn_prev_params],
            [btn_next_rect, btn_next_params],
        ]
        # 6个装备栏的格子surface / 武器,帽子,衣物,首饰,腰带,靴子
        self.equips = {
            # 武器
            "weapon": {
                "type": 1,
                "rect": (160, 75, 40, 40),
                "item": None
            },
            # 帽子
            "hat": {
                "type": 2,
                "rect": (160, 25, 40, 40),
                "item": None
            },
            # 盔甲--衣服
            "armor": {
                "type": 3,
                "rect": (205, 75, 40, 40),
                "item": None
            },
            # 首饰
            "jewelry": {
                "type": 4,
                "rect": (205, 25, 40, 40),
                "item": None
            },
            # 腰带
            "belt": {
                "type": 5,
                "rect": (160, 123, 40, 40),
                "item": None
            },
            # 鞋子
            "shoe": {
                "type": 6,
                "rect": (205, 123, 40, 40),
                "item": None
            },
        }
        for si in self.equips.values():
            si["rect"] = pygame.Rect(si.get("rect"))

        self.__select_item = None
        self.__hover_item = None
        self.__drag = False
        # 道具的详情Surface
        self.__curr_item_detail = None
        # 按下鼠标时的移动路径--用于判断是否在拖拽
        self.__move_path = []
        # 加载配置项目
        self.__load_config()

    def __load_config(self):
        item_type: list[list] = SourceManager.get_csv("item_type")
        t_head: list = item_type.pop(0)
        t_head.pop(0)
        for t in item_type:
            key = int(t.pop(0))
            self.__item_type[key] = {}
            for cfg_i in range(len(t)):
                self.__item_type[key][int(t_head[cfg_i])] = t[cfg_i]

    def add_item(self, item_id: str, total: int = 0, merge: bool = True, target_page: int = -1,
                 target_x: int = -1, target_y: int = -1, has_call: bool = False,
                 primary_attr_id: int = 0, secondary_attr_id: int = 0, expire_time: int = 0,
                 quality: str = "white", enhance_level: int = 0):
        """
        向背包添加物品
        :param item_id:  道具ID
        :param total: 道具数量
        :param merge: 是否指定了允许强制合并道具数量. 可以忽视道具的不允许叠加 属性
        :param target_page: 直接指定追加到的页数: 1, 2, 3, ...
        :param target_x: 直接指定追加到的横坐标
        :param target_y: 直接指定追加到的纵坐标
        :param has_call: 是否是递归调用追加道具方法
        :param primary_attr_id: 装备额外主属性id
        :param secondary_attr_id: 装备额外副属性id
        :param expire_time: 装备过期时间 0 则永久
        :param quality: 道具品质预留字段
        :param enhance_level: 强化等级
        :return:
        """
        call_total = 0

        item_data: dict[str, str | int | list] = SourceManager.get_csv("items", str(item_id))
        if item_data is None:
            GameToastManager.add_message(f"无法追加道具:[{item_id}], 不存在的道具信息")
            GameLogManager.log_service_error(f"无法追加道具:[{item_id}], 不存在的道具信息")
            return

        self.update_blit = True
        page = x = y = -1
        if target_page != -1:
            target_page -= 1

        for index_k in self.items_index_dict:
            if target_page != -1:
                page, x, y = index_k.split("#")
                if target_x != -1:
                    x = max(target_x, 0)
                if target_y != -1:
                    y = max(target_y, 0)
                page = max(target_page, 0)
                curr_key = f"{page}#{x}#{y}"
                if not self.items_index_dict.get(curr_key):
                    break
                else:
                    GameLogManager.log_service_error(f"无效背包位置:{curr_key}")
            else:
                if not self.items_index_dict[index_k]:
                    page, x, y = index_k.split("#")
                    break

        if 0 <= target_page < self.max_page:
            page = target_page

        # 是否指定了默认数量
        if total > 0:
            if item_data.get("可重叠摆放") == "1":
                item_data["初始使用次数"] = str(min(total, int(item_data.get("最大使用次数", total))))
            else:
                if not has_call:
                    call_total = total - 1

        # 道具是否可叠加,以及是否指定了不允许自动叠加
        if item_data.get("可重叠摆放") == "1" and merge:
            # 获取到当前是否持有这个道具
            have_items = self.get_item_by_id(item_id)
            for item in have_items:
                # 数量是否上限
                if item.count >= item.max_count:
                    continue
                # 绑定状态不一致的也不允许追加叠加
                if item.bind ^ bool(item_data.get("bind")):
                    continue
                if not self.__same_stack_meta(item, quality, enhance_level, expire_time):
                    continue

                item_count = int(item_data.get("初始使用次数"))
                # 差值是否小于新增的数量
                if item_count + item.count <= item.max_count:
                    item.count += item_count
                    return
                difference = item.max_count - item.count
                item.count += difference
                item_data["初始使用次数"] = item_count - difference

        item_data["__pos"] = [page, x, y]
        if primary_attr_id:
            item_data["主属性"] = primary_attr_id

        if secondary_attr_id:
            item_data["副属性"] = secondary_attr_id

        if expire_time:
            item_data["过期时间"] = expire_time
        if quality:
            item_data["品质"] = quality

        # 挡在叠加操作的下面
        if page == -1:
            # 背包满了
            GameToastManager.add_message("背包满了")
            return

        item = Item(item_data)
        item.enhance_level = enhance_level
        self.items[int(page)][int(x)][int(y)] = item
        self.items_index_dict[f"{page}#{x}#{y}"] = True

        self.update_blit = True
        if call_total > 0:
            for i in range(call_total, 0, -1):
                self.add_item(item_id, i - 1, has_call=True, expire_time=expire_time, quality=quality,
                              enhance_level=enhance_level)

    def add_item_exist(self, item: Item):
        """将已有的道具增加到背包里面"""
        for index_k in self.items_index_dict:
            page, x, y = index_k.split("#")
            curr_key = f"{page}#{x}#{y}"
            if not self.items_index_dict[curr_key]:
                item.set_pos(x, y, page)
                self.items[int(page)][int(x)][int(y)] = item
                self.items_index_dict[f"{page}#{x}#{y}"] = True
                self.update_blit = True
                return True
        return False

    def get_item_surface(self, sur_width: int, sur_height: int):
        """
        将当前背包页的所有道具都转为surface,用于渲染
        :param sur_width:
        :param sur_height:
        :return:
        """
        item_all = self.get_items_by_page(self.current_page)
        mask_sur = pygame.Surface((sur_width, sur_height), pygame.SRCALPHA)
        if len(item_all):
            for item in item_all:
                item_page, item_row, item_column = item.get_pos()
                mask_sur.blit(item.icon, ((item_column * 42) + 22, (item_row * 45) + 180))
                # 是否可堆叠, 可堆叠的还需要显示数量
                if item.can_stack and item.count > 1:
                    mask_sur.blit(GameFont.get_text_surface_line(str(item.count), True, bolder=True),
                                  ((item_column * 42) + 52 - (len(str(item.count)) * 2), (item_row * 45) + 207))
                if item.bind:
                    mask_sur.blit(self.item_lock, (item_column * 42 + 20, (item_row * 45) + 205))

            return mask_sur
        return None

    def remove_item(self, item_uid: str):
        """从背包移除物品, 根据道具的UID进行扣除
        @:return  返回是否扣除成功的状态
        """
        for index in self.items_index_dict:
            if self.items_index_dict[index]:
                page, x, y = index.split("#")
                if self.items[int(page)][int(x)][int(y)].UID == str(item_uid):
                    self.items[int(page)][int(x)][int(y)] = None
                    self.items_index_dict[index] = False
                    return True
        return False

    def sort_items(self):
        """根据排序规则对物品排序（需自行实现逻辑）"""
        # 1. 生成当前背包页数的最大格子数量
        items_arr: list[None | Item] = [None for _ in range(self.max_page * self.max_capacity)]
        # 2. 返回扁平化的一维数组结构
        items = self.get_items_all()
        for item in items:
            [page, row, column] = item.get_pos()
            item_index = row * self.column + column + (page * self.max_capacity)
            items_arr[item_index] = item

        # 2. 将背包和背包索引初始化
        self.items: list[list[list[Item | None]]] = [[[None for _ in range(self.column)] for _ in range(self.row)] for _
                                                     in range(self.max_page)]  # 存储物品对象或引用（列表形式）
        # 3. 清空背包格子索引
        self.items_index_dict: dict[str, bool] = {
            f"{page}#{y}#{x}": False
            for page in range(self.max_page)
            for y in range(self.row)
            for x in range(self.column)
        }

        # 使用快排
        def quick_sort(arr: list[Item]) -> list[Item | None]:
            if len(arr) <= 1:
                return arr

            pivot = arr[0]
            left = []
            middle = [pivot]
            right = []

            for x in arr[1:]:
                if x.ID < pivot.ID:
                    left.append(x)
                elif x.ID > pivot.ID:
                    right.append(x)
                else:
                    #  这俩道具其中是否有一个是绑定的, 绑定的优先排在前面
                    if x.bind and not pivot.bind:
                        left.append(x)
                    elif not x.bind and pivot.bind:
                        right.append(x)
                    # 确保数量少的排在后面
                    elif x.count > pivot.count:
                        left.append(x)
                    elif x.count < pivot.count:
                        right.append(x)
                    else:
                        middle.append(x)

            return quick_sort(left) + middle + quick_sort(right)

        # 整理背包逻辑
        def sort_inventory(arr: list[Item | None]) -> list[Item | None]:
            items_only = [it for it in arr if it is not None]
            sorted_items = quick_sort(items_only)
            empty_slots = [None] * (len(arr) - len(sorted_items))
            return sorted_items + empty_slots

        items_arr = sort_inventory(items_arr)

        for i in range(len(items_arr)):
            curr_item = items_arr[i]
            if curr_item is None:
                continue

            if curr_item.count >= curr_item.max_count:
                continue

            for y in range(len(items_arr)):
                if i == y:
                    continue

                next_item = items_arr[y]
                if next_item is None:
                    continue
                # 绑定状态不一致的不允许叠加
                if curr_item.bind and not next_item.bind or not curr_item.bind and next_item.bind:
                    continue
                if curr_item.ID == next_item.ID and curr_item.UID != next_item.UID:
                    # 计算当前 item 还能叠加多少
                    can_add = curr_item.max_count - curr_item.count
                    if can_add <= 0:
                        break  # 已满，退出寻找

                    # 本轮准备叠加多少
                    transfer_count = min(can_add, next_item.count)
                    curr_item.count += transfer_count
                    next_item.count -= transfer_count

                    # 如果 next_item 已空，移除
                    if next_item.count == 0:
                        items_arr[y] = None

        items_arr = sort_inventory(items_arr)

        # finally: 重新生成索引
        for y in range(len(items_arr)):
            page = y // self.max_capacity
            row = y // self.column - (page * self.row)
            column = y % self.column
            item: Item = items_arr[y]
            if item:
                item.set_pos(row, column, page)
                self.items[page][row][column] = item
                self.items_index_dict[f"{page}#{row}#{column}"] = True

    def prev_page(self):
        """切换背包页-上一页"""
        self.current_page = (self.current_page - 2) % self.max_page + 1

    def next_page(self):
        """切换背包页-下一页"""
        self.current_page = self.current_page % self.max_page + 1

    def get_items_all(self) -> list[Item]:
        """返回当前背包的所有道具"""
        item_arr: list[Item] = []
        for index in self.items_index_dict:
            if self.items_index_dict[index]:
                page, x, y = index.split("#")
                item_arr.append(self.items[int(page)][int(x)][int(y)])
        return item_arr

    def get_item_by_id(self, item_id: str) -> list[Item]:
        """根据道具的真实ID获取当前在背包里面的该道具"""
        item_arr: list[Item] = []
        for index in self.items_index_dict:
            if self.items_index_dict[index]:
                page, x, y = index.split("#")
                if self.items[int(page)][int(x)][int(y)].ID == str(item_id):
                    item_arr.append(self.items[int(page)][int(x)][int(y)])
        return item_arr

    def get_item_by_uid(self, item_uid: str) -> Item | None:
        """根据道具的背包UID获取当前在背包里面的该道具"""
        for index in self.items_index_dict:
            if self.items_index_dict[index]:
                page, x, y = index.split("#")
                if self.items[int(page)][int(x)][int(y)].UID == str(item_uid):
                    return self.items[int(page)][int(x)][int(y)]
        return None

    def get_item_by_loc(self, x: int, y: int, page: int = -1):
        """根据索引获取到背包对应位置的道具, 包括None , 默认获取第一页的"""
        if not self.has_box(x, y):
            return None
        if page == -1:
            page = self.current_page - 1
        return self.items[page][x][y]

    def get_items_by_page(self, page: int):
        """根据背包页码数获取道具信息"""
        item_arr: list[Item] = []
        for index in self.items_index_dict:
            if self.items_index_dict[index]:
                _page, x, y = index.split("#")
                if int(_page) + 1 != page:
                    continue
                item_arr.append(self.items[int(_page)][int(x)][int(y)])
        return item_arr

    def get_items_count(self) -> int:
        """返回当前背包的剩余容量"""
        total = self.max_capacity * self.max_page
        for index in self.items_index_dict:
            if self.items_index_dict[index]:
                total -= 1
        return total

    def get_target_item_count(self, item_id: str, number: int, quality: str = "white", enhance_level: int = 0,
                              expire_time: int = 0) -> bool:
        """根据传入的道具ID,来判断剩余的背包容量是否还允许追加到背包"""
        # 先得到剩余的背包容量
        item_data: dict[str, str] = SourceManager.get_csv("items", str(item_id))
        if item_data is None:
            GameToastManager.add_message(f"无法追加道具:[{item_id}], 不存在的道具信息")
            GameLogManager.log_service_error(f"无法追加道具:[{item_id}], 不存在的道具信息")
            return False

        bag_total = self.get_items_count()

        if item_data.get("可重叠摆放") == "1":
            exist_arr = self.get_item_by_id(item_id)
            for item in exist_arr:
                # 已经满了就不管
                if item.count == item.max_count:
                    continue

                # 绑定状态不一致的也不允许追加叠加
                if item.bind ^ bool(item_data.get("bind")):
                    continue
                if not self.__same_stack_meta(item, quality, enhance_level, expire_time):
                    continue
                # 如果传进来的数量是能够被目前的道具给瓜分完的, 那就视为允许添加
                number -= item.max_count - item.count
                if number <= 0:
                    return True
            max_count = int(item_data.get("最大使用次数", 1) or 1)
            need_slots = max(1, (max(number, 1) + max_count - 1) // max_count)
            return bag_total >= need_slots
        else:
            # 不能叠加的那就只需要判断还有没有剩余的背包空间就行了
            return bag_total >= number

        return False

    @staticmethod
    def __same_stack_meta(item: Item, quality: str = "white", enhance_level: int = 0, expire_time: int = 0) -> bool:
        """同一堆叠必须是同品质、同强化、同到期时间."""
        return (
            str(getattr(item, "quality", "white") or "white") == str(quality or "white")
            and int(getattr(item, "enhance_level", 0) or 0) == int(enhance_level or 0)
            and int(getattr(item, "expire_time", 0) or 0) == int(expire_time or 0)
        )

    def has_box(self, x: int, y: int):
        return x <= 3 and y <= 4

    def change_item_loc(self, from_pos: list, target_pos: list, page: int = -1):
        """更换背包格子位置"""
        x1, y1 = from_pos
        x2, y2 = target_pos
        if not self.has_box(x1, y1) or not self.has_box(x2, y2):
            # GameLogManager.log_service_debug(f"选中坐标:{from_pos}, 终点坐标:{target_pos}")
            return False
        if page == -1:
            page = self.current_page - 1
        from_item: Item = self.items[page][x1][y1]
        target_item: Item = self.items[page][x2][y2]
        if from_item is None and target_item is None:
            return False  # 无变化

        if target_item is None:
            """目标是空的? 那么就直接换过去"""
            from_item.set_pos(x2, y2, page)
            # 更新索引
            self.items_index_dict[f"{page}#{x1}#{y1}"] = False
            self.items_index_dict[f"{page}#{x2}#{y2}"] = True
            self.items[page][x2][y2], self.items[page][x1][y1] = self.items[page][x1][y1], self.items[page][x2][y2]
            return True

        if from_item is None:
            """自身是空的? 那么就直接换过去, 一般用于在其他地方的调用 比如整理背包"""
            target_item.set_pos(x2, y2, page)
            self.items_index_dict[f"{page}#{x1}#{y1}"] = False
            self.items_index_dict[f"{page}#{x2}#{y2}"] = True
            self.items[page][x1][y1], self.items[page][x2][y2] = self.items[page][x2][y2], self.items[page][x1][y1]
            return True

        # 自身交换?  直接返回
        if from_item.UID == target_item.UID:
            return False

        # 自己和目标是不是不允许叠加, 如果有一个不允许叠加,,  或者这俩就完全不是一个道具 那么直接交换. 不需要判断类型 或者他俩有一个已经是满的
        if not from_item.can_stack or not target_item.can_stack or from_item.ID != target_item.ID \
                or from_item.count == from_item.max_count or target_item.count == target_item.max_count:
            #  索引不需要更新, 这俩位置都有道具
            from_item.set_pos(x2, y2, page)
            target_item.set_pos(x1, y1, page)
            self.items[page][x1][y1], self.items[page][x2][y2] = self.items[page][x2][y2], self.items[page][x1][y1]
            return True

        # 绑定状态不一致的不允许叠加-- 确保绑定的道具始终排在相同类型道具的前面
        if from_item.bind != target_item.bind:
            #  索引不需要更新, 这俩位置都有道具
            from_item.set_pos(x2, y2, page)
            target_item.set_pos(x1, y1, page)
            self.items[page][x1][y1], self.items[page][x2][y2] = self.items[page][x2][y2], self.items[page][x1][y1]
            return True

        # 相同的道具,且允许叠加的,  判断双方的数量加起来是否超过了 上限,
        difference = from_item.max_count - (from_item.count + target_item.count)
        if difference >= 0:
            # 如果这俩加起来的数量都没有超过上限, 那么直接把当前拖动的这个道具数量加到目标点,并销毁这个道具
            # 销毁被选中的道具索引,  目标的索引不用修改
            target_item.count += from_item.count
            self.items_index_dict[f"{page}#{x1}#{y1}"] = False
            self.items[page][x1][y1] = None
            return True

        # 超过上限了, 那么就把当前拖动的数量加到目标位置, 其他的不用变
        difference_count = from_item.count + difference
        from_item.count -= difference_count
        target_item.count += difference_count
        return True

    def mouse_down(self, **args):
        check_bag = self.__check_bag()
        if check_bag[0]:
            if check_bag[1]:
                self.__select_item = {
                    "item": check_bag[1],
                    "pos": check_bag[2],
                    "texture": SourceManager.set_surface_alpha(check_bag[1].avatar, 120),
                    "uid": check_bag[1].UID
                }
            else:
                self.__select_item = None
            return
        mouse_pos = pygame.mouse.get_pos()
        game_ui: GameUI = self.gm.get("游戏UI")
        bag_sprite = game_ui.get_surface_sprite("角色背包")  # 需要加上背包的偏移

        for [gui_rect, gui_params] in self.__GUI_rect_list:
            if gui_rect.collidepoint(mouse_pos[0] - bag_sprite.get("rect").x, mouse_pos[1] - bag_sprite.get("rect").y):
                gui_fun = gui_params.get("mouse_down")
                if gui_fun:
                    gui_fun()
                gui_params.get("frame")["index"] = 1 if gui_params.get("frame").get(
                    "target_index") is None else gui_params.get("frame").get("target_index")
                self.update_blit = True
                return

    def right_mouse_down(self, **args):
        check_bag = self.__check_bag()
        if not check_bag[0] or not check_bag[1]:
            return False
        chat_system = getattr(self.gm, "chat_system", None)
        if chat_system is None or not hasattr(chat_system, "insert_item_link"):
            GameToastManager.add_message("聊天框未开启")
            return False
        chat_system.insert_item_link(check_bag[1])
        self.__select_item = None
        self.__drag = False
        self.__move_path.clear()
        self.update_blit = True
        return False

    def mouse_up(self, **arg):
        self.__drag = False
        for [_, gui_params] in self.__GUI_rect_list:
            gui_params.get("frame")["index"] = 0

        if self.__select_item is None:
            self.__select_item = None
            self.update_blit = True
            self.__move_path.clear()  # 清空移动路径
            return
        check_bag = self.__check_bag()
        if check_bag[0]:
            if self.__select_item["pos"] != check_bag[2] and len(self.__move_path) > 1 and self.__select_item[
                "texture"]:
                self.change_item_loc(self.__select_item["pos"], check_bag[2])
        else:
            drag_equip = self.__drag_equip()
            if drag_equip:
                curr_item: Item = self.get_item_by_uid(self.__select_item.get("uid"))
                if curr_item.type == 1 and drag_equip.get("type") == curr_item.type:
                    self.__use_equip(curr_item)
            else:
                if self.__select_item:
                    if not self.__select_item.get("item").can_drop:
                        GameToastManager.add_message("当前道具不允许丢弃")
                    else:
                        u_player: "SpriteBase" = self.gm.get("主角")
                        __world_pos = u_player.get_pos_world()
                        # 扔到地上
                        GameWorldManager.add_pick_item(self.__select_item.get("item"), __world_pos[0], __world_pos[1],
                                                       True)
                        # 从背包移除
                        self.remove_item(self.__select_item.get("uid"))

        self.update_blit = True
        self.__select_item = None
        self.__move_path.clear()  # 清空移动路径

    def mouse_move(self, **args):
        check_bag = self.__check_bag()
        self.__hover_item = check_bag
        self.__drag = False
        self.__move_path.clear()
        if check_bag[0]:
            if self.__select_item and self.__select_item.get("texture"):
                if check_bag[2] not in self.__move_path:
                    self.__move_path.append(check_bag[2])
                    self.__drag = True
            item: Item = check_bag[1]
            if item:
                self.__move_path.append([0, 0])  # 确保能出现预览图
                if self.__curr_item_detail is not None and (
                        self.__curr_item_detail and self.__curr_item_detail.get("uid") == item.UID):
                    return

                mask_rect = check_bag[3]
                mask_rect[0] = max(mask_rect[0] - 200, 0)
                mask_rect[1] = max(mask_rect[1] - 150, 0)
                self.__set_item_detail(item, mask_rect)
                return
        else:
            drag_equip = self.__drag_equip()
            if drag_equip and drag_equip.get("item"):
                mask_rect = drag_equip.get("rect")
                mask_rect.x = max(mask_rect.x - 200, 0)
                mask_rect.y = max(mask_rect.y - 150, 0)
                self.__set_item_detail(drag_equip.get("item"), mask_rect)
                return

        self.__move_path.append([0, 0])  # 确保在边缘的道具执行拖拽的时候也能出现预览图
        self.__curr_item_detail = None
        if self.__select_item and self.__select_item.get("texture"):
            self.__drag = True

    def mouse_out(self):
        self.__curr_item_detail = None

    def mouse_double_click(self):
        check_bag = self.__check_bag()
        if check_bag[0] and check_bag[1]:
            self.__use_item(check_bag[1])
            return
        drag_equip = self.__drag_equip()
        if drag_equip:
            if drag_equip.get("item"):
                self.__use_equip(drag_equip.get("item"), True)
                # self.add_item_exist(drag_equip.get("item"))
                # drag_equip["item"] = None

    def render(self):
        if self.__select_item and self.__select_item.get("texture") and self.__drag:
            # 显示道具的预览图
            mouse_pos = pygame.mouse.get_pos()
            self.gm.game_win.blit(self.__select_item.get("texture"),
                                  (mouse_pos[0] - 35, mouse_pos[1] - 30))

        if self.__select_item:
            game_ui: GameUI = self.gm.get("游戏UI")
            item_cursor_sprite = game_ui.get_surface_sprite("item_cursor")
            frame_index = item_cursor_sprite.get("frame").get("index")
            if item_cursor_sprite.get("frame").get("time") > 0:
                item_cursor_sprite.get("frame")["time"] -= 1
            else:
                item_cursor_sprite.get("frame")["time"] = item_cursor_sprite.get("frame").get("timer")
                item_cursor_sprite.get("frame")["index"] = (frame_index + 1) % item_cursor_sprite.get("frame").get(
                    "count")
            self.update_blit = True

        if self.__curr_item_detail and not self.__drag:
            self.gm.game_win.blit(self.__curr_item_detail.get("texture"), self.__curr_item_detail.get("rect"))

    def __check_bag(self):
        """检查是否在背包的道具区域
        @return  如果没有匹配, 那么就返回 [False]
         否则 返回 [True, 当前得到的道具, 主角对象, 当前鼠标计算的背包格子]
        """
        mouse_pos = pygame.mouse.get_pos()
        target = {
            "bag_offset": pygame.Rect([25, 180, 200, 172]),
            "bag_size": [45, 40]
        }
        game_ui: GameUI = self.gm.get("游戏UI")
        bag_offset: pygame.Rect = target.get("bag_offset")
        rect: pygame.Rect = game_ui.get_surface_sprite("角色背包").get("rect")

        left_offset = rect.x + bag_offset.x
        top_offset = rect.y + bag_offset.y
        right_offset = 25
        bottom_offset = 45
        box_width, box_height = target.get("bag_size")
        if left_offset <= mouse_pos[0] < rect.right - right_offset and top_offset <= mouse_pos[
            1] <= rect.bottom - bottom_offset:
            bag_pos = [int((mouse_pos[1] - top_offset) / box_width), int((mouse_pos[0] - left_offset) / box_height)]
            item = self.get_item_by_loc(bag_pos[0], bag_pos[1])
            # 将当前的格子坐标转换为精准的屏幕坐标
            bag_pos_scene = [bag_pos[1] * box_height + left_offset, bag_pos[0] * box_width + top_offset]
            return [True, item, bag_pos, bag_pos_scene]
        return [False]

    def __update_blit(self):
        """用于提供给游戏UI进行重绘的方法"""
        if not self.update_blit:
            return
        self.update_blit = False
        game_ui: GameUI = self.gm.get("游戏UI")
        bag_sur = game_ui.get_surface_ui("角色背包")
        item_sur = self.get_item_surface(240, 400)
        if item_sur:
            bag_sur.blit(item_sur)
        if self.__hover_item and self.__hover_item[0]:
            # item_cursor_sprite = game_ui.get_surface_sprite("item_cursor")
            # item_cursor = game_ui.get_surface_ui("item_cursor")
            # frame_size = item_cursor_sprite.get("frame").get("size")
            # frame_index = item_cursor_sprite.get("frame").get("index")
            # bag_pos = ((self.__hover_item[2][1] * 42) + 22, (self.__hover_item[2][0] * 45) + 180)
            # bag_sur.blit(item_cursor, bag_pos, (frame_index * frame_size, 0, frame_size, frame_size))

            item_selected = game_ui.get_surface_ui("item_selected")
            bag_pos = ((self.__hover_item[2][1] * 42) + 22, (self.__hover_item[2][0] * 45) + 180)
            bag_sur.blit(item_selected, bag_pos)

        # 显示道具的选中框
        if self.__select_item:
            # item_selected = game_ui.get_surface_ui("item_selected")
            # bag_pos = ((self.__select_item["pos"][1] * 42) + 22, (self.__select_item["pos"][0] * 45) + 180)
            # bag_sur.blit(item_selected, bag_pos)
            item_cursor_sprite = game_ui.get_surface_sprite("item_cursor")
            item_cursor = game_ui.get_surface_ui("item_cursor")
            frame_size = item_cursor_sprite.get("frame").get("size")
            frame_index = item_cursor_sprite.get("frame").get("index")
            bag_pos = ((self.__select_item["pos"][1] * 42) + 22, (self.__select_item["pos"][0] * 45) + 180)
            bag_sur.blit(item_cursor, bag_pos, (frame_index * frame_size, 0, frame_size, frame_size))

        # 渲染背包按钮
        for [rect, params] in self.__GUI_rect_list:
            btn_sort_frame_size = params.get("frame").get("size")
            btn_sort_frame_index = params.get("frame").get("index")
            bag_sur.blit(params.get("surface"), params.get("frame").get("loc"),
                         (btn_sort_frame_index * btn_sort_frame_size, 0, btn_sort_frame_size, btn_sort_frame_size))

            if params.get("label"):
                # 计算文本坐标,确保文件处于ui的中间
                width = len(params.get("label").get("text")) * params.get("label").get("size")
                lab_left = 0 if rect.width < width else (rect.width - width) // 2
                lab_top = 0 if rect.height < params.get("label").get("size") else (rect.height - params.get(
                    "label").get("size")) // 2
                bag_sur.blit(GameFont.get_text_surface_line(params.get("label").get("text"), True,
                                                            params.get("label").get("size")),
                             (
                                 params.get("frame").get("loc")[0] + lab_left,
                                 params.get("frame").get("loc")[1] + lab_top))

        bag_sur.blit(
            GameFont.get_text_surface_line(f"{self.current_page} / {self.max_page}", True, 15, "#436EEE"), (45, 362))

        for i in self.equips.keys():
            pygame.draw.rect(bag_sur, (120, 120, 120), self.equips[i].get("rect"), 1)
            eq_item: Item = self.equips[i].get("item")
            if eq_item:
                bag_sur.blit(eq_item.icon, (self.equips[i].get("rect")[0], self.equips[i].get("rect")[1]))

        # 渲染金币
        bag_sur.blit(GameFont.get_text_surface_line("金钱", True), (7, 135))
        bag_sur.blit(GameFont.get_text_surface_line(str(self.money), True, font_color="#FFFFFF"), (42, 136))
        bag_sur.blit(GameFont.get_text_surface_line(str(self.point), True, font_color="#FFFFFF"), (42, 156))
        game_ui.set_surface_ui("角色背包", bag_sur)

    def listen_keyboard(self):
        """决定是否允许触发事件"""
        game_ui: GameUI = self.gm.get("游戏UI")
        return game_ui.get_surface_show("角色背包")

    def get_item_type(self, item: Item):
        """返回当前道具的类型"""
        return self.__item_type[item.type][item.sub_type]

    def __drag_equip(self):
        """推拽道具到装备栏区域"""
        mouse_pos = pygame.mouse.get_pos()
        game_ui: GameUI = self.gm.get("游戏UI")
        bag_sprite = game_ui.get_surface_sprite("角色背包")  # 需要加上背包的偏移

        for i in self.equips.keys():
            s_rect: pygame.Rect = self.equips[i].get("rect")
            if s_rect.collidepoint(mouse_pos[0] - bag_sprite.get("rect").x,
                                   mouse_pos[1] - bag_sprite.get("rect").y):
                sur = copy.deepcopy(self.equips[i])
                sur["rect"].x = self.equips[i].get("rect").x + bag_sprite.get("rect").x
                sur["rect"].y = self.equips[i].get("rect").y + bag_sprite.get("rect").y
                return sur

        return None

    def __use_item(self, item: Item):
        """使用道具"""
        # 如果存在回调. 那么可能是在战斗中. 使用一次道具就把背包关闭
        self.__set_item_detail(None, [0, 0])
        if BattleManager.battle_sta():
            if item.type == 2 and BattleManager.use_battle_item(item):
                return
            if item.type != 2:
                GameToastManager.add_message("战斗中只能使用消耗品")
                return
        match item.type:
            case 1:  # 装备
                self.__use_equip(item)
                return
            case 2:  # 消耗品
                self.__use_consumables(item)
                return
            case 3:  # 矿石
                GameToastManager.add_message(f"矿石道具未实现:{item}")
                return
        GameToastManager.add_message(f"无效类型的道具:{item}")

    def __use_equip(self, equip: Item, un_use: bool = False) -> bool:
        """ 使用装备 """
        # 是否处于战斗状态, 战斗中不允许使用装备
        if BattleManager.battle_sta():
            GameToastManager.add_message("战斗中无法使用装备")
            return False

        # 先判断当前是不是已经有了装备
        has_equip: Item | None = None
        has_key: str = ""
        for key in self.equips.keys():
            eq = self.equips[key]
            if eq.get("type") == equip.type:
                has_key = key
                if eq.get("item"):
                    has_equip = eq.get("item")
                break

        if self.get_items_count() == 0 and (has_equip or un_use):
            # 没有容量, 但是有装备需要替换下来, 提示用户没有空间了--
            GameToastManager.add_message("背包剩余容量不足")
            return False

        u_player: "Player" = self.gm.get("主角")
        # 先把当前使用中的装备卸下来
        if has_equip:
            __world_pos = u_player.change_status(has_equip.get_attr(), False)
            self.add_item_exist(has_equip)

        if not un_use:
            self.equips[has_key]["item"] = equip
            self.remove_item(equip.UID)
            __world_pos = u_player.change_status(equip.get_attr())
        else:
            self.equips[has_key]["item"] = None
            u_player.refresh_final_status()  # 卸下后立即重算属性
        self.__curr_item_detail = None
        return True

    def __use_consumables(self, item: Item):
        if item.stage == 1:
            self.money += int(item.money)
            # 金币类
            # if GameLuaManager.exec_lua("add_money", [self, item.money]):
            #     GameLogManager.log_service_debug(f"增加金钱:{item.money}")
            # else:
            #     return
        elif item.stage == 2:
            # 点卡类
            self.point += int(item.points)
            # if GameLuaManager.exec_lua("add_point", [self, item.points]):
            #     GameLogManager.log_service_debug(f"增加点卡:{item.points}")
            # else:
            #     return
        else:
            GameToastManager.add_message(f"[消耗品]无效道具阶段:{item.stage}")
            return
        item.count -= 1
        if item.count <= 0:
            self.remove_item(item.UID)

        game_ui: GameUI = self.gm.get("游戏UI")
        bs = game_ui.get_surface_sprite("角色背包")
        if bs.get("hide_callback_once"):
            bs["hide_callback_once"]()

    def __set_item_detail(self, item: Item | None, loc: list):
        """显示道具的描述"""
        if item is None:
            self.__curr_item_detail = item
            return
        mask_sur = pygame.Surface((200, self.gm.game_win_rect.height), pygame.SRCALPHA)
        # 填充圆角矩形背景
        pygame.draw.rect(mask_sur, (0, 0, 0, 190), (0, 0, mask_sur.width, mask_sur.height), border_radius=5)
        mask_sur.blit(self.icon_item_bg, (0, 0))
        mask_sur.blit(item.avatar, (2, 3))
        # 绑定状态
        if item.bind:
            mask_sur.blit(self.item_lock, (5, 40))
        quality_color = {
            "white": "#FFFFFF",
            "green": "#32CD32",
            "blue": "#4AA3FF",
            "gold": "#FFD700",
            "purple": "#C87BFF",
        }.get(str(getattr(item, "quality", "white") or "white").lower(), "#FFFFFF")
        # 道具名称
        mask_sur.blit(GameFont.get_text_surface_line(item.name, True, 15, quality_color),
                      (65, 5))
        if item.bind:
            mask_sur.blit(GameFont.get_text_surface_line("已绑定", True, 11, "#FF6A6A"),
                          (165, 25))
        else:
            mask_sur.blit(GameFont.get_text_surface_line("未绑定", True, 11, "#228B22"),
                          (165, 25))
        if not item.can_trade:
            mask_sur.blit(GameFont.get_text_surface_line("不可交易", True, 11, "#FF6A6A"),
                          (155, 40))
        # 道具类型
        mask_sur.blit(GameFont.get_text_surface_line(self.get_item_type(item), True, 11, "#00BFFF"),
                      (65, 25))
        mask_sur.blit(
            GameFont.get_text_surface_line(f"使用等级: [#FF7F24]{item.level}", True, 11, "#FFFFFF"),
            (65, 40))

        if item.can_stack and item.count > 1:
            mask_sur.blit(GameFont.get_text_surface_line(f"数量:{item.count}", True, 11, "#FFFFFF"),
                          (65, 55))

        render_y = 90
        if getattr(item, "enhance_level", 0) > 0:
            mask_sur.blit(GameFont.get_text_surface_line(f"强化等级:+{item.enhance_level}", True, 11, quality_color),
                          (5, render_y - 18))
        if item.type == 1:
            # 直接调用新方法获取已经排好序、分好色的数组
            display_list = item.get_display_attrs()

            for text, color in display_list:
                # 直接根据数组里的内容渲染，相同属性名会显示多行
                mask_sur.blit(
                    GameFont.get_multiple_text(text, 195, 145, True, 11, quality_color),
                    (5, render_y)
                )
                render_y += 13

            # attrs = item.get_attr()
            # # 如果是装备, 那么就需要展示属性
            # for ak in attrs:
            #     # 跳过暂时还没有使用的属性字段
            #     if not item.FIELD_MAPPING.get(ak):
            #         continue
            #     field_name = item.FIELD_MAPPING.get(ak).get("attr")
            #     val = int(getattr(item, field_name))
            #     if val == 0:
            #         continue
            #     mask_sur.blit(GameFont.get_multiple_text(f"{ak}: +{val}", 195, 145, True, 11, "#FFFF00"),
            #                   (5, render_y))
            #     render_y += 13

            # 获取到装备的主副属性 / 过期时间
            # pass_attr = ['ID', '可装备附魔', '可宠物附魔', '备注', '有效', '说明', '阶段', '道具类型', '品质', '附加价格']
            # percentage_attr = ['攻击速度', '伤害', '防御', '命中', '闪躲', '水攻', '火攻', '毒攻', '水防', '火防', '毒防', 'hp', 'mp', '爆击率', '比率吸魔', '伤害吸收', '杀怪经验获得率', '杀怪金钱获得率']
            # show_attr = ['力量强度', '体质强度', '精准强度', '敏捷强度', '智力强度', '必杀', '伤害', '防御', '命中', '闪躲', '爆击伤害', '力量', '敏捷', '体质', '精准', '智力', '吸血', '吸魔', '移动速度']
            # skill_attr = ['装备后技能']
            # # show_attr = ['力量强度', '体质强度', '精准强度', '敏捷强度', '智力强度', '必杀', '攻击速度', '伤害', '防御', '命中', '闪躲', '水攻', '火攻', '毒攻', '水防', '火防', '毒防', 'hp', 'mp', '爆击率', '爆击伤害', '力量', '敏捷', '体质', '精准', '智力', '吸血', '吸魔', '比率吸魔', '移动速度', '伤害吸收', '杀怪经验获得率', '杀怪金钱获得率', '装备后技能']
            # if item.primary_attr_id:
            #     item_data: dict[str, str] = SourceManager.get_csv("attribs", str(item.primary_attr_id))
            #     for ak, val in item_data.items():
            #         if len(val) == 0 or int(val) <= 0:
            #             continue
            #         if ak in pass_attr:
            #             continue
            #         if ak in percentage_attr:
            #             val = f"{val}%"
            #         mask_sur.blit(GameFont.get_multiple_text(f"{ak}: +{val}", 195, 145, True, 11, "#00E500"),
            #                       (5, render_y))
            #         render_y += 13
            # if item.secondary_attr_id:
            #     item_data: dict[str, str] = SourceManager.get_csv("attribs", str(item.secondary_attr_id))
            #     for ak, val in item_data.items():
            #         if len(val) == 0 or int(val) <= 0:
            #             continue
            #         if ak in pass_attr:
            #             continue
            #         if ak in percentage_attr:
            #             val = f"{val}%"
            #         mask_sur.blit(GameFont.get_multiple_text(f"{ak}: +{val}", 195, 145, True, 11, "#00E500"),
            #                       (5, render_y))
            #         render_y += 13
            # if item.expire_time:
            #     pass

        desc_sur = GameFont.get_multiple_text(item.description, 195, 145, True, 11, "#32CD32")
        # 道具描述
        mask_sur.blit(desc_sur, (5, render_y + 10))
        render_y += desc_sur.height
        self.update_blit = True
        mask_sur_full = pygame.Surface((200, render_y + 10), pygame.SRCALPHA)
        mask_sur_full.blit(mask_sur, (0, 0))
        # 内容是否太长超出了屏幕底部
        # 1. 先通过 Surface 获取 rect 对象
        mask_rect = mask_sur_full.get_rect()

        # 2. 如果你的 loc 是当前的渲染坐标，需要把坐标同步给 rect
        # mask_rect.topleft = loc
        # 确保 loc 是一个有效的坐标序列
        if loc and len(loc) >= 2:
            # 强制转换一次确保类型正确
            mask_rect.topleft = (int(loc[0]), int(loc[1]))
        else:
            # 如果 loc 异常，给个默认值防止崩溃
            mask_rect.topleft = (0, 0)

        # 3. 现在可以使用 rect 的属性进行逻辑判断了
        if mask_rect.bottom > self.gm.game_win_rect.height:
            # 计算超出的高度并减去
            overflow = mask_rect.bottom - self.gm.game_win_rect.height
            loc[1] -= overflow

        self.__curr_item_detail = {
            "uid": item.UID,
            "texture": mask_sur_full,
            "rect": loc
        }

    def refresh_bag(self, raw_data: str):
        """
        根据服务器/数据库传入的字符串数据刷新背包
        格式: page,y,x,id,count|page,y,x,id,count
        """
        if not raw_data:
            return

        # 1. 拆分背包和装备栏
        parts = raw_data.split("&")
        bag_data_str = parts[0]
        equip_raw = parts[1] if len(parts) > 1 else ""

        # 1. 过滤空字符串，避免 split(",") 报错
        item_raw_list = [ii for ii in bag_data_str.split("|") if ii.strip()]

        # 记录本次数据中所有有效的位置
        new_positions = set()

        item_data: dict[str, dict[str, str | int]] = SourceManager.get_csv("items")
        for item_raw in item_raw_list:
            try:
                # 解析格式: xxxx,1,0,0,1,1 -> uid, page, y, x, id, count
                parts = item_raw.split(",")
                # 1. 基础解包：uid 是字符串，其余核心字段转 int
                uid = parts[0]
                # 核心字段：位置(p, y, x)、ID(item_id)、数量(count)
                p, y, x, item_id, count = map(int, parts[1:6])

                # 2. 获取剩余的动态字段
                extras = parts[6:]
                # 3. 业务逻辑解析
                item_info = item_data.get(str(item_id))
                # 主副属性 / 有效期 / 品质 / 强化等级
                primary_attr_id = 0
                secondary_attr_id = 0
                expire_time = 0
                quality = "white"
                enhance_level = 0
                if item_info and len(extras) > 0:
                    padded_extras = extras + [0] * 5
                    match int(item_info.get("类型")):
                        # 装备类: 兼容旧格式 uid,page,y,x,id,count,主属性,副属性,过期时间
                        case 1:
                            primary_attr_id, secondary_attr_id, expire_time = padded_extras[:3]
                            quality = padded_extras[3] or "white"
                            enhance_level = padded_extras[4] or 0
                        # 非装备类旧格式没有主副属性, 新格式从 extras[0] 开始追加品质/强化/过期时间
                        case _:
                            quality = padded_extras[0] or "white"
                            enhance_level = padded_extras[1] or 0
                            expire_time = padded_extras[2] or 0

                # 内部索引转换：页码从 1 开始转为从 0 开始
                page_idx = p - 1
                if not (0 <= page_idx < self.max_page):
                    continue

                pos_key = f"{page_idx}#{y}#{x}"
                new_positions.add(pos_key)

                current_item = self.items[page_idx][y][x]

                # 判定 A: 该位置为空，或者道具 ID 变了 -> 创建新道具并赋予短 UID
                if current_item is None or current_item.ID != str(item_id):
                    item_cfg = SourceManager.get_csv("items", str(item_id))
                    if item_cfg:
                        new_data = copy.deepcopy(item_cfg)
                        new_data["初始使用次数"] = str(count)
                        new_data["__pos"] = [page_idx, y, x]

                        if primary_attr_id:
                            new_data["主属性"] = int(primary_attr_id)

                        if secondary_attr_id:
                            new_data["副属性"] = int(secondary_attr_id)

                        if expire_time:
                            new_data["过期时间"] = int(expire_time)

                        if quality:
                            new_data["品质"] = str(quality)

                        if enhance_level:
                            new_data["强化等级"] = int(enhance_level)

                        # 实例化 Item，确保其内部生成的 UID 长度适中
                        new_obj = Item(new_data)
                        new_obj.UID = uid
                        self.items[page_idx][y][x] = new_obj
                        self.items_index_dict[pos_key] = True

                # 判定 B: 道具 ID 没变 -> 更新数量和扩展字段，保留原 UID
                else:
                    current_item.count = count
                    current_item.quality = str(quality or "white")
                    current_item.enhance_level = int(enhance_level or 0)
                    current_item.expire_time = int(expire_time or 0)

            except (ValueError, IndexError) as e:
                GameLogManager.log_service_error(f"解析装备数据[{item_raw}]失败=> {e}")
                continue

        # 2. 清理逻辑：如果背包原有位置不在新数据中，视为已被移除
        for index_key in list(self.items_index_dict.keys()):
            if self.items_index_dict[index_key] and index_key not in new_positions:
                pg, iy, ix = [int(i) for i in index_key.split("#")]
                # 只有当前页或全量同步时才执行清理，这里采用全量清理逻辑
                self.items[pg][iy][ix] = None
                self.items_index_dict[index_key] = False

        # --- 3. 处理装备栏 ---
        if equip_raw:
            for e_str in equip_raw.split("|"):
                if not e_str: continue
                e_data = e_str.split(",")
                if len(e_data) < 5: continue

                slot_key = e_data[0]
                item_id = e_data[1]
                p_attr = int(e_data[2])
                s_attr = int(e_data[3])
                expire = int(e_data[4])
                quality = e_data[5] if len(e_data) > 5 and e_data[5] else "white"
                enhance_level = int(e_data[6]) if len(e_data) > 6 and e_data[6] else 0

                # 创建 Item 对象
                config = SourceManager.get_csv("items", item_id)
                if config:
                    config["__pos"] = [-1,-1,-1]
                    config["品质"] = quality
                    config["强化等级"] = enhance_level
                    item = Item(config)
                    item.primary_attr_id = p_attr
                    item.secondary_attr_id = s_attr
                    item.expire_time = expire
                    item.quality = quality
                    item.enhance_level = enhance_level
                    # 放入装备栏
                    if slot_key in self.equips:
                        self.equips[slot_key]["item"] = item

        # 4. 关键：加载完所有东西后，强制刷新玩家属性
        u_player = self.gm.get("主角")
        if u_player:
            u_player.refresh_final_status()
        self.update_blit = True  # 标记需要重绘 UI

    def serialize_equips(self) -> str:
        """
        将当前装备栏数据序列化
        格式: slot_key,id,primary_attr_id,secondary_attr_id,expire_time|...
        """
        serialized_equips = []
        for slot_key, slot_data in self.equips.items():
            item:Item = slot_data.get("item")
            if item:
                # 记录：部位Key, 道具ID, 主属性ID, 副属性ID, 过期时间
                # 注意：部位Key是字符串(如"头饰"), 道具ID是配置ID
                equip_str = (
                    f"{slot_key},{item.ID},{item.primary_attr_id},{item.secondary_attr_id},"
                    f"{item.expire_time},{getattr(item, 'quality', 'white') or 'white'},"
                    f"{int(getattr(item, 'enhance_level', 0) or 0)}"
                )
                serialized_equips.append(equip_str)

        return "|".join(serialized_equips)

    def get_full_save_data(self) -> str:
        """
        获取完整的保存字符串（背包 & 装备栏）
        """
        bag_str = self.serialize_bag()
        equip_str = self.serialize_equips()
        # 使用 & 符号分割
        return  "&".join([bag_str,equip_str])

    def serialize_bag(self) -> str:
        """
        将当前背包数据序列化为原始字符串格式
        格式: page,y,x,id,count|page,y,x,id,count
        """
        serialized_items = []

        # 遍历所有索引
        for index_key, has_item in self.items_index_dict.items():
            if has_item:
                # 解析索引键获取位置
                page_idx, y, x = [int(i) for i in index_key.split("#")]

                # 获取对应的物品对象
                item = self.items[page_idx][y][x]

                if item:
                    # 将页码索引恢复为 1-based (符合 refresh_bag 的逻辑)
                    page_num = page_idx + 1
                    # 拼接单个物品数据
                    item_str = f"{item.UID},{page_num},{y},{x},{item.ID},{item.count}"
                    quality = getattr(item, "quality", "white") or "white"
                    enhance_level = int(getattr(item, "enhance_level", 0) or 0)
                    expire_time = int(getattr(item, "expire_time", 0) or 0)
                    if item.type == 1:
                        item_str += (
                            f",{item.primary_attr_id},{item.secondary_attr_id},{expire_time},"
                            f"{quality},{enhance_level}"
                        )
                    elif quality != "white" or enhance_level > 0 or expire_time > 0:
                        item_str += f",{quality},{enhance_level},{expire_time}"
                    serialized_items.append(item_str)

        # 使用 | 连接所有物品字符串
        return "|".join(serialized_items)
