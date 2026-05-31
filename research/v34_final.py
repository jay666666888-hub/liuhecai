#!/usr/bin/env python3
"""
澳门六合 - v34 最终融合策略
基于v12核心 + 微调增强
目标：超过v12的55.27%
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


def v12_core(history, top_k=6):
    """v12核心预测"""
    return predict_top6(history, V12_PARAMS, "pattern_based")


def enhanced_v12(history, top_k=6):
    """增强版v12：加入多尺度gap分析"""
    n = len(history)
    lookback = 11
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

        # 多尺度gap增强
        gap_30 = 999
        for i in range(n - 1, -1, -1):
            if history[i].get('特码生肖') == z:
                gap_30 = n - i - 1
                break

        # gap加权：短期gap和长期gap结合
        gap_score = min(current_gap, 50) * 0.098 + min(gap_30, 100) * 0.03

        scores[z] = (
            pattern_ratio * 1.45 +
            gap_score +
            trend * 0.267 +
            (1 / (1 + variance)) * 0.177
        )

    return sorted(ZODIACS, key=lambda z: scores[z], reverse=True)[:6]


def adaptive_v12(history, top_k=6):
    """自适应v12：根据近期表现调整参数"""
    n = len(history)

    # 计算近期准确率
    if n < 150:
        return v12_core(history, top_k)

    # 使用history本身计算近期准确率
    recent_hits = []
    for i in range(max(0, n - 50), n):
        history_i = history[:i]
        actual_i = history[i]['特码生肖']
        pred_i = v12_core(history_i, top_k)
        recent_hits.append(actual_i in pred_i)

    recent_rate = sum(recent_hits) / len(recent_hits)

    # 如果近期表现好，保持v12
    if recent_rate >= 0.55:
        return v12_core(history, top_k)

    # 如果近期表现差，尝试增强版
    return enhanced_v12(history, top_k)


def freq_blend(history, top_k=6):
    """v12 + 频率融合"""
    pred_v12 = v12_core(history, top_k)

    # 频率预测
    freq = Counter(r['特码生肖'] for r in history[-50:])
    pred_freq = [z for z, c in freq.most_common(top_k)]

    # 融合：v12为主，freq补充
    fused = pred_v12[:4]  # 取v12前4个
    for z in pred_freq:
        if z not in fused and len(fused) < top_k:
            fused.append(z)

    return fused[:top_k]


def trend_adjusted(history, top_k=6):
    """趋势调整版v12"""
    pred_v12 = v12_core(history, top_k)

    n = len(history)
    # 计算近期趋势
    recent_zodiacs = [r['特码生肖'] for r in history[-10:]]
    recent_freq = Counter(recent_zodiacs)

    # 调整：如果某个v12预测的生肖近期很热，降低其优先级
    adjusted = []
    for z in pred_v12:
        recent_count = recent_freq.get(z, 0)
        # 如果近期出现>=4次，可能过热
        if recent_count < 4:
            adjusted.append(z)
        else:
            # 放到后面
            adjusted.append((recent_count, z))

    # 重新排序
    adjusted = sorted(adjusted, key=lambda x: x[0] if isinstance(x, tuple) else 0)
    result = [z if not isinstance(z, tuple) else z[1] for z in adjusted]

    # 如果调整后不够6个，用原始
    while len(result) < top_k:
        for z in pred_v12:
            if z not in result:
                result.append(z)
                if len(result) >= top_k:
                    break

    return result[:top_k]


def window_test(predict_func, standard, name):
    """分窗口测试"""
    n = len(standard)

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


def full_backtest(predict_func, standard, name):
    """全量回测"""
    n = len(standard)
    hits = 0
    total = 0
    results = []

    for i in range(100, n):
        history = standard[:i]
        actual = standard[i]['特码生肖']
        pred = predict_func(history, top_k=6)
        if actual in pred:
            hits += 1
        total += 1
        results.append(actual in pred)

    return {
        'name': name,
        'hits': hits,
        'total': total,
        'hit_rate': hits / total if total > 0 else 0,
        'results': results
    }


print("=" * 60)
print("v34 最终融合策略测试")
print("=" * 60)

records = get_all_records([2024, 2025, 2026])
standard = build_standard_records(records)
print(f"数据: {len(standard)}期")

versions = [
    ("v12核心", v12_core),
    ("增强版v12", enhanced_v12),
    ("v12+频率融合", freq_blend),
    ("趋势调整版", trend_adjusted),
]

print("\n--- 全量回测 ---")
results = []
for name, func in versions:
    r = full_backtest(func, standard, name)
    results.append(r)
    print(f"{name}: {r['hits']}/{r['total']} = {r['hit_rate']*100:.2f}%")

best = max(results, key=lambda x: x['hit_rate'])
print(f"\n最佳: {best['name']} ({best['hit_rate']*100:.2f}%)")

print(f"\n--- {best['name']} 分窗口测试 ---")
best_func = next(f for n, f in versions if n == best['name'])
window_test(best_func, standard, best['name'])

# 稳定性
print(f"\n--- {best['name']} 稳定性 ---")
res = best['results']
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