#!/usr/bin/env python3
"""
V26 平特一肖 - 纯频率法测试
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from predictor.data_fetcher import get_all_records, build_standard_records

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f"数据: {len(hist)}期")

# 纯频率法
def eval_freq_only(history, lb):
    n = len(history)
    if n < lb + 5:
        return 0
    h = t_ = 0
    for i in range(lb, n):
        w = history[max(0,i-lb):i]
        cur = history[i]
        freq = {}
        for z in ZODIACS:
            freq[z] = sum(1 for r in w if r['特码生肖']==z)
        p = max(freq, key=freq.get)
        if p in (cur.get('开奖生肖') or []): h += 1
        t_ += 1
    return h/t_ if t_>0 else 0

# 测试不同lookback
print("=== 纯频率法测试 ===")
for lb in [5, 10, 15, 20, 30, 50, 80, 100]:
    rate = eval_freq_only(hist, lb)
    print(f"lb={lb}: rate={rate:.4f}")

# 随机基准
print("\n=== 随机基准(10000次模拟) ===")
import random
random.seed(42)
total = 0
for _ in range(10000):
    correct = 0
    for i in range(100, len(hist)):
        pred = random.choice(ZODIACS)
        if pred in (hist[i].get('开奖生肖') or []): correct += 1
    total += correct / (len(hist) - 100)
print(f"随机基准: {total/10000:.4f}")
