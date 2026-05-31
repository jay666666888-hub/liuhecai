#!/usr/bin/env python3
"""
AB测试指标计算
"""

from typing import List, Dict, Tuple


def calc_hit_rate(hits: List[int]) -> float:
    """计算命中率"""
    if not hits:
        return 0.0
    return sum(hits) / len(hits)


def calc_rolling_hit_rates(hits: List[int]) -> Dict[str, float]:
    """计算滚动命中率"""
    result = {}
    for window in [10, 20, 50]:
        if len(hits) >= window:
            window_hits = hits[-window:]
            result[f"rolling_{window}"] = sum(window_hits) / window
        else:
            result[f"rolling_{window}"] = None
    return result


def calc_streak_stats(hits: List[int]) -> Dict[str, int]:
    """计算连中/连错"""
    if not hits:
        return {"max_win_streak": 0, "max_lose_streak": 0}

    max_win = max_lose = 0
    current_win = current_lose = 0

    for h in hits:
        if h == 1:
            current_win += 1
            current_lose = 0
            max_win = max(max_win, current_win)
        else:
            current_lose += 1
            current_win = 0
            max_lose = max(max_lose, current_lose)

    return {"max_win_streak": max_win, "max_lose_streak": max_lose}


def calc_consistency(hits: List[int], window: int = 20) -> float:
    """计算一致性（滚动命中率方差）"""
    if len(hits) < window:
        return 0.0

    rates = []
    for i in range(window, len(hits) + 1):
        window_hits = hits[i - window:i]
        rates.append(sum(window_hits) / window)

    if len(rates) < 2:
        return 0.0

    mean = sum(rates) / len(rates)
    variance = sum((r - mean) ** 2 for r in rates) / len(rates)
    return variance


def calc_strategy_score(hits: List[int]) -> Dict:
    """综合评分"""
    hit_rate = calc_hit_rate(hits)
    rolling = calc_rolling_hit_rates(hits)
    streaks = calc_streak_stats(hits)
    consistency = calc_consistency(hits)

    # 综合得分 = 命中率 * 0.4 + 近期20期 * 0.3 + 稳定性 * 0.3
    recent_20 = rolling.get("rolling_20", 0) or 0
    stability_score = 1 - min(consistency * 10, 1)  # 方差越小稳定性越高

    score = hit_rate * 0.4 + recent_20 * 0.3 + stability_score * 0.3

    return {
        "hit_rate": hit_rate,
        "rolling_10": rolling.get("rolling_10"),
        "rolling_20": rolling.get("rolling_20"),
        "rolling_50": rolling.get("rolling_50"),
        "max_win_streak": streaks["max_win_streak"],
        "max_lose_streak": streaks["max_lose_streak"],
        "consistency": consistency,
        "score": score,
    }


def rank_strategies(all_data: Dict[str, Dict]) -> List[Tuple[str, Dict]]:
    """对所有策略排名"""
    rankings = []

    for name, data in all_data.items():
        metrics = calc_strategy_score(data["hits"])
        rankings.append((name, metrics))

    # 按综合得分排序
    rankings.sort(key=lambda x: x[1]["score"], reverse=True)
    return rankings


def compare_two_strategies(
    strategy_a: str, hits_a: List[int],
    strategy_b: str, hits_b: List[int]
) -> Dict:
    """对比两个策略"""
    metrics_a = calc_strategy_score(hits_a)
    metrics_b = calc_strategy_score(hits_b)

    # 计算直接对比（同一期谁更准）
    if len(hits_a) != len(hits_b):
        return {"error": "长度不一致"}

    wins = sum(1 for a, b in zip(hits_a, hits_b) if a > b)
    ties = sum(1 for a, b in zip(hits_a, hits_b) if a == b)
    total = len(hits_a)

    return {
        "strategy_a": strategy_a,
        "strategy_b": strategy_b,
        "score_a": metrics_a["score"],
        "score_b": metrics_b["score"],
        "hit_rate_a": metrics_a["hit_rate"],
        "hit_rate_b": metrics_b["hit_rate"],
        "wins_a": wins,
        "wins_b": total - wins - ties,
        "ties": ties,
        "win_rate": wins / total if total > 0 else 0,
        "recommendation": strategy_a if metrics_a["score"] > metrics_b["score"] else strategy_b,
    }


if __name__ == "__main__":
    # 测试
    test_hits = [1, 0, 1, 1, 0, 1, 1, 1, 0, 0]
    print(calc_strategy_score(test_hits))
