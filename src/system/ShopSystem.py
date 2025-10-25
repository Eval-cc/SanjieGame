#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：ShopSystem.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/7/17 20:02 
@Describe: 商城类
"""
from typing import TYPE_CHECKING

import pygame
from src.code.Item import Item
from src.lib.GameEnum import ShopType
from src.manager.GameLogManger import GameLogManager
from src.manager.SourceManager import SourceManager
from src.system.GameToast import GameToastManager

if TYPE_CHECKING:
    from src.manager.GameManager import GameManager
    from src.render.GameUI import GameUI


class ShopSystem:
    def __init__(self, gm):
        # 基础属性
        self.gm: "GameManager" = gm
        self.column = 5
        self.row = 4
        self.max_capacity = self.column * self.row  # 单页背包最大容量（格子数或重量上限）
        self.current_page = 1  # 当前背包的分页
        self.max_page = 1  # 最大分页数量--- 动态根据传入的道具数量来控制
        self.update_blit = True
        # 默认名称
        self.shop_name = "商城"

        self.items: list[Item] = []
        # 右侧道具数组
        self.r_items: list[Item] = []
        self.r_current_page = 1  # 当前背包的分页--右侧
        self.r_max_page = 1  # 最大分页数量--- 动态根据传入的道具数量来控制--右侧
        # 生成格子索引
        self.items_index_dict: dict[str, bool] = {}

        self.shop_size = [500, 400]

        # 道具锁定框
        self.item_lock = None
        # 道具描述UI的道具图片背景
        self.icon_item_bg = None

        # 用于判断点击的数组
        self.__GUI_rect_list = []

        self.__select_item = None
        self.__hover_item = None
        self.__drag = False
        # 道具的详情Surface
        self.__curr_item_detail = None

        # 当前商城的交易类型, 是出售还是购买
        self.__shop_type: ShopType = ShopType.BUY

        self.__load_ui()

    def __load_ui(self):
        game_ui: GameUI = self.gm.get("游戏UI")

        # 道具锁定框
        self.item_lock = SourceManager.surface_cale(SourceManager.load(f"{SourceManager.ui_system_path}/lock_1.png"),
                                                    [20, 20])
        # 道具描述UI的道具图片背景
        self.icon_item_bg = SourceManager.surface_cale(
            SourceManager.load(f"{SourceManager.ui_system_path}/icon_skill_bg.png"), [60, 60])

        shop_left_bg = SourceManager.surface_cale(SourceManager.load(f"{SourceManager.ui_system_path}/window_shop.png"),
                                                  [250, self.shop_size[1] - 30])
        shop_right_bg = SourceManager.load(f"{SourceManager.ui_system_path}/window_empty.png")
        shop_right_bg = SourceManager.surface_cale(shop_right_bg, [250, 290])
        dialog_title = SourceManager.surface_cale(
            SourceManager.load(f"{SourceManager.ui_system_path}/dialog_title.png"), [self.shop_size[0], 32])

        shop_bg = pygame.Surface(tuple(self.shop_size), pygame.SRCALPHA)
        shop_bg.blit(dialog_title, (0, 0))
        shop_bg.blit(shop_left_bg, (0, 30))
        shop_bg.blit(shop_right_bg, (250, 30), (5, 20, shop_right_bg.width, shop_right_bg.height))

        [_, rect, _] = game_ui.load_system_ui(shop_bg,
                                              self.shop_size,
                                              "middle",
                                              {
                                                  "name": "游戏商城",
                                                  "mouse_down": self.mouse_down,
                                                  "mouse_up": self.mouse_up,
                                                  "mouse_move": self.mouse_move,
                                                  "mouse_out": self.mouse_out,
                                                  "mouse_double_click": self.mouse_double_click,
                                                  "mouse_scroll_wheel_up": self.mouse_scroll_wheel_up,
                                                  "mouse_scroll_wheel_down": self.mouse_scroll_wheel_down,
                                                  "update_event": self.render,
                                                  "drag": True,
                                                  "drag_rect": ["auto", "auto", "-25px", "35"],
                                                  "bag_offset": pygame.Rect([25, 180, 200, 172]),
                                                  "bag_size": [45, 40],
                                                  "item_event": None,
                                                  "item_hover_event": None,
                                                  "update_blit": self.__update_blit,
                                                  "listen_keyboard": lambda: True,
                                                  "un_allow": True  # 显示此UI的时候 禁止其他操作, 除了另一个UI
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
                               [45, 45],
                               "middle",
                               {
                                   "name": "item_selected",
                               }, sort=True)
        # 切换上一页
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
                                                                         "is_share": True
                                                                     },
                                                                     pos=[20, 360])
        # 切换下一页
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
                                                                             "loc": (80, 360),
                                                                         },
                                                                         "is_share": True
                                                                     },
                                                                     pos=[80, 360])

        # [_, btn_add_rect, btn_add_params] = game_ui.load_system_ui(f"{SourceManager.ui_system_path}/btn_add.png",
        #                                                            [76, 19],
        #                                                            options=
        #                                                            {
        #                                                                "name": "btn_add",
        #                                                                "mouse_down": self.btn_add,
        #                                                                "frame": {
        #                                                                    "size": 19,
        #                                                                    "count": 2,
        #                                                                    "index": 0,
        #                                                                    "target_index": 2,
        #                                                                    "loc": (80, 360),
        #                                                                },
        #                                                                "is_share": True
        #                                                            },
        #                                                            pos=[205, 290])
        # [_, btn_dec_rect, btn_dec_params] = game_ui.load_system_ui(f"{SourceManager.ui_system_path}/btn_dec.png",
        #                                                            [76, 19],
        #                                                            options=
        #                                                            {
        #                                                                "name": "btn_dec",
        #                                                                "mouse_down": self.btn_dec,
        #                                                                "frame": {
        #                                                                    "size": 19,
        #                                                                    "count": 2,
        #                                                                    "index": 0,
        #                                                                    "target_index": 2,
        #                                                                    "loc": (80, 360),
        #                                                                },
        #                                                                "is_share": True
        #                                                            },
        #                                                            pos=[225, 290])

        # 购买按钮
        [_, btn_buy_rect, btn_buy_params] = game_ui.load_system_ui(f"{SourceManager.ui_system_path}/button2.png",
                                                                   [240, 20],
                                                                   options=
                                                                   {
                                                                       "name": "button_buy_UI",
                                                                       "mouse_down": self.buy_shop,
                                                                       "frame": {
                                                                           "size": 60,
                                                                           "count": 2,
                                                                           "index": 0,
                                                                           "loc": (160, 363),
                                                                       },
                                                                       "label": {
                                                                           "text": "购买",
                                                                           "size": 11
                                                                       },
                                                                   }, sort=True)

        # 切换上一页
        [_, btn_prev_r_rect, btn_prev_r_params] = game_ui.load_system_ui(f"{SourceManager.ui_system_path}/btn_left.png",
                                                                         [72, 18],
                                                                         options=
                                                                         {
                                                                             "name": "button_prev",
                                                                             "mouse_down": self.prev_page_r,
                                                                             "frame": {
                                                                                 "size": 18,
                                                                                 "count": 2,
                                                                                 "index": 0,
                                                                                 "target_index": 2,
                                                                                 "loc": (20, 360),
                                                                             },
                                                                             "is_share": True
                                                                         },
                                                                         pos=[260, 270])
        # 切换下一页
        [_, btn_next_r_rect, btn_next_r_params] = game_ui.load_system_ui(
            f"{SourceManager.ui_system_path}/btn_right.png",
            [72, 18],
            options=
            {
                "name": "button_next",
                "mouse_down": self.next_page_r,
                "frame": {
                    "size": 18,
                    "count": 2,
                    "index": 0,
                    "target_index": 2,
                    "loc": (80, 360),
                },
                "is_share": True
            },
            pos=[320, 270])

        self.__GUI_rect_list = [
            [btn_prev_rect, btn_prev_params],
            [btn_next_rect, btn_next_params],
            [btn_buy_rect, btn_buy_params],
            # [btn_add_rect, btn_add_params],
            # [btn_dec_rect, btn_dec_params],
            [btn_prev_r_rect, btn_prev_r_params],
            [btn_next_r_rect, btn_next_r_params]
        ]

    def add_shops(self, items: list, npc_name: str, shop_type: ShopType):
        """将传入的道具ID追加到商城"""
        self.__shop_type = shop_type
        self.r_items.clear()
        self.r_current_page = 1
        self.r_max_page = 1
        self.current_page = 1
        self.max_page = 1
        # 传入的道具和当前已经创建的是否全部一致, 如果有不一致的那就清空当前的商城, 避免同一个NPC一直重复的创建Item
        if len(self.items) == len(items) and shop_type == ShopType.BUY:
            for i in range(len(self.items)):
                if self.items[i].ID != items[i]:
                    self.items.clear()
                    break
        else:
            self.items.clear()
        game_ui: "GameUI" = self.gm.get("游戏UI")
        game_ui.set_btn_text("button_buy_UI", "购买" if shop_type == ShopType.BUY else "出售")

        if len(self.items) == 0:
            for item in items:
                self.add_item(item)

            self.update_blit = True
            if game_ui.get_surface_show("游戏商城"):
                return

        if len(items) == 0:
            self.update_blit = True

        self.shop_name = f"{npc_name}的店铺"
        game_ui.change_ui_layer("游戏商城", center=True)
        self.__select_item = None
        self.__hover_item = None

    def add_item(self, item: str | Item, total: int = 0):
        """向商城添加物品
        @:param 道具的ID或者道具的实例
        """
        item_id = item if type(item) == str else item.ID
        # 绑定的道具和禁止出售的道具不允许出售-- 显示出来吧. 不然玩家看不见这个道具, 还以为闹鬼了
        # if self.__shop_type == ShopType.SELL:
        #     if item.bind or not item.can_shop:
        #         return
        item_data: dict[str, str] = SourceManager.get_csv("items", str(item_id))
        if item_data is None:
            GameToastManager.add_message(f"无法追加商品:[{item_id}], 不存在的道具信息")
            GameLogManager.log_service_error(f"无法追加商品:[{item_id}], 不存在的道具信息")
            return

        # 是否指定了默认数量
        if total > 0:
            item_data["初始使用次数"] = str(total)

        x, y, page = self.calc_page_loc(len(self.items))
        item_data["__pos"] = [page, x, y]

        self.max_page = page + 1

        new_item = Item(item_data)
        if self.__shop_type == ShopType.SELL:
            new_item.bind = item.bind
            new_item.count = item.count
            new_item.enhance_level = item.enhance_level

        self.items.append(new_item)

    def get_item_surface(self, sur_width: int, sur_height: int, source_items: list, _dir: str):
        """
        将当前的所有商品都转为surface,用于渲染
        :param source_items:
        :param sur_width:
        :param sur_height:
        :param _dir: "L" 左侧 "R" 右侧
        :return:
        """
        mask_sur = pygame.Surface((sur_width, sur_height), pygame.SRCALPHA)

        max_len = len(source_items)
        start_index = ((self.current_page if _dir == "L" else self.r_current_page) - 1) * self.max_capacity
        for i in range(start_index, start_index + self.max_capacity):
            if i >= max_len:
                break
            item = source_items[i]
            item_page, item_row, item_column = item.get_pos()
            mask_sur.blit(item.icon, ((item_column * 46) + 12, (item_row * 47) + 40))
            # 是否可堆叠, 可堆叠的还需要显示数量
            if item.can_stack and item.count > 1:
                mask_sur.blit(
                    self.gm.game_font.get_text_surface_line(str(item.count), True, font_color="#FFFFFF", bolder=True),
                    ((item_column * 46) + 42 - (len(str(item.count)) * 2), (item_row * 46) + 68))
            if item.bind:
                mask_sur.blit(self.item_lock, (item_column * 46 + 20, (item_row * 47) + 40))

        return mask_sur

    def remove_item(self, item_uid: str):
        """从商城移除道具, 后续用来用作限购商品,  或者弄成冷却购买的
        @:return  返回是否扣除成功的状态
        """
        for item in self.items:
            if item.UID == str(item_uid):
                self.items.remove(item)
                return True
        return False

    def prev_page(self):
        """切换上一页"""
        self.current_page = (self.current_page - 2) % self.max_page + 1
        self.__select_item = None

    def next_page(self):
        """切换下一页"""
        self.current_page = self.current_page % self.max_page + 1
        self.__select_item = None

    """右侧背包"""

    def prev_page_r(self):
        """切换上一页"""
        self.r_current_page = (self.r_current_page - 2) % self.r_max_page + 1
        self.__select_item = None

    def next_page_r(self):
        """切换下一页"""
        self.r_current_page = self.r_current_page % self.r_max_page + 1
        self.__select_item = None

    def get_item_by_id(self, item_id: str) -> list[Item]:
        """根据道具的真实ID获取当前在背包里面的该道具"""
        item_arr: list[Item] = []
        for item in self.items:
            if item.ID == str(item_id):
                item_arr.append(item)
        return item_arr

    def get_item_by_uid(self, item_uid: str) -> Item | None:
        """根据道具的UID获取当前在商城里面的该道具"""
        for item in self.items:
            if item.UID == str(item_uid):
                return item
        return None

    def get_item_by_loc(self, bag_pos: list[int]) -> Item | None:
        """根据道具的坐标获取当前在商城里面的该道具"""
        for item in self.items:
            [page, x, y] = item.get_pos()
            if x == bag_pos[0] and y == bag_pos[1] and self.current_page == page + 1:
                return item
        return None

    def mouse_down(self):
        mouse_pos = pygame.mouse.get_pos()
        game_ui: "GameUI" = self.gm.get("游戏UI")
        bag_sprite = game_ui.get_surface_sprite("游戏商城")  # 需要加上背包的偏移
        # 小于拖拽区域高度的只能是关闭按钮了
        if mouse_pos[1] <= int(bag_sprite.get("rect").y) + int(bag_sprite.get("drag_rect")[3]):
            x_offset = int(bag_sprite.get("drag_rect")[2]) - bag_sprite.get("rect").width
            if mouse_pos[0] > int(bag_sprite.get("rect").x) + int(bag_sprite.get("rect").width) + x_offset:
                game_ui.change_ui_layer("游戏商城")
                return

        check_bag = self.__hover_item
        if check_bag[0]:
            item: Item = check_bag[1]
            if item:
                if not self.__select_item or self.__select_item.get("uid") != item.UID:
                    self.__select_item = {
                        "ID": item.ID,
                        "pos": check_bag[2],
                        "texture": SourceManager.set_surface_alpha(item.avatar, 120),
                        "uid": item.UID,
                        # "count": item.count,
                        # "price": item.points if item.points > 0 and self.__shop_type == ShopType.BUY else item.money,
                        # "total_price": item.points if item.points > 0 and self.__shop_type == ShopType.BUY else item.money,
                        # 首次点击的时候不应该有数量
                        "count": 0,
                        # 单价可以显示, 毕竟不会变化
                        "price": item.points if item.points > 0 and self.__shop_type == ShopType.BUY else item.money,
                        "total_price": 0,
                        "target": check_bag[4],
                        "item": item
                    }
            else:
                self.__select_item = None
            return

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
            return

        self.update_blit = True

    def mouse_move(self):
        check_bag = self.__check_bag()
        self.__hover_item = check_bag
        self.__drag = False
        if check_bag[0]:
            self.__drag = True
            self.update_blit = True
            item: Item = check_bag[1]
            if item:
                if self.__curr_item_detail is None or (
                        self.__curr_item_detail and self.__curr_item_detail.get("uid") != item.UID):
                    mask_rect = check_bag[3]
                    mask_rect[0] = max(mask_rect[0] - 200, 0)
                    mask_rect[1] = max(mask_rect[1] - 50, 0)
                    self.__set_item_detail(item, mask_rect)

                return

        self.__curr_item_detail = None

    def mouse_out(self):
        self.__curr_item_detail = None

    def mouse_double_click(self):
        check_bag = self.__check_bag()
        self.__hover_item = check_bag
        if check_bag[0] and check_bag[1]:
            item: Item = check_bag[1]
            if self.__shop_type == ShopType.SELL:
                # 如果类型是出售, 那么判断当前道具是否允许进行交易  或者是否绑定了. 绑定道具不允许出售
                if not item.can_trade or not item.can_shop or item.bind:
                    GameToastManager.add_message(f"道具:[{item.name}]禁止交易")
                    return
            self.change_item(item)
            if self.__select_item and self.__select_item.get("uid") == item.UID:
                self.__select_item["count"] += 1
                self.__select_item[
                    "total_price"] = item.points if item.points > 0 and self.__shop_type == ShopType.BUY else item.money * \
                                                                                                              self.__select_item[
                                                                                                                  "count"]
        return

    def mouse_scroll_wheel_down(self):
        """
        UI的滚轮向下事件
        :return:
        """
        pass
        # GameLogManager.log_service_debug("向下")
        # check_bag = self.__hover_item
        # if check_bag[0]:
        #     GameLogManager.log_service_debug(check_bag)

    def mouse_scroll_wheel_up(self):
        """
        UI的滚轮向上事件
        :return:
        """
        pass
        # GameLogManager.log_service_debug("向上")
        # check_bag = self.__hover_item
        # if check_bag[0]:
        #     GameLogManager.log_service_debug(check_bag)

    def render(self):
        if self.__select_item:
            self.update_blit = True
            game_ui: "GameUI" = self.gm.get("游戏UI")
            item_cursor_sprite = game_ui.get_surface_sprite("item_cursor")
            frame_index = item_cursor_sprite.get("frame").get("index")
            if item_cursor_sprite.get("frame").get("time") > 0:
                item_cursor_sprite.get("frame")["time"] -= 1
            else:
                item_cursor_sprite.get("frame")["time"] = item_cursor_sprite.get("frame").get("timer")
                item_cursor_sprite.get("frame")["index"] = (frame_index + 1) % item_cursor_sprite.get("frame").get(
                    "count")

        if self.__curr_item_detail:
            self.gm.game_win.blit(self.__curr_item_detail.get("texture"), self.__curr_item_detail.get("rect"))

    def __check_bag(self):
        """检查是否在背包的道具区域
        @return  如果没有匹配, 那么就返回 [False]
         否则 返回 [True, 当前得到的道具, 主角对象, 当前鼠标计算的背包格子]
        """
        mouse_pos = pygame.mouse.get_pos()
        target = {
            "bag_offset": pygame.Rect([12, 68, self.shop_size[0], 62]),
            "bag_size": [46, 46]
        }
        # 右边区域的偏移 -- left top right , bottom
        right_bag_offset = [255, 45, 225, 180]

        game_ui: "GameUI" = self.gm.get("游戏UI")
        bag_offset: pygame.Rect = target.get("bag_offset")
        rect: pygame.Rect = game_ui.get_surface_sprite("游戏商城").get("rect")

        left_offset = rect.x + bag_offset.x
        top_offset = rect.y + bag_offset.y
        # right_offset = 10
        bottom_offset = 160
        box_width, box_height = target.get("bag_size")

        # 判断当前鼠标的位置是左边还是右边的格子
        if mouse_pos[0] - rect.x > right_bag_offset[0] + 5 and mouse_pos[1] - rect.y > right_bag_offset[1] and \
                mouse_pos[0] < rect.x + right_bag_offset[2] + right_bag_offset[0] and \
                mouse_pos[1] < rect.y + right_bag_offset[3] + right_bag_offset[1]:

            bag_pos = [int((mouse_pos[1] - top_offset + 15) / box_width),
                       int((mouse_pos[0] - left_offset - 15) / box_height)]
            # 将二维坐标转为一维索引
            item_index = (bag_pos[1] - self.column) + (bag_pos[0] * self.column) + (
                    self.r_current_page - 1) * self.max_capacity

            item = None
            if 0 <= item_index < len(self.r_items):
                item = self.r_items[item_index]
            # 将当前的格子坐标转换为精准的屏幕坐标
            bag_pos_scene = [bag_pos[1] * box_height + left_offset, bag_pos[0] * box_width + top_offset]
            return [True, item, bag_pos, bag_pos_scene, "R"]
        elif left_offset <= mouse_pos[0] < rect.x + right_bag_offset[0] - 15 and top_offset <= mouse_pos[
            1] <= rect.bottom - bottom_offset:
            bag_pos = [int((mouse_pos[1] - top_offset) / box_width), int((mouse_pos[0] - left_offset) / box_height)]

            # 将二维坐标转为一维索引
            item_index = bag_pos[1] + (bag_pos[0] * self.column) + (self.current_page - 1) * self.max_capacity
            item = None
            if 0 <= item_index < len(self.items):
                item = self.items[item_index]
            # 将当前的格子坐标转换为精准的屏幕坐标
            bag_pos_scene = [bag_pos[1] * box_height + left_offset, bag_pos[0] * box_width + top_offset]
            return [True, item, bag_pos, bag_pos_scene, "L"]
        return [False]

    def __update_blit(self):
        """用于提供给游戏UI进行重绘的方法"""
        if not self.update_blit:
            return

        self.update_blit = False
        game_ui: "GameUI" = self.gm.get("游戏UI")
        bag_sur = game_ui.get_surface_ui("游戏商城")

        item_sur = self.get_item_surface(240, 400, self.items, "L")
        if item_sur:
            bag_sur.blit(item_sur, (0, 20))
        r_item_sur = self.get_item_surface(240, 400, self.r_items, "R")
        if r_item_sur:
            bag_sur.blit(r_item_sur, (245, 5))
        if self.__hover_item and self.__hover_item[0]:
            item_selected = game_ui.get_surface_ui("item_selected")
            box_offset = [10 if self.__hover_item[4] == "L" else 19, 62 if self.__hover_item[4] == "L" else 46]
            box_multiple = [46 if self.__hover_item[4] == "L" else 47, 46 if self.__hover_item[4] == "L" else 46]
            bag_pos = ((self.__hover_item[2][1] * box_multiple[0]) + box_offset[0],
                       (self.__hover_item[2][0] * box_multiple[1]) + box_offset[1])
            bag_sur.blit(item_selected, bag_pos)

        # 显示道具的选中框
        if self.__select_item:
            item_cursor_sprite = game_ui.get_surface_sprite("item_cursor")
            item_cursor = game_ui.get_surface_ui("item_cursor")
            frame_size = item_cursor_sprite.get("frame").get("size")
            frame_index = item_cursor_sprite.get("frame").get("index")

            box_offset = [10 if self.__select_item["target"] == "L" else 20,
                          62 if self.__select_item["target"] == "L" else 46]
            box_multiple = [46 if self.__select_item["target"] == "L" else 47,
                            46 if self.__select_item["target"] == "L" else 46]
            bag_pos = ((self.__select_item["pos"][1] * box_multiple[0]) + box_offset[0],
                       (self.__select_item["pos"][0] * box_multiple[1]) + box_offset[1])
            bag_sur.blit(item_cursor, bag_pos, (frame_index * frame_size, 0, frame_size, frame_size))

            # 显示商品的购买数量和价格信息
            bag_sur.blit(self.gm.game_font.get_text_surface_line(self.__select_item["price"], True, 13),
                         (115, 275))  # 单价
            bag_sur.blit(self.gm.game_font.get_text_surface_line(self.__select_item["count"], True, 13),
                         (115, 298))  # 数量
            bag_sur.blit(self.gm.game_font.get_text_surface_line(self.__select_item["total_price"], True, 13),
                         (115, 319))  # 总价

        # 渲染按钮
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
                bag_sur.blit(self.gm.game_font.get_text_surface_line(params.get("label").get("text"), True,
                                                                     params.get("label").get("size")),
                             (
                                 params.get("frame").get("loc")[0] + lab_left,
                                 params.get("frame").get("loc")[1] + lab_top))

        # 页码
        bag_sur.blit(
            self.gm.game_font.get_text_surface_line(f"{self.current_page} / {self.max_page}", True, 15, "#436EEE"),
            (45, 362))

        # 页码--右侧
        bag_sur.blit(
            self.gm.game_font.get_text_surface_line(f"{self.r_current_page} / {self.r_max_page}", True, 15, "#436EEE"),
            (285, 272))

        # 商铺名称
        name_text_sur = self.gm.game_font.get_text_surface_line(str(self.shop_name), True, 13)
        name_text_width, _ = self.gm.game_font.get_text_size(self.shop_name)
        bag_sur.blit(name_text_sur, (abs(bag_sur.width // 2 - name_text_width) // 2, 33))

        game_ui.set_surface_ui("游戏商城", bag_sur)

        # for i in range(20):
        #     column = i % self.column * 46 + 12
        #     row = i // self.column * 46 + 62
        #     pygame.draw.rect(bag_sur, (255,255,255), (column, row , 46, 46), 1)
        #
        #
        # for i in range(20):
        #     column = i % self.column * 46 + 255
        #     row = i // self.column * 46 + 40
        #     pygame.draw.rect(bag_sur, (255,255,255), (column, row , 46, 46), 1)

    def __set_item_detail(self, item: Item | None, loc: list):
        """显示道具的描述"""
        if item is None:
            self.__curr_item_detail = item
            return
        mask_sur = pygame.Surface((200, 180), pygame.SRCALPHA)
        # 填充圆角矩形背景
        pygame.draw.rect(mask_sur, (0, 0, 0, 190), (0, 0, mask_sur.width, mask_sur.height), border_radius=5)
        mask_sur.blit(self.icon_item_bg, (0, 0))
        mask_sur.blit(item.avatar, (2, 3))
        # 绑定状态
        if item.bind:
            mask_sur.blit(self.item_lock, (5, 40))
        # 道具名称
        mask_sur.blit(self.gm.game_font.get_text_surface_line(item.name, True, 15, "#FFD700"),
                      (65, 5))
        if item.bind:
            mask_sur.blit(self.gm.game_font.get_text_surface_line("已绑定", True, 11, "#FF6A6A"),
                          (165, 25))
        else:
            mask_sur.blit(self.gm.game_font.get_text_surface_line("未绑定", True, 11, "#228B22"),
                          (165, 25))
        mask_sur.blit(
            self.gm.game_font.get_text_surface_line(f"使用等级: [#FF7F24]{item.level}", True, 11, "#FFFFFF"),
            (65, 30))
        mask_sur.blit(self.gm.game_font.get_text_surface_line(f"数量:{item.count}", True, 11, "#FFFFFF"),
                      (65, 45))
        # 道具描述
        mask_sur.blit(self.gm.game_font.get_multiple_text(item.description, 195, 85, True, 13, "#32CD32"),
                      (5, 85))
        # 道具单价
        price_text = f"点卡: {item.points}" if item.points > 0 and self.__shop_type == ShopType.BUY else f"金币: {item.money}"
        mask_sur.blit(self.gm.game_font.get_text_surface_line(price_text, True, 12, "#EEEE00"),
                      (5, 65))

        self.update_blit = True
        self.__curr_item_detail = {
            "uid": item.UID,
            "texture": mask_sur,
            "rect": loc
        }

    def buy_shop(self):
        if not self.__select_item:
            return
        u_player = self.gm.get("主角")
        if u_player.bag.get_target_item_count(self.__select_item.get("ID"), self.__select_item.get("count")):
            u_player.bag.add_item(self.__select_item.get("ID"), self.__select_item.get("count"))
        self.clear_item()

    # def btn_add(self):
    #     if not self.__select_item:
    #         return
    #     total = int(self.__select_item.get("count"))
    #     total += 1
    #     self.__select_item["count"] = total
    #     self.__select_item["total_price"] = self.__select_item["price"] * self.__select_item["count"]
    #     self.change_item(self.__select_item["item"])
    #
    # def btn_dec(self):
    #     if not self.__select_item:
    #         return
    #     total = int(self.__select_item.get("count"))
    #     total -= 1
    #     if total == 0:
    #         self.change_item(self.__select_item["item"], "R")
    #         self.__select_item = None
    #         return
    #     self.__select_item["count"] = total
    #     self.__select_item["total_price"] = self.__select_item["price"] * self.__select_item["count"]
    #
    #     for _item in self.r_items:
    #         if _item.UID == self.__select_item["item"].UID:
    #             _item.count = total
    #             break

    def change_item(self, item: Item, box_target: str = "L"):
        """购入/出售 执行道具的位置切换"""
        if self.__hover_item[0]:
            box_target = self.__hover_item[4]
        if self.__shop_type == ShopType.BUY:
            if box_target == "L":
                self.__append_r_item(item)
            else:
                for _item in self.r_items:
                    if _item.UID == item.UID:
                        self.r_items.remove(_item)
                        break
                total = 0
                for _item in self.r_items:
                    x, y, page = self.calc_page_loc(total)
                    self.r_max_page = page + 1
                    _item.set_pos(x, y, page)
                    total += 1
        else:
            # 出售道具的话直接扣减道具
            if box_target == "L":
                self.__append_r_item(item, False, True)
            else:
                self.__append_l_item(item, False, True)

    def calc_page_loc(self, item_len: int):
        """根据传入的背包计算对应的x,y,page"""
        page = item_len // self.max_capacity
        index_in_page = item_len % self.max_capacity
        x = index_in_page // self.column
        y = index_in_page % self.column

        return x, y, page

    def __append_l_item(self, item: Item, is_clone: bool = True, remove_r: bool = None):
        x, y, page = self.calc_page_loc(len(self.items))
        self.max_page = page + 1
        if is_clone:
            buy_item = item.clone()
            buy_item.set_pos(x, y, page)
            self.items.append(buy_item)
        else:
            item.set_pos(x, y, page)
            self.items.append(item)
        if remove_r:
            for __item in self.r_items:
                if __item.UID == item.UID:
                    self.items.remove(__item)
                    break

            if len(self.r_items) <= self.max_capacity * (self.r_current_page - 1):
                self.r_current_page = 1
            total = 0
            for _item in self.r_items:
                x, y, page = self.calc_page_loc(total)
                self.r_max_page = page + 1
                _item.set_pos(x, y, page)
                total += 1

    def __append_r_item(self, item: Item, is_clone: bool = True, remove_l: bool = None):
        if item.can_stack and self.__shop_type == ShopType.BUY:
            for _item in self.r_items:
                if _item.ID == item.ID:
                    _item.count += item.count
                    return
        x, y, page = self.calc_page_loc(len(self.r_items))
        self.r_max_page = page + 1
        if is_clone:
            buy_item = item.clone()
            buy_item.set_pos(x, y, page)
            self.r_items.append(buy_item)
        else:
            item.set_pos(x, y, page)
            self.r_items.append(item)

        if remove_l:
            for __item in self.items:
                if __item.UID == item.UID:
                    self.items.remove(__item)
                    break
            if len(self.items) <= self.max_capacity * (self.current_page - 1):
                self.current_page = 1
            total = 0
            for _item in self.items:
                x, y, page = self.calc_page_loc(total)
                self.max_page = page + 1
                _item.set_pos(x, y, page)
                total += 1

    def clear_item(self):
        """
        清空已加入购入栏的道具
        :return:
        """
        self.r_items.clear()
        self.r_current_page = 1
        self.r_max_page = 1
        self.current_page = 1
        self.max_page = 1

        self.__select_item = None
        self.__hover_item = None
