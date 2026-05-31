#!/usr/bin/env python3
"""
澳门六合 - v33 Walk-Forward参数验证
验证各版本的真实命中率
"""

import sys
sys.path.insert(0, '/mnt/c/Users/Admin/liuhecai')
from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.six_zodiac_predictor import predict_top6
import numpy as np
from collections import Counter

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

V12_PARAMS = {
    "lookback": 11,
    "pattern_weight": 1.45,
    "gap_weight": 0.098,
    "trend_weight": 0.267,
    "variance_weight": 0.177,
    "alt_mode": "trend"
}


def v12_predict(history, top_k=6):
    """v12原始预测"""
    return predict_top6(history, V12_PARAMS, "pattern_based")


def v12_standalone(history, top_k=6):
    """v12独立实现"""
    n = len(history)
    lookback = min(11, n)
    window = history[n-lookback:n]

    scores = {}
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
            avg_int = sum(recent_intervals) / len(recent_intervals)
            variance = sum((x - avg_int) ** 2 for x in recent_intervals) / len(recent_intervals)
        else:
            variance = 0

        scores[z] = (
            pattern_ratio * 1.45 +
            min(current_gap, 50) * 0.098 +
            trend * 0.267 +
            (1 / (1 + variance)) * 0.177
        )

    return sorted(ZODIACS, key=lambda z: scores[z], reverse=True)[:6]


def freq_predict(history, top_k=6):
    """频率模型预测"""
    freq = Counter(r['特码生肖'] for r in history[-100:])
    return [z for z, c in freq.most_common(top_k)]


def walkforward_test(predict_func, standard, name="Test"):
    """Walk-forward诚实回测"""
    n = len(standard)
    hits = 0
    total = 0
    results = []

    for i in range(100, n):
        history = standard[:i]
        actual = standard[i]['特码生肖']
        pred = predict_func(history, top_k=6)
        hit = actual in pred
        if hit:
            hits += 1
        total += 1
        results.append(hit)

    return {
        'name': name,
        'total': total,
        'hits': hits,
        'hit_rate': hits / total if total > 0 else 0,
        'results': results
    }


def window_test(predict_func, standard, name):
    """分窗口测试"""
    n = len(standard)
    print(f"\n--- {name} 分窗口测试 ---")

    for w in [30, 50, 100, 200, 500]:
        if w >= n - 100:
            start = 100
        else:
            start = n - w

        hits = 0
        total = 0
        for i in range(start, n):
            history = standard[:i]
            actual = standard[i]['特码生肖']
            pred = predict_func(history, top_k=6)
            if actual in pred:
                hits += 1
            total += 1

        print(f"最近{w}: {hits}/{total} = {hits/total*100:.2f}%")


print("=" * 60)
print("v33 Walk-Forward验证")
print("=" * 60)

records = get_all_records([2024, 2025, 2026])
standard = build_standard_records(records)
print(f"数据: {len(standard)}期")

# 测试各版本
versions = [
    (v12_predict, "v12原始"),
    (v12_standalone, "v12独立实现"),
    (freq_predict, "频率模型"),
]

print("\n--- 全量回测 ---")
results = {}
for pred_func, name in versions:
    result = walkforward_test(pred_func, standard, name)
    results[name] = result
    print(f"{name}: {result['hits']}/{result['total']} = {result['hit_rate']*100:.2f}%")

# 找到最好的版本
best_name = max(results.keys(), key=lambda k: results[k]['hit_rate'])
print(f"\n最佳版本: {best_name}")

# 对最佳版本做分窗口测试
best_func = next(f for f, n in versions if n == best_name)
window_test(best_func, standard, best_name)

# 稳定性分析
print(f"\n--- {best_name} 稳定性分析 ---")
res = results[best_name]['results']
window_size = 50
sliding = []
for i in range(len(res)):
    start = max(0, i - window_size + 1)
    sliding.append(np.mean(res[start:i+1]))

print(f"滑动50期: min={min(sliding)*100:.2f}%, max={max(sliding)*100:.2f}%, std={np.std(sliding)*100:.2f}%")

for w in [30, 50, 100]:
    if len(res) >= w:
        recent = res[-w:]
        print(f"最近{w}: {sum(recent)}/{w} = {sum(recent)/w*100:.2f}%")

print("\n" + "=" * 60)