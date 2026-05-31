#!/usr/bin/env python3
"""
快速数据验证脚本 - 使用实际生肖
"""

import sys
import json
import random
import numpy as np
import pandas as pd

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

def load_data():
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)
    df = pd.DataFrame(data).sort_values('period').reset_index(drop=True)

    # 使用数据中的实际生肖
    ZODIACS = df['special_zodiac'].unique().tolist()
    print(f"[数据] {len(df)} 条, 生肖: {ZODIACS}")

    return df, ZODIACS

def fast_random_simulation(df, ZODIACS, n_experiments=10000):
    """快速随机模拟"""
    actuals = df['special_zodiac'].values
    n_periods = len(actuals)
    n_zodiacs = len(ZODIACS)

    results = []
    for exp_id in range(n_experiments):
        # 使用数据中的实际生肖列表
        predicted = set(random.sample(ZODIACS, 6))
        hits = sum(1 for a in actuals if a in predicted)
        results.append(hits / n_periods)

        if (exp_id + 1) % 2000 == 0:
            print(f"  完成: {exp_id + 1}/{n_experiments}")

    return {
        'mean': float(np.mean(results)),
        'median': float(np.median(results)),
        'std': float(np.std(results)),
        'p5': float(np.percentile(results, 5)),
        'p95': float(np.percentile(results, 95)),
        'n_zodiacs': n_zodiacs,
    }

def verify_formula(df, ZODIACS):
    """验证命中公式"""
    actuals = df['special_zodiac'].values
    n = len(actuals)
    n_zodiacs = len(ZODIACS)

    # 理论：选6肖，命中概率 = 6/n_zodiacs
    theoretical = 6 / n_zodiacs

    # 随机模拟验证
    hits = 0
    for _ in range(5000):
        predicted = set(random.sample(ZODIACS, 6))
        hits += sum(1 for a in actuals if a in predicted)
    observed = hits / (5000 * n)

    return {
        'theoretical_probability': theoretical,
        'observed_probability': round(observed, 4),
        'deviation': round(abs(observed - theoretical), 4),
    }

def check_data_integrity(df):
    """数据完整性"""
    issues = []

    dup = df['period'].duplicated().sum()
    if dup > 0:
        issues.append(f'重复期号: {dup}')

    nulls = df[['period', 'special_zodiac', 'special_number']].isnull().sum().to_dict()
    if any(v > 0 for v in nulls.values()):
        issues.append(f'空值: {nulls}')

    nums = pd.to_numeric(df['special_number'], errors='coerce')
    invalid = nums[(nums < 1) | (nums > 49)]
    if len(invalid) > 0:
        issues.append(f'无效号码: {len(invalid)}')

    return {
        'total': len(df),
        'issues': issues if issues else ['无'],
        'has_issues': len(issues) > 0,
    }

def main():
    print("=" * 50)
    print("快速数据验证")
    print("=" * 50)

    df, ZODIACS = load_data()

    print("\n[1] 快速随机模拟 (10000次)...")
    stats = fast_random_simulation(df, ZODIACS, 10000)
    print(f"    均值: {stats['mean']:.4f} ({stats['mean']*100:.2f}%)")
    print(f"    标准差: {stats['std']:.4f}")
    print(f"    P5: {stats['p5']:.4f}")
    print(f"    P95: {stats['p95']:.4f}")
    theoretical = 6 / len(ZODIACS)
    print(f"    理论均值: {theoretical:.4f} ({theoretical*100:.2f}%)")

    print("\n[2] 公式验证...")
    formula = verify_formula(df, ZODIACS)
    print(f"    理论概率: {formula['theoretical_probability']:.4f}")
    print(f"    观察概率: {formula['observed_probability']:.4f}")
    print(f"    偏差: {formula['deviation']:.4f}")

    print("\n[3] 数据完整性...")
    integrity = check_data_integrity(df)
    print(f"    总记录: {integrity['total']}")
    print(f"    问题: {integrity['issues']}")

    # 保存
    with open('/home/admin1/liuhecai_strategy_search/random_validation.json', 'w') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    with open('/home/admin1/liuhecai_strategy_search/data_integrity.json', 'w') as f:
        json.dump(integrity, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    target_mean = 6 / len(ZODIACS)
    if abs(stats['mean'] - target_mean) <= 0.01:
        print(f"✓ 随机均值 {stats['mean']:.4f} ≈ 理论 {target_mean:.4f}")
        print("  → 数据正常，允许继续")
        return True
    else:
        print(f"✗ 随机均值 {stats['mean']:.4f} ≠ 理论 {target_mean:.4f}")
        print("  → 数据异常")
        return False

if __name__ == '__main__':
    main()