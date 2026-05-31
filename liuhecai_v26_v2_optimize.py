#!/usr/bin/env python3
"""
澳门六合 - V26 平特一肖参数优化 V5

更多特征 + Optuna 优化
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from predictor.data_fetcher import get_all_records, build_standard_records
import random
import math

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


def evaluate_v5(history, lookback, weights):
    """V5评估：更多特征"""
    n = len(history)
    if n < lookback + 10:
        return 0, 0

    hits = 0
    total = 0

    for i in range(lookback, n):
        window = history[max(0, i-lookback):i]
        current = history[i]

        scores = {}
        for z in ZODIACS:
            positions = [idx for idx, r in enumerate(window) if r["特码生肖"] == z]

            if not positions:
                scores[z] = 0.0
                continue

            # 基础特征
            gap = len(window) - positions[-1] - 1
            frequency = len(positions)
            avg_interval = (positions[-1] - positions[0]) / frequency if frequency > 1 else lookback

            # 间隔列表
            intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]

            # 特征计算
            gap_score = min(gap, 50) / 50
            freq_score = frequency / lookback
            avg_int_score = 1 / (1 + abs(avg_interval - 12) / 10)  # 12期平均

            # Trend
            if len(intervals) >= 2:
                trend = intervals[0] - intervals[1]
                trend_score = max(0, min(trend, 10)) / 10
            else:
                trend_score = 0.5

            # Variance
            if len(intervals) >= 2:
                avg_i = sum(intervals) / len(intervals)
                variance = sum((x - avg_i) ** 2 for x in intervals) / len(intervals)
                variance_score = 1 / (1 + variance / 10)
            else:
                variance_score = 0.5

            # Recency (最近出现位置，越近越好)
            recency_score = 1 - (gap / 50)

            # First appearance (首次出现在窗口内的位置)
            first_pos_score = positions[0] / len(window) if positions else 0

            # Consecutive gap (上次出现到现在隔了多少期)
            if len(positions) >= 2:
                last_interval = positions[-1] - positions[-2]
                consec_score = 1 / (1 + last_interval / 20)
            else:
                consec_score = 0.5

            scores[z] = (
                weights[0] * gap_score +       # gap
                weights[1] * freq_score +     # frequency
                weights[2] * trend_score +    # trend
                weights[3] * variance_score +  # variance
                weights[4] * recency_score +  # recency
                weights[5] * avg_int_score +  # avg_interval
                weights[6] * consec_score     # consecutive
            )

        predicted = max(scores, key=scores.get)
        actual_zodiacs = current.get("开奖生肖", [])
        hit = predicted in actual_zodiacs

        if hit:
            hits += 1
        total += 1

    return hits / total if total > 0 else 0, total


def search_v5():
    """V5搜索"""
    print("获取历史数据...")
    records = get_all_records([2024, 2025, 2026])
    history = build_standard_records(records)
    print(f"历史数据: {len(history)} 期")

    best_hit_rate = 0
    best_params = {}
    results = []

    print("随机搜索 10000 组参数...")

    for _ in range(10000):
        lb = random.randint(15, 80)
        # 7个权重
        w = [random.uniform(0, 1) for _ in range(7)]
        total_w = sum(w)
        if total_w == 0:
            continue
        weights = [x / total_w for x in w]

        hit_rate, total_tests = evaluate_v5(history, lb, weights)

        if total_tests > 100:
            results.append({
                "lookback": lb,
                "weights": weights,
                "hit_rate": hit_rate,
                "total": total_tests
            })

            if hit_rate > best_hit_rate:
                best_hit_rate = hit_rate
                best_params = {"lookback": lb, "weights": weights}
                print(f"  New best: lb={lb}, hit_rate={hit_rate:.4f}")

    results.sort(key=lambda x: x["hit_rate"], reverse=True)
    print("\n=== Top 20 V5 参数组合 ===")
    for i, r in enumerate(results[:20]):
        print(f"  {i+1}. lb={r['lookback']}, w={[f'{x:.3f}' for x in r['weights']]} -> {r['hit_rate']:.4f} ({r['total']}期)")

    print(f"\n=== 最佳 V5 参数 ===")
    print(f"  lookback: {best_params['lookback']}")
    print(f"  weights: {best_params['weights']}")
    print(f"  命中率: {best_hit_rate:.4f}")

    return best_params


def evaluate_advanced(history, lookback, params):
    """高级评估：周日效应"""
    n = len(history)
    if n < lookback + 10:
        return 0, 0

    hits = 0
    total = 0

    w_gap = params.get("gap", 0.1)
    w_freq = params.get("freq", 0.2)
    w_trend = params.get("trend", 0.3)
    w_var = params.get("variance", 0.3)
    w_recency = params.get("recency", 0.1)
    sunday_adjust = params.get("sunday_adjust", 0.0)

    for i in range(lookback, n):
        window = history[max(0, i-lookback):i]
        current = history[i]

        # 判断是否为周日开奖（简化判断）
        is_sunday = False  # 实际应根据日期判断

        scores = {}
        for z in ZODIACS:
            positions = [idx for idx, r in enumerate(window) if r["特码生肖"] == z]

            if not positions:
                scores[z] = 0.0
                continue

            gap = len(window) - positions[-1] - 1
            frequency = len(positions)

            gap_score = min(gap, 50) / 50
            freq_score = frequency / lookback
            recency_score = 1 - (gap / 50)

            intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]

            trend_score = 0.5
            variance_score = 0.5
            if len(intervals) >= 2:
                trend = intervals[0] - intervals[1]
                trend_score = max(0, min(trend, 10)) / 10
                avg_i = sum(intervals) / len(intervals)
                variance = sum((x - avg_i) ** 2 for x in intervals) / len(intervals)
                variance_score = 1 / (1 + variance / 10)

            score = (
                w_gap * gap_score +
                w_freq * freq_score +
                w_trend * trend_score +
                w_var * variance_score +
                w_recency * recency_score
            )

            # 周日调整：提高gap权重
            if is_sunday and sunday_adjust > 0:
                score = (
                    gap_score * (1 + sunday_adjust) * 0.5 +
                    trend_score * 0.3 +
                    variance_score * 0.2
                )

            scores[z] = score

        predicted = max(scores, key=scores.get)
        actual_zodiacs = current.get("开奖生肖", [])
        hit = predicted in actual_zodiacs

        if hit:
            hits += 1
        total += 1

    return hits / total if total > 0 else 0, total


def search_advanced():
    """高级搜索：包含周日调整"""
    print("获取历史数据...")
    records = get_all_records([2024, 2025, 2026])
    history = build_standard_records(records)
    print(f"历史数据: {len(history)} 期")

    best_hit_rate = 0
    best_params = {}
    results = []

    print("高级搜索 5000 组...")

    for _ in range(5000):
        lb = random.randint(20, 60)
        params = {
            "gap": random.uniform(0.05, 0.3),
            "freq": random.uniform(0.1, 0.4),
            "trend": random.uniform(0.1, 0.5),
            "variance": random.uniform(0.1, 0.5),
            "recency": random.uniform(0, 0.2),
            "sunday_adjust": random.uniform(0, 0.5)
        }

        hit_rate, total_tests = evaluate_advanced(history, lb, params)

        if total_tests > 100:
            results.append({
                "lookback": lb,
                "params": params,
                "hit_rate": hit_rate,
                "total": total_tests
            })

            if hit_rate > best_hit_rate:
                best_hit_rate = hit_rate
                best_params = {"lookback": lb, "params": params}
                print(f"  New best: lb={lb}, hit_rate={hit_rate:.4f}")

    results.sort(key=lambda x: x["hit_rate"], reverse=True)
    print("\n=== Top 15 高级参数 ===")
    for i, r in enumerate(results[:15]):
        p = r['params']
        print(f"  {i+1}. lb={r['lookback']}, gap={p['gap']:.3f}, freq={p['freq']:.3f}, "
              f"trend={p['trend']:.3f}, variance={p['variance']:.3f}, "
              f"recency={p['recency']:.3f}, sunday={p['sunday_adjust']:.3f} "
              f"-> {r['hit_rate']:.4f} ({r['total']}期)")

    print(f"\n=== 最佳高级参数 ===")
    print(f"  lookback: {best_params['lookback']}")
    print(f"  params: {best_params['params']}")
    print(f"  命中率: {best_hit_rate:.4f}")

    return best_params


if __name__ == "__main__":
    print("=" * 60)
    print("V5 搜索 (7个特征)")
    print("=" * 60)
    best_v5 = search_v5()

    print("\n" + "=" * 60)
    print("高级搜索 (含周日调整)")
    print("=" * 60)
    best_adv = search_advanced()

    print("\n" + "=" * 60)
    print("最终对比")
    print("=" * 60)
    print(f"V5 最佳: {best_v5['lookback']}, hit_rate={best_v5.get('hit_rate', 'N/A')}")
    print(f"高级最佳: {best_adv['lookback']}, hit_rate={best_adv.get('hit_rate', 'N/A')}")
