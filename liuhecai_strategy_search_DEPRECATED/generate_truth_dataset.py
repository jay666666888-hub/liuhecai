#!/usr/bin/env python3
"""
真值数据集生成
=============

规则：
- 一级真值（不可修改）：期号、开奖日期、特码号码
- 二级衍生（允许重建）：生肖、波色、五行、大小、单双、尾数

流程：
1. 丢弃所有历史生肖字段
2. 重新生成生肖（使用农历年份规则）
3. 输出truth_dataset.json
4. 验证generated_validation.csv
"""

import sys
import json
from datetime import date
from collections import defaultdict

import pandas as pd

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
ZODIAC_INDEX = {z: i for i, z in enumerate(ZODIACS)}

# 农历新年日期（公历）
LUNAR_NEW_YEAR = {
    2023: date(2023, 1, 22),   # 兔年
    2024: date(2024, 2, 10),   # 龙年
    2025: date(2025, 1, 29),   # 蛇年
    2026: date(2026, 2, 17),   # 马年
}

# 波色映射
COLOR_MAP = {
    'red': [1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46],
    'blue': [3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48],
    'green': [5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49]
}

# 五行映射
WUXING_MAP = {
    '金': [17, 18, 21, 22, 29, 30, 37, 38],
    '木': [13, 14, 21, 22, 27, 28, 35, 36],
    '水': [11, 12, 19, 20, 27, 28, 33, 34],
    '火': [5, 6, 13, 14, 23, 24, 31, 32],
    '土': [49, 1, 2, 9, 10, 41, 42, 49]
}

def get_lunar_year(d):
    """根据日期获取农历年份"""
    d = d if isinstance(d, date) else date.fromisoformat(str(d))
    for year in sorted(LUNAR_NEW_YEAR.keys(), reverse=True):
        if d >= LUNAR_NEW_YEAR[year]:
            return year
    return 2022

def build_zodiac_table(lunar_year):
    """
    生成指定农历年的49号码生肖表
    规则: position 0 = 该年生肖 (兔年时position0=兔)
    """
    start_zodiac = ZODIACS[(lunar_year - 2020) % 12]  # 2020=鼠
    start_idx = ZODIAC_INDEX[start_zodiac]

    table = {}
    for num in range(1, 50):
        pos = (num - 1) % 12
        zodiac = ZODIACS[(start_idx + pos) % 12]
        table[num] = zodiac

    return start_zodiac, table

def number_to_zodiac(num, lunar_year):
    """号码 → 生肖（动态）"""
    _, table = build_zodiac_table(lunar_year)
    return table[int(num)]

def number_to_color(num):
    """号码 → 波色"""
    n = int(num)
    for color, nums in COLOR_MAP.items():
        if n in nums:
            return color
    return 'unknown'

def number_to_wuxing(num):
    """号码 → 五行"""
    n = int(num)
    for wx, nums in WUXING_MAP.items():
        if n in nums:
            return wx
    return 'unknown'

def number_to_size(num):
    """号码 → 大小"""
    return '大' if int(num) > 24 else '小'

def number_to_parity(num):
    """号码 → 单双"""
    return '单' if int(num) % 2 == 1 else '双'

def number_to_tail(num):
    """号码 → 尾数"""
    return int(num) % 10

