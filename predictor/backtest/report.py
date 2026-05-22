#!/usr/bin/env python3
"""
输出层：CLI 回测报告
"""

from datetime import datetime
from typing import Dict, List


def format_percentage(value: float, default: str = "N/A") -> str:
    """格式化百分比"""
    if value is None:
        return default
    return f"{value * 100:.1f}%"


def format_trend(metrics: Dict) -> str:
    """格式化趋势箭头"""
    verified = metrics.get("total", 0)
    if verified < 20:
        return "⚪ 数据不足"

    trend = metrics.get("trend", "➡️ 平稳")

    # 滚动对比
    rolling_20 = metrics.get("rolling_20")
    rolling_50 = metrics.get("rolling_50")
    rolling_100 = metrics.get("rolling_100")

    parts = []
    if rolling_20 is not None:
        arrow = "↑" if rolling_20 > 0.65 else ("↓" if rolling_20 < 0.55 else "→")
        parts.append(f"20期: {format_percentage(rolling_20)} {arrow}")

    if rolling_50 is not None:
        arrow = "↑" if rolling_50 > 0.65 else ("↓" if rolling_50 < 0.55 else "→")
        parts.append(f"50期: {format_percentage(rolling_50)} {arrow}")

    if rolling_100 is not None:
        arrow = "↑" if rolling_100 > 0.65 else ("↓" if rolling_100 < 0.55 else "→")
        parts.append(f"100期: {format_percentage(rolling_100)} {arrow}")

    return f"{trend}\n  {' | '.join(parts)}"


def format_stability(metrics: Dict) -> str:
    """格式化稳定性指标"""
    cv = metrics.get("coefficient_of_variation")
    if cv is None:
        return "⚪ 数据不足"

    # CV 越小越稳定
    if cv < 0.1:
        return f"🟢 非常稳定 (CV={cv:.3f})"
    elif cv < 0.2:
        return f"🟡 正常波动 (CV={cv:.3f})"
    else:
        return f"🔴 波动较大 (CV={cv:.3f})"


def format_report(metrics: Dict, records: List[Dict]) -> str:
    """生成完整回测报告"""
    lines = []

    lines.append("=" * 50)
    lines.append(f"  澳门六合回测报告  v1.0.0")
    lines.append(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 50)

    # 基础统计
    total = metrics.get("total", 0)
    hit_count = metrics.get("hit_count", 0)
    hit_rate = metrics.get("hit_rate", 0)

    lines.append("")
    lines.append("【基础统计】")
    lines.append(f"  总期数:   {total}")
    lines.append(f"  命中次数: {hit_count}")
    lines.append(f"  命中率:   {format_percentage(hit_rate)}")

    # 滚动命中率
    lines.append("")
    lines.append("【滚动命中率】")
    lines.append(f"  {format_trend(metrics)}")

    # 连中/连错
    max_hits = metrics.get("max_consecutive_hits", 0)
    max_misses = metrics.get("max_consecutive_misses", 0)
    lines.append("")
    lines.append("【连胜/连错分析】")
    lines.append(f"  最大连中: {max_hits} 期")
    lines.append(f"  最大连错: {max_misses} 期")

    # 稳定性
    lines.append("")
    lines.append("【系统稳定性】")
    lines.append(f"  {format_stability(metrics)}")

    # 趋势判断
    lines.append("")
    lines.append("【趋势判断】")
    trend = metrics.get("trend", "⚪ 数据不足")
    lines.append(f"  {trend}")

    lines.append("")
    lines.append("=" * 50)

    # 标注待验证记录
    pending = [r for r in records if r.get("pending", False)]
    if pending:
        lines.append("")
        lines.append(f"⚠️  待验证: {pending[0]['issue']}期 (预测: {', '.join(pending[0]['prediction'])})")

    return "\n".join(lines)


def print_report(metrics: Dict, records: List[Dict]) -> None:
    """打印报告到控制台"""
    print(format_report(metrics, records))


if __name__ == "__main__":
    # 测试
    test_metrics = {
        "total": 508,
        "hit_count": 316,
        "hit_rate": 0.622,
        "rolling_20": 0.70,
        "rolling_50": 0.64,
        "rolling_100": 0.58,
        "max_consecutive_hits": 6,
        "max_consecutive_misses": 4,
        "variance": 0.015,
        "std": 0.122,
        "coefficient_of_variation": 0.191,
        "trend": "📈 上升",
    }
    test_records = [{"issue": "2026100", "pending": True, "prediction": ["鼠", "牛"]}]

    print(format_report(test_metrics, test_records))
