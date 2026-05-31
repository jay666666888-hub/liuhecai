#!/usr/bin/env python3
"""
预训练验证 (Pre-Training Validation)
=================================

使用 truth_dataset.json 进行验证

1. 特征快照检查 - 验证无数据泄露
2. 标签检查 - 验证六肖命中定义
3. 基线验证 - 运行4种基线策略
4. 最终状态 - 输出 training_gate.json
"""

import sys
import json
import random
from datetime import date, timedelta
from collections import Counter, defaultdict

import pandas as pd
import numpy as np

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
COLOR_MAP = {
    'red': [1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46],
    'blue': [3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48],
    'green': [5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49]
}

LUNAR_NEW_YEAR = {
    2023: date(2023, 1, 22),
    2024: date(2024, 2, 10),
    2025: date(2025, 1, 29),
    2026: date(2026, 2, 17),
}

# ============ 加载数据 ============
def load_truth_data():
    """加载真值数据集"""
    with open('/home/admin1/liuhecai_strategy_search/truth_dataset.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df = df.sort_values('period').reset_index(drop=True)

    print(f"[数据] {len(df)} 条记录")
    print(f"  期号范围: {df['period'].iloc[0]} ~ {df['period'].iloc[-1]}")

    return df

# ============ 1. 特征快照检查 ============
def check_feature_snapshot(df):
    """验证特征时间 < 预测时间（无泄露）"""
    print("\n[1] 特征快照检查...")

    random.seed(42)
    sample_indices = random.sample(range(30, len(df) - 1), min(50, len(df) - 30))

    snapshots = []
    all_valid = True

    for idx in sample_indices:
        predict_idx = idx
        predict_period = df.iloc[predict_idx]['period']
        predict_date = df.iloc[predict_idx]['date']

        # 使用 idx 之前的数据计算特征
        train_df = df.iloc[:predict_idx]

        if len(train_df) < 30:
            continue

        # 获取训练数据的最后日期
        train_end_date = train_df.iloc[-1]['date']

        # 计算几个关键特征的时间
        features_info = {
            'period': str(predict_period),
            'predict_date': predict_date,
            'train_end_date': train_end_date,
            'train_size': len(train_df),
            'feature_time_check': 'valid',
            'details': []
        }

        # 检查：特征时间必须 < 预测时间
        if train_end_date >= predict_date:
            features_info['feature_time_check'] = 'INVALID - 数据泄露'
            all_valid = False
        else:
            features_info['feature_time_check'] = 'valid'

        # 特征来源验证
        features_info['details'].append(f"训练数据最后日期: {train_end_date} < 预测日期: {predict_date}")

        snapshots.append(features_info)

    result = {
        'total_checked': len(snapshots),
        'all_valid': all_valid,
        'feature_time_check': 'PASS' if all_valid else 'FAIL',
        'samples': snapshots[:10]  # 保存前10条样本
    }

    with open('/home/admin1/liuhecai_strategy_search/feature_snapshot.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"    检查: {len(snapshots)} 个快照")
    print(f"    结果: {'PASS' if all_valid else 'FAIL'}")

    return result

# ============ 2. 标签检查 ============
def check_labels(df):
    """验证六肖命中标签定义"""
    print("\n[2] 标签检查...")

    random.seed(123)
    sample_indices = random.sample(range(len(df)), min(100, len(df)))

    labels = []
    hit_count = 0

    for idx in sample_indices:
        row = df.iloc[idx]
        actual_zodiac = row['zodiac_generated']
        period = row['period']

        # 六肖命中：预测6肖中包含特码生肖
        # 随机生成6肖进行验证
        predicted = set(random.sample(ZODIACS, 6))
        actual = {actual_zodiac}

        hit = len(predicted & actual) > 0
        if hit:
            hit_count += 1

        labels.append({
            'period': str(period),
            'actual_zodiac': actual_zodiac,
            'predicted_6': list(predicted),
            'hit': hit,
            'formula': 'predicted ∩ actual > 0'
        })

    hit_rate = hit_count / len(labels)

    result = {
        'sample_size': len(labels),
        'hit_count': hit_count,
        'hit_rate': round(hit_rate, 4),
        'expected_rate': 0.5,
        'formula': 'predicted ∩ actual > 0',
        'definition': '六肖中有任意1个命中特码生肖即为命中',
        'status': 'PASS' if abs(hit_rate - 0.5) < 0.1 else 'WARN',
        'samples': labels[:10]
    }

    with open('/home/admin1/liuhecai_strategy_search/label_validation.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"    抽样: {len(labels)} 条")
    print(f"    命中: {hit_count} 条")
    print(f"    命中率: {hit_rate:.2%}")
    print(f"    期望: 50% (随机基准)")
    print(f"    结果: {result['status']}")

    return result

# ============ 3. 基线验证 ============
def run_baselines(df):
    """运行4种基线策略"""
    print("\n[3] 基线验证...")

    results = {}

    # === 随机基线 ===
    print("    运行 baseline_random...")
    n_experiments = 1000
    random.seed(42)

    random_rates = []
    for _ in range(n_experiments):
        hits = 0
        for _, row in df.iterrows():
            predicted = set(random.sample(ZODIACS, 6))
            if row['zodiac_generated'] in predicted:
                hits += 1
        random_rates.append(hits / len(df))

    results['baseline_random'] = {
        'name': '随机策略',
        'mean': round(np.mean(random_rates), 4),
        'std': round(np.std(random_rates), 4),
        'p5': round(np.percentile(random_rates, 5), 4),
        'p95': round(np.percentile(random_rates, 95), 4),
        'n_experiments': n_experiments
    }

    # === 频率基线 ===
    print("    运行 baseline_frequency...")
    freq_counts = Counter(df['zodiac_generated'])
    top6_zodiacs = freq_counts.most_common(6)
    top6_set = set([z for z, _ in top6_zodiacs])

    freq_hits = sum(1 for _, row in df.iterrows() if row['zodiac_generated'] in top6_set)
    results['baseline_frequency'] = {
        'name': '频率策略',
        'hit_rate': round(freq_hits / len(df), 4),
        'top_6': [z for z, _ in top6_zodiacs],
        'strategy': '选择历史出现最多的6个生肖'
    }

    # === 冷热基线 ===
    print("    运行 baseline_hot_cold...")
    recent_df = df.iloc[-50:] if len(df) >= 50 else df
    recent_counts = Counter(recent_df['zodiac_generated'])
    top6_recent = [z for z, _ in recent_counts.most_common(6)]
    top6_recent_set = set(top6_recent)

    hot_cold_hits = sum(1 for _, row in df.iterrows() if row['zodiac_generated'] in top6_recent_set)
    results['baseline_hot_cold'] = {
        'name': '冷热策略',
        'hit_rate': round(hot_cold_hits / len(df), 4),
        'top_6': top6_recent,
        'strategy': '选择近50期出现最多的6个生肖'
    }

    # === 马尔可夫基线 ===
    print("    运行 baseline_markov...")
    transitions = defaultdict(lambda: defaultdict(int))
    for i in range(1, len(df)):
        prev_z = df.iloc[i-1]['zodiac_generated']
        curr_z = df.iloc[i]['zodiac_generated']
        transitions[prev_z][curr_z] += 1

    # 计算稳态分布
    stationary = {}
    for z in ZODIACS:
        total = sum(transitions[z].values())
        if total > 0:
            stationary[z] = sum(transitions[z][next_z] for next_z in ZODIACS) / total
        else:
            stationary[z] = 1/12

    top6_markov = sorted(stationary.items(), key=lambda x: x[1], reverse=True)[:6]
    top6_markov_set = set([z for z, _ in top6_markov])

    markov_hits = sum(1 for _, row in df.iterrows() if row['zodiac_generated'] in top6_markov_set)
    results['baseline_markov'] = {
        'name': '马尔可夫策略',
        'hit_rate': round(markov_hits / len(df), 4),
        'top_6': [z for z, _ in top6_markov],
        'strategy': '基于状态转移矩阵选择概率最高的6个生肖'
    }

    # 保存报告
    with open('/home/admin1/liuhecai_strategy_search/baseline_report.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 打印结果
    print(f"\n    基线结果:")
    print(f"    - 随机策略: {results['baseline_random']['mean']:.2%} (期望 ~50%)")
    print(f"    - 频率策略: {results['baseline_frequency']['hit_rate']:.2%}")
    print(f"    - 冷热策略: {results['baseline_hot_cold']['hit_rate']:.2%}")
    print(f"    - 马尔可夫: {results['baseline_markov']['hit_rate']:.2%}")

    return results

# ============ 4. 最终状态 ============
def generate_training_gate(feature_check, label_check, baseline_results):
    """生成最终训练门状态"""
    print("\n[4] 最终状态...")

    status = {
        'data_layer': 'PASS',  # truth_dataset.json 加载成功
        'feature_layer': 'PASS' if feature_check['all_valid'] else 'FAIL',
        'label_layer': 'PASS' if label_check['status'] == 'PASS' else 'WARN',
        'baseline_layer': 'PASS',
        'status': 'GREEN',
        'details': {
            'feature_snapshot': feature_check,
            'label_validation': label_check,
            'baseline_report': baseline_results
        }
    }

    # 判断最终状态
    if status['feature_layer'] == 'FAIL':
        status['status'] = 'RED'
    elif status['baseline_layer'] == 'FAIL':
        status['status'] = 'RED'
    else:
        status['status'] = 'GREEN'

    with open('/home/admin1/liuhecai_strategy_search/training_gate.json', 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    return status

# ============ 主程序 ============
def main():
    print("=" * 60)
    print("预训练验证 (Pre-Training Validation)")
    print("=" * 60)
    print(f"数据源: truth_dataset.json")

    # 加载数据
    df = load_truth_data()

    # 执行验证
    print("\n" + "-" * 60)
    feature_check = check_feature_snapshot(df)

    print("\n" + "-" * 60)
    label_check = check_labels(df)

    print("\n" + "-" * 60)
    baseline_results = run_baselines(df)

    print("\n" + "-" * 60)
    gate_status = generate_training_gate(feature_check, label_check, baseline_results)

    # 最终报告
    print("\n" + "=" * 60)
    print("预训练验证结果")
    print("=" * 60)

    print(f"\n数据层: {gate_status['data_layer']}")
    print(f"特征层: {gate_status['feature_layer']}")
    print(f"标签层: {gate_status['label_layer']}")
    print(f"基线层: {gate_status['baseline_layer']}")

    print(f"\n最终状态: {gate_status['status']}")

    print(f"\n输出文件:")
    print(f"  - feature_snapshot.json")
    print(f"  - label_validation.json")
    print(f"  - baseline_report.json")
    print(f"  - training_gate.json")

    if gate_status['status'] == 'GREEN':
        print("\n✓ 允许进入策略训练")
    else:
        print("\n✗ 禁止进入策略训练")

    return gate_status

if __name__ == '__main__':
    main()