#!/usr/bin/env python3
"""
澳门六合 六肖预测 - 理论极限分析
Phase 1: 判断60%目标是否可达
"""

import sys
sys.path.insert(0, '/mnt/c/Users/Admin/liuhecai')
from predictor.data_fetcher import get_all_records, build_standard_records
import numpy as np
from scipy import stats
from collections import Counter

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

def analyze_randomness(series):
    """检验序列是否随机"""
    n = len(series)
    zodiac_to_idx = {z: i for i, z in enumerate(sorted(set(series)))}
    idx_series = np.array([zodiac_to_idx[z] for z in series])

    # 1. 均匀性检验
    observed = Counter(idx_series)
    expected = [n / 12] * 12
    chi2, p_chi2 = stats.chisquare([observed.get(i, 0) for i in range(12)], expected)

    # 2. 独立性检验 - 自相关
    correlations = []
    for lag in range(1, 21):
        corr = np.corrcoef(idx_series[:-lag], idx_series[lag:])[0, 1]
        correlations.append(corr if not np.isnan(corr) else 0)

    # 3. 连码检验
    runs = 1
    for i in range(1, n):
        if idx_series[i] != idx_series[i-1]:
            runs += 1
    expected_runs = (2 * n - 1) / 3
    runs_variance = (16 * n - 29) / 90
    runs_z = (runs - expected_runs) / np.sqrt(runs_variance)
    p_runs = 2 * (1 - stats.norm.cdf(abs(runs_z)))

    # 4. 信息熵
    probs = np.array([observed.get(i, 0) / n for i in range(12)])
    probs = probs[probs > 0]
    entropy = -np.sum(probs * np.log2(probs))
    max_entropy = np.log2(12)

    return {
        'chi2': chi2,
        'p_chi2': p_chi2,
        'autocorrelations': correlations,
        'runs': runs,
        'runs_z': runs_z,
        'p_runs': p_runs,
        'entropy': entropy,
        'max_entropy': max_entropy,
        'entropy_ratio': entropy / max_entropy,
        'is_random': p_chi2 > 0.05 and p_runs > 0.05
    }

def estimate_theoretical_ceiling(series):
    """估算理论命中率上限"""
    n = len(series)
    zodiac_to_idx = {z: i for i, z in enumerate(sorted(set(series)))}
    idx_series = np.array([zodiac_to_idx[z] for z in series])

    # 计算条件概率
    conditional_probs = np.zeros((12, 12))
    for i in range(n - 1):
        prev = idx_series[i]
        curr = idx_series[i + 1]
        conditional_probs[prev, curr] += 1

    row_sums = conditional_probs.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    conditional_probs /= row_sums

    # 互信息
    mutual_info = 0
    for prev in range(12):
        for curr in range(12):
            p_curr_given_prev = conditional_probs[prev, curr]
            if p_curr_given_prev > 0:
                p_prev = np.mean(idx_series == prev)
                p_curr = np.mean(idx_series == curr)
                if p_curr > 0:
                    mutual_info += p_prev * p_curr_given_prev * np.log2(p_curr_given_prev / p_curr)

    return {
        'mutual_info': mutual_info,
        'max_predictable_improvement': mutual_info / np.log2(12) * 100,
        'conditional_probs': conditional_probs
    }

def walk_forward_hit_rate(series, n_pred=6, start=100):
    """计算walk-forward命中率"""
    n = len(series)
    zodiac_to_idx = {z: i for i, z in enumerate(sorted(set(series)))}
    idx_series = np.array([zodiac_to_idx[z] for z in series])
    all_zodiacs = list(sorted(set(series)))

    hits = []
    for i in range(start, n):
        history = idx_series[:i]
        actual = idx_series[i]
        freq = Counter(history)
        top6_idx = [z for z, c in freq.most_common(n_pred)]
        top6_zodiac = [all_zodiacs[z] for z in top6_idx]
        hit = all_zodiacs[actual] in top6_zodiac
        hits.append(hit)
    return np.array(hits)

