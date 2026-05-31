#!/usr/bin/env python3
"""
澳门六合 - V26 平特一肖参数优化 V4

混合策略：pattern_based + gap/frequency
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from predictor.data_fetcher import get_all_records, build_standard_records
import random

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


def evaluate_hybrid(history, lookback, pattern_w, gap_w, freq_w, trend_w, variance_w, alt_mode="strict"):
    """混合策略评估"""
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

            if len(positions) < 3:
                pattern_score = 0.5
            else:
                positions = positions[-lookback:] if len(positions) > lookback else positions
                intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]

                # Pattern score
                if alt_mode == "strict":
                    alt_score = sum(1 for i in range(len(intervals)-1) if intervals[i] > intervals[i+1])
                    pattern_ratio = alt_score / max(len(intervals)-1, 1)
                else:
                    if len(intervals) >= 3:
                        trend_count = sum(1 for i in range(len(intervals)-1) if intervals[i] > intervals[i+1])
                        pattern_ratio = trend_count / (len(intervals) - 1)
                    else:
                        pattern_ratio = 0.5
                pattern_score = pattern_ratio

            # Gap/Frequency/Trend/Variance
            if not positions:
                gap = 999
                frequency = 0
                streak = 0
                trend = 0
                variance = 0
            else:
                gap = len(window) - positions[-1] - 1
                frequency = len(positions)

                # streak
                streak = 0
                for idx in range(len(window)-1, -1, -1):
                    if window[idx]["特码生肖"] == z:
                        streak += 1
                    else:
                        break

                # trend
                if len(positions) >= 2:
                    intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]
                    trend = intervals[0] - intervals[1] if len(intervals) >= 2 else 0
                else:
                    trend = 0

                # variance
                if len(positions) >= 3:
                    intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]
                    avg_int = sum(intervals) / len(intervals)
                    variance = sum((x - avg_int) ** 2 for x in intervals) / len(intervals)
                else:
                    variance = 0

            gap_score = min(gap, 50) / 50
            freq_score = frequency / lookback
            streak_score = min(streak, 5) / 5
            trend_score = max(0, min(trend, 10)) / 10
            variance_score = 1 / (1 + variance / 10)

            # 归一化
            total_w = pattern_w + gap_w + freq_w + trend_w + variance_w
            if total_w > 0:
                pattern_w_n = pattern_w / total_w
                gap_w_n = gap_w / total_w
                freq_w_n = freq_w / total_w
                trend_w_n = trend_w / total_w
                variance_w_n = variance_w / total_w
            else:
                pattern_w_n = gap_w_n = freq_w_n = trend_w_n = variance_w_n = 0

            scores[z] = (
                pattern_score * pattern_w_n +
                gap_score * gap_w_n +
                freq_score * freq_w_n +
                trend_score * trend_w_n +
                variance_score * variance_w_n
            )

        predicted = max(scores, key=scores.get)
        actual_zodiacs = current.get("开奖生肖", [])
        hit = predicted in actual_zodiacs

        if hit:
            hits += 1
        total += 1

    return hits / total if total > 0 else 0, total


def search_hybrid():
    """混合策略搜索"""
    print("获取历史数据...")
    records = get_all_records([2024, 2025, 2026])
    history = build_standard_records(records)
    print(f"历史数据: {len(history)} 期")

    best_hit_rate = 0
    best_params = {}
    results = []

    print("随机搜索 5000 组混合参数...")

    for _ in range(5000):
        lb = random.randint(15, 60)
        pattern_w = random.uniform(0, 1)
        gap_w = random.uniform(0, 0.5)
        freq_w = random.uniform(0, 0.5)
        trend_w = random.uniform(0, 0.5)
        variance_w = random.uniform(0, 0.5)
        alt_mode = random.choice(["strict", "trend"])

        total_w = pattern_w + gap_w + freq_w + trend_w + variance_w
        if total_w == 0:
            continue

        hit_rate, total_tests = evaluate_hybrid(
            history, lb, pattern_w, gap_w, freq_w, trend_w, variance_w, alt_mode
        )

        if total_tests > 100:
            results.append({
                "lookback": lb,
                "pattern_weight": pattern_w / total_w,
                "gap_weight": gap_w / total_w,
                "freq_weight": freq_w / total_w,
                "trend_weight": trend_w / total_w,
                "variance_weight": variance_w / total_w,
                "alt_mode": alt_mode,
                "hit_rate": hit_rate,
                "total": total_tests
            })

            if hit_rate > best_hit_rate:
                best_hit_rate = hit_rate
                best_params = {
                    "lookback": lb,
                    "pattern_weight": pattern_w / total_w,
                    "gap_weight": gap_w / total_w,
                    "freq_weight": freq_w / total_w,
                    "trend_weight": trend_w / total_w,
                    "variance_weight": variance_w / total_w,
                    "alt_mode": alt_mode
                }
                print(f"  New best: lb={lb}, pattern={pattern_w/total_w:.3f}, "
                      f"gap={gap_w/total_w:.3f}, freq={freq_w/total_w:.3f}, "
                      f"trend={trend_w/total_w:.3f}, variance={variance_w/total_w:.3f}, "
                      f"mode={alt_mode}, hit_rate={hit_rate:.4f}")

    results.sort(key=lambda x: x["hit_rate"], reverse=True)
    print("\n=== Top 20 混合参数组合 ===")
    for i, r in enumerate(results[:20]):
        print(f"  {i+1}. lb={r['lookback']}, pattern={r['pattern_weight']:.3f}, "
              f"gap={r['gap_weight']:.3f}, freq={r['freq_weight']:.3f}, "
              f"trend={r['trend_weight']:.3f}, variance={r['variance_weight']:.3f}, "
              f"mode={r['alt_mode']} -> {r['hit_rate']:.4f} ({r['total']}期)")

    print(f"\n=== 最佳混合参数 ===")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    print(f"  命中率: {best_hit_rate:.4f}")

    return best_params


if __name__ == "__main__":
    best = search_hybrid()
    print(f"\n最终最佳参数: {best}")
