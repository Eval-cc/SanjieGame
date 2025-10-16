#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：color_replace.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/7/14 09:15 
@Describe: 颜色替换测试
"""
import re

# color_str = "哈哈,什么[#B22222]666[#8B4726]你在说什么呢"

# "哈哈,什么[#B22222]666[#8B4726]你在说什么呢,[#B22222]8888"
#
# format_dict = [{
#     "label":"哈哈,什么",
#     "color":"None",
# },{
#     "label":"666",
#     "color":"#B22222"
# },{
#     "label":"你在说什么呢",
#     "color":"#8B4726"
# },{
#     "label":"8888",
#     "color":"#B22222"
# }]


if __name__ == "__main__":
    def parse_color_string(format_str: str):
        # 增加对 [#end] 的匹配
        pattern = re.compile(r"(?:\[#([0-9A-Fa-f]{6}|end)])?([^\[#]+)")
        result = []

        current_color = "None"
        for match in pattern.finditer(format_str):
            color_tag, text = match.groups()
            if color_tag:
                if color_tag.lower() == "end":
                    current_color = "None"
                else:
                    current_color = f"#{color_tag}"
            result.append({
                "label": text,
                "color": current_color
            })

        return result


    # 示例
    # color_str = "哈哈[#B22222]666[#8B4726]你在说[#end]什么呢,[#B22222]8888"
    color_str = '[#FF7F24]从真封神借来的武器.[#end] 佳[#FFFFFF]梦[#end]关四将魔礼青所使用的兵器。上有符印，剑到之处如有青风烈火扫过，凡人逢着此风火，四肢成为齑粉'
    format_dict = parse_color_string(color_str)

    from pprint import pprint
    pprint(format_dict)