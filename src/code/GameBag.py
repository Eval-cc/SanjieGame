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
from typing import TYPE_CHECKING

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
        self.item_lock = SourceManager.ssurface_scale(SourceManager.load(f"{SourceManager.ui_system_path}/lock_1.png"),
                                                      [20, 20])
        # 道具描述UI的道具图片背景
        self.icon_item_bg = SourceManager.ssurface_scale(
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
            },
            # 帽子
            "hat": {
                "type": 2,
                "rect": (160, 25, 40, 40),
            },
            # 盔甲--衣服
            "armor": {
                "type": 3,
                "rect": (205, 75, 40, 40),
            },
            # 首饰
            "jewelry": {
                "type": 4,
                "rect": (205, 25, 40, 40),
            },
            # 腰带
            "belt": {
                "type": 5,
                "rect": (160, 123, 40, 40),
            },
            # 鞋子
            "shoe": {
                "type": 6,
                "rect": (205, 123, 40, 40),
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
                 target_x: int = -1, target_y: int = -1, has_call: bool = False):
        """
        向背包添加物品
        :param item_id:  道具ID
        :param total: 道具数量
        :param merge: 是否指定了允许强制合并道具数量. 可以忽视道具的不允许叠加 属性
        :param target_page: 直接指定追加到的页数: 1, 2, 3, ...
        :param target_x: 直接指定追加到的横坐标
        :param target_y: 直接指定追加到的纵坐标
        :param has_call: 是否是递归调用追加道具方法
        :return:
        """
        call_total = 0

        item_data: dict[str, str] = SourceManager.get_csv("items", str(item_id))
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

                item_count = int(item_data.get("初始使用次数"))
                # 差值是否小于新增的数量
                if item_count + item.count <= item.max_count:
                    item.count += item_count
                    return
                difference = item.max_count - item.count
                item.count += difference
                item_data["初始使用次数"] = item_count - difference

        item_data["__pos"] = [page, x, y]
        # 挡在叠加操作的下面
        if page == -1:
            # TODO: 需要在游戏里面提示 背包满了
            GameToastManager.add_message("背包满了")
            return

        item = Item(item_data)
        self.items[int(page)][int(x)][int(y)] = item
        self.items_index_dict[f"{page}#{x}#{y}"] = True

        self.update_blit = True
        if call_total > 1:
            for i in range(call_total, 0, -1):
                self.add_item(item_id, i - 1, has_call=True)

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

    def get_target_item_count(self, item_id: str, number: int) -> bool:
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
                # 如果传进来的数量是能够被目前的道具给瓜分完的, 那就视为允许添加
                number -= item.max_count - item.count
                if number <= 0:
                    return True
        else:
            # 不能叠加的那就只需要判断还有没有剩余的背包空间就行了
            return bag_total >= number

        return False

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

    def mouse_up(self):
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

    def mouse_move(self):
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
        # 道具名称
        mask_sur.blit(GameFont.get_text_surface_line(item.name, True, 15, "#FFD700"),
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
        if item.type == 1:
            attrs = item.get_attr()
            # 如果是装备, 那么就需要展示属性
            for ak in attrs:
                field_name = item.FIELD_MAPPING.get(ak).get("attr")
                val = int(getattr(item, field_name))
                if val == 0:
                    continue
                mask_sur.blit(GameFont.get_multiple_text(f"{ak}: +{val}", 195, 145, True, 11, "#FFFF00"),
                              (5, render_y))
                render_y += 13

        desc_sur = GameFont.get_multiple_text(item.description, 195, 145, True, 11, "#32CD32")
        # 道具描述
        mask_sur.blit(desc_sur, (5, render_y + 10))
        render_y += desc_sur.height
        self.update_blit = True
        mask_sur_full = pygame.Surface((200, render_y + 10), pygame.SRCALPHA)
        mask_sur_full.blit(mask_sur, (0, 0))
        self.__curr_item_detail = {
            "uid": item.UID,
            "texture": mask_sur_full,
            "rect": loc
        }
