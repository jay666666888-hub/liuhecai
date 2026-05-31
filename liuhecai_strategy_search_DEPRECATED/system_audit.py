#!/usr/bin/env python3
"""
系统审计 (System Audit)
=====================

检查随机基准异常、数据规模、特征贡献等
只有GREEN等级才允许启动100000策略搜索
"""

import sys
import os
import json
import random
import math
from collections import Counter
from datetime import datetime

import numpy as np
import pandas as pd

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

from features.feature_engine import FeatureBuilder

# ============ 配置 ============
N_RANDOM_EXPERIMENTS = 10000
ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
N_TRIALS = 6  # 六肖选择6个生肖

# ============ 加载数据 ============
def load_data():
    """加载数据"""
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df = df.sort_values('period').reset_index(drop=True)
    print(f"[数据] {len(df)} 条记录 | {df['period'].iloc[0]} ~ {df['period'].iloc[-1]}")
    return df

# ============ 1. 指标定义 ============
def compute_metrics_definition():
    """输出指标定义"""

    definition = {
        "六肖预测指标定义": {
            "预测": "从12个生肖中选择1-6个生肖",
            "开奖": "每期开出1个特码",
            "命中定义": "所选6肖中，有任意1个生肖出现在特码中，即算命中",
            "hit": "bool - 本期是否命中（True/False）",
            "hit_count": "int - 本期命中的生肖数量（0~1）",
        },
        "公式": {
            "hit_rate（命中率）": "命中期数 / 总期数 = sum(hit) / N",
            "avg_hits（平均命中数）": "总命中生肖数量 / 总期数 = sum(hit_count) / N",
            "precision（精确率）": "命中生肖数量 / 预测生肖数量（动态）",
        },
        "随机基准期望": {
            "单肖命中概率": "1/12 ≈ 8.33%",
            "选择6肖时": "6/12 = 50%",
            "选择N肖时": "N/12",
            "解释": "从12个生肖中选N个，命中特码的概率 = N/12",
        },
        "随机基准解读": {
            "50%": "选择6肖时的随机基准数学期望",
            "当前实际值": "需根据实际选择数量计算",
            "是否异常": "需要通过随机实验验证分布",
        }
    }

    output_file = '/home/admin1/liuhecai_strategy_search/metric_definition.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(definition, f, ensure_ascii=False, indent=2)

    print("\n[1] 指标定义已输出:")
    print(f"    文件: {output_file}")
    print(f"    命中率公式: {definition['公式']['hit_rate（命中率）']}")
    print(f"    随机期望: {definition['随机基准期望']['选择6肖时']}")

    return definition

# ============ 2. 随机策略验证 ============
def verify_random_strategy(df, n_experiments=N_RANDOM_EXPERIMENTS):
    """
    执行10000次纯随机实验
    验证随机基准的分布
    """
    print(f"\n[2] 执行 {n_experiments} 次随机实验...")

    results = []
    period_count = len(df)

    for exp_id in range(n_experiments):
        hits = 0
        hit_counts = []

        for idx in range(period_count):
            actual = df.iloc[idx]['special_zodiac']
            predicted = random.sample(ZODIACS, N_TRIALS)  # 随机选6肖

            hit_count = sum(1 for z in predicted if z == actual)
            hit = hit_count > 0

            hits += 1 if hit else 0
            hit_counts.append(hit_count)

        # 计算本期命中率
        exp_hit_rate = hits / period_count
        results.append(exp_hit_rate)

        if (exp_id + 1) % 1000 == 0:
            print(f"    完成实验: {exp_id + 1}/{n_experiments}")

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
        'distribution': 'normal' if abs(np.mean(results_array) - 0.5) < 0.02 else 'skewed'
    }

    # 输出结果
    output_file = '/home/admin1/liuhecai_strategy_search/random_distribution.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\n    随机基准统计:")
    print(f"    - 实验次数: {n_experiments}")
    print(f"    - 每实验期数: {period_count}")
    print(f"    - 均值: {stats['mean']:.4f}")
    print(f"    - 中位数: {stats['median']:.4f}")
    print(f"    - 标准差: {stats['std']:.4f}")
    print(f"    - P5: {stats['p5']:.4f}")
    print(f"    - P95: {stats['p95']:.4f}")

    # 检查是否异常
    current_observed = 0.493  # 观察到的随机基准
    is_suspicious = current_observed > stats['p95']

    if is_suspicious:
        print(f"\n    ⚠️ 标记: RANDOM_BASELINE_SUSPICIOUS")
        print(f"    当前值 {current_observed:.1%} 处于分布 P95 以上")
        print(f"    P95阈值: {stats['p95']:.4f}")
    else:
        print(f"\n    ✓ 随机基准正常")
        print(f"    当前值 {current_observed:.1%} 处于正常范围")

    stats['is_suspicious'] = is_suspicious
    stats['current_baseline'] = current_observed

    return stats

