#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：FindPath_Theta.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/6/13 21:12 
@Describe: Theta*寻路（A*的改进版，路径更平滑）
"""
import math
import heapq


class ThetaStarPathfinder:
    def __init__(self, passable:list):
        """
        初始化Theta*寻路器
        :param passable: 二维数组表示的网格，0表示可通行，1表示障碍物
        """
        self.grid = passable
        self.width = len(passable[0]) if passable else 0
        self.height = len(passable) if passable else 0

    def heuristic(self, a, b):
        """
        启发式函数：欧几里得距离（更适合Theta*）
        :param a: 起点坐标 (x, y)
        :param b: 终点坐标 (x, y)
        :return: 欧几里得距离
        """
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    def find_path(self, start_pos, end_pos):
        """
        寻找从start到end的最短路径（Theta*算法）
        :param start_pos: 起点坐标 (x, y)
        :param end_pos: 终点坐标 (x, y)
        :return: 路径列表，包含从起点到终点的坐标序列
        """
        # 检查起点和终点是否有效
        if not self._is_valid_position(start_pos) or not self._is_valid_position(end_pos):
            return []

        # 如果起点或终点是障碍物，直接返回空路径
        if str(self.grid[start_pos[1]][start_pos[0]]) == "0":
            return []
        if str(self.grid[end_pos[1]][end_pos[0]]) == "0":
            return []

        # 初始化开放列表(优先队列)和关闭列表
        open_list = []
        heapq.heappush(open_list, (0, start_pos))  # (f_score, position)
        came_from = {}  # 记录路径
        g_score = {start_pos: 0}  # 从起点到当前点的实际距离
        f_score = {start_pos: self.heuristic(start_pos, end_pos)}  # 估计的总距离

        open_set = {start_pos}  # 用于快速查找

        while open_list:
            _, current = heapq.heappop(open_list)
            open_set.remove(current)

            # 如果到达终点，重构路径
            if current == end_pos:
                return self._reconstruct_path(came_from, current)

            # 检查8方向的邻居（Theta*允许对角线移动）
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0),
                           (-1, -1), (-1, 1), (1, -1), (1, 1)]:  # 8方向
                neighbor = (current[0] + dx, current[1] + dy)

                # 检查邻居是否有效且不是障碍物
                if not self._is_valid_position(neighbor) or str(self.grid[neighbor[1]][neighbor[0]]) == "0":
                    continue

                # 计算从起点到邻居的距离
                tentative_g_score = g_score[current] + self._get_move_cost(current, neighbor)

                # 如果这是更好的路径
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    # Theta*的关键改进：检查是否可以"跳过"中间节点
                    if current in came_from:  # 如果当前节点有父节点
                        parent = came_from[current]
                        # 检查parent和neighbor之间是否有直接通路（无障碍物）
                        if self._has_line_of_sight(parent, neighbor):
                            # 如果可以直接连接parent和neighbor，就跳过current
                            came_from[neighbor] = parent
                            g_score[neighbor] = g_score[parent] + self._get_move_cost(parent, neighbor)
                            f_score[neighbor] = g_score[neighbor] + self.heuristic(neighbor, end_pos)
                        else:
                            # 否则，按照A*的方式处理
                            came_from[neighbor] = current
                            g_score[neighbor] = tentative_g_score
                            f_score[neighbor] = tentative_g_score + self.heuristic(neighbor, end_pos)
                    else:
                        # 如果没有父节点（起点情况），按照A*的方式处理
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g_score
                        f_score[neighbor] = tentative_g_score + self.heuristic(neighbor, end_pos)

                    if neighbor not in open_set:
                        heapq.heappush(open_list, (f_score[neighbor], neighbor))
                        open_set.add(neighbor)

        # 没有找到路径
        return []

    def _is_valid_position(self, pos):
        """
        检查位置是否在网格范围内
        :param pos: 坐标 (x, y)
        :return: 是否有效
        """
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def _get_move_cost(self, a, b):
        """
        计算从a到b的移动成本（直线=1，对角线=√2）
        :param a: 起点 (x, y)
        :param b: 终点 (x, y)
        :return: 移动成本
        """
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        if dx + dy == 1:  # 直线移动
            return 1.0
        else:  # 对角线移动
            return math.sqrt(2)

    def _has_line_of_sight(self, a, b):
        """
        检查a和b之间是否有直接通路（无障碍物）
        :param a: 起点 (x, y)
        :param b: 终点 (x, y)
        :return: 是否有直接通路
        """
        x0, y0 = a
        x1, y1 = b
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            if x != x1 or y != y1:  # 如果不是终点
                if str(self.grid[y][x]) == "0":  # 如果路径上有障碍物
                    return False
            else:  # 到达终点
                return True
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def _reconstruct_path(self, came_from, current):
        """
        从终点回溯重构路径
        :param came_from: 记录路径的字典
        :param current: 终点坐标
        :return: 路径列表
        """
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()  # 从起点到终点
        return path


# # 示例用法
if __name__ == "__main__":
    # 示例网格：0表示可通行，1表示障碍物
    grid = [
        ['', '', '', '', '0', '', '', '', '', ''],
        ['', '', '', '', '0', '', '', '', '', ''],
        ['', '', '', '', '0', '', '', '0', '', ''],
        ['', '', '', '', '0', '', '0', '', '', ''],
        ['', '', '', '', '0', '0', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', ''],
        ['', '', '', '', '0', '', '', '', '', ''],
        ['', '', '', '', '0', '', '', '', '', ''],
        ['', '', '', '', '0', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '']
    ]

    pathfinder = ThetaStarPathfinder(grid)
    start = (0, 0)  # 起点
    end = (5, 3)  # 终点

    path = pathfinder.find_path(start, end)
    print("找到的路径:", path)

    # 可视化路径
    if path:
        for y in range(len(grid)):
            row = []
            for x in range(len(grid[0])):
                if (x, y) == start:
                    row.append('S')
                elif (x, y) == end:
                    row.append('E')
                elif (x, y) in path:
                    row.append('*')
                else:
                    row.append('■' if grid[y][x] == "0" else '-')
            print(' '.join(row))