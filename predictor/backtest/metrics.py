#!/usr/bin/env python3
"""
指标层：计算核心回测指标
"""

import statistics
from typing import List, Dict, Tuple


def calc_hit_rate(records: List[Dict]) -> float:
    """基础命中率 = hit_count / total"""
    if not records:
        return 0.0

    # 排除待验证的记录
    verified = [r for r in records if not r.get("pending", False)]
    if not verified:
        return 0.0

    hits = sum(1 for r in verified if r.get("hit", False))
    return hits / len(verified)


def calc_rolling_hit_rates(records: List[Dict]) -> Dict[str, float]:
    """滚动命中率：20/50/100期"""
    # 排除待验证的记录
    verified = [r for r in records if not r.get("pending", False)]

    result = {}

    for window in [20, 50, 100]:
        if len(verified) >= window:
            window_records = verified[-window:]
            hits = sum(1 for r in window_records if r.get("hit", False))
            result[f"rolling_{window}"] = hits / window
        else:
            result[f"rolling_{window}"] = None

    return result


def calc_streak_stats(records: List[Dict]) -> Dict[str, int]:
    """连中/连错分析"""
    # 排除待验证的记录
    verified = [r for r in records if not r.get("pending", False)]

    if not verified:
        return {"max_consecutive_hits": 0, "max_consecutive_misses": 0}

    max_hits = 0
    max_misses = 0
    current_hits = 0
    current_misses = 0

    for r in verified:
        if r.get("hit", False):
            current_hits += 1
            current_misses = 0
            max_hits = max(max_hits, current_hits)
        else:
            current_misses += 1
            current_hits = 0
            max_misses = max(max_misses, current_misses)

    return {
        "max_consecutive_hits": max_hits,
        "max_consecutive_misses": max_misses,
    }


def calc_stability(records: List[Dict], window: int = 20) -> Dict[str, float]:
    """稳定性分析：滚动窗口内的命中率方差"""
    # 排除待验证的记录
    verified = [r for r in records if not r.get("pending", False)]

    if len(verified) < window:
        return {"variance": None, "std": None, "coefficient_of_variation": None}

    hit_rates = []
    for i in range(window, len(verified) + 1):
        window_records = verified[i - window:i]
        hits = sum(1 for r in window_records if r.get("hit", False))
        hit_rates.append(hits / window)

    if len(hit_rates) < 2:
        return {"variance": 0.0, "std": 0.0, "coefficient_of_variation": 0.0}

    variance = statistics.variance(hit_rates)
    std = statistics.stdev(hit_rates)
    mean = statistics.mean(hit_rates)

    # 变异系数 = std / mean（防止除零）
    cv = std / mean if mean > 0 else 0.0

    return {
        "variance": variance,
        "std": std,
        "coefficient_of_variation": cv,
    }


def calc_trend(records: List[Dict], short: int = 20, long: int = 50) -> str:
    """趋势判断：短期 vs 长期命中率对比"""
    verified = [r for r in records if not r.get("pending", False)]

    if len(verified) < long:
        return "数据不足"

    short_records = verified[-short:]
    long_records = verified[-long:]

    short_hits = sum(1 for r in short_records if r.get("hit", False))
    long_hits = sum(1 for r in long_records if r.get("hit", False))

    short_rate = short_hits / len(short_records)
    long_rate = long_hits / len(long_records)

    diff = short_rate - long_rate

    if diff > 0.05:
        return "📈 上升"
    elif diff < -0.05:
        return "📉 退化"
    else:
        return "➡️ 平稳"


def calc_all_metrics(records: List[Dict]) -> Dict:
    """计算所有指标（主入口）"""
    verified = [r for r in records if not r.get("pending", False)]

    metrics = {
        "total": len(verified),
        "hit_count": sum(1 for r in verified if r.get("hit", False)),
        "hit_rate": calc_hit_rate(records),
    }

    # 滚动命中率
    rolling = calc_rolling_hit_rates(records)
    metrics.update(rolling)

    # 连中/连错
    streak = calc_streak_stats(records)
    metrics.update(streak)

    # 稳定性
    stability = calc_stability(records)
    metrics.update(stability)

    # 趋势
    metrics["trend"] = calc_trend(records)

    return metrics


if __name__ == "__main__":
    # 测试
    test_records = [
        {"issue": "1", "hit": True, "pending": False},
        {"issue": "2", "hit": True, "pending": False},
        {"issue": "3", "hit": False, "pending": False},
        {"issue": "4", "hit": True, "pending": False},
        {"issue": "5", "hit": True, "pending": False},
    ]
    print(calc_all_metrics(test_records))