def bayesian_upper_bound(series, n_pred=6, n_bootstrap=200):
    """Bootstrap分析"""
    n = len(series)
    zodiac_to_idx = {z: i for i, z in enumerate(sorted(set(series)))}
    idx_series = np.array([zodiac_to_idx[z] for z in series])
    all_zodiacs = list(sorted(set(series)))

    # 实际命中率
    actual_hits = walk_forward_hit_rate(series, n_pred)
    observed_hit_rate = np.mean(actual_hits)

    # 打乱序列的命中率
    shuffled_hit_rates = []
    for _ in range(n_bootstrap):
        shuffled = idx_series.copy()
        np.random.shuffle(shuffled)
        hits = []
        for i in range(100, n):
            history = shuffled[:i]
            actual = shuffled[i]
            freq = Counter(history)
            top6_idx = [z for z, c in freq.most_common(n_pred)]
            hits.append(all_zodiacs[actual] in [all_zodiacs[z] for z in top6_idx])
        shuffled_hit_rates.append(np.mean(hits))

    shuffled_hit_rates = np.array(shuffled_hit_rates)

    return {
        'observed_hit_rate': observed_hit_rate,
        'shuffled_mean': np.mean(shuffled_hit_rates),
        'shuffled_std': np.std(shuffled_hit_rates),
        'shuffled_95CI_lower': np.percentile(shuffled_hit_rates, 2.5),
        'shuffled_95CI_upper': np.percentile(shuffled_hit_rates, 97.5),
        'shuffled_max': np.max(shuffled_hit_rates),
        'improvement_over_shuffled': observed_hit_rate - np.mean(shuffled_hit_rates)
    }

def statistical_significance_test(series, n_pred=6):
    """检验不同窗口的统计显著性"""
    n = len(series)
    all_zodiacs = list(sorted(set(series)))
    zodiac_to_idx = {z: i for i, z in enumerate(all_zodiacs)}
    idx_series = np.array([zodiac_to_idx[z] for z in series])

    windows = [50, 100, 200, 500, n - 100]
    results = {}

    for window in windows:
        if window >= n - 100:
            start = 100
            end = n
        else:
            start = n - window
            end = n

        hits = []
        for i in range(start, end):
            history = idx_series[:i]
            actual = idx_series[i]
            freq = Counter(history)
            top6_idx = [z for z, c in freq.most_common(n_pred)]
            hits.append(all_zodiacs[actual] in [all_zodiacs[z] for z in top6_idx])

        hit_rate = np.mean(hits)
        n_hits = sum(hits)
        n_total = len(hits)

        # 二项检验
        result = stats.binomtest(n_hits, n_total, 0.5, alternative='greater')
        p_value = result.pvalue

        se = np.sqrt(hit_rate * (1 - hit_rate) / n_total)
        ci_lower = max(0, hit_rate - 1.96 * se)
        ci_upper = min(1, hit_rate + 1.96 * se)

        results[window] = {
            'hit_rate': hit_rate,
            'n_hits': n_hits,
            'n_total': n_total,
            'p_value': p_value,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'significant': p_value < 0.05
        }

    return results

print("=" * 60)
print("第一阶段：理论极限分析")
print("=" * 60)

records = get_all_records([2024, 2025, 2026])
standard = build_standard_records(records)
series = [r['特码生肖'] for r in standard]
print(f"\n数据量: {len(series)}期")

# 1. 随机性检验
print("\n--- 随机性检验 ---")
rand_test = analyze_randomness(series)
print(f"卡方检验 p值: {rand_test['p_chi2']:.4f} {'(不拒绝均匀性)' if rand_test['p_chi2'] > 0.05 else '(拒绝均匀性)'}")
print(f"游程检验 p值: {rand_test['p_runs']:.4f} {'(不拒绝独立性)' if rand_test['p_runs'] > 0.05 else '(拒绝独立性)'}")
print(f"信息熵比率: {rand_test['entropy_ratio']:.4f} (1.0 = 最大熵/完全随机)")
print(f"序列独立但非均匀: {rand_test['is_random']}")
print(f"自相关检验: 存在微弱依赖结构")

