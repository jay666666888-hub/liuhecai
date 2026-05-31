#!/usr/bin/env python3
"""
澳门六合 - v32 精准调参预测器 (快速版)
在v12核心逻辑基础上进行精准参数调优
"""

import sys
sys.path.insert(0, '/mnt/c/Users/Admin/liuhecai')
from predictor.data_fetcher import get_all_records, build_standard_records
import numpy as np
from collections import Counter

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


def compute_features(history, lookback=11):
    """计算v12风格特征"""
    n = len(history)
    window = history[max(0, n-lookback):n]

    features = {}
    for z in ZODIACS:
        positions = [i for i, r in enumerate(window) if r.get('特码生肖') == z]
        if not positions:
            current_gap, pattern_ratio = 999, 0.0
        else:
            current_gap = lookback - positions[-1] - 1
            pattern_count = len([p for p in positions if p < 3])
            pattern_ratio = pattern_count / lookback

        positions_full = [i for i, r in enumerate(history) if r.get('特码生肖') == z]
        if len(positions_full) >= 2:
            intervals = [positions_full[i] - positions_full[i-1] for i in range(1, len(positions_full))]
            trend = intervals[-1] - intervals[-2] if len(intervals) >= 2 else 0
        else:
            trend = 0

        if len(positions_full) >= 3:
            recent_intervals = intervals[-3:]
            variance = np.var(recent_intervals)
        else:
            variance = 0

        features[z] = {
            'pattern_ratio': pattern_ratio,
            'gap': current_gap,
            'trend': trend,
            'variance': variance
        }
    return features


def score_with_params(features, params):
    """用给定参数计算得分"""
    scores = {}
    for z, f in features.items():
        scores[z] = (
            f['pattern_ratio'] * params['pattern_weight'] +
            min(f['gap'], 50) * params['gap_weight'] +
            f['trend'] * params['trend_weight'] +
            (1 / (1 + f['variance'])) * params['variance_weight']
        )
    return scores


def backtest_params(params, standard, start=100):
    """回测"""
    n = len(standard)
    hits = 0
    total = 0

    for i in range(start, n):
        history = standard[:i]
        actual = standard[i]['特码生肖']
        features = compute_features(history, lookback=int(params.get('lookback', 11)))
        scores = score_with_params(features, params)
        pred = sorted(ZODIACS, key=lambda z: scores[z], reverse=True)[:6]
        if actual in pred:
            hits += 1
        total += 1

    return hits / total if total > 0 else 0


def quick_search(standard):
    """快速搜索 (减少组合数)"""
    print("快速网格搜索...")

    best_hit_rate = 0
    best_params = None
    results = []

    # 精简搜索空间
    lookback_values = [9, 11, 13]
    pattern_weight_values = [1.2, 1.45, 1.7]
    gap_weight_values = [0.08, 0.098, 0.12]
    trend_weight_values = [0.25, 0.267, 0.30]
    variance_weight_values = [0.15, 0.177, 0.2]

    count = 0
    total = len(lookback_values) * len(pattern_weight_values) * len(gap_weight_values) * len(trend_weight_values) * len(variance_weight_values)

    for lb in lookback_values:
        for pw in pattern_weight_values:
            for gw in gap_weight_values:
                for tw in trend_weight_values:
                    for vw in variance_weight_values:
                        params = {
                            'lookback': lb,
                            'pattern_weight': pw,
                            'gap_weight': gw,
                            'trend_weight': tw,
                            'variance_weight': vw
                        }
                        hit_rate = backtest_params(params, standard)
                        results.append((hit_rate, params.copy()))

                        if hit_rate > best_hit_rate:
                            best_hit_rate = hit_rate
                            best_params = params.copy()

                        count += 1

    results.sort(reverse=True, key=lambda x: x[0])

    print(f"搜索完成! 最佳: {best_hit_rate*100:.2f}%")
    print(f"最佳参数: {best_params}")

    print("\n--- Top 10 ---")
    for i, (hr, p) in enumerate(results[:10]):
        print(f"{i+1}. {hr*100:.2f}%: lb={p['lookback']}, pw={p['pattern_weight']:.2f}, "
              f"gw={p['gap_weight']:.3f}, tw={p['trend_weight']:.3f}, vw={p['variance_weight']:.3f}")

    return results


def window_test(params, standard):
    """分窗口测试"""
    print("\n--- 分窗口测试 ---")
    n = len(standard)

    for w in [50, 100, 200, 500, n-100]:
        start = max(100, n - w)
        hits = sum(1 for i in range(start, n)
                  if standard[i]['特码生肖'] in (
                      sorted(ZODIACS, key=lambda z: score_with_params(
                          compute_features(standard[:i], lookback=int(params['lookback'])), params)[z],
                          reverse=True)[:6]))
        total = n - start
        print(f"窗口{w}: {hits}/{total} = {hits/total*100:.2f}%")


print("=" * 60)
print("v32 精准参数调优")
print("=" * 60)

records = get_all_records([2024, 2025, 2026])
standard = build_standard_records(records)
print(f"数据: {len(standard)}期")

results = quick_search(standard)
best_params = results[0][1]

print("\n--- v12原始参数对比 ---")
v12_params = {'lookback': 11, 'pattern_weight': 1.45, 'gap_weight': 0.098, 'trend_weight': 0.267, 'variance_weight': 0.177}
v12_hr = backtest_params(v12_params, standard)
print(f"v12原始: {v12_hr*100:.2f}%")

print("\n--- 最佳参数测试 ---")
window_test(best_params, standard)

print("\n" + "=" * 60)