#!/usr/bin/env python3
"""
生肖动态映射 - 最终修正版
========================

分析规律：
- 兔年(2023): num%12 -> zodiac (offset=0基础)
- 龙年(2024): (num + offset) % 12 -> zodiac

正确公式：
zodiac_index = (num + year_offset) % 12
其中 year_offset = (year_zodiac_index - 1) % 12
"""

import sys
import json
from datetime import date
from collections import defaultdict

import pandas as pd

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']

# 农历新年
LUNAR_NEW_YEAR = {
    2023: date(2023, 1, 22),   # 兔年
    2024: date(2024, 2, 10),  # 龙年
    2025: date(2025, 1, 29),   # 蛇年
}

# 生肖位置
ZODIAC_INDEX = {z: i for i, z in enumerate(ZODIACS)}  # 鼠=0, 牛=1, ..., 豬=11

def get_lunar_year(d):
    d = d if isinstance(d, date) else date.fromisoformat(str(d))
    for year in sorted(LUNAR_NEW_YEAR.keys(), reverse=True):
        if d >= LUNAR_NEW_YEAR[year]:
            return year
    return 2022

def build_year_zodiac_table(lunar_year):
    """
    生成指定农历年的49号码生肖表

    规则：zodiac_index = (num - 1) % 12，位置0=该年生肖
    例如：兔年 position[0]=兔, position[1]=龙, ...
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
    """动态计算号码对应的生肖"""
    _, table = build_year_zodiac_table(lunar_year)
    return table[int(num)]

# ============ 测试正确公式 ============
def test_formula():
    """测试公式是否正确"""
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    print("测试公式: zodiac_index = (num - 1) % 12, position 0 = year_start_zodiac")
    print()

    # 兔年测试
    print("兔年测试:")
    test_nums = [40, 6, 26, 19, 23, 20]
    _, table_2023 = build_year_zodiac_table(2023)
    for num in test_nums:
        print(f"  {num} -> {table_2023[num]}")

    print()
    print("龙年测试:")
    _, table_2024 = build_year_zodiac_table(2024)
    for num in test_nums:
        print(f"  {num} -> {table_2024[num]}")

    print()
    print("蛇年测试:")
    _, table_2025 = build_year_zodiac_table(2025)
    for num in test_nums:
        print(f"  {num} -> {table_2025[num]}")

# ============ 完整验证 ============
def full_validation():
    """完整验证870条数据"""
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    print("\n" + "=" * 60)
    print("完整验证")
    print("=" * 60)

    results = []
    year_stats = defaultdict(lambda: {'correct': 0, 'total': 0})

    for _, row in df.iterrows():
        period = row['period']
        raw_date = row.get('date', '')
        num = int(row['special_number'])
        raw_zodiac = row.get('special_zodiac', '')

        try:
            d = date.fromisoformat(raw_date)
            lunar_year = get_lunar_year(d)
        except:
            lunar_year = 2024

        # 计算生肖
        calc_zodiac = number_to_zodiac(num, lunar_year)

        is_match = raw_zodiac == calc_zodiac
        results.append({
            'period': str(period),
            'date': str(raw_date),
            'lunar_year': lunar_year,
            'number': num,
            'raw_zodiac': raw_zodiac,
            'calc_zodiac': calc_zodiac,
            'match': is_match
        })

        year_stats[lunar_year]['total'] += 1
        if is_match:
            year_stats[lunar_year]['correct'] += 1

    # 统计
    total = len(results)
    match_count = sum(1 for r in results if r['match'])
    match_rate = match_count / total

    print(f"\n总体: {match_count}/{total} = {match_rate:.2%}")

    print("\n按年份:")
    for year, stats in sorted(year_stats.items()):
        rate = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  {year}年: {stats['correct']}/{stats['total']} = {rate:.2%}")

    # 保存验证结果
    df_valid = pd.DataFrame(results)
    df_valid.to_csv('/home/admin1/liuhecai_strategy_search/zodiac_validation.csv', index=False, encoding='utf-8-sig')

    # 保存不匹配记录
    mismatches = [r for r in results if not r['match']]
    if mismatches:
        with open('/home/admin1/liuhecai_strategy_search/zodiac_mismatches.json', 'w', encoding='utf-8') as f:
            json.dump(mismatches, f, ensure_ascii=False, indent=2)

    return match_rate, mismatches

# ============ 生成年映射表 ============
def generate_year_mapping():
    """生成每年映射表"""
    years = [2023, 2024, 2025]
    all_mappings = {}

    for year in years:
        start_z, table = build_year_zodiac_table(year)

        # 按生肖分组
        by_zodiac = defaultdict(list)
        for num, zodiac in table.items():
            by_zodiac[zodiac].append(num)

        all_mappings[str(year)] = {
            'start_zodiac': start_z,
            'formula': 'zodiac_index = (num - 1) % 12, position 0 = year_start_zodiac',
            'zodiac_numbers': {z: sorted(nums) for z, nums in by_zodiac.items()}
        }

    with open('/home/admin1/liuhecai_strategy_search/year_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(all_mappings, f, ensure_ascii=False, indent=2)

    return all_mappings

# ============ 主程序 ============
def main():
    print("=" * 60)
    print("生肖动态映射验证")
    print("=" * 60)

    # 测试公式
    test_formula()

    # 验证
    match_rate, mismatches = full_validation()

    # 生成映射表
    print("\n" + "=" * 60)
    print("生成年映射表")
    print("=" * 60)

    mappings = generate_year_mapping()
    for year, mapping in mappings.items():
        print(f"\n{year}年 ({mapping['start_zodiac']}年):")
        for z in ZODIACS:
            nums = mapping['zodiac_numbers'].get(z, [])
            print(f"  {z}: {nums}")

    # 最终判断
    print("\n" + "=" * 60)
    print("最终结果")
    print("=" * 60)

    if match_rate > 0.99:
        print(f"✓ 一致率 {match_rate:.2%} > 99%，允许进入策略搜索")
        return 'GREEN'
    else:
        print(f"✗ 一致率 {match_rate:.2%} <= 99%，禁止进入策略搜索")
        if mismatches:
            print(f"  不匹配记录: {len(mismatches)}条")
            print("  示例:")
            for m in mismatches[:5]:
                print(f"    {m['period']}: 号码{m['number']} 农历年{m['lunar_year']} 原始={m['raw_zodiac']} 计算={m['calc_zodiac']}")
        return 'RED'

if __name__ == '__main__':
    result = main()