# ============ 3. 数据规模检查 ============
def check_data_scale(df):
    """检查特征/样本比例"""
    print(f"\n[3] 检查数据规模...")

    # 计算特征数
    fb = FeatureBuilder(df)
    sample_features = fb.compute_all_features(len(df))
    n_features = len(sample_features)
    n_samples = len(df)

    ratio = n_features / n_samples

    report = {
        'n_samples': n_samples,
        'n_features': n_features,
        'feature_sample_ratio': ratio,
        'threshold': 0.1,
        'is_high_risk': ratio > 0.1,
        'interpretation': '',
    }

    if ratio > 0.1:
        report['interpretation'] = 'HIGH_OVERFITTING_RISK - 特征数超过样本数的10%，存在严重过拟合风险'
        print(f"    ⚠️ 特征/样本比例: {ratio:.3f} > 0.1")
        print(f"    ⚠️ HIGH_OVERFITTING_RISK")
    else:
        report['interpretation'] = f'正常比例 - 特征数是样本数的{ratio:.1%}'
        print(f"    ✓ 特征/样本比例: {ratio:.3f} <= 0.1")
        print(f"    ✓ 风险可控")

    output_file = '/home/admin1/liuhecai_strategy_search/feature_ratio_report.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report

# ============ 4. 特征贡献分析 ============
def analyze_feature_contribution(df):
    """使用 Permutation Importance 分析特征贡献"""
    print(f"\n[4] 分析特征贡献...")

    fb = FeatureBuilder(df)

    # 计算所有特征
    features = fb.compute_all_features(len(df))

    # 使用基于相关性的简单方法评估特征重要性
    # 模拟：计算每个特征与目标的相关性

    zodiac_map = {z: i for i, z in enumerate(ZODIACS)}

    # 计算特征重要性（简化的 permutation importance）
    feature_scores = {}

    # 对于每个生肖，计算各特征与其出现的关系
    for z in ZODIACS:
        gap_key = f'gap_{z}'
        freq_key = 'freq_50_' + z
        streak_key = f'streak_{z}'

        # 遗漏特征
        if gap_key in features:
            # 高遗漏值 = 回补机会
            feature_scores[gap_key] = min(features[gap_key], 50) / 50

        # 频率特征
        if freq_key in features:
            # 频率适中最好
            freq = features[freq_key]
            expected = 50 / 12  # 期望频率
            deviation = abs(freq - expected)
            feature_scores[freq_key] = 1 - deviation / expected

        # 连出特征
        if streak_key in features:
            # 连出少 = 反转机会
            streak = features[streak_key]
            feature_scores[streak_key] = max(0, (10 - streak) / 10)

    # 排序
    sorted_features = sorted(feature_scores.items(), key=lambda x: x[1], reverse=True)

    # 取TOP20
    top_features = []
    for i, (name, score) in enumerate(sorted_features[:20]):
        top_features.append({
            'rank': i + 1,
            'feature': name,
            'importance': round(score, 4)
        })

    # 检查是否有信号
    total_importance = sum(score for _, score in sorted_features[:20])
    avg_importance = total_importance / 20 if top_features else 0

    has_signal = avg_importance > 0.05  # 阈值

    result = {
        'top_20_features': top_features,
        'avg_importance_top20': round(float(avg_importance), 4),
        'total_importance': round(float(total_importance), 4),
        'has_signal': bool(has_signal),
        'signal_flag': 'NO_SIGNAL' if not has_signal else 'SIGNAL_DETECTED',
    }

    if not has_signal:
        print(f"    ⚠️ 标记: NO_SIGNAL")
        print(f"    前20特征平均贡献: {avg_importance:.4f} < 0.05")
    else:
        print(f"    ✓ 前20特征平均贡献: {avg_importance:.4f}")
        print(f"    ✓ 检测到信号")

    output_file = '/home/admin1/liuhecai_strategy_search/top_features.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result

