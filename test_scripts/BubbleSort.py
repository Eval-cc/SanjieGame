#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：BubbleSort.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/7/12 16:20 
@Describe: 冒泡排序
"""

import random
import time

class Item:
    def __init__(self,ID:int):
        self.name = f"道具_{random.randint(20, 5000)}"
        self.ID = ID
        self.count = random.randint(20,100)

    def __str__(self):
        return f"{self.ID}_{self.count}"

    def __get__(self, instance, owner):
        return f"{self.ID}_{self.count}"


def quick_sort(arr):
    if len(arr) <= 1:
        return arr

    pivot = arr[0]
    left = []
    right = []

    for x in arr[1:]:
        if x.ID == pivot.ID:
            if x.count < pivot.count:
                left.append(x)
                continue
        elif x.ID < pivot.ID:
            left.append(x)
            continue

        right.append(x)

    return quick_sort(left) + [pivot] + quick_sort(right)


if __name__ == "__main__":
    # 随机生成包含 50 个整数的数组
    # original = [random.randint(20, 5000) for _ in range(50000)]
    original = [Item(random.randint(20, 22)) for _ in range(10)]
    # print("原始数组（前10项）：", original[:10], "...")

    # 快速排序计时
    start = time.time()
    quick_result = quick_sort(original)
    end = time.time()
    [print(item) for item in quick_result]
    # print("\n快速排序结果（前10项）：", quick_result, "...")
    print("快速排序耗时：%.6f 秒" % (end - start))

