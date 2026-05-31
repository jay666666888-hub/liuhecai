#!/usr/bin/env python3
"""
生肖动态映射 - 修正版
====================

发现规则：
- 期号(如2023xxx)表示农历年份，不是公历年份
- 期号2023xxx = 兔年(春节2023-01-22开始)
- 期号2024xxx = 龙年(春节2024-02-10开始)
- 期号2025xxx = 蛇年(春节2025-01-29开始)
- 期号2026xxx = 马年(春节2026-02-17开始)

因此：
- 期号年份决定生肖年
- 日期只用于确认具体日期（用于判断边界）
"""

import sys
import json
from datetime import date
from collections import defaultdict

import pandas as pd

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
ZODIAC_INDEX = {z: i for i, z in enumerate(ZODIACS)}

# 农历新年日期（公历）- 用于确认边界
LUNAR_NEW_YEAR = {
    2023: date(2023, 1, 22),   # 兔年
    2024: date(2024, 2, 10),  # 龙年
    2025: date(2025, 1, 29),   # 蛇年
    2026: date(2026, 2, 17),   # 马年
}

def get_zodiac_year_from_period(period):
    """从期号获取农历年份"""
    return int(str(period)[:4])

def build_year_zodiac_table(lunar_year):
    """
    生成指定农历年的49号码生肖表
    规则: position 0 = 该年生肖
    """
    start_zodiac = ZODIACS[(lunar_year - 2020) % 12]
    start_idx = ZODIAC_INDEX[start_zodiac]

    table = {}
    for num in range(1, 50):
        pos = (num - 1) % 12
        zodiac = ZODIACS[(start_idx + pos) % 12]
        table[num] = zodiac

    return start_zodiac, table

def number_to_zodiac(num, zodiac_year):
    """动态计算号码对应的生肖"""
    _, table = build_year_zodiac_table(zodiac_year)
    return table[int(num)]

# ============ 验证 ============
def validate():
    """完整验证"""
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    print("=" * 60)
    print("完整验证（使用期号年份）")
    print("=" * 60)

    results = []
    year_stats = defaultdict(lambda: {'correct': 0, 'total': 0})

    for _, row in df.iterrows():
        period = row['period']
        raw_date = row.get('date', '')
        num = int(row['special_number'])
        raw_zodiac = row.get('special_zodiac', '')

        # 使用期号年份而不是日期
        zodiac_year = get_zodiac_year_from_period(period)

        # 计算生肖
        calc_zodiac = number_to_zodiac(num, zodiac_year)

        is_match = raw_zodiac == calc_zodiac
        results.append({
            'period': str(period),
            'date': str(raw_date),
            'zodiac_year': zodiac_year,
            'number': num,
            'raw_zodiac': raw_zodiac,
            'calc_zodiac': calc_zodiac,
            'match': is_match
        })

        year_stats[zodiac_year]['total'] += 1
        if is_match:
            year_stats[zodiac_year]['correct'] += 1

    # 统计
    total = len(results)
    match_count = sum(1 for r in results if r['match'])
    match_rate = match_count / total

    print(f"\n总体: {match_count}/{total} = {match_rate:.2%}")

    print("\n按期号年份:")
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
        print(f"\n不匹配记录: {len(mismatches)}条")

    return match_rate, mismatches

# ============ 生成年映射表 ============
def generate_year_mapping():
    """生成每年映射表"""
    years = [2023, 2024, 2025, 2026]
    all_mappings = {}

    for year in years:
        start_z, table = build_year_zodiac_table(year)

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

    match_rate, mismatches = validate()

    print("\n" + "=" * 60)
    print("生成年映射表")
    print("=" * 60)

    mappings = generate_year_mapping()
    for year, mapping in sorted(mappings.items()):
        print(f"\n{year}年 ({mapping['start_zodiac']}年):")
        for z in ZODIACS:
            nums = mapping['zodiac_numbers'].get(z, [])
            print(f"  {z}: {nums}")

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
                print(f"    {m['period']}: 号码{m['number']} 生肖年{m['zodiac_year']} 原始={m['raw_zodiac']} 计算={m['calc_zodiac']}")
        return 'RED'

if __name__ == '__main__':
    result = main()