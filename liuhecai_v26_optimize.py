#!/usr/bin/env python3
"""
澳门六合 - V26 平特一肖参数优化 V2

增强版：加入更多特征
- gap（遗漏值）
- frequency（出现频率）
- streak（连出现次数）
- trend（趋势：间隔递增还是递减）
- variance（间隔稳定性）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from predictor.data_fetcher import get_all_records, build_standard_records
from itertools import product
import random

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


def evaluate_enhanced(history, lookback, gap_w, freq_w, streak_w, trend_w, variance_w):
    """评估增强参数组合的命中率"""
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

            if not positions:
                gap = 999
                frequency = 0
                streak = 0
                trend = 0
                variance = 0
            else:
                # gap
                gap = len(window) - positions[-1] - 1

                # frequency
                frequency = len(positions)

                # streak（从后往前数连续出现次数）
                streak = 0
                for idx in range(len(window)-1, -1, -1):
                    if window[idx]["特码生肖"] == z:
                        streak += 1
                    else:
                        break

                # trend（间隔趋势）
                if len(positions) >= 2:
                    intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]
                    trend = intervals[0] - intervals[1] if len(intervals) >= 2 else 0
                else:
                    trend = 0

                # variance（间隔稳定性）
                if len(positions) >= 3:
                    intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]
                    avg_int = sum(intervals) / len(intervals)
                    variance = sum((x - avg_int) ** 2 for x in intervals) / len(intervals)
                else:
                    variance = 0

            gap_score = min(gap, 50) / 50
            freq_score = frequency / lookback
            streak_score = min(streak, 5) / 5
            trend_score = max(0, min(trend, 10)) / 10  # 0-10 normalize
            variance_score = 1 / (1 + variance / 10)  # lower is better

            scores[z] = (
                gap_score * gap_w +
                freq_score * freq_w +
                streak_score * streak_w +
                trend_score * trend_w +
                variance_score * variance_w
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


def search_enhanced():
    """增强参数搜索"""
    print("获取历史数据...")
    records = get_all_records([2024, 2025, 2026])
    history = build_standard_records(records)
    print(f"历史数据: {len(history)} 期")

    # 参数范围
    lookbacks = [20, 30, 40, 50, 60]
    weight_options = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]

    best_hit_rate = 0
    best_params = {}
    results = []

    print("开始增强搜索...")

    # 网格搜索
    for lb in lookbacks:
        for gw in weight_options:
            for fw in weight_options:
                for sw in weight_options:
                    for tw in weight_options:
                        for vw in weight_options:
                            total_w = gw + fw + sw + tw + vw
                            if total_w == 0 or total_w > 1.0:
                                continue

                            # 归一化权重
                            gw_n = gw / total_w
                            fw_n = fw / total_w
                            sw_n = sw / total_w
                            tw_n = tw / total_w
                            vw_n = vw / total_w

                            hit_rate, total_tests = evaluate_enhanced(
                                history, lb, gw_n, fw_n, sw_n, tw_n, vw_n
                            )

                            if total_tests > 100:
                                results.append({
                                    "lookback": lb,
                                    "gap_weight": gw_n,
                                    "freq_weight": fw_n,
                                    "streak_weight": sw_n,
                                    "trend_weight": tw_n,
                                    "variance_weight": vw_n,
                                    "hit_rate": hit_rate,
                                    "total": total_tests
                                })

                                if hit_rate > best_hit_rate:
                                    best_hit_rate = hit_rate
                                    best_params = {
                                        "lookback": lb,
                                        "gap_weight": gw_n,
                                        "freq_weight": fw_n,
                                        "streak_weight": sw_n,
                                        "trend_weight": tw_n,
                                        "variance_weight": vw_n
                                    }
                                    print(f"  New best: {best_params}, hit_rate={hit_rate:.4f}")

    # 排序输出top15
    results.sort(key=lambda x: x["hit_rate"], reverse=True)
    print("\n=== Top 15 参数组合 ===")
    for i, r in enumerate(results[:15]):
        print(f"  {i+1}. lb={r['lookback']}, gap={r['gap_weight']:.2f}, freq={r['freq_weight']:.2f}, "
              f"streak={r['streak_weight']:.2f}, trend={r['trend_weight']:.2f}, variance={r['variance_weight']:.2f} "
              f"-> {r['hit_rate']:.4f} ({r['total']}期)")

    print(f"\n=== 最佳参数 ===")
    for k, v in best_params.items():
        print(f"  {k}: {v:.4f}")
    print(f"  命中率: {best_hit_rate:.4f}")

    return best_params


def random_search():
    """随机搜索（更快，覆盖更大范围）"""
    print("获取历史数据...")
    records = get_all_records([2024, 2025, 2026])
    history = build_standard_records(records)
    print(f"历史数据: {len(history)} 期")

    best_hit_rate = 0
    best_params = {}
    results = []

    print("随机搜索 2000 组参数...")

    for _ in range(2000):
        lb = random.randint(15, 80)
        weights = [random.uniform(0, 1) for _ in range(5)]
        total_w = sum(weights)
        if total_w == 0:
            continue
        weights = [w / total_w for w in weights]

        hit_rate, total_tests = evaluate_enhanced(
            history, lb, weights[0], weights[1], weights[2], weights[3], weights[4]
        )

        if total_tests > 100:
            results.append({
                "lookback": lb,
                "gap_weight": weights[0],
                "freq_weight": weights[1],
                "streak_weight": weights[2],
                "trend_weight": weights[3],
                "variance_weight": weights[4],
                "hit_rate": hit_rate,
                "total": total_tests
            })

            if hit_rate > best_hit_rate:
                best_hit_rate = hit_rate
                best_params = {
                    "lookback": lb,
                    "gap_weight": weights[0],
                    "freq_weight": weights[1],
                    "streak_weight": weights[2],
                    "trend_weight": weights[3],
                    "variance_weight": weights[4]
                }
                print(f"  New best: {best_params}, hit_rate={hit_rate:.4f}")

    # 排序输出top15
    results.sort(key=lambda x: x["hit_rate"], reverse=True)
    print("\n=== Top 15 参数组合 ===")
    for i, r in enumerate(results[:15]):
        print(f"  {i+1}. lb={r['lookback']}, gap={r['gap_weight']:.3f}, freq={r['freq_weight']:.3f}, "
              f"streak={r['streak_weight']:.3f}, trend={r['trend_weight']:.3f}, variance={r['variance_weight']:.3f} "
              f"-> {r['hit_rate']:.4f} ({r['total']}期)")

    print(f"\n=== 最佳参数 ===")
    for k, v in best_params.items():
        print(f"  {k}: {v:.4f}")
    print(f"  命中率: {best_hit_rate:.4f}")

    return best_params


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 1: 随机搜索")
    print("=" * 60)
    best1 = random_search()

    print("\n" + "=" * 60)
    print("Phase 2: 在最佳参数附近精细搜索")
    print("=" * 60)
    # 在最佳参数附近细化搜索
    lb = best1["lookback"]
    gw = best1["gap_weight"]

    best2 = search_enhanced()
    print(f"\n最终最佳参数: {best2}")

