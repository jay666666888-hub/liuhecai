#!/usr/bin/env python3
"""
澳门六合 - V26 平特一肖参数优化 V6
快速版本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from predictor.data_fetcher import get_all_records, build_standard_records
import random

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


def evaluate(history, lb, w_gap, w_freq, w_trend, w_var):
    """快速评估"""
    n = len(history)
    if n < lb + 10:
        return 0, 0

    hits = 0
    total = 0

    for i in range(lb, n):
        window = history[max(0, i-lb):i]
        current = history[i]

        scores = {}
        for z in ZODIACS:
            positions = [idx for idx, r in enumerate(window) if r["特码生肖"] == z]

            if not positions:
                scores[z] = 0.0
                continue

            gap = len(window) - positions[-1] - 1
            frequency = len(positions)
            intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]

            gap_score = min(gap, 50) / 50
            freq_score = frequency / lb

            trend_score = 0.5
            var_score = 0.5
            if len(intervals) >= 2:
                trend = intervals[0] - intervals[1]
                trend_score = max(0, min(trend, 10)) / 10
                avg_i = sum(intervals) / len(intervals)
                variance = sum((x - avg_i) ** 2 for x in intervals) / len(intervals)
                var_score = 1 / (1 + variance / 10)

            total_w = w_gap + w_freq + w_trend + w_var
            if total_w > 0:
                scores[z] = (
                    gap_score * w_gap / total_w +
                    freq_score * w_freq / total_w +
                    trend_score * w_trend / total_w +
                    var_score * w_var / total_w
                )
            else:
                scores[z] = 0.5

        predicted = max(scores, key=scores.get)
        actual = current.get("开奖生肖", [])
        if predicted in actual:
            hits += 1
        total += 1

    return hits / total if total > 0 else 0, total


def search():
    print("获取历史数据...")
    records = get_all_records([2024, 2025, 2026])
    history = build_standard_records(records)
    print(f"历史数据: {len(history)} 期")

    best = 0
    best_params = {}

    print("快速搜索 3000 组...")

    for _ in range(3000):
        lb = random.randint(15, 60)
        w_gap = random.uniform(0, 0.5)
        w_freq = random.uniform(0, 0.5)
        w_trend = random.uniform(0, 0.5)
        w_var = random.uniform(0, 0.5)

        rate, total = evaluate(history, lb, w_gap, w_freq, w_trend, w_var)

        if total > 100 and rate > best:
            best = rate
            best_params = {"lookback": lb, "gap": w_gap, "freq": w_freq, "trend": w_trend, "variance": w_var}
            print(f"  New best: lb={lb}, gap={w_gap:.3f}, freq={w_freq:.3f}, trend={w_trend:.3f}, var={w_var:.3f} -> {rate:.4f}")

    print(f"\n=== 最佳参数 ===")
    print(f"  {best_params}")
    print(f"  命中率: {best:.4f}")
    return best_params


if __name__ == "__main__":
    best = search()
    print(f"\n最终: {best}")
