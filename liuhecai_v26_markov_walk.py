#!/usr/bin/env python3
"""
V26 平特一肖 - Markov链步行验证
"""
import sys, random
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from predictor.data_fetcher import get_all_records, build_standard_records

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f"数据: {len(hist)}期")

# 步行验证Markov
def build_markov_n(hist, n):
    """只用hist[:n]的数据构建n阶Markov链"""
    counts = {}
    for i in range(n, len(hist)):
        state = tuple(hist[j]['特码生肖'] for j in range(i-n, i))
        next_z = hist[i]['特码生肖']
        if state not in counts:
            counts[state] = {}
        counts[state][next_z] = counts[state].get(next_z, 0) + 1
    
    probs = {}
    for state, trans in counts.items():
        total = sum(trans.values())
        if total >= 2:  # 至少2个样本
            probs[state] = {z: c/total for z, c in trans.items()}
    
    return probs

def predict_markov_walk(hist, n, probs):
    m = len(hist)
    if m < n:
        return random.choice(ZODIACS)
    
    state = tuple(hist[i]['特码生肖'] for i in range(m-n, m))
    
    if state in probs:
        trans = probs[state]
        if trans:
            return max(trans, key=trans.get)
    
    # 回退到低阶
    if n > 1:
        return predict_markov_walk(hist, n-1, probs)
    return random.choice(ZODIACS)

# 步行验证
print("=== Markov步行验证 ===")
for order in [1, 2, 3]:
    hits = 0
    total = 0
    
    # 从第100期开始
    for i in range(100, len(hist)):
        # 用0到i-1的数据构建Markov链
        probs = build_markov_n(hist[:i], order)
        pred = predict_markov_walk(hist[:i], order, probs)
        
        actual_list = hist[i].get('开奖生肖', [])
        if pred in actual_list:
            hits += 1
        total += 1
    
    print(f"Markov-{order}阶步行: {hits}/{total} = {hits/total:.4f}")

# 带有置信度的投票
print("\n=== 置信度投票 ===")
def predict_confidence_vote(hist, lookback=30, min_count=3):
    n = len(hist)
    window = hist[max(0,n-lookback):n]
    
    # Markov 2阶概率
    probs_2 = {}
    for i in range(2, len(window)):
        state = (window[i-2]['特码生肖'], window[i-1]['特码生肖'])
        next_z = window[i]['特码生肖']
        if state not in probs_2:
            probs_2[state] = {}
        probs_2[state][next_z] = probs_2[state].get(next_z, 0) + 1
    
    # 转为概率
    for state, trans in probs_2.items():
        total = sum(trans.values())
        if total >= min_count:
            probs_2[state] = {z: c/total for z, c in trans.items()}
    
    # 当前状态
    if n >= 2:
        cur_state = (hist[n-2]['特码生肖'], hist[n-1]['特码生肖'])
        if cur_state in probs_2 and probs_2[cur_state]:
            markov_preds = probs_2[cur_state]
        else:
            markov_preds = {}
    else:
        markov_preds = {}
    
    # 频率统计
    freq = {}
    for r in window:
        z = r['特码生肖']
        freq[z] = freq.get(z, 0) + 1
    
    # 综合评分
    scores = {}
    for z in ZODIACS:
        markov_prob = markov_preds.get(z, 0.0)
        freq_score = freq.get(z, 0) / lookback
        # 综合: Markov * 0.6 + 频率 * 0.4
        scores[z] = markov_prob * 0.6 + freq_score * 0.4
    
    return max(scores, key=scores.get)

hits = 0
total = 0
for i in range(50, len(hist)):
    pred = predict_confidence_vote(hist[:i], lookback=50)
    actual_list = hist[i].get('开奖生肖', [])
    if pred in actual_list:
        hits += 1
    total += 1
print(f"置信度投票: {hits}/{total} = {hits/total:.4f}")

# 尝试：只用近期数据构建Markov
print("\n=== 近期Markov ===")
def build_recent_markov(hist, n, lookback=100):
    """只用最近lookback期构建Markov"""
    recent = hist[-lookback:]
    counts = {}
    for i in range(n, len(recent)):
        state = tuple(recent[j]['特码生肖'] for j in range(i-n, i))
        next_z = recent[i]['特码生肖']
        if state not in counts:
            counts[state] = {}
        counts[state][next_z] = counts[state].get(next_z, 0) + 1
    
    probs = {}
    for state, trans in counts.items():
        total = sum(trans.values())
        if total >= 2:
            probs[state] = {z: c/total for z, c in trans.items()}
    
    return probs

for order in [2, 3]:
    probs = build_recent_markov(hist, order, lookback=100)
    
    hits = 0
    total = 0
    for i in range(100, len(hist)):
        pred = predict_markov_walk(hist[:i], order, probs)
        actual_list = hist[i].get('开奖生肖', [])
        if pred in actual_list:
            hits += 1
        total += 1
    
    print(f"近期Markov-{order}阶: {hits}/{total} = {hits/total:.4f}")

# 更大窗口
print("\n=== 扩展窗口Markov ===")
for lookback in [50, 100, 200, 300]:
    probs = build_recent_markov(hist, 2, lookback=lookback)
    
    hits = 0
    total = 0
    for i in range(lookback, len(hist)):
        pred = predict_markov_walk(hist[:i], 2, probs)
        actual_list = hist[i].get('开奖生肖', [])
        if pred in actual_list:
            hits += 1
        total += 1
    
    print(f"Markov-2阶 win={lookback}: {hits}/{total} = {hits/total:.4f}")
