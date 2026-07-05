#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：TaskParingEngine.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/7/19 19:05 
@Describe: 游戏对话的HTML解析引擎
"""
from html.parser import HTMLParser
from src.manager.GameLogManger import GameLogManager


class DOMNode:
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []
        self.text = ""


class TaskParingEngine(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = None
        self.node_stack = []  # 节点栈
        self.in_app_div = False
        self.app_div_node = None

    def handle_starttag(self, tag, attrs):
        node = DOMNode(tag, attrs)

        if self.root is None:
            self.root = node
        else:
            if len(self.node_stack):
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

    def get_paring_engine(self, html_str: str) -> dict | None:
        """
        返回解析结果
        :return: 字典结构的HTML解析结果
        """
        self.root = None
        self.node_stack = []
        self.in_app_div = False
        self.app_div_node = None
        super().reset()

        self.feed(html_str)
        if self.app_div_node:
            return self._node_to_dict(self.app_div_node)

        GameLogManager.log_service_debug("未找到 id='app' 的 div")
        return None

    def _node_to_dict(self, node):
        """
        将DOMNode递归转换为字典结构
        @:param node 节点
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
