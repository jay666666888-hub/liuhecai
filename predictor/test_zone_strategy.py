#!/usr/bin/env python3
"""
区间优先策略测试
优先选 20-49 区（历史上75.5%开出）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, build_standard_records
from collections import Counter

records = get_all_records([2024, 2025, 2026])
standard = build_standard_records(records)
print(f"总期数: {len(standard)}")

lookback = 50

# 策略1: 固定选 20-49
print("\n=== 策略1: 固定选 20-49 (30码) ===")
hits = 0
total = 0
for i in range(lookback, len(standard)):
    prediction = [f"{j:02d}" for j in range(20, 50)]
    actual = standard[i].get("特码号码")
    hit = actual in prediction if actual else False
    if hit:
        hits += 1
    total += 1
print(f"命中率: {hits/total*100:.2f}%")

# 策略2: 只选 25-49 (25码)
print("\n=== 策略2: 只选 25-49 (25码) ===")
hits = 0
total = 0
for i in range(lookback, len(standard)):
    prediction = [f"{j:02d}" for j in range(25, 50)]
    actual = standard[i].get("特码号码")
    hit = actual in prediction if actual else False
    if hit:
        hits += 1
    total += 1
print(f"命中率: {hits/total*100:.2f}%")

# 策略3: 只选 30-49 (20码)
print("\n=== 策略3: 只选 30-49 (20码) ===")
hits = 0
total = 0
for i in range(lookback, len(standard)):
    prediction = [f"{j:02d}" for j in range(30, 50)]
    actual = standard[i].get("特码号码")
    hit = actual in prediction if actual else False
    if hit:
        hits += 1
    total += 1
print(f"命中率: {hits/total*100:.2f}%")

# 策略4: 前后区混合 - 前区只选热号
print("\n=== 策略4: 后区30个 + 前区热号3个 (33码) ===")
# 前区热号: 1,6,10,16,23 (历史上出现22-23次)
hot_from_low = ["01", "06", "10", "16", "23"]
hits = 0
total = 0
for i in range(lookback, len(standard)):
    prediction = [f"{j:02d}" for j in range(20, 50)] + hot_from_low
    actual = standard[i].get("特码号码")
    hit = actual in prediction if actual else False
    if hit:
        hits += 1
    total += 1
print(f"命中率: {hits/total*100:.2f}%")

# 策略5: 动态区间 - 根据最近趋势调整
print("\n=== 策略5: 根据近10期动态选择区间 ===")
for i in range(lookback, len(standard)):
    recent = standard[i-10:i]
    low_count = sum(1 for r in recent if int(r.get("特码号码", 0)) < 20)
    high_count = 10 - low_count

    # 如果前期后区占优，继续选后区；否则考虑前区
    if high_count >= 7:
        prediction = [f"{j:02d}" for j in range(20, 50)]
    else:
        prediction = [f"{j:02d}" for j in range(20, 50)]  # 始终选后区

hits = 0
total = 0
for i in range(lookback, len(standard)):
    recent = standard[i-10:i] if i >= 10 else standard[:i]
    low_count = sum(1 for r in recent if int(r.get("特码号码", 0)) < 20)
    high_count = len(recent) - low_count

    if high_count >= 7:
        prediction = [f"{j:02d}" for j in range(20, 50)]
    else:
        prediction = [f"{j:02d}" for j in range(20, 50)]

    actual = standard[i].get("特码号码")
    hit = actual in prediction if actual else False
    if hit:
        hits += 1
    total += 1
print(f"命中率: {hits/total*100:.2f}%")

print("\n" + "="*50)
print("结论: 固定选 20-49 (30码) 历史命中率 75.5%")
print("模型需要学会利用这个偏态分布")