#!/usr/bin/env python3
"""
波色映射表
统一管理，避免多份映射
"""

MAP_VERSION = "2026_v1"

# 波色定义：将12生肖分为4个波色
# 绿波: 鼠 兔 馬 雞
# 红波: 牛 蛇 羊 狗
# 蓝波: 虎 龍 猴 豬
WAVES = {
    "绿波": ["鼠", "兔", "馬", "雞"],
    "红波": ["牛", "蛇", "羊", "狗"],
    "蓝波": ["虎", "龍", "猴", "豬"],
}

# ============================================================
# 号码到波色的映射（用于遗漏计算）
# ============================================================
# 红波: 01 02 07 08 12 13 18 19 23 24 29 30 34 35 40 45 46
# 蓝波: 03 04 09 10 14 15 20 25 26 31 36 37 41 42 47 48
# 绿波: 05 06 11 16 17 21 22 27 28 32 33 38 39 43 44 49
WAVE_NUMBERS = {
    '红波': [1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46],
    '蓝波': [3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48],
    '绿波': [5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49],
}

# 号码到波色的快速映射
NUMBER_TO_WAVE = {}
for wave, numbers in WAVE_NUMBERS.items():
    for n in numbers:
        NUMBER_TO_WAVE[n] = wave


def get_wave(zodiac: str) -> str | None:
    """根据生肖获取对应波色"""
    for wave, members in WAVES.items():
        if zodiac in members:
            return wave
    return None


def get_all_waves() -> list:
    """获取所有波色"""
    return list(WAVES.keys())


def get_wave_members(wave: str) -> list:
    """获取指定波色的所有生肖成员"""
    return WAVES.get(wave, [])


def get_wave_by_number(number: int) -> str | None:
    """根据号码获取对应波色"""
    return NUMBER_TO_WAVE.get(number)