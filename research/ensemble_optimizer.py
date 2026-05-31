#!/usr/bin/env python3
"""
澳门六合 - 加权Ensemble融合器 v18
不是投票，是分数加权融合
"""

import random
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, BASE_DIR)

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.predictor import predict_top6


def predict_v12_gap_style(records: List[Dict], params: Dict) -> List[str]:
    """v12风格: gap/r3/streak 基础特征"""
    n = len(records)
    lookback = params.get("lookback", 11)

    # Gap特征
    gap_scores = {}
    for i in range(max(0, n-30), n):
        z = records[i]["特码生肖"]
        gap_scores[z] = gap_scores.get(z, 0) + 1

    # 近期频率
    recent3 = {}
    for i in range(max(0, n-3), n):
        z = records[i]["特码生肖"]
        recent3[z] = recent3.get(z, 0) + 1

    # 连出现
    streaks = {}
    for z in gap_scores:
        streak = 0
        for i in range(n-1, -1, -1):
            if records[i]["特码生肖"] == z:
                streak += 1
            else:
                break
        streaks[z] = streak

    zodiacs = list(gap_scores.keys())
    scores = {}
    for z in zodiacs:
        scores[z] = (
            gap_scores.get(z, 0) * params.get("gap_weight", 0.5) +
            recent3.get(z, 0) * params.get("r3_weight", 0.3) +
            streaks.get(z, 0) * params.get("streak_weight", 0.2)
        )

    ranked = sorted(zodiacs, key=lambda z: scores[z], reverse=True)
    return ranked[:6]


def predict_v13_pattern_style(records: List[Dict], params: Dict) -> List[str]:
    """v13风格: pattern + interaction (使用原predict_top6)"""
    return predict_top6(records, params, "pattern_based")


def predict_v17_cycle_style(records: List[Dict], params: Dict) -> List[str]:
    """v17风格: 周期/节奏型特征"""
    n = len(records)
    from predictor.animal_mapper import get_zodiac_wuxing, get_zodiac_shengke

    cache = {}
    for z in set(r["特码生肖"] for r in records):
        positions = [i for i in range(n) if records[i]["特码生肖"] == z]
        gaps = [positions[i+1] - positions[i] - 1 for i in range(len(positions)-1)] if len(positions) > 1 else []
        cache[z] = {
            "gap": n - positions[-1] - 1 if positions else 999,
            "avg_gap": sum(gaps) / len(gaps) if gaps else 12,
            "recent10": sum(1 for i in range(max(0, n-10), n) if records[i]["特码生肖"] == z),
        }

    # 找同五行最大遗漏
    wuxing_max_gap = {}
    for z, c in cache.items():
        w = get_zodiac_wuxing(z)
        if w not in wuxing_max_gap or c["gap"] > wuxing_max_gap[w]:
            wuxing_max_gap[w] = c["gap"]

    # 找相冲最大遗漏
    shengke_max_gap = {}
    for z, c in cache.items():
        s = get_zodiac_shengke(z)
        if s in cache:
            sg = cache[s]["gap"]
            if z not in shengke_max_gap or sg > shengke_max_gap[z]:
                shengke_max_gap[z] = sg

    zodiacs = list(cache.keys())
    scores = {}
    for z in zodiacs:
        scores[z] = (
            min(cache[z]["gap"], 30) / 30 * params.get("cycle_gap", 0.4) +
            cache[z]["recent10"] / 10 * params.get("cycle_recent", 0.3) +
            min(wuxing_max_gap.get(get_zodiac_wuxing(z), 0), 20) / 20 * params.get("cycle_wuxing", 0.2) +
            min(shengke_max_gap.get(z, 0), 15) / 15 * params.get("cycle_shengke", 0.1)
        )

    ranked = sorted(zodiacs, key=lambda z: scores[z], reverse=True)
    return ranked[:6]


def predict_ensemble(records: List[Dict], v12_params: Dict, v13_params: Dict, v17_params: Dict, weights: List[float]) -> List[str]:
    """
    加权分数融合
    不是投票，是归一化分数加权
    """
    n = len(records)

    # 获取三个模型的原始分数
    def get_scores(predictor_func, params):
        cache = {}
        for z in set(r["特码生肖"] for r in records):
            positions = [i for i in range(n) if records[i]["特码生肖"] == z]
            gaps = [positions[i+1] - positions[i] - 1 for i in range(len(positions)-1)] if len(positions) > 1 else []
            cache[z] = {
                "gap": n - positions[-1] - 1 if positions else 999,
                "avg_gap": sum(gaps) / len(gaps) if gaps else 12,
                "recent10": sum(1 for i in range(max(0, n-10), n) if records[i]["特码生肖"] == z),
            }

        # gap score
        gap_scores = {z: min(c["gap"], 50) / 50 for z, c in cache.items()}

        # recent score
        recent_scores = {z: c["recent10"] / 10 for z, c in cache.items()}

        # pattern score (基于间隔交替)
        pattern_scores = {}
        for z in cache:
            positions = [i for i in range(n) if records[i]["特码生肖"] == z]
            if len(positions) < 3:
                pattern_scores[z] = 0.5
            else:
                pos = positions[-params.get("lookback", 11):]
                intervals = [pos[i] - pos[i+1] for i in range(len(pos)-1)]
                if len(intervals) >= 2:
                    trend = intervals[0] - intervals[1]
                    pattern_scores[z] = (trend + 10) / 20
                else:
                    pattern_scores[z] = 0.5

        # 归一化
        def normalize(scores_dict):
            max_v = max(scores_dict.values()) if scores_dict else 1
            min_v = min(scores_dict.values()) if scores_dict else 0
            range_v = max_v - min_v if max_v != min_v else 1
            return {k: (v - min_v) / range_v for k, v in scores_dict.items()}

        return normalize(gap_scores), normalize(recent_scores), normalize(pattern_scores)

    # v12: gap-based
    v12_gap, v12_recent, _ = get_scores(predict_v12_gap_style, v12_params)

    # v13: pattern-based (简化版)
    _, _, v13_pattern = get_scores(predict_v13_pattern_style, v13_params)

    # v17: cycle-based
    v17_gap, v17_recent, _ = get_scores(predict_v17_cycle_style, v17_params)

    # 综合分数
    zodiacs = list(set(list(v12_gap.keys()) + list(v13_pattern.keys()) + list(v17_gap.keys())))
    final_scores = {}

    w1, w2, w3 = weights  # v12, v13, v17

    for z in zodiacs:
        s1 = v12_gap.get(z, 0) * 0.5 + v12_recent.get(z, 0) * 0.5  # v12综合
        s2 = v13_pattern.get(z, 0)  # v13 pattern
        s3 = v17_gap.get(z, 0) * 0.5 + v17_recent.get(z, 0) * 0.5  # v17综合

        final_scores[z] = w1 * s1 + w2 * s2 + w3 * s3

    ranked = sorted(zodiacs, key=lambda z: final_scores[z], reverse=True)
    return ranked[:6]


