#!/usr/bin/env python3
"""
V26 平特一肖 - 多策略融合
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from predictor.data_fetcher import get_all_records, build_standard_records

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f"数据: {len(hist)}期")

# 策略1: 纯频率
def strategy_freq(window):
    freq = {}
    for r in window:
        z = r['特码生肖']
        freq[z] = freq.get(z, 0) + 1
    return max(freq, key=freq.get)

# 策略2: 最大遗漏
def strategy_gap(window):
    gap = {}
    for z in ZODIACS:
        positions = [i for i,r in enumerate(window) if r['特码生肖']==z]
        gap[z] = len(window) - positions[-1] - 1 if positions else 999
    return max(gap, key=gap.get)

# 策略3: 综合评分
def strategy_score(window, w_g=0.5, w_f=0.5):
    scores = {}
    lb = len(window)
    for z in ZODIACS:
        positions = [i for i,r in enumerate(window) if r['特码生肖']==z]
        if not positions:
            scores[z] = 0.0; continue
        gap = len(window) - positions[-1] - 1
        freq = len(positions)
        g_s = min(gap, 50) / 50
        f_s = freq / lb
        scores[z] = g_s * w_g + f_s * w_f
    return max(scores, key=scores.get)

# 多策略融合
def eval_fusion(history, lookback):
    n = len(history)
    if n < lookback + 5:
        return 0
    h = t_ = 0
    for i in range(lookback, n):
        window = history[max(0,i-lookback):i]
        cur = history[i]
        
        # 三策略投票
        votes = {}
        for strat_fn in [strategy_freq, strategy_gap, 
                        lambda w: strategy_score(w, 0.3, 0.7),
                        lambda w: strategy_score(w, 0.7, 0.3),
                        lambda w: strategy_score(w, 0.5, 0.5)]:
            pred = strat_fn(window)
            votes[pred] = votes.get(pred, 0) + 1
        
        p = max(votes, key=votes.get)
        if p in (cur.get('开奖生肖') or []): h += 1
        t_ += 1
    return h/t_ if t_>0 else 0

# 测试不同lookback
print("=== 多策略融合测试 ===")
for lb in [10, 15, 20, 25, 30, 40, 50]:
    rate = eval_fusion(hist, lb)
    print(f"lb={lb}: {rate:.4f}")

# 单策略测试
print("\n=== 单策略测试(lb=20) ===")
h = t = 0
for i in range(20, len(hist)):
    window = hist[max(0,i-20):i]
    pred = strategy_score(window, 0.5, 0.5)
    if pred in (hist[i].get('开奖生肖') or []): h += 1
    t += 1
print(f"综合评分: {h/t:.4f}")

h = t = 0
for i in range(20, len(hist)):
    window = hist[max(0,i-20):i]
    pred = strategy_freq(window)
    if pred in (hist[i].get('开奖生肖') or []): h += 1
    t += 1
print(f"纯频率: {h/t:.4f}")

h = t = 0
for i in range(20, len(hist)):
    window = hist[max(0,i-20):i]
    pred = strategy_gap(window)
    if pred in (hist[i].get('开奖生肖') or []): h += 1
    t += 1
print(f"最大遗漏: {h/t:.4f}")
