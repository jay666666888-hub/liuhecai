#!/usr/bin/env python3
"""
生肖动态映射 - 农历年版本 (修正版)
================================

分析数据找出正确的映射规律
"""

import sys
import json
from datetime import date, datetime
from collections import defaultdict

import pandas as pd

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']

# 农历新年日期（公历）
LUNAR_NEW_YEAR = {
    2023: date(2023, 1, 22),   # 兔年
    2024: date(2024, 2, 10),   # 龙年
    2025: date(2025, 1, 29),   # 蛇年
}

def get_lunar_year(d):
    d = d if isinstance(d, date) else date.fromisoformat(str(d))
    for year in sorted(LUNAR_NEW_YEAR.keys(), reverse=True):
        if d >= LUNAR_NEW_YEAR[year]:
            return year
    return 2022

def analyze_mapping():
    """分析数据找出正确的映射规律"""
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    # 按农历年分组分析
    print("=" * 60)
    print("分析每个农历年的生肖映射规律")
    print("=" * 60)

    # 找每个生肖年的正确offset
    # 公式: zodiac_position = (num - 1 + offset) % 12
    # 或: zodiac_position = (num + offset) % 12

    # 验证: 假设 zodiac_position = (num - 1 + offset) % 12
    # offset_year = zodiac_position - (num - 1) % 12

    results = {}

    for year, new_year_date in LUNAR_NEW_YEAR.items():
        # 获取该年的数据
        year_data = []
        for _, row in df.iterrows():
            try:
                d = date.fromisoformat(row.get('date', '2024-01-01'))
                if d >= new_year_date:
                    # 确定是否属于该年
                    if year == 2023:
                        if d < LUNAR_NEW_YEAR.get(2024, date(2025, 1, 1)):
                            year_data.append(row)
                    elif year == 2024:
                        if d < LUNAR_NEW_YEAR.get(2025, date(2026, 1, 1)):
                            year_data.append(row)
            except:
                pass

        if len(year_data) < 5:
            continue

        print(f"\n农历{year}年 ({len(year_data)}条数据)")

        # 计算每个数据的offset
        offsets = []
        for row in year_data:
            num = int(row['special_number'])
            raw_zodiac = row['special_zodiac']
            zodiac_idx = ZODIACS.index(raw_zodiac) if raw_zodiac in ZODIACS else -1

            if zodiac_idx >= 0:
                # offset = zodiac_position - (num - 1) % 12
                offset = (zodiac_idx - (num - 1) % 12) % 12
                offsets.append(offset)

        if offsets:
            from collections import Counter
            counter = Counter(offsets)
            most_common = counter.most_common(1)[0]
            print(f"  最常见offset: {most_common[0]} (出现{most_common[1]}次)")
            print(f"  Offset分布: {dict(counter)}")

            # 用最常见的offset验证
            offset = most_common[0]
            correct = 0
            total = 0
            for row in year_data[:20]:
                num = int(row['special_number'])
                raw_zodiac = row['special_zodiac']
                calc_idx = ((num - 1 + offset) % 12)
                calc_zodiac = ZODIACS[calc_idx]
                if calc_zodiac == raw_zodiac:
                    correct += 1
                total += 1
                print(f"    {row['period']} 号码:{num:2d} 原始:{raw_zodiac} 计算:{calc_zodiac} {'✓' if calc_zodiac == raw_zodiac else '✗'}")

            print(f"  前20条验证正确率: {correct}/{total} = {correct/total:.0%}")
            results[year] = {'offset': offset, 'correct': correct, 'total': total}

    return results

# 验证分析结果
def verify_analysis(df, results):
    """用分析出的offset验证全部数据"""
    print("\n" + "=" * 60)
    print("验证分析结果")
    print("=" * 60)

    # 为每年确定正确的offset
    # 从数据分析: 兔年offset=? 龙年offset=?
    # 假设: offset = (12 - zodiac_position_of_year动物) % 12 + base

    # 生肖位置: 鼠=0, 牛=1, 虎=2, 兔=3, 龙=4, 蛇=5, 马=6, 羊=7, 猴=8, 鸡=9, 狗=10, 猪=11
    year_positions = {
        2023: 3,  # 兔
        2024: 4,  # 龙
        2025: 5,  # 蛇
    }

    # offset计算: offset = (target_position - (num - 1) % 12) % 12
    # 当 num=40, 期望zodiac=鼠(position=0)时, offset = (0 - 39 % 12) % 12 = (-3) % 12 = 9

    for year, pos in year_positions.items():
        print(f"\n农历{year}年 (起始生肖位置={pos}):")
        # 40 % 12 = 4, 如果offset=9, (40 + 9) % 12 = 1 = 牛
        # 测试offset计算
        test_num = 40
        target_zodiac = '鼠'  # 我们期望40->鼠
        target_pos = ZODIACS.index(target_zodiac)

        # 反推: offset = (target_pos - (num - 1) % 12) % 12
        offset = (target_pos - (test_num - 1) % 12) % 12
        print(f"  40 -> 鼠 需要offset = {offset}")
        print(f"  验证: (40 + {offset}) % 12 = {(test_num + offset) % 12} = {ZODIACS[(test_num + offset) % 12]}")

# 直接测试正确的offset
def test_offsets():
    """测试不同offset的效果"""
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    print("\n测试各种offset:")
    for offset in range(12):
        correct = 0
        total = 0
        for _, row in df.iterrows():
            try:
                d = date.fromisoformat(row.get('date', '2024-01-01'))
                year = get_lunar_year(d)
            except:
                year = 2024

            num = int(row['special_number'])
            raw_zodiac = row['special_zodiac']

            # 使用年份特定的offset
            if year == 2023:
                year_offset = (offset + 8) % 12  # 兔年offset
            elif year == 2024:
                year_offset = (offset + 1) % 12  # 龙年offset
            else:
                year_offset = offset

            calc_idx = (num + year_offset) % 12
            calc_zodiac = ZODIACS[calc_idx]

            if calc_zodiac == raw_zodiac:
                correct += 1
            total += 1

        print(f"  offset基础={offset}: 正确率 {correct}/{total} = {correct/total:.1%}")

# 主程序
if __name__ == '__main__':
    print("=" * 60)
    print("生肖映射规律分析")
    print("=" * 60)

    analyze_mapping()

    print("\n" + "=" * 60)
    print("简单offset测试")
    print("=" * 60)

    test_offsets()