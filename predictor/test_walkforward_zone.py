#!/usr/bin/env python3
"""
固定选 20-49 策略的 walk-forward 测试
检验偏态是否稳定
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, build_standard_records

records = get_all_records([2024, 2025, 2026])
standard = build_standard_records(records)
print(f"总期数: {len(standard)}")

# 分段统计：每100期统计一次
segments = []
for start in range(0, len(standard) - 100, 100):
    end = min(start + 100, len(standard))
    segment = standard[start:end]

    low_count = sum(1 for r in segment if int(r.get("特码号码", 0)) < 20)
    high_count = len(segment) - low_count

    segments.append({
        "range": f"{start+1}-{end}",
        "low_count": low_count,
        "high_count": high_count,
        "high_rate": high_count / len(segment) * 100
    })

print("\n=== 100期分段统计 (后区20-49占比) ===")
for s in segments:
    bar = "█" * int(s["high_rate"] / 5)
    print(f"{s['range']:>10}: {s['high_rate']:5.1f}% {bar}")

# 统计最近50期
print("\n=== 最近50期 ===")
recent_50 = standard[-50:]
low_count = sum(1 for r in recent_50 if int(r.get("特码号码", 0)) < 20)
high_count = 50 - low_count
print(f"后区占比: {high_count/50*100:.1f}%")

# 预测：如果后区占比下降，命中率会降低
print("\n" + "="*50)
print("如果未来后区占比下降:")
print("  80% → 预测命中率 80%*61.22% ≈ 49%")
print("  70% → 预测命中率 70%*61.22% ≈ 42.9%")
print("  60% → 预测命中率 60%*61.22% ≈ 36.7%")
print("  50% → 预测命中率 50%*61.22% ≈ 30.6%")