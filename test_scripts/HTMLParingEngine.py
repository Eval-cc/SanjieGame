#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：HTMLParingEngine.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/7/19 12:58 
@Describe: 游戏对话的HTML解析引擎
"""
from html.parser import HTMLParser
import json


class DOMNode:
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []
        self.text = ""


class AppParser(HTMLParser):
    def __init__(self, html_str: str):
        super().__init__()
        self.root = None
        self.node_stack = []  # 节点栈
        self.in_app_div = False
        self.app_div_node = None

        self.feed(html_str)

    def handle_starttag(self, tag, attrs):
        node = DOMNode(tag, attrs)

        if self.root is None:
            self.root = node
        else:
            self.node_stack[-1].children.append(node)

        self.node_stack.append(node)

        if tag == 'div' and ('id', 'app') in attrs:
            self.in_app_div = True
            self.app_div_node = node

    def handle_endtag(self, tag):
        if self.node_stack:
            self.node_stack.pop()

        if self.in_app_div and tag == 'div':
            self.in_app_div = False

    def handle_data(self, data):
        if self.node_stack:
            self.node_stack[-1].text += data

    def get_paring_engine(self):
        """
        返回解析结果
        :return: 字典结构的HTML解析结果
        """
        if self.app_div_node:
            return self._node_to_dict(self.app_div_node)

        print("未找到 id='app' 的 div")
        return None

    def _node_to_dict(self, node):
        """
        将DOMNode递归转换为字典结构
        """
        node_dict = {
            "tag": node.tag,
            "attrs": node.attrs,
            "text": node.text.strip() if node.text.strip() else None,
            "children": []
        }

        # 递归处理子节点
        for child in node.children:
            child_dict = self._node_to_dict(child)
            node_dict["children"].append(child_dict)

        return node_dict


if __name__ == "__main__":
    html_path = r"E:\Project Code\Python Code\a_pygame\三界奇谈\resources\sv_task\common.html"
    html = ""
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    parser = AppParser(html)
    result = parser.get_paring_engine()
    pretty_json = json.dumps(result, indent=4, ensure_ascii=False)
    print(pretty_json)