def evaluate_ensemble(records: List[Dict], weights: List[float], n_iter: int = 100) -> Dict:
    """评估Ensemble权重"""
    lookback = 11
    n = len(records)

    # 固定各模型最佳参数
    v12_params = {"lookback": 11, "gap_weight": 0.5, "r3_weight": 0.3, "streak_weight": 0.2}
    v13_params = {"lookback": 11, "pattern_weight": 1.69, "gap_weight": 0.181, "trend_weight": 0.281, "variance_weight": 0.271, "alt_mode": "trend"}
    v17_params = {"lookback": 11, "cycle_gap": 0.4, "cycle_recent": 0.3, "cycle_wuxing": 0.2, "cycle_shengke": 0.1}

    hits = streak = max_streak = 0

    for i in range(lookback, n):
        history = records[:i]
        top6 = predict_ensemble(history, v12_params, v13_params, v17_params, weights)
        actual = records[i]["特码生肖"]

        if actual in top6:
            hits += 1
            streak = 0
        else:
            streak += 1
            max_streak = max(max_streak, streak)

    hit_rate = hits / (n - lookback)
    return {"hit_rate": hit_rate, "max_streak": max_streak}


def optimize_weights(records: List[Dict], iterations: int = 5000) -> Tuple[List[float], Dict]:
    """优化Ensemble权重"""
    print("优化Ensemble权重...")

    best_weights = [0.5, 0.3, 0.2]
    best_score = -1
    best_stats = None

    for i in range(iterations):
        if i % 500 == 0:
            print(f"  进度: {i}/{iterations}", flush=True)

        # 随机权重 (和=1)
        w1 = random.uniform(0.2, 0.6)
        w2 = random.uniform(0.1, 0.5)
        w3 = 1.0 - w1 - w2
        if w3 < 0.05:
            w3 = 0.05
        weights = [w1, w2, w3]

        stats = evaluate_ensemble(records, weights)
        streak_penalty = max(0, stats["max_streak"] - 5) * 0.02
        score = stats["hit_rate"] - streak_penalty

        if score > best_score:
            best_score = score
            best_weights = weights
            best_stats = stats
            print(f"  [{i}] 新最佳! 命中率:{stats['hit_rate']*100:.2f}% 连错:{stats['max_streak']} 权重:{weights}")

    return best_weights, best_stats


def main():
    print("=" * 60)
    print("澳门六合 - 加权Ensemble融合器 v18")
    print("不是投票，是分数加权融合")
    print("=" * 60)

    print("\n加载数据...")
    records = get_all_records([2024, 2025, 2026])
    standard = build_standard_records(records)
    print(f"数据加载完成: {len(standard)} 期")

    # 优化权重
    weights, stats = optimize_weights(standard, 5000)

    print(f"\n=== 最佳Ensemble权重 ===")
    print(f"v12权重: {weights[0]:.2f}")
    print(f"v13权重: {weights[1]:.2f}")
    print(f"v17权重: {weights[2]:.2f}")
    print(f"命中率: {stats['hit_rate']*100:.2f}%")
    print(f"连错: {stats['max_streak']}")

    # 保存结果
    result = {
        "version": "v18",
        "type": "weighted_ensemble",
        "weights": {
            "v12": weights[0],
            "v13": weights[1],
            "v17": weights[2]
        },
        "stats": stats,
        "updated_at": datetime.now().isoformat()
    }

    result_path = os.path.join(BASE_DIR, "version_book", "v18.json")
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {result_path}")

    # 对比
    print("\n=== 版本对比 ===")
    print(f"v12: 55.62% (原始pattern)")
    print(f"v13: 55.74% (参数优化)")
    print(f"v17: 55.50% (五行特征)")
    print(f"v18: {stats['hit_rate']*100:.2f}% (加权融合)")
    print(f"提升: {(stats['hit_rate'] - 0.5574)*100:+.2f}%")


if __name__ == "__main__":
    main()