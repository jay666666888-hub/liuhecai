#!/usr/bin/env python3
"""
AB测试报告输出
"""

from datetime import datetime
from typing import List, Tuple, Dict


def format_percentage(value: float, default: str = "N/A") -> str:
    """格式化百分比"""
    if value is None:
        return default
    return f"{value * 100:.1f}%"


def format_strategy_card(name: str, metrics: Dict, rank: int) -> str:
    """格式化单个策略卡片"""
    lines = []
    lines.append(f"  #{rank:2d} {name}")
    lines.append(f"       综合得分: {metrics['score']:.3f}")
    lines.append(f"       命中率:   {format_percentage(metrics['hit_rate'])}")
    lines.append(f"       最近20期: {format_percentage(metrics['rolling_20'])}")
    lines.append(f"       最近50期: {format_percentage(metrics['rolling_50'])}")
    lines.append(f"       最大连中: {metrics['max_win_streak']}")
    lines.append(f"       最大连错: {metrics['max_lose_streak']}")
    lines.append(f"       一致性:   {metrics['consistency']:.4f}")
    return "\n".join(lines)


def format_top_strategies(rankings: List[Tuple[str, Dict]], top_n: int = 10) -> str:
    """格式化 Top N 策略"""
    lines = []
    lines.append("")
    lines.append("【Top {} 策略】".format(top_n))
    lines.append("")

    for i, (name, metrics) in enumerate(rankings[:top_n], 1):
        lines.append(format_strategy_card(name, metrics, i))
        lines.append("")

    return "\n".join(lines)


def format_comparison(result: Dict) -> str:
    """格式化策略对比"""
    lines = []
    lines.append("")
    lines.append("【策略对比】")
    lines.append(f"  {result['strategy_a']} vs {result['strategy_b']}")
    lines.append(f"  得分: {result['score_a']:.3f} vs {result['score_b']:.3f}")
    lines.append(f"  命中率: {format_percentage(result['hit_rate_a'])} vs {format_percentage(result['hit_rate_b'])}")
    lines.append(f"  直接对比: {result['wins_a']}胜 {result['ties']}平 {result['wins_b']}负")
    lines.append(f"  推荐: {result['recommendation']}")
    return "\n".join(lines)


def format_report(
    rankings: List[Tuple[str, Dict]],
    current_strategy: str,
    all_data: Dict[str, Dict]
) -> str:
    """生成完整AB测试报告"""
    lines = []

    lines.append("=" * 60)
    lines.append(f"  澳门六合策略 AB 测试报告  v1.0.0")
    lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)

    # 统计概览
    total_strategies = len(rankings)
    top1_name = rankings[0][0]
    top1_score = rankings[0][1]["score"]
    top1_hit_rate = rankings[0][1]["hit_rate"]

    lines.append("")
    lines.append("【概览】")
    lines.append(f"  测试策略数: {total_strategies}")
    lines.append(f"  最佳策略: {top1_name}")
    lines.append(f"  最佳得分: {top1_score:.3f}")
    lines.append(f"  最佳命中率: {format_percentage(top1_hit_rate)}")

    # Top 10
    lines.append(format_top_strategies(rankings, 10))

    # 当前策略对比
    lines.append("")
    lines.append("【当前策略 vs 最佳策略】")

    # 找到当前策略的排名
    current_rank = None
    current_metrics = None
    for i, (name, metrics) in enumerate(rankings, 1):
        if name == current_strategy:
            current_rank = i
            current_metrics = metrics
            break

    if current_rank:
        best = rankings[0]
        comparison = {
            "strategy_a": current_strategy,
            "strategy_b": best[0],
            "score_a": current_metrics["score"],
            "score_b": best[1]["score"],
            "hit_rate_a": current_metrics["hit_rate"],
            "hit_rate_b": best[1]["hit_rate"],
            "wins_a": sum(1 for a, b in zip(all_data[current_strategy]["hits"], all_data[best[0]]["hits"]) if a > b),
            "ties": sum(1 for a, b in zip(all_data[current_strategy]["hits"], all_data[best[0]]["hits"]) if a == b),
            "wins_b": 0,
            "recommendation": best[0] if best[1]["score"] > current_metrics["score"] else current_strategy,
        }
        comparison["wins_b"] = len(all_data[current_strategy]["hits"]) - comparison["wins_a"] - comparison["ties"]

        lines.append(f"  当前策略排名: #{current_rank}")
        lines.append(f"  当前策略得分: {current_metrics['score']:.3f}")
        lines.append(format_comparison(comparison))

        if best[0] != current_strategy:
            lines.append("")
            lines.append(f"  ⚠️ 建议切换到: {best[0]}")
    else:
        lines.append(f"  当前策略 '{current_strategy}' 未在测试列表中")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def print_report(rankings: List, current_strategy: str, all_data: Dict) -> None:
    """打印报告"""
    print(format_report(rankings, current_strategy, all_data))


if __name__ == "__main__":
    # 测试
    test_rankings = [
        ("策略A", {"score": 0.75, "hit_rate": 0.70, "rolling_20": 0.65, "rolling_50": 0.68, "max_win_streak": 8, "max_lose_streak": 3, "consistency": 0.02}),
        ("策略B", {"score": 0.68, "hit_rate": 0.65, "rolling_20": 0.60, "rolling_50": 0.63, "max_win_streak": 6, "max_lose_streak": 4, "consistency": 0.03}),
    ]
    print(format_report(test_rankings, "策略B", {}))
