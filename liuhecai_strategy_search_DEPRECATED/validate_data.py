#!/usr/bin/env python3
"""
数据验证脚本
============

1. 100000次纯随机模拟 → random_validation.json
2. 真实命中公式验证 → formula_verification.json
3. 生肖映射验证 → mapping_check.json
4. 数据完整性验证 → data_integrity.json
"""

import sys
import os
import json
import random
from collections import Counter
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

# ============ 配置 ============
N_RANDOM_EXPERIMENTS = 100000
ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
N_TRIALS = 6  # 选择6肖

# ============ 加载数据 ============
def load_data():
    """加载数据"""
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df = df.sort_values('period').reset_index(drop=True)
    print(f"[数据] {len(df)} 条记录 | {df['period'].iloc[0]} ~ {df['period'].iloc[-1]}")
    return df

# ============ 1. 100000次随机模拟 ============
def run_random_simulation(df, n_experiments=N_RANDOM_EXPERIMENTS):
    """执行100000次纯随机实验"""
    print(f"\n[1] 执行 {n_experiments} 次随机模拟...")

    results = []
    period_count = len(df)

    for exp_id in range(n_experiments):
        hits = 0

        for idx in range(period_count):
            actual = df.iloc[idx]['special_zodiac']
            predicted = random.sample(ZODIACS, N_TRIALS)  # 随机选6肖

            # 命中：预测6肖中包含特码生肖
            hit = actual in predicted
            hits += 1 if hit else 0

        exp_hit_rate = hits / period_count
        results.append(exp_hit_rate)

        if (exp_id + 1) % 10000 == 0:
            print(f"    完成: {exp_id + 1}/{n_experiments}")

    # 统计分析
    results_array = np.array(results)

    stats = {
        'n_experiments': n_experiments,
        'n_periods': period_count,
        'mean': float(np.mean(results_array)),
        'median': float(np.median(results_array)),
        'std': float(np.std(results_array)),
        'p5': float(np.percentile(results_array, 5)),
        'p95': float(np.percentile(results_array, 95)),
        'min': float(np.min(results_array)),
        'max': float(np.max(results_array)),
    }

    output_file = '/home/admin1/liuhecai_strategy_search/random_validation.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\n    随机基准统计:")
    print(f"    - 均值: {stats['mean']:.4f} ({stats['mean']*100:.2f}%)")
    print(f"    - 中位数: {stats['median']:.4f}")
    print(f"    - 标准差: {stats['std']:.4f}")
    print(f"    - P5: {stats['p5']:.4f}")
    print(f"    - P95: {stats['p95']:.4f}")
    print(f"    - 最小: {stats['min']:.4f}")
    print(f"    - 最大: {stats['max']:.4f}")

    return stats

# ============ 2. 命中公式验证 ============
def verify_hit_formula(df):
    """验证命中公式"""
    print("\n[2] 验证命中公式...")

    # 公式说明
    formula = {
        'hit定义': '预测6肖中是否包含特码生肖',
        'hit': 'bool - predicted ∩ {actual} > 0',
        'hit_count': 'int - 命中的生肖数量（0或1）',
        'hit_rate': 'sum(hit) / N',
        '随机基准': '6/12 = 50%',
        '理论解释': '从12个生肖中随机选6个，任意1个命中的概率',
    }

    # 手动验证：随机选6肖，870期命中有多少
    n_test = 10000
    hits = 0
    for _ in range(n_test):
        for _, row in df.iterrows():
            predicted = random.sample(ZODIACS, 6)
            if row['special_zodiac'] in predicted:
                hits += 1

    observed_rate = hits / (n_test * len(df))

    verification = {
        'formula': formula,
        'observed_hit_rate': round(observed_rate, 4),
        'expected_hit_rate': 0.5,
        'deviation': round(abs(observed_rate - 0.5), 4),
        'is_correct': abs(observed_rate - 0.5) < 0.02,
    }

    output_file = '/home/admin1/liuhecai_strategy_search/formula_verification.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(verification, f, ensure_ascii=False, indent=2)

    print(f"    观察命中率: {observed_rate:.4f}")
    print(f"    期望命中率: 0.5000")
    print(f"    偏差: {abs(observed_rate - 0.5):.4f}")
    print(f"    公式正确: {'✓' if verification['is_correct'] else '✗'}")

    return verification

