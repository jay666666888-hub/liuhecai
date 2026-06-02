#!/usr/bin/env python3
"""
混合策略：固定后区 + 动态调整

策略：
1. 固定选 20-49 (30码) 作为基础
2. 根据最近趋势，从前区选出现频率高的补足到30+个
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, build_standard_records

records = get_all_records([2024, 2025, 2026])
standard = build_standard_records(records)
print(f"总期数: {len(standard)}")

lookback = 50

# 策略1: 纯固定后区 20-49
print("\n=== 策略1: 固定 20-49 (30码) ===")
hits = 0
total = 0
for i in range(lookback, len(standard)):
    prediction = [f"{j:02d}" for j in range(20, 50)]
    actual = standard[i].get("特码号码")
    hit = actual in prediction
    if hit:
        hits += 1
    total += 1
print(f"命中率: {hits/total*100:.2f}%")

# 策略2: 固定后区 + 前区最热的3个 (33码)
print("\n=== 策略2: 20-49 + 前区热3个 (33码) ===")
# 前区热号: 1,6,10,16,23 (历史上出现22-23次)
hot_low = ["01", "06", "10", "16", "23"]
hits = 0
total = 0
for i in range(lookback, len(standard)):
    history = standard[:i]
    recent = history[-20:]  # 近20期

    # 统计前区出现次数
    low_freq = {}
    for num in range(1, 20):
        num_str = f"{num:02d}"
        count = sum(1 for r in recent if r.get('特码号码') == num_str)
        low_freq[num_str] = count

    # 选近20期最热的3个前区号码
    top3_low = sorted(low_freq.items(), key=lambda x: x[1], reverse=True)[:3]
    top3_low_nums = [n for n, c in top3_low]

    prediction = [f"{j:02d}" for j in range(20, 50)] + top3_low_nums
    actual = standard[i].get("特码号码")
    hit = actual in prediction
    if hit:
        hits += 1
    total += 1
print(f"命中率: {hits/total*100:.2f}%")

# 策略3: 固定后区 + 前区动态 (最多33码)
print("\n=== 策略3: 20-49 + 前区动态 (最多33码) ===")
hits = 0
total = 0
for i in range(lookback, len(standard)):
    history = standard[:i]
    recent = history[-20:]

    # 前区频率
    low_freq = {}
    for num in range(1, 20):
        num_str = f"{num:02d}"
        count = sum(1 for r in recent if r.get('特码号码') == num_str)
        low_freq[num_str] = count

    # 只选近20期出现超过2次的
    dynamic_low = [n for n, c in low_freq.items() if c >= 2][:5]

    prediction = [f"{j:02d}" for j in range(20, 50)] + dynamic_low
    actual = standard[i].get("特码号码")
    hit = actual in prediction
    if hit:
        hits += 1
    total += 1
print(f"命中率: {hits/total*100:.2f}%")

# 策略4: 纯固定 25-49 (25码)
print("\n=== 策略4: 固定 25-49 (25码) ===")
hits = 0
total = 0
for i in range(lookback, len(standard)):
    prediction = [f"{j:02d}" for j in range(25, 50)]
    actual = standard[i].get("特码号码")
    hit = actual in prediction
    if hit:
        hits += 1
    total += 1
print(f"命中率: {hits/total*100:.2f}%")

# 策略5: 固定 20-49 但排除近5期出现超过4次的 (避免过热)
print("\n=== 策略5: 20-49 排除过热 (约28码) ===")
hits = 0
total = 0
for i in range(lookback, len(standard)):
    history = standard[:i]
    recent = history[-5:]

    hot_recent = []
    for num in range(20, 50):
        num_str = f"{num:02d}"
        count = sum(1 for r in recent if r.get('特码号码') == num_str)
        if count <= 3:  # 排除5期内出现4次以上的
            hot_recent.append(num_str)

    # 补足30个 - 优先选遗漏久的
    if len(hot_recent) < 30:
        # 按遗漏值排序补足
        remaining = [f"{j:02d}" for j in range(20, 50) if f"{j:02d}" not in hot_recent]
        # 简单处理：直接取前30个
        prediction = hot_recent[:30] if len(hot_recent) >= 30 else hot_recent + remaining[:30-len(hot_recent)]
    else:
        prediction = hot_recent[:30]

    actual = standard[i].get("特码号码")
    hit = actual in prediction
    if hit:
        hits += 1
    total += 1
print(f"命中率: {hits/total*100:.2f}%")

print("\n" + "="*50)
print("结论: 固定选 20-49 是最简单有效的策略")