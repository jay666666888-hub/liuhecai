#!/usr/bin/env python3
"""
澳门六合 - V26 平特一肖参数优化 V3

使用 v12 的 pattern_based (zigzag间隔交替模式) 策略
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from predictor.data_fetcher import get_all_records, build_standard_records
from itertools import product
import random

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


def evaluate_pattern(history, lookback, pattern_w, gap_w, trend_w, variance_w, alt_mode="strict"):
    """使用v12的pattern_based策略评估参数"""
    n = len(history)
    if n < lookback + 10:
        return 0, 0

    hits = 0
    total = 0

    for i in range(lookback, n):
        window = history[max(0, i-lookback):i]
        current = history[i]

        # 计算各生肖得分
        scores = {}
        for z in ZODIACS:
            positions = [idx for idx, r in enumerate(window) if r["特码生肖"] == z]

            if len(positions) < 3:
                scores[z] = 0.5
            else:
                # 只用最近的 lookback 期数据
                positions = positions[-lookback:] if len(positions) > lookback else positions
                intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]

                # 交替模式评分
                if alt_mode == "strict":
                    alt_score = sum(1 for i in range(len(intervals)-1) if intervals[i] > intervals[i+1])
                    pattern_ratio = alt_score / max(len(intervals)-1, 1)
                else:  # trend mode
                    if len(intervals) >= 3:
                        trend_count = sum(1 for i in range(len(intervals)-1) if intervals[i] > intervals[i+1])
                        pattern_ratio = trend_count / (len(intervals) - 1)
                    else:
                        pattern_ratio = 0.5

                # 当前遗漏
                current_gap = len(window) - positions[0] - 1

                # 趋势
                trend = intervals[0] - intervals[1] if len(intervals) >= 2 else 0

                # 间隔稳定性（方差）
                avg_int = sum(intervals) / len(intervals) if intervals else 12
                variance = sum((x - avg_int) ** 2 for x in intervals) / len(intervals) if intervals else 0

                scores[z] = (
                    pattern_ratio * pattern_w +
                    min(current_gap, 50) * gap_w +
                    trend * trend_w +
                    (1 / (1 + variance)) * variance_w
                )

        # 预测：分数最高的生肖
        predicted = max(scores, key=scores.get)

        # 实际开奖生肖（完整7个）
        actual_zodiacs = current.get("开奖生肖", [])
        hit = predicted in actual_zodiacs

        if hit:
            hits += 1
        total += 1

    return hits / total if total > 0 else 0, total


def search_pattern():
    """使用pattern_based策略搜索"""
    print("获取历史数据...")
    records = get_all_records([2024, 2025, 2026])
    history = build_standard_records(records)
    print(f"历史数据: {len(history)} 期")

    best_hit_rate = 0
    best_params = {}
    results = []

    print("随机搜索 3000 组参数...")

    for _ in range(3000):
        lb = random.randint(8, 50)
        pattern_w = random.uniform(0.5, 5.0)
        gap_w = random.uniform(0.01, 0.15)
        trend_w = random.uniform(0.0, 0.5)
        variance_w = random.uniform(0.1, 0.5)
        alt_mode = random.choice(["strict", "trend"])

        total_w = pattern_w + gap_w + trend_w + variance_w
        if total_w == 0:
            continue

        hit_rate, total_tests = evaluate_pattern(
            history, lb,
            pattern_w / total_w,
            gap_w / total_w,
            trend_w / total_w,
            variance_w / total_w,
            alt_mode
        )

        if total_tests > 100:
            results.append({
                "lookback": lb,
                "pattern_weight": pattern_w / total_w,
                "gap_weight": gap_w / total_w,
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
                    "trend_weight": trend_w / total_w,
                    "variance_weight": variance_w / total_w,
                    "alt_mode": alt_mode
                }
                print(f"  New best: lookback={lb}, pattern={pattern_w/total_w:.3f}, "
                      f"gap={gap_w/total_w:.3f}, trend={trend_w/total_w:.3f}, "
                      f"variance={variance_w/total_w:.3f}, mode={alt_mode}, "
                      f"hit_rate={hit_rate:.4f}")

    # 排序输出top20
    results.sort(key=lambda x: x["hit_rate"], reverse=True)
    print("\n=== Top 20 参数组合 ===")
    for i, r in enumerate(results[:20]):
        print(f"  {i+1}. lb={r['lookback']}, pattern={r['pattern_weight']:.3f}, "
              f"gap={r['gap_weight']:.3f}, trend={r['trend_weight']:.3f}, "
              f"variance={r['variance_weight']:.3f}, mode={r['alt_mode']} "
              f"-> {r['hit_rate']:.4f} ({r['total']}期)")

    print(f"\n=== 最佳参数 ===")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    print(f"  命中率: {best_hit_rate:.4f}")

    return best_params


if __name__ == "__main__":
    best = search_pattern()
    print(f"\n最终最佳参数: {best}")
