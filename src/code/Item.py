#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：三界奇谈 
@File    ：Item.py
@IDE     ：PyCharm 
@Author  ：eval-
@Email  ： eval-email@qq.com
@Date    ：2025/7/17 20:41 
@Describe: 
"""
from uuid import uuid4

from src.code.SpriteBase import SpriteBase
from src.manager.GameLogManger import GameLogManager
from src.manager.SourceManager import SourceManager
from copy import deepcopy


class Item(SpriteBase):
    # 定义字段映射表：配置文件中的字段名 -> Item类的属性名
    FIELD_MAPPING = {
        'ID': {'attr': 'ID', 'default': None, 'type': str},
        '名称': {'attr': 'name', 'default': None, 'type': str},
        '阶段': {'attr': 'stage', 'default': 1, 'type': int},
        '类型': {'attr': 'type', 'default': None, 'type': int},
        '子类型': {'attr': 'sub_type', 'default': None, 'type': int},
        '神兽ID': {'attr': 'pet_id', 'default': None, 'type': str},
        '分解ID': {'attr': 'decom_id', 'default': None, 'type': str},
        '可锻造': {'attr': 'can_forge', 'default': False, 'type': lambda x: x == '1'},
        '可交易': {'attr': 'can_trade', 'default': False, 'type': lambda x: x == '1'},
        '可商店': {'attr': 'can_shop', 'default': False, 'type': lambda x: x == '1'},
        '可删除': {'attr': 'can_delete', 'default': False, 'type': lambda x: x == '1'},
        '可丢弃': {'attr': 'can_drop', 'default': False, 'type': lambda x: x == '1'},
        '可重叠摆放': {'attr': 'can_stack', 'default': False, 'type': lambda x: x == '1'},
        '是否任务道具': {'attr': 'is_quest_item', 'default': False, 'type': lambda x: x == '1'},
        '不允许融合': {'attr': 'can_not_fuse', 'default': False, 'type': lambda x: x == '1'},
        '价值': {'attr': 'money', 'default': 0, 'type': int},
        '点数': {'attr': 'points', 'default': 0, 'type': int},
        '命中': {'attr': 'hit', 'default': 0, 'type': int},
        '伤害': {'attr': 'damage', 'default': 0, 'type': int},
        '防御': {'attr': 'defense', 'default': 0, 'type': int},
        '闪躲': {'attr': 'dodge', 'default': 0, 'type': int},
        '攻击速度': {'attr': 'attack_speed', 'default': 0, 'type': int},
        '必杀率': {'attr': 'critical_rate', 'default': 0, 'type': int},
        'MaxHp': {'attr': 'max_hp', 'default': 0, 'type': int},
        'MaxMp': {'attr': 'max_mp', 'default': 0, 'type': int},
        '抗火': {'attr': 'fire_resistance', 'default': 0, 'type': int},
        '抗水': {'attr': 'water_resistance', 'default': 0, 'type': int},
        '抗毒': {'attr': 'poison_resistance', 'default': 0, 'type': int},
        '法宝属性': {'attr': 'talisman_attribute', 'default': None, 'type': str},
        '等级需求': {'attr': 'level_requirement', 'default': 0, 'type': int},
        '力量需求': {'attr': 'strength_requirement', 'default': 0, 'type': int},
        '敏捷需求': {'attr': 'agility_requirement', 'default': 0, 'type': int},
        '智力需求': {'attr': 'intelligence_requirement', 'default': 0, 'type': int},
        '精准需求': {'attr': 'accuracy_requirement', 'default': 0, 'type': int},
        '职业需求': {'attr': 'class_requirement', 'default': None, 'type': str},
        '阶段需求': {'attr': 'stage_requirement', 'default': None, 'type': str},
        'Icon': {'attr': 'icon', 'default': None, 'type': str},
        'Sound': {'attr': 'sound', 'default': None, 'type': str},
        '初始使用次数': {'attr': 'count', 'default': 1, 'type': int},
        '最大使用次数': {'attr': 'max_count', 'default': 1, 'type': int},
        '技能ID': {'attr': 'skill_id', 'default': None, 'type': str},
        '套装ID': {'attr': 'set_id', 'default': None, 'type': str},
        '说明': {'attr': 'description', 'default': None, 'type': str},
        '主属性': {'attr': 'primary_attr_id', 'default': 0, 'type': int},
        '副属性': {'attr': 'secondary_attr_id', 'default': 0, 'type': int},
        '过期时间': {'attr': 'expire_time', 'default': 0, 'type': int},
    }

    def __init__(self, item_data: dict):
        super().__init__()
        self.ID: str = ""  # 道具ID
        self.name: str = ""  # 道具名称
        self.stage: int = 0  # 阶段
        self.type: int = 0  # 主类型
        self.sub_type: int = 0  # 子类型
        self.pet_id = None  # 神兽 id
        self.decom_id = None  # 分解ID
        self.can_forge = None  # 可锻造
        self.can_trade = None  # 可交易
        self.can_shop = None  # 可商店（是否可在商店中出售/购买）
        self.can_delete = None  # 可删除
        self.can_drop = None  # 可丢弃
        self.can_stack = None  # 可重叠摆放（是否可以堆叠）
        self.is_quest_item = None  # 是否任务道具
        self.can_not_fuse = None  # 不允许融合
        self.money = None  # 金币
        self.points = None  # 点数
        self.hit = None  # 命中
        self.damage = None  # 伤害
        self.defense = None  # 防御
        self.dodge = None  # 闪躲
        self.attack_speed = None  # 攻击速度
        self.critical_rate = None  # 必杀率（暴击率）
        self.max_hp = None  # MaxHp（最大生命值）
        self.max_mp = None  # MaxMp（最大魔法值）
        self.fire_resistance = None  # 抗火
        self.water_resistance = None  # 抗水
        self.poison_resistance = None  # 抗毒
        self.talisman_attribute = None  # 法宝属性（或 special_attribute）
        self.level_requirement = None  # 等级需求
        self.strength_requirement = None  # 力量需求
        self.agility_requirement = None  # 敏捷需求
        self.intelligence_requirement = None  # 智力需求
        self.accuracy_requirement = None  # 精准需求
        self.class_requirement = None  # 职业需求
        self.stage_requirement = None  # 阶段需求
        self.icon = None  # Icon（图标）
        self.avatar = None
        self.sound = None  # Sound（音效）
        self.count = None  # 初始使用次数
        self.max_count = None  # 最大使用次数
        self.skill_id = None  # 技能ID
        self.set_id = None  # 套装ID
        self.description = None  # 说明
        self.bind = False  # 默认所有的道具都是绑定的
        self.enhance_level = 0  # 强化等级

        self.primary_attr_id = -1  # 主属性 ID (基础攻击、防御等)   暂时应该用不到. 先留着
        self.secondary_attr_id = -1  # 副属性 ID (强化等级、词条等)
        self.expire_time = -1  # 过期时间 (时间戳)

        # 当前道具位于背包的位置, 第一个参数是在第几页, 后面两个是背包的 x, y 坐标系
        self.__pos = [0, 0, 0]

        self.set_data(item_data)

    def set_data(self, item_data: dict):
        # page, x, y = item_data.get("__pos")
        # self.__pos = [int(page), int(x), int(y)]
        # 1. 处理位置信息 (增加安全检查)
        pos_data = item_data.get("__pos")
        if pos_data and len(pos_data) >= 3:
            self.__pos = [int(pos_data[0]), int(pos_data[1]), int(pos_data[2])]
        else:
            # 使用 -1 表示该道具当前不在背包格子内（即在装备栏）
            self.__pos = [-1, -1, -1]

        for config_key, mapping in Item.FIELD_MAPPING.items():
            raw_value = item_data.get(config_key)  # 从配置中取值
            if config_key == "Icon":
                self.avatar = SourceManager.ssurface_scale(
                    SourceManager.load(fr"{SourceManager.ui_item_path}\help\{raw_value}.png"), [55, 55])
                self.icon = SourceManager.ssurface_scale(
                    SourceManager.load(fr"{SourceManager.ui_item_path}\{raw_value}.png"), [40, 40])
                self.rect = self.icon.get_rect()
                continue
            if raw_value is not None:
                # 如果有 type 转换函数，则应用转换
                if 'type' in mapping:
                    value = mapping['type'](raw_value)
                else:
                    value = raw_value
            else:
                # 如果配置中缺少该字段，使用默认值
                value = mapping['default']
            # 赋值给 Item 的属性
            try:
                if not hasattr(self, mapping.get("attr")):
                    raise AttributeError(f"无效字段:[{mapping.get("attr")}]")
                setattr(self, mapping['attr'], value)
            except AttributeError as attrE:
                GameLogManager.log_service_debug(attrE)

    def __str__(self):
        info = {
            "名称": self.name,
            "类型": self.type,
            "价值": f"金钱:{self.money}",
            "伤害": f"伤害:{self.damage}",
            "说明": self.description,
            "位置": self.__pos
        }
        # 将字典格式化为字符串（每行一个属性）
        info_str = " , ".join(f"{key}: {value}" for key, value in info.items())
        return f"[{info_str}]"

    def get_attr_text(self):
        # 构建一个字典，存储要显示的属性和值
        return {
            "名称": self.name,
            "类型": self.type,
            "可锻造": "是" if self.can_forge else "否",
            "可交易": "是" if self.can_trade else "否",
            "可商店": "是" if self.can_shop else "否",
            "可删除": "是" if self.can_delete else "否",
            "可丢弃": "是" if self.can_drop else "否",
            "可重叠摆放": "是" if self.can_stack else "否",
            "是否任务道具": "是" if self.is_quest_item else "否",
            "不允许融合": "是" if self.can_not_fuse else "否",
            "价值": f"金钱:{self.money}",
            "点数": f"点数:{self.points}",
            "命中": f"命中:{self.hit}",
            "伤害": f"伤害:{self.damage}",
            "防御": f"防御:{self.defense}",
            "闪躲": f"闪躲:{self.dodge}",
            "攻击速度": f"攻击速度:{self.attack_speed}",
            "必杀率": f"必杀率:{self.critical_rate}",
            "最大生命值": f"MaxHp:{self.max_hp}",
            "最大魔法值": f"MaxMp:{self.max_mp}",
            "抗火": f"抗火:{self.fire_resistance}",
            "抗水": f"抗水:{self.water_resistance}",
            "抗毒": f"抗毒:{self.poison_resistance}",
            "法宝属性": self.talisman_attribute,
            "等级需求": f"等级需求:{self.level_requirement}",
            "力量需求": f"力量需求:{self.strength_requirement}",
            "敏捷需求": f"敏捷需求:{self.agility_requirement}",
            "智力需求": f"智力需求:{self.intelligence_requirement}",
            "精准需求": f"精准需求:{self.accuracy_requirement}",
            "职业需求": self.class_requirement,
            "阶段需求": self.stage_requirement,
            "预览": self.avatar,
            "初始使用次数": f"初始使用次数:{self.count}",
            "最大使用次数": f"最大使用次数:{self.max_count}",
            "技能ID": self.skill_id,
            "套装ID": self.set_id,
            "说明": self.description,
        }

    def get_attr(self):
        """
        获取装备属性包。
        不再内部计算百分比，而是分类汇总，交给 Player 处理。
        """
        # 1. 基础固有属性 (固定值)
        res = {
            "fixed": {
                "伤害": self.damage, "防御": self.defense, "闪躲": self.dodge,
                "命中": self.hit, "攻击速度": self.attack_speed, "必杀率": self.critical_rate,
                "MaxHp": self.max_hp, "MaxMp": self.max_mp,
                "抗火": self.fire_resistance, "抗水": self.water_resistance, "抗毒": self.poison_resistance
            },
            "points": {},  # 强度点数 (力量、体质等)
            "ratio": {}  # 百分比加成 (伤害%, 生命% 等)
        }

        pass_attr = ['ID', '可装备附魔', '可宠物附魔', '备注', '有效', '说明', '阶段', '道具类型', '品质', '附加价格']
        percentage_keys = ['攻击速度', '伤害', '防御', '命中', '闪躲', '爆击率', 'hp', 'mp']
        point_keys = ['力量强度', '体质强度', '精准强度', '敏捷强度', '智力强度']

        def collect_script_data(attr_id):
            if attr_id <= 0: return
            script_data = SourceManager.get_csv("attribs", str(attr_id))
            if not script_data: return

            for key, val in script_data.items():
                if key in pass_attr or not val: continue
                try:
                    num_val = float(val)
                    if num_val == 0: continue

                    if key in percentage_keys:
                        # 统一存入 ratio，除以 100 方便计算
                        res["ratio"][key] = res["ratio"].get(key, 0.0) + (num_val / 100.0)
                    elif key in point_keys:
                        res["points"][key] = res["points"].get(key, 0.0) + num_val
                    else:
                        res["fixed"][key] = res["fixed"].get(key, 0) + int(num_val)
                except:
                    continue

        collect_script_data(self.primary_attr_id)
        collect_script_data(self.secondary_attr_id)

        return res


    def get_display_attrs(self):
        """
        获取用于 UI 显示的战斗增益属性列表。
        排除掉‘可锻造’、‘可交易’等系统字段。
        返回格式: [ (文本, 颜色), ... ]
        """
        display_results = []

        # 1. 基础战斗属性 (黄色)
        # 我们只列出 FIELD_MAPPING 中属于数值加成的部分
        combat_fields = [
            '命中', '伤害', '防御', '闪躲', '攻击速度', '必杀率',
            'MaxHp', 'MaxMp', '抗火', '抗水', '抗毒'
        ]

        for config_key in combat_fields:
            mapping = self.FIELD_MAPPING.get(config_key)
            if not mapping:
                continue

            attr_name = mapping.get("attr")
            val = getattr(self, attr_name, 0)

            # 只有数值大于 0 才显示基础加成
            if isinstance(val, (int, float)) and val > 0:
                display_results.append((f"{config_key}: +{val}", "#FFFF00"))

        # 2. 脚本额外增益属性 (绿色)
        # 过滤掉非战斗增益的字段
        pass_attr = ['ID', '可装备附魔', '可宠物附魔', '备注', '有效', '说明', '阶段', '道具类型', '品质', '附加价格']
        # 需要显示为百分比的字段
        percentage_attr = ['攻击速度', '伤害', '防御', '命中', '闪躲', '爆击率', '杀怪经验获得率', '杀怪金钱获得率']

        def collect_script_attrs(attr_id):
            if not attr_id or attr_id <= 0:
                return
            # 这里 SourceManager 内部会处理 get，我们直接拿数据
            script_data = SourceManager.get_csv("attribs", str(attr_id))
            if not script_data:
                return

            for ak, val in script_data.items():
                # 如果在忽略列表，或者值为空，则跳过
                if ak in pass_attr or not val:
                    continue
                try:
                    num_val = int(float(val))
                    if num_val <= 0:
                        continue

                    # 格式化数值：百分比 or 纯数字
                    display_val = f"{num_val}%" if ak in percentage_attr else f"{num_val}"
                    # display_results.append((f"{ak}: +{display_val}", "#00E500"))
                    display_results.append((f"{ak}: +{display_val}", "#FF0000"))
                except (ValueError, TypeError):
                    continue

        # 按顺序采集主、副属性脚本中的增益
        collect_script_attrs(self.primary_attr_id)
        collect_script_attrs(self.secondary_attr_id)

        return display_results

    def get_pos(self):
        """返回道具的坐标, page,x,y"""
        return self.__pos

    def set_pos(self, x: int | str, y: int | str, page: int | str = 0):
        """更新道具位置"""
        self.__pos = [int(page), int(x), int(y)]

    def set_bind(self, sta: bool):
        """更换道具的绑定状态"""
        self.bind = sta

    def clone(self):
        """返回当前道具的克隆对象"""
        clone_item = deepcopy(self)
        clone_item.UID = uuid4().hex[:8]  # 道具的唯一id
        return clone_item
