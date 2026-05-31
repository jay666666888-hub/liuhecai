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


def predict_top6(records: List[Dict], weights: Dict[str, float], feature_type: str = "binary",
                 is_sunday: bool = False) -> List[str]:
    """预测六肖

    Args:
        records: 历史记录
        weights: 权重配置
        feature_type: "binary", "continuous", 或 "pattern_based"
        is_sunday: 是否为周日（有周日负效应调整）
    """
    n = len(records)
    cache = build_cache(records, n)
    zodiacs = list(cache.keys())

    # 特征评分
    scores = {}
    for z in zodiacs:
        c = cache[z]

        if feature_type == "pattern_based":
            # zigzag间隔交替模式策略
            positions = [i for i in range(n) if records[i]["特码生肖"] == z]
            if len(positions) < 3:
                scores[z] = 0.5
            else:
                lookback = weights.get("lookback", 13)
                positions = positions[-lookback:] if len(positions) > lookback else positions
                intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]

                # 交替模式评分
                alt_mode = weights.get("alt_mode", "strict")
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
                current_gap = n - positions[0] - 1

                # 趋势
                trend = intervals[0] - intervals[1] if len(intervals) >= 2 else 0

                # 间隔稳定性（方差）
                avg_int = sum(intervals) / len(intervals) if intervals else 12
                variance = sum((x - avg_int) ** 2 for x in intervals) / len(intervals) if intervals else 0

                scores[z] = (
                    pattern_ratio * weights.get("pattern_weight", 2.0) +
                    min(current_gap, 50) * weights.get("gap_weight", 0.04) +
                    trend * weights.get("trend_weight", 0.08) +
                    (1 / (1 + variance)) * weights.get("variance_weight", 0.25)
                )

                # 周日调整：如果周日，提高gap权重（基于2024年学习的周日负效应）
                if is_sunday:
                    gap_score_normalized = min(current_gap, 50) / 50
                    # 提高gap贡献，降低pattern贡献
                    scores[z] = (
                        gap_score_normalized * 1.3 +  # 提高gap权重
                        pattern_ratio * weights.get("pattern_weight", 2.0) * 0.8  # 降低pattern权重
                    )
        elif feature_type == "continuous":
            gap_score = min(c["gap"], 50) / 50
            scores[z] = (
                gap_score * weights.get("gap_weight", 0) +
                c["recent3"] / 3 * weights.get("r3", 0) +
                c["streak"] * weights.get("streak", 0)
            )
        else:
            scores[z] = (
                (1 if c["gap"] >= 16 else 0) * weights.get("gap_ge16", 0) +
                (1 if c["gap"] >= 10 else 0) * weights.get("gap_ge10", 0) +
                (1 if c["gap"] >= 6 else 0) * weights.get("gap_ge6", 0) +
                c["recent3"] / 3 * weights.get("r3", 0) +
                c["streak"] * weights.get("streak", 0)
            )

    # 按分数排序
    ranked = sorted(zodiacs, key=lambda z: scores[z], reverse=True)
    return ranked[:6]


def is_sunday(records: List[Dict]) -> bool:
    """判断最近一期是否为周日"""
    if not records or '开奖时间' not in records[-1]:
        return False
    try:
        from datetime import datetime
        dt = datetime.strptime(records[-1]['开奖时间'], '%Y-%m-%d %H:%M:%S')
        return dt.weekday() == 6
    except:
        return False


def predict_next(records: List[Dict]) -> Tuple[str, List[str], Dict]:
    """预测下期

    注意：周日效应已通过参数优化嵌入模型，不再做额外条件判断。
    """
    strategy = load_strategy()
    strategy_type = strategy.get("strategy_type", "binary")

    if strategy_type == "pattern_based":
        # zigzag pattern strategy - 直接使用参数，不做 is_sunday 条件判断
        weights = strategy.get("params", {})
        top6 = predict_top6(records, weights, "pattern_based")
    else:
        weights = strategy.get("weights", {})
        feature_type = strategy.get("feature_type", "binary")
        top6 = predict_top6(records, weights, feature_type)

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
    records = get_all_records([2024, 2025, 2026])
    standard_records = build_standard_records(records)

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