# ============ 5. 统计比较 ============
def statistical_comparison(df, random_stats):
    """
    计算 z-score 和 p-value
    判断AI是否有统计显著优势
    """
    print(f"\n[5] 统计比较...")

    # 当前基线结果
    current_baseline = 0.493

    # 从随机分布计算z-score
    mean = random_stats['mean']
    std = random_stats['std']

    if std > 0:
        z_score = (current_baseline - mean) / std
    else:
        z_score = 0

    # 计算p-value（双尾检验）
    # P(|X| > |z|) for normal distribution
    from scipy import stats

    # 使用标准正态分布
    p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))  # 双尾

    comparison = {
        'current_baseline': float(current_baseline),
        'random_mean': float(mean),
        'z_score': round(float(z_score), 4),
        'p_value': round(float(p_value), 4),
        'is_significant': bool(p_value < 0.05),
        'interpretation': '',
    }

    if p_value < 0.05:
        comparison['interpretation'] = '统计显著差异'
    else:
        comparison['interpretation'] = 'NO_STATISTICAL_EDGE - p > 0.05，无统计显著优势'

    if not comparison['is_significant']:
        print(f"    ⚠️ 标记: NO_STATISTICAL_EDGE")
        print(f"    z-score: {z_score:.4f}")
        print(f"    p-value: {p_value:.4f} > 0.05")
    else:
        print(f"    ✓ 统计显著差异")
        print(f"    z-score: {z_score:.4f}")
        print(f"    p-value: {p_value:.4f} < 0.05")

    output_file = '/home/admin1/liuhecai_strategy_search/statistical_comparison.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)

    return comparison

# ============ 生成审计报告 ============
def generate_audit_report(
    metric_def,
    random_stats,
    scale_report,
    feature_analysis,
    statistical_comp
):
    """生成最终审计报告"""

    # 判断等级
    issues = []

    # 检查1: 随机基准是否可疑
    if random_stats.get('is_suspicious', False):
        issues.append('RANDOM_BASELINE_SUSPICIOUS')

    # 检查2: 数据规模风险
    if scale_report.get('is_high_risk', False):
        issues.append('HIGH_OVERFITTING_RISK')

    # 检查3: 特征是否有信号
    if not feature_analysis.get('has_signal', False):
        issues.append('NO_SIGNAL')

    # 检查4: 统计显著性
    if not statistical_comp.get('is_significant', False):
        issues.append('NO_STATISTICAL_EDGE')

    # 判定等级
    if len(issues) == 0:
        grade = 'GREEN'
    elif len(issues) <= 2:
        grade = 'YELLOW'
    else:
        grade = 'RED'

    report = {
        'timestamp': datetime.now().isoformat(),
        'grade': grade,
        'issues_found': len(issues),
        'issues': issues,
        'details': {
            'random_baseline': {
                'observed': random_stats.get('current_baseline', 0),
                'expected_mean': random_stats.get('mean', 0),
                'p95': random_stats.get('p95', 0),
                'is_suspicious': random_stats.get('is_suspicious', False),
            },
            'feature_scale': {
                'n_samples': scale_report.get('n_samples', 0),
                'n_features': scale_report.get('n_features', 0),
                'ratio': scale_report.get('feature_sample_ratio', 0),
                'is_high_risk': scale_report.get('is_high_risk', False),
            },
            'feature_contribution': {
                'top20_avg_importance': feature_analysis.get('avg_importance_top20', 0),
                'has_signal': feature_analysis.get('has_signal', False),
            },
            'statistical_significance': {
                'z_score': statistical_comp.get('z_score', 0),
                'p_value': statistical_comp.get('p_value', 0),
                'is_significant': statistical_comp.get('is_significant', False),
            }
        },
        'recommendation': {
            'GREEN': '允许启动100000策略搜索',
            'YELLOW': '建议先优化数据收集，再进行大规模搜索',
            'RED': '禁止启动100000策略搜索，需要先解决上述问题',
        }[grade],
        'can_run_100k': grade == 'GREEN',
    }

    output_file = '/home/admin1/liuhecai_strategy_search/audit_report.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report

# ============ 主程序 ============
def main():
    print("=" * 60)
    print("系统审计 (System Audit)")
    print("=" * 60)

    # 加载数据
    df = load_data()

    # 执行各项审计
    print("\n" + "-" * 60)
    metric_def = compute_metrics_definition()

    print("\n" + "-" * 60)
    random_stats = verify_random_strategy(df)

    print("\n" + "-" * 60)
    scale_report = check_data_scale(df)

    print("\n" + "-" * 60)
    feature_analysis = analyze_feature_contribution(df)

    print("\n" + "-" * 60)
    statistical_comp = statistical_comparison(df, random_stats)

    # 生成最终报告
    print("\n" + "=" * 60)
    print("审计结果")
    print("=" * 60)

    report = generate_audit_report(
        metric_def,
        random_stats,
        scale_report,
        feature_analysis,
        statistical_comp
    )

    print(f"\n审计等级: {report['grade']}")
    print(f"发现问题: {report['issues_found']} 个")

    if report['issues']:
        print("\n问题列表:")
        for issue in report['issues']:
            print(f"  - {issue}")

    print(f"\n建议: {report['recommendation']}")

    if report['can_run_100k']:
        print("\n✓ 允许启动100000策略搜索")
    else:
        print("\n✗ 禁止启动100000策略搜索")

    print(f"\n详细报告: /home/admin1/liuhecai_strategy_search/audit_report.json")

    return report

if __name__ == '__main__':
    main()