# ============ 主程序 ============
def main():
    print("=" * 60)
    print("真值数据集生成")
    print("=" * 60)

    # 加载原始数据
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df = df.sort_values('period').reset_index(drop=True)

    print(f"\n[数据] {len(df)} 条记录")
    print(f"  期号范围: {df['period'].iloc[0]} ~ {df['period'].iloc[-1]}")

    # 生成真值数据集
    print("\n[1] 生成真值数据集...")

    truth_data = []

    for _, row in df.iterrows():
        period = row['period']
        date_str = row['date']
        number = int(row['special_number'])

        # 获取农历年份
        try:
            d = date.fromisoformat(date_str)
        except:
            d = date(2024, 1, 1)

        lunar_year = get_lunar_year(d)

        # 生成衍生字段
        zodiac = number_to_zodiac(number, lunar_year)
        color = number_to_color(number)
        element = number_to_wuxing(number)
        size = number_to_size(number)
        parity = number_to_parity(number)
        tail = number_to_tail(number)

        truth_data.append({
            'period': str(period),
            'date': date_str,
            'number': number,
            'zodiac_generated': zodiac,
            'color_generated': color,
            'element_generated': element,
            'size_generated': size,
            'parity_generated': parity,
            'tail_generated': tail,
            'lunar_year': lunar_year
        })

    # 保存truth_dataset.json
    output_file = '/home/admin1/liuhecai_strategy_search/truth_dataset.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(truth_data, f, ensure_ascii=False, indent=2)

    print(f"    生成 {len(truth_data)} 条记录")
    print(f"    保存: {output_file}")

    # 统计
    zodiac_counts = defaultdict(int)
    color_counts = defaultdict(int)
    element_counts = defaultdict(int)
    year_counts = defaultdict(int)

    for row in truth_data:
        zodiac_counts[row['zodiac_generated']] += 1
        color_counts[row['color_generated']] += 1
        element_counts[row['element_generated']] += 1
        year_counts[row['lunar_year']] += 1

    print(f"\n    生肖分布: {dict(zodiac_counts)}")
    print(f"    波色分布: {dict(color_counts)}")
    print(f"    五行分布: {dict(element_counts)}")
    print(f"    农历年分布: {dict(year_counts)}")

    # 随机抽样验证
    print("\n[2] 随机抽样验证 (100期)...")

    import random
    random.seed(42)
    sample_indices = random.sample(range(len(truth_data)), min(100, len(truth_data)))
    sample_indices.sort()

    validation_data = []
    for idx in sample_indices:
        row = truth_data[idx]
        validation_data.append({
            'period': row['period'],
            'date': row['date'],
            'number': row['number'],
            'lunar_year': row['lunar_year'],
            'zodiac_generated': row['zodiac_generated'],
            'color_generated': row['color_generated'],
            'element_generated': row['element_generated']
        })

    # 保存CSV
    df_valid = pd.DataFrame(validation_data)
    df_valid.to_csv('/home/admin1/liuhecai_strategy_search/generated_validation.csv', index=False, encoding='utf-8-sig')

    print(f"    抽样 {len(validation_data)} 条")
    print(f"    保存: generated_validation.csv")

    print("\n    前20条:")
    print("    " + "-" * 70)
    print("    期号      日期         号码  农历年  生肖   波色   五行")
    print("    " + "-" * 70)
    for row in validation_data[:20]:
        print(f"    {row['period']}  {row['date']}  {row['number']:>2}    {row['lunar_year']}    {row['zodiac_generated']}    {row['color_generated']:6s}   {row['element_generated']}")

    # 验证映射表
    print("\n[3] 验证映射表...")

    for year in sorted(LUNAR_NEW_YEAR.keys()):
        start_z, table = build_zodiac_table(year)
        print(f"\n    {year}年 ({start_z}年):")
        for z in ZODIACS:
            nums = sorted([n for n, zodiac in table.items() if zodiac == z])
            print(f"      {z}: {nums}")

    # 最终输出
    print("\n" + "=" * 60)
    print("完成")
    print("=" * 60)
    print(f"\n真值数据集: truth_dataset.json ({len(truth_data)}条)")
    print(f"验证抽样: generated_validation.csv (100条)")
    print(f"\n规则:")
    print(f"  - 号码{1-49} → 生肖 (按农历年动态计算)")
    print(f"  - 号码 → 波色 (红:1,2,7,8... 蓝:3,4,9,10... 绿:5,6,11,16...)")
    print(f"  - 号码 → 五行 (金:17,18,21,22... 木:13,14,21,22...)")
    print(f"\n✓ 策略系统必须使用 truth_dataset.json")

    return truth_data

if __name__ == '__main__':
    main()