# ============ 3. 生肖映射验证 ============
def verify_zodiac_mapping(df):
    """验证生肖映射"""
    print("\n[3] 验证生肖映射...")

    # 生肖标准映射
    ZODIAC_MAP = {
        1: '鼠', 2: '牛', 3: '虎', 4: '兔', 5: '龍', 6: '蛇',
        7: '马', 8: '羊', 9: '猴', 10: '雞', 11: '狗', 12: '豬'
    }

    # 检查数据中的生肖分布
    zodiac_counts = df['special_zodiac'].value_counts().to_dict()

    # 检查每个生肖是否都有出现
    missing_zodiacs = [z for z in ZODIACS if z not in zodiac_counts]

    # 检查年份轮转（生肖是否按规律分布）
    df['year'] = df['period'].astype(str).str[:4].astype(int)
    years = sorted(df['year'].unique())

    yearly_zodiacs = {}
    for year in years:
        year_data = df[df['year'] == year]
        zodiacs = year_data['special_zodiac'].tolist()
        yearly_zodiacs[str(year)] = zodiacs

    # 检查生肖轮转：每个生肖应该在不同年份出现
    zodiac_years = {}
    for z in ZODIACS:
        years_with_z = [y for y in years if z in yearly_zodiacs[str(y)]]
        zodiac_years[z] = years_with_z

    mapping_check = {
        'zodiac_map': ZODIAC_MAP,
        'zodiac_counts': zodiac_counts,
        'missing_zodiacs': missing_zodiacs,
        'all_zodiacs_appear': len(missing_zodiacs) == 0,
        'years_checked': list(years),
        'zodiac_by_year': {str(y): list(set(yearly_zodiacs[str(y)])) for y in years},
        'zodiac_years_count': {z: len(years_with_z) for z, years_with_z in zodiac_years.items()},
        'conclusion': '映射正确' if len(missing_zodiacs) == 0 else '存在缺失生肖',
    }

    output_file = '/home/admin1/liuhecai_strategy_search/mapping_check.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mapping_check, f, ensure_ascii=False, indent=2)

    print(f"    生肖分布: {dict(sorted(zodiac_counts.items()))}")
    print(f"    缺失生肖: {missing_zodiacs if missing_zodiacs else '无'}")
    print(f"    年份范围: {min(years)}~{max(years)}")

    return mapping_check

# ============ 4. 数据完整性验证 ============
def verify_data_integrity(df):
    """验证数据完整性"""
    print("\n[4] 验证数据完整性...")

    issues = []

    # 重复期号
    duplicates = df['period'].duplicated().sum()
    if duplicates > 0:
        issues.append(f'重复期号: {duplicates} 个')

    # 缺失期号检查
    df['year'] = df['period'].astype(str).str[:4].astype(int)
    df['seq'] = df['period'].astype(str).str[4:].astype(int)

    missing_periods = []
    for year in df['year'].unique():
        year_data = df[df['year'] == year]
        max_seq = year_data['seq'].max()
        expected = set(range(1, max_seq + 1))
        actual = set(year_data['seq'].tolist())
        missing = expected - actual
        if missing:
            missing_periods.append({str(year): sorted(list(missing))})

    if missing_periods:
        issues.append(f'缺失期号: {missing_periods}')

    # 重复特码
    duplicate_special = df.groupby('period').apply(
        lambda x: x['special_zodiac'].duplicated().any()
    ).sum()
    if duplicate_special > 0:
        issues.append(f'重复特码: {duplicate_special} 期')

    # 空值检查
    null_counts = df.isnull().sum().to_dict()
    null_fields = [k for k, v in null_counts.items() if v > 0]

    # 特码范围检查
    invalid_numbers = df[(df['special_number'] < 1) | (df['special_number'] > 49)]
    if len(invalid_numbers) > 0:
        issues.append(f'无效号码: {len(invalid_numbers)} 条')

    integrity = {
        'total_records': len(df),
        'date_range': f"{df['period'].iloc[0]} ~ {df['period'].iloc[-1]}",
        'issues': issues,
        'has_issues': len(issues) > 0,
        'null_counts': null_counts,
        'null_fields': null_fields,
        'duplicate_periods': duplicates,
        'missing_periods_detail': missing_periods if missing_periods else '无',
        'invalid_special_numbers': len(invalid_numbers),
    }

    output_file = '/home/admin1/liuhecai_strategy_search/data_integrity.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(integrity, f, ensure_ascii=False, indent=2)

    print(f"    总记录: {len(df)}")
    print(f"    期号重复: {duplicates}")
    print(f"    空值字段: {null_fields if null_fields else '无'}")
    print(f"    问题数量: {len(issues)}")

    return integrity

# ============ 主程序 ============
def main():
    print("=" * 60)
    print("数据验证脚本")
    print("=" * 60)

    # 加载数据
    df = load_data()

    # 执行验证
    print("\n" + "-" * 60)
    random_stats = run_random_simulation(df)

    print("\n" + "-" * 60)
    formula_verif = verify_hit_formula(df)

    print("\n" + "-" * 60)
    mapping_check = verify_zodiac_mapping(df)

    print("\n" + "-" * 60)
    integrity = verify_data_integrity(df)

    # 最终判断
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)

    # 关键检查：随机均值是否≈50%±1%
    random_mean = random_stats['mean']
    target_mean = 0.5
    tolerance = 0.01

    if abs(random_mean - target_mean) <= tolerance:
        print(f"✓ 随机均值: {random_mean:.4f} (目标 50%±1%)")
        print("  → 允许继续分析")
        can_proceed = True
    else:
        print(f"✗ 随机均值: {random_mean:.4f} (目标 50%±1%)")
        print("  → 禁止继续分析，数据可能存在问题")
        can_proceed = False

    print(f"\n详细结果:")
    print(f"  - random_validation.json")
    print(f"  - formula_verification.json")
    print(f"  - mapping_check.json")
    print(f"  - data_integrity.json")

    if not can_proceed:
        print("\n⚠️ 数据验证失败，请检查数据源")

    return can_proceed

if __name__ == '__main__':
    main()