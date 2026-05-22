#!/usr/bin/env python3
"""
澳门六合六肖预测器
- 基于特征评分的排名预测
- 特征：gap（遗漏）、近期频率、连出现
"""

import json
from typing import List, Dict, Tuple
from collections import Counter

from .data_fetcher import (
    get_all_records,
    build_standard_records,
    extract_zodiac_mapping,
    get_special_zodiac
)
from .config import load_strategy, save_verification_state, load_verification_state


def build_cache(records: List[Dict], upto: int) -> Dict:
    """构建特征缓存"""
    zodiacs = sorted(set(r["特码生肖"] for r in records))
    cache = {}

    for z in zodiacs:
        positions = [i for i in range(upto) if records[i]["特码生肖"] == z]
        gaps = [positions[i+1] - positions[i] - 1 for i in range(len(positions) - 1)]
        last_gap = upto - positions[-1] - 1 if positions else 999

        cache[z] = {
            "gap": last_gap,
            "avg_gap": sum(gaps) / len(gaps) if gaps else 12,
            "recent3": sum(1 for i in range(max(0, upto-3), upto) if records[i]["特码生肖"] == z),
            "recent5": sum(1 for i in range(max(0, upto-5), upto) if records[i]["特码生肖"] == z),
            "recent10": sum(1 for i in range(max(0, upto-10), upto) if records[i]["特码生肖"] == z),
            "recent20": sum(1 for i in range(max(0, upto-20), upto) if records[i]["特码生肖"] == z),
            "recent30": sum(1 for i in range(max(0, upto-30), upto) if records[i]["特码生肖"] == z),
            "streak": 0,
        }

        # 计算连出现：从后往前数当前生肖连续出现次数
        for i in range(upto - 1, -1, -1):
            if records[i]["特码生肖"] == z:
                cache[z]["streak"] += 1
            else:
                break  # 遇到不匹配的生肖，停止继续计数

    return cache


def predict_top6(records: List[Dict], weights: Dict[str, float]) -> List[str]:
    """预测六肖"""
    n = len(records)
    cache = build_cache(records, n)
    zodiacs = list(cache.keys())

    # 特征评分
    scores = {}
    for z in zodiacs:
        c = cache[z]
        score = (
            (1 if c["gap"] >= 16 else 0) * weights.get("gap_ge16", 0) +
            (1 if c["gap"] >= 10 else 0) * weights.get("gap_ge10", 0) +
            (1 if c["gap"] >= 6 else 0) * weights.get("gap_ge6", 0) +
            c["recent3"] / 3 * weights.get("r3", 0) +
            c["streak"] * weights.get("streak", 0)
        )
        scores[z] = score

    # 按分数排序
    ranked = sorted(zodiacs, key=lambda z: scores[z], reverse=True)
    return ranked[:6]


def predict_next(records: List[Dict]) -> Tuple[str, List[str], Dict]:
    """预测下期"""
    weights = load_strategy()["weights"]
    top6 = predict_top6(records, weights)

    latest = records[-1]
    latest_period = latest["期号"]
    # 期号格式：2025001，需要 +1
    next_period = str(int(latest_period) + 1)

    # 计算各生肖得分
    n = len(records)
    cache = build_cache(records, n)
    scores = {z: cache[z]["gap"] for z in cache}

    return next_period, top6, scores


def verify_prediction(records: List[Dict], pending_period: str, pending_top6: List[str]) -> Tuple[bool, str]:
    """验证预测"""
    latest = records[-1]
    latest_period = latest["期号"]

    if latest_period != pending_period:
        return False, latest_period

    actual = latest["特码生肖"]
    hit = actual in pending_top6
    return hit, actual


def run_prediction_pipeline() -> Dict:
    """运行预测流程"""
    # 1. 获取数据
    records = get_all_records([2024, 2025])
    standard_records = build_standard_records(
        records,
        extract_zodiac_mapping(records)
    )

    # 2. 加载状态
    state = load_verification_state()
    last_verified = state.get("last_verified_period")
    pending_period = state.get("pending_period")
    pending_top6 = state.get("pending_top6", [])

    # 3. 验证上期预测
    verified_period = None
    verified_hit = None
    verified_actual = None

    latest = standard_records[-1]
    latest_period = latest["期号"]

    if pending_period and pending_top6:
        if latest_period == pending_period:
            # 可以验证
            hit, actual = verify_prediction(standard_records, pending_period, pending_top6)
            verified_period = pending_period
            verified_hit = hit
            verified_actual = actual
        elif int(latest_period) > int(pending_period):
            # 跳期，跳过验证
            pass

    # 4. 生成新预测
    next_period, next_top6, scores = predict_next(standard_records)

    # 5. 更新状态
    state["last_verified_period"] = verified_period or state.get("last_verified_period")
    state["pending_period"] = next_period
    state["pending_top6"] = next_top6
    save_verification_state(state)

    # 6. 返回结果
    return {
        "verified_period": verified_period,
        "verified_hit": verified_hit,
        "verified_actual": verified_actual,
        "pending_period": next_period,
        "pending_top6": next_top6,
        "scores": scores,
        "total_records": len(standard_records),
    }


if __name__ == "__main__":
    result = run_prediction_pipeline()
    print(json.dumps(result, ensure_ascii=False, indent=2))