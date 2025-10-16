#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：FindPath_AStart.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email   ：eval-email@qq.com
@Date    ：2025/6/12 23:10
@Describe: 改进版 A* 寻路（支持8方向 + 避墙 + 平滑路径）
"""
import heapq
import math


class AStarPathfinder:
    def __init__(self, grid, avoid_wall=True, smooth_path=True):
        """
        初始化A*寻路器
        :param grid: 二维数组表示的网格，非"0"表示可通行，"0"表示障碍物
        :param avoid_wall: 是否启用避墙代价修正
        :param smooth_path: 是否在结果中进行路径平滑
        """
        self.grid = grid
        self.width = len(grid[0]) if grid else 0
        self.height = len(grid) if grid else 0
        self.avoid_wall = avoid_wall
        self.smooth_enabled = smooth_path

    def heuristic(self, a, b):
        """启发式函数：欧几里得距离"""
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def _is_valid_position(self, pos):
        """检查位置是否在网格内"""
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def _is_blocked(self, x, y):
        """判断是否为障碍物"""
        return str(self.grid[y][x]) == "0"

    def _is_near_wall(self, x, y):
        """判断是否靠近墙体（上下左右方向）"""
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                if str(self.grid[ny][nx]) == "0":
                    return True
        return False

    def _reconstruct_path(self, came_from, current):
        """从终点回溯重构路径"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def _has_obstacle_between(self, a, b):
        """判断两点之间是否有障碍（用于平滑路径）"""
        x1, y1 = a
        x2, y2 = b
        dx, dy = x2 - x1, y2 - y1
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            return False
        for i in range(1, steps):
            x = int(round(x1 + dx * i / steps))
            y = int(round(y1 + dy * i / steps))
            if self._is_blocked(x, y):
                return True
        return False

    def _smooth_path(self, path):
        """去掉多余的折线点"""
        if len(path) <= 2:
            return path
        smooth = [path[0]]
        last = 0
        for i in range(2, len(path)):
            if self._has_obstacle_between(smooth[-1], path[i]):
                smooth.append(path[i - 1])
                last = i - 1
        if last < len(path) - 1:
            smooth.append(path[-1])
        return smooth

    def find_path(self, start, end):
        """A*寻路主逻辑"""
        if not self._is_valid_position(start) or not self._is_valid_position(end):
            return []
        if self._is_blocked(start[0], start[1]) or self._is_blocked(end[0], end[1]):
            return []

        open_list = []
        heapq.heappush(open_list, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self.heuristic(start, end)}
        open_set = {start}

        # 八方向移动
        directions = [
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (1, -1), (-1, 1), (1, 1)
        ]

        while open_list:
            _, current = heapq.heappop(open_list)
            open_set.remove(current)

            if current == end:
                path = self._reconstruct_path(came_from, current)
                if self.smooth_enabled:
                    path = self._smooth_path(path)
                return path

            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                if not self._is_valid_position(neighbor) or self._is_blocked(neighbor[0], neighbor[1]):
                    continue

                # 斜方向代价 √2
                step_cost = math.hypot(dx, dy)
                tentative_g_score = g_score[current] + step_cost

                # 靠近墙体代价修正
                if self.avoid_wall and self._is_near_wall(neighbor[0], neighbor[1]):
                    tentative_g_score += 0.3

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self.heuristic(neighbor, end)

                    if neighbor not in open_set:
                        heapq.heappush(open_list, (f_score[neighbor], neighbor))
                        open_set.add(neighbor)

        return []  # 无路可走


# 示例用法
if __name__ == "__main__":
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

    start = (0, 0)
    end = (9, 9)
    pathfinder = AStarPathfinder(grid, avoid_wall=True, smooth_path=True)
    path = pathfinder.find_path(start, end)

    print("找到的路径:", path)
    print()

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
