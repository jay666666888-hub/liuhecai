#!/usr/bin/env python3
"""
生肖映射表
统一管理，避免多份映射
"""

MAP_VERSION = "2026_v1"

ZODIACS = ["鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"]

def get_zodiac_index(zodiac: str) -> int:
    """获取生肖索引"""
    return ZODIACS.index(zodiac) if zodiac in ZODIACS else -1

def get_all_zodiacs() -> list:
    """获取所有生肖"""
    return ZODIACS.copy()