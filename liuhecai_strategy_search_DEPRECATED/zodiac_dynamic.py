#!/usr/bin/env python3
"""
生肖动态映射 - 农历年版本
=======================

规则：
- 号码→生肖按农历生肖年动态计算
- 以春节作为生肖年切换边界
- 禁止固定号码→生肖映射

流程：
1. 开奖日期 → 判断农历年
2. 生成当年49个号码对应生肖表
3. 号码映射生肖

输出：
- year_mapping.json (每年生肖映射表)
- zodiac_validation.csv (100期验证)
"""

import sys
import json
import random
from datetime import datetime, date
from collections import defaultdict

import pandas as pd

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

# ============ 农历生肖年定义 ============
# 生肖顺序：鼠、牛、虎、兔、龍、蛇、马、羊、猴、雞、狗、豬
ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']

# 农历新年日期（公历）-> 生肖年
# 来源：历史农历数据
LUNAR_NEW_YEAR = {
    2020: date(2020, 1, 25),   # 鼠年
    2021: date(2021, 2, 12),   # 牛年
    2022: date(2022, 2, 1),    # 虎年
    2023: date(2023, 1, 22),   # 兔年
    2024: date(2024, 2, 10),   # 龙年
    2025: date(2025, 1, 29),   # 蛇年
}

def get_lunar_year(d):
    """
    根据日期判断农历年
    春节前属于上一年
    """
    d = d if isinstance(d, date) else date.fromisoformat(str(d))

    for year in sorted(LUNAR_NEW_YEAR.keys(), reverse=True):
        if d >= LUNAR_NEW_YEAR[year]:
            return year

    # 2020年之前
    return 2019

def build_zodiac_table(lunar_year):
    """
    生成指定农历年的49号码生肖表

    生肖排列（以该年生肖为1）：
    例如：兔年 -> 兔=1, 龙=2, 蛇=3, 马=4, 羊=5, 猴=6, 鸡=7, 狗=8, 猪=9, 鼠=10, 牛=11, 虎=12

    号码对应：
    1-49 对应 12生肖循环
    """
    zodiac_index = {z: i for i, z in enumerate(ZODIACS)}
    start_zodiac = ZODIACS[(lunar_year - 2020) % 12]  # 2020=鼠年

    table = {}
    for num in range(1, 50):
        # 号码从1开始，生肖从start_zodiac开始
        # (num - 1) % 12 得到偏移量
        offset = (num - 1) % 12
        zodiac = ZODIACS[(zodiac_index[start_zodiac] + offset) % 12]
        table[num] = zodiac

    return start_zodiac, table

def number_to_zodiac_dynamic(num, lunar_year):
    """动态计算号码对应的生肖"""
    _, table = build_zodiac_table(lunar_year)
    return table[int(num)]

def validate_zodiac_mapping(df):
    """验证生肖映射"""
    print("\n[1] 验证生肖映射...")

    results = []
    mismatches = []

    for _, row in df.iterrows():
        period = row['period']
        raw_date = row.get('date', row.get('开奖日期', ''))
        num = row['special_number']
        raw_zodiac = row.get('special_zodiac', '')

        # 解析日期
        try:
            if isinstance(raw_date, str) and raw_date:
                d = date.fromisoformat(raw_date)
            else:
                d = date(2024, 1, 1)  # 默认
        except:
            d = date(2024, 1, 1)

        # 获取农历年
        lunar_year = get_lunar_year(d)

        # 计算生肖
        calc_zodiac = number_to_zodiac_dynamic(num, lunar_year)

        # 对比
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

        if not is_match:
            mismatches.append(results[-1])

    # 统计
    total = len(results)
    match_count = sum(1 for r in results if r['match'])
    match_rate = match_count / total if total > 0 else 0

    print(f"    总验证: {total}条")
    print(f"    匹配: {match_count}条")
    print(f"    不匹配: {len(mismatches)}条")
    print(f"    一致率: {match_rate:.2%}")

    if mismatches:
        print(f"\n    不匹配示例:")
        for m in mismatches[:5]:
            print(f"      {m['period']}: 号码{m['number']} 农历年{m['lunar_year']} 原始={m['raw_zodiac']} 计算={m['calc_zodiac']}")

    return results, match_rate, mismatches

# ============ 主程序 ============
def main():
    print("=" * 60)
    print("生肖动态映射验证")
    print("=" * 60)

    # 加载数据
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df = df.sort_values('period').reset_index(drop=True)

    print(f"[数据] {len(df)} 条记录")

    # 生成每年映射表
    print("\n[2] 生成每年映射表...")

    all_years = set()
    for _, row in df.iterrows():
        raw_date = row.get('date', '')
        try:
            if raw_date:
                d = date.fromisoformat(raw_date)
                all_years.add(get_lunar_year(d))
        except:
            pass

    year_mappings = {}
    for y in sorted(all_years):
        start_z, table = build_zodiac_table(y)
        # 按生肖分组
        by_zodiac = defaultdict(list)
        for num, zodiac in table.items():
            by_zodiac[zodiac].append(num)

        year_mappings[str(y)] = {
            'start_zodiac': start_z,
            'zodiac_numbers': {z: sorted(nums) for z, nums in by_zodiac.items()}
        }

    # 保存
    with open('/home/admin1/liuhecai_strategy_search/year_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(year_mappings, f, ensure_ascii=False, indent=2)

    print(f"    生成 {len(year_mappings)} 个年份的映射表")
    print(f"    保存: year_mapping.json")

    for y, mapping in sorted(year_mappings.items()):
        print(f"\n    {y}年 ({mapping['start_zodiac']}年):")
        for z in ZODIACS:
            nums = mapping['zodiac_numbers'].get(z, [])
            print(f"      {z}: {nums}")

    # 验证
    print("\n" + "-" * 60)
    results, match_rate, mismatches = validate_zodiac_mapping(df)

    # 保存验证结果
    print("\n[3] 保存验证结果...")

    df_valid = pd.DataFrame(results)
    df_valid.to_csv('/home/admin1/liuhecai_strategy_search/zodiac_validation.csv', index=False, encoding='utf-8-sig')

    print(f"    保存: zodiac_validation.csv ({len(results)}条)")

    # 最终判断
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)
    print(f"\n一致率: {match_rate:.2%}")

    if match_rate > 0.99:
        print("\n✓ 一致率 > 99%，允许进入策略搜索")
        audit_result = 'GREEN'
    else:
        print(f"\n✗ 一致率 {match_rate:.2%} <= 99%，禁止进入策略搜索")
        audit_result = 'RED'

    # 保存不匹配记录
    if mismatches:
        with open('/home/admin1/liuhecai_strategy_search/mismatch_detail.json', 'w', encoding='utf-8') as f:
            json.dump(mismatches, f, ensure_ascii=False, indent=2)

    return audit_result, match_rate

if __name__ == '__main__':
    audit_result, match_rate = main()