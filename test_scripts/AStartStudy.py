#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project : 三界奇谈
@File    : AStartStudy.py
@IDE     : PyCharm
@Author  : eval-
@Email   : eval-email@qq.com
@Date    : 2025/10/14 22:25
@Desc    : A*简略版学习
"""

#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：FindPath_AStar.py
@Author  ：eval-
@Desc    ：简洁版 A* 寻路（8方向 + 避墙）
"""
import heapq
import math


class AStarPathfinder:
    def __init__(self, grid):
        self.grid = grid
        self.w = len(grid[0])
        self.h = len(grid)

    def _valid(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h and str(self.grid[y][x]) != "0"

    def _near_wall(self, x, y):
        """靠近障碍则返回 True"""
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.w and 0 <= ny < self.h and str(self.grid[ny][nx]) == "0":
                return True
        return False

    def heuristic(self, a, b):
        """欧几里得距离"""
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def find_path(self, start, end):
        if not self._valid(*start) or not self._valid(*end):
            return []

        open_list = [(0, start)]
        came, g = {}, {start: 0}
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1),
                (-1, -1), (-1, 1), (1, -1), (1, 1)]

        while open_list:
            _, cur = heapq.heappop(open_list)
            if cur == end:
                return self._reconstruct(came, cur)

            for dx, dy in dirs:
                nx, ny = cur[0] + dx, cur[1] + dy
                if not self._valid(nx, ny):
                    continue
                cost = math.hypot(dx, dy)
                if self._near_wall(nx, ny):
                    cost += 0.3  # 避墙代价
                new_g = g[cur] + cost
                if (nx, ny) not in g or new_g < g[(nx, ny)]:
                    g[(nx, ny)] = new_g
                    f = new_g + self.heuristic((nx, ny), end)
                    heapq.heappush(open_list, (f, (nx, ny)))
                    came[(nx, ny)] = cur
        return []

    def _reconstruct(self, came, cur):
        path = [cur]
        while cur in came:
            cur = came[cur]
            path.append(cur)
        return path[::-1]


# ===== 示例用法 =====
if __name__ == "__main__":
    grid = [
        ['', '', '', '', '0', '', '', '', '', ''],
        ['', '', '', '', '0', '', '', '', '', ''],
        ['', '', '', '', '0', '', '', '0', '', ''],
        ['', '', '', '', '0', '', '0', '', '', ''],
        ['', '', '', '', '0', '0', '', '', '', ''],
        ['', '', '', '', '', '', '', '0', '', ''],
        ['', '', '', '', '0', '0', '0', '0', '', ''],
        ['', '', '', '', '0', '', '', '', '', ''],
        ['', '', '', '', '0', '', '', '', '', ''],
        ['', '', '', '', '', '', '', '', '', '']
    ]

    start, end = (0, 0), (9, 9)
    astar = AStarPathfinder(grid)
    path = astar.find_path(start, end)
    print("路径:", path)

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

