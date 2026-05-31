#!/usr/bin/env python3
"""
生肖动态映射 - 反推正确offset
===========================

分析规则：
- 龙年时，shift = +5 或其他
- 兔年时，shift = +9
- 蛇年时，shift = +7 (假设)

测试不同offset找出最高匹配率
"""

import sys
import json
from collections import defaultdict

import pandas as pd

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']

# 农历年定义
LUNAR_YEAR = {
    2023: '兔',
    2024: '龙',
    2025: '蛇',
    2026: '马',
}

def get_lunar_year(period):
    """从期号获取农历年"""
    return int(str(period)[:4])

def test_offset(offset):
    """测试给定offset的正确率"""
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    correct = 0
    total = 0
    year_stats = defaultdict(lambda: {'correct': 0, 'total': 0})

    for _, row in df.iterrows():
        period = row['period']
        num = int(row['special_number'])
        raw_zodiac = row['special_zodiac']

        lunar_year = get_lunar_year(period)

        # 计算
        calc_idx = (num + offset) % 12
        calc_zodiac = ZODIACS[calc_idx]

        is_match = raw_zodiac == calc_zodiac
        if is_match:
            correct += 1
            year_stats[lunar_year]['correct'] += 1
        year_stats[lunar_year]['total'] += 1
        total += 1

    return correct, total, year_stats

# 测试所有可能的offset
print("测试所有offset:")
print("offset | 总正确率 | 2023年 | 2024年 | 2025年 | 2026年")
print("-" * 60)

best_offset = 0
best_rate = 0

for offset in range(12):
    correct, total, year_stats = test_offset(offset)
    rate = correct / total if total > 0 else 0

    y2023 = f"{year_stats[2023]['correct']}/{year_stats[2023]['total']}" if 2023 in year_stats else '-'
    y2024 = f"{year_stats[2024]['correct']}/{year_stats[2024]['total']}" if 2024 in year_stats else '-'
    y2025 = f"{year_stats[2025]['correct']}/{year_stats[2025]['total']}" if 2025 in year_stats else '-'
    y2026 = f"{year_stats[2026]['correct']}/{year_stats[2026]['total']}" if 2026 in year_stats else '-'

    print(f"  {offset:2d}   | {rate:.1%}     | {y2023}    | {y2024}    | {y2025}    | {y2026}")

    if rate > best_rate:
        best_rate = rate
        best_offset = offset

print()
print(f"最佳offset: {best_offset}, 正确率: {best_rate:.1%}")

# 使用最佳offset验证
print()
print("=" * 60)
print(f"使用 offset={best_offset} 进行完整验证")
print("=" * 60)

correct, total, year_stats = test_offset(best_offset)
print(f"\n总体: {correct}/{total} = {correct/total:.2%}")

# 显示不匹配的例子
with open('/home/admin1/liuhecai_standard_v2.json') as f:
    data = json.load(f)

df = pd.DataFrame(data)

print("\n不匹配示例:")
mismatches = []
for _, row in df.iterrows():
    period = row['period']
    num = int(row['special_number'])
    raw_zodiac = row['special_zodiac']

    calc_idx = (num + best_offset) % 12
    calc_zodiac = ZODIACS[calc_idx]

    if raw_zodiac != calc_zodiac:
        mismatches.append({
            'period': str(period),
            'lunar_year': get_lunar_year(period),
            'number': num,
            'raw': raw_zodiac,
            'calc': calc_zodiac
        })

print(f"共 {len(mismatches)} 条不匹配")

# 按年份分组不匹配
by_year = defaultdict(list)
for m in mismatches:
    by_year[m['lunar_year']].append(m)

for year in sorted(by_year.keys()):
    year_mismatches = by_year[year]
    print(f"\n{year}年 ({len(year_mismatches)}条不匹配):")
    for m in year_mismatches[:5]:
        print(f"  {m['period']}: 号码{m['number']} 原始={m['raw']} 计算={m['calc']}")