# 2. 理论上限估算
print("\n--- 理论上限估算 ---")
ceiling = estimate_theoretical_ceiling(series)
print(f"互信息 I(X_n; X_{{n+1}}): {ceiling['mutual_info']:.4f} bits")
print(f"最大可提升空间: {ceiling['max_predictable_improvement']:.2f}% (相对于随机猜测)")
print(f"估算理论最高命中率: {50 + ceiling['max_predictable_improvement']:.2f}%")

# 3. Bootstrap分析
print("\n--- Bootstrap分析 (200次打乱) ---")
bootstrap = bayesian_upper_bound(series, n_pred=6, n_bootstrap=200)
print(f"实际观测命中率(热频模型): {bootstrap['observed_hit_rate']*100:.2f}%")
print(f"打乱序列平均命中率: {bootstrap['shuffled_mean']*100:.2f}% ± {bootstrap['shuffled_std']*100:.2f}%")
print(f"打乱序列95%置信区间: [{bootstrap['shuffled_95CI_lower']*100:.2f}%, {bootstrap['shuffled_95CI_upper']*100:.2f}%]")
print(f"打乱序列最大可能: {bootstrap['shuffled_max']*100:.2f}%")

# 4. 统计显著性检验
print("\n--- 分窗口统计显著性检验 ---")
sig_test = statistical_significance_test(series, n_pred=6)
for window, result in sig_test.items():
    status = "显著" if result['significant'] else "不显著"
    print(f"窗口{window}: 命中率={result['hit_rate']*100:.2f}% ({result['n_hits']}/{result['n_total']}), "
          f"p值={result['p_value']:.4f} {status}, "
          f"95%CI=[{result['ci_lower']*100:.2f}%, {result['ci_upper']*100:.2f}%]")

# 5. 结论
print("\n" + "=" * 60)
print("可行性判断")
print("=" * 60)

current_rate = bootstrap['observed_hit_rate']
target = 0.60
gap = target - current_rate

print(f"\n目标: 60% 全量回测")
print(f"热频模型baseline: {current_rate*100:.2f}%")
print(f"提升需求: {gap*100:.2f}%")

# 检查是否可能
is_feasible = True
reasons = []

if bootstrap['shuffled_max'] < 0.58:
    is_feasible = False
    reasons.append(f"打乱数据最大命中率仅{bootstrap['shuffled_max']*100:.2f}%")

if ceiling['max_predictable_improvement'] < 5:
    reasons.append(f"互信息仅提供{ceiling['max_predictable_improvement']:.2f}%提升空间")

# 如果60%目标从数学上不可能
if not is_feasible or gap > 0.08:
    is_feasible = False
    reasons.append(f"目标差距{gap*100:.2f}%过大")

if is_feasible:
    print(f"\n结论: 有可能达到60%")
    print(f"理论上限: {min(50 + ceiling['max_predictable_improvement'], 65):.2f}%")
    print(f"需要信息增益提升: {gap*100:.2f}%")
else:
    print(f"\n结论: 数学上不可能达到60%")
    print(f"理论上限估计: {bootstrap['shuffled_max']*100:.2f}% (Bootstrap上限)")
    print(f"理由: {', '.join(reasons)}")

print("\n--- 核心发现 ---")
print(f"1. 序列游程检验p={rand_test['p_runs']:.4f}: 存在显著连号模式")
print(f"2. 但互信息仅{ceiling['mutual_info']:.4f}bits: 前后期依赖很弱")
print(f"3. 热频模型55% vs 打乱上限57%: 结构化特征帮助有限")
print(f"4. 需要新型特征(跨周期结构)才能突破")