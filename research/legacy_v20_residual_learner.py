#!/usr/bin/env python3
"""
澳门六合 - v20 残差学习预测器

架构：
v12先预测 → 马尔可夫修正 → 错误偏差修正 → 漂移检测 → 最终Top6

核心思想：
不是新增数据，而是学习模型自己的偏差
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.predictor import predict_top6
from predictor.animal_mapper import get_zodiac_wuxing, get_zodiac_shengke
from collections import Counter
import numpy as np

ALL_ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

# v12参数（已验证最稳定）
V12_PARAMS = {
    "lookback": 11,
    "pattern_weight": 1.45,
    "gap_weight": 0.098,
    "trend_weight": 0.267,
    "variance_weight": 0.177,
    "alt_mode": "trend"
}


def compute_transition_matrix(records, upto):
    """计算马尔可夫转移矩阵"""
    transitions = {z: Counter() for z in ALL_ZODIACS}
    for i in range(1, upto):
        prev = records[i-1]["特码生肖"]
        curr = records[i]["特码生肖"]
        transitions[prev][curr] += 1

    trans_matrix = {}
    for z in ALL_ZODIACS:
        total = sum(transitions[z].values())
        trans_matrix[z] = {k: v/total for k, v in transitions[z].items()} if total > 0 else {}
    return trans_matrix


def compute_error_bias(records, upto, v12_params, window=30):
    """
    计算历史预测错误偏差
    核心：学习v12什么时候容易犯错
    """
    lookback = v12_params.get("lookback", 11)
    bias = {z: 0.0 for z in ALL_ZODIACS}

    # 只用最近window期计算偏差
    start = max(lookback, upto - window)
    under_est = Counter()  # 持续低估
    over_est = Counter()   # 持续高估

    for i in range(start, upto):
        history = records[:i]
        actual = records[i]["特码生肖"]

        top6 = predict_top6(history, v12_params, "pattern_based")

        # 检查每个生肖的预测偏差
        for z in ALL_ZODIACS:
            in_top6 = z in top6
            is_actual = z == actual

            if is_actual and not in_top6:
                # 实际出现但没预测到 = 低估
                under_est[z] += 1
            elif not is_actual and in_top6:
                # 没出现但预测了 = 高估
                over_est[z] += 1

    # 计算偏差分数
    total_under = sum(under_est.values())
    total_over = sum(over_est.values())

    if total_under + total_over > 0:
        for z in ALL_ZODIACS:
            # 正数 = 倾向低估（应该多加）
            # 负数 = 倾向高估（应该少加）
            bias[z] = (under_est[z] - over_est.get(z, 0)) / (total_under + total_over)

    return bias


def compute_drift_detector(records, upto, window=50):
    """
    漂移检测：最近50期分布是否有明显变化
    """
    if upto < window * 2:
        return {z: 0.0 for z in ALL_ZODIACS}

    half = window // 2

    # 前半段分布
    counts1 = Counter()
    for i in range(upto - window, upto - half):
        counts1[records[i]["特码生肖"]] += 1

    # 后半段分布
    counts2 = Counter()
    for i in range(upto - half, upto):
        counts2[records[i]["特码生肖"]] += 1

    # 计算漂移
    drift = {}
    for z in ALL_ZODIACS:
        freq1 = counts1.get(z, 0) / half
        freq2 = counts2.get(z, 0) / half
        drift[z] = freq2 - freq1  # 正数 = 最近在变多

    return drift


def get_base_scores(records, upto, params):
    """获取v12基础分数"""
    cache = {}
    for z in ALL_ZODIACS:
        positions = [i for i in range(upto) if records[i]["特码生肖"] == z]
        gaps = [positions[i+1] - positions[i] - 1 for i in range(len(positions)-1)] if len(positions) > 1 else []
        cache[z] = {
            "gap": upto - positions[-1] - 1 if positions else 999,
            "recent10": sum(1 for i in range(max(0, upto-10), upto) if records[i]["特码生肖"] == z),
            "positions": positions,
        }

    def norm(scores):
        vals = list(scores.values())
        max_v, min_v = max(vals), min(vals)
        range_v = max_v - min_v if max_v != min_v else 1
        return {k: (v - min_v) / range_v for k, v in scores.items()}

    gap_scores = {z: min(c["gap"], 50) / 50 for z, c in cache.items()}
    recent_scores = {z: c["recent10"] / 10 for z, c in cache.items()}

    base_scores = {}
    for z in cache.keys():
        base_scores[z] = gap_scores.get(z, 0) * 0.5 + recent_scores.get(z, 0) * 0.5

    return base_scores


def predict_v20(records, upto, v12_params, error_window=30, drift_window=50):
    """
    v20 预测流程

    1. v12基础分数
    2. 马尔可夫转移修正
    3. 错误偏差修正
    4. 漂移检测
    5. 综合评分
    """
    # 1. 基础分数
    base_scores = get_base_scores(records, upto, v12_params)

    # 2. 马尔可夫转移修正
    trans_matrix = compute_transition_matrix(records, upto)
    prev_zodiac = records[upto - 1]["特码生肖"] if upto > 0 else None
    trans_scores = {}
    if prev_zodiac and prev_zodiac in trans_matrix:
        for z in ALL_ZODIACS:
            trans_scores[z] = trans_matrix[prev_zodiac].get(z, 1/12)
    else:
        trans_scores = {z: 1/12 for z in ALL_ZODIACS}

    # 归一化trans_scores
    trans_vals = list(trans_scores.values())
    trans_max, trans_min = max(trans_vals), min(trans_vals)
    trans_range = trans_max - trans_min if trans_max != trans_min else 1
    trans_scores = {z: (v - trans_min) / trans_range for z, v in trans_scores.items()}

    # 3. 错误偏差
    error_bias = compute_error_bias(records, upto, v12_params, error_window)

    # 4. 漂移检测
    drift = compute_drift_detector(records, upto, drift_window)

    # 5. 综合评分
    scores = {}
    for z in ALL_ZODIACS:
        base = base_scores.get(z, 0)
        trans = trans_scores.get(z, 0)
        bias = error_bias.get(z, 0) * 0.5  # 缩放偏差
        drift_val = drift.get(z, 0) * 0.3  # 缩放漂移

        # 权重：基础0.5, 转移0.2, 偏差0.2, 漂移0.1
        scores[z] = base * 0.5 + trans * 0.2 + bias * 0.2 + drift_val * 0.1

    # 排序取top6
    ranked = sorted(ALL_ZODIACS, key=lambda z: scores[z], reverse=True)
    return ranked[:6], scores


def evaluate_v20(records, v12_params, start=700, error_window=30, drift_window=50):
    """评估v20"""
    n = len(records)
    lookback = v12_params.get("lookback", 11)

    hits = 0
    streak = 0
    max_streak = 0
    results = []

    for i in range(start, n):
        history = records[:i]
        actual = records[i]["特码生肖"]

        top6, scores = predict_v20(history, i, v12_params, error_window, drift_window)

        hit = actual in top6
        if hit:
            hits += 1
            streak = 0
        else:
            streak += 1
            max_streak = max(max_streak, streak)

        results.append({
            "idx": i,
            "actual": actual,
            "top6": top6,
            "hit": hit,
            "scores": scores
        })

    return {
        "hit_rate": hits / len(results),
        "max_streak": max_streak,
        "num_tests": len(results),
        "results": results
    }


def main():
    print("=" * 60)
    print("澳门六合 - v20 残差学习预测器")
    print("不是新增数据，而是学习模型自己的偏差")
    print("=" * 60)

    print("\n加载数据...")
    records = get_all_records([2024, 2025, 2026])
    standard = build_standard_records(records)
    print(f"数据加载完成: {len(standard)} 期")

    # 参数测试
    print("\n验证v20...")
    stats = evaluate_v20(standard, V12_PARAMS, start=700)

    print(f"\n=== v20 验证结果 ===")
    print(f"测试数量: {stats['num_tests']}")
    print(f"命中率: {stats['hit_rate']*100:.2f}%")
    print(f"最高连错: {stats['max_streak']}")

    # 对比v12
    print("\n=== 对比 ===")
    v12_hits = 0
    v12_streak = 0
    v12_max_streak = 0
    for i in range(700, len(standard)):
        actual = standard[i]["特码生肖"]
        v12_top6 = predict_top6(standard[:i], V12_PARAMS, "pattern_based")
        if actual in v12_top6:
            v12_hits += 1
            v12_streak = 0
        else:
            v12_streak += 1
            v12_max_streak = max(v12_max_streak, v12_streak)

    v12_hit_rate = v12_hits / (len(standard) - 700)
    print(f"v12 原始: {v12_hit_rate*100:.2f}%, 最高连错 {v12_max_streak}")
    print(f"v20: {stats['hit_rate']*100:.2f}%, 最高连错 {stats['max_streak']}")
    print(f"提升: {(stats['hit_rate'] - v12_hit_rate)*100:+.2f}%")

    # 保存结果
    import json
    from datetime import datetime

    result = {
        "version": "v20",
        "type": "residual_learning",
        "architecture": "v12_base + Markov + error_bias + drift_detection",
        "params": {
            "v12": V12_PARAMS,
            "error_window": 30,
            "drift_window": 50
        },
        "validation": {
            "hit_rate": stats["hit_rate"],
            "max_streak": stats["max_streak"],
            "num_tests": stats["num_tests"]
        },
        "updated_at": datetime.now().isoformat()
    }

    result_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "version_book", "v20.json")
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {result_path}")


if __name__ == "__main__":
    main()