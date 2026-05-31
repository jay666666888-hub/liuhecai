#!/usr/bin/env python3
"""
V26 平特一肖 - 增强Markov链 + 多阶特征
"""
import sys, random, math
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from predictor.data_fetcher import get_all_records, build_standard_records
import numpy as np

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f"数据: {len(hist)}期")

# Markov转移矩阵
def build_markov_chain(hist, order=2):
    """构建N阶Markov链"""
    counts = {}
    for i in range(order, len(hist)):
        state = tuple(hist[j]['特码生肖'] for j in range(i-order, i))
        next_z = hist[i]['特码生肖']
        if state not in counts:
            counts[state] = {}
        counts[state][next_z] = counts[state].get(next_z, 0) + 1
    
    # 转为概率
    probs = {}
    for state, trans in counts.items():
        total = sum(trans.values())
        probs[state] = {z: c/total for z, c in trans.items()}
    
    return probs, order

# 预测
def predict_markov(hist, order, probs):
    n = len(hist)
    if n < order:
        return random.choice(ZODIACS)
    
    state = tuple(hist[i]['特码生肖'] for i in range(n-order, n))
    
    if state in probs:
        trans = probs[state]
        # 返回概率最高的
        return max(trans, key=trans.get)
    else:
        # 回退到1阶
        if order > 1:
            return predict_markov(hist, order-1, probs)
        return random.choice(ZODIACS)

# 测试不同阶数
print("=== Markov链测试 ===")
for order in [1, 2, 3]:
    probs, _ = build_markov_chain(hist, order)
    
    hits = 0
    total = 0
    for i in range(order + 10, len(hist)):
        pred = predict_markov(hist[:i], order, probs)
        actual_list = hist[i].get('开奖生肖', [])
        if pred in actual_list:
            hits += 1
        total += 1
    
    print(f"Markov-{order}阶: {hits}/{total} = {hits/total:.4f}")

# 混合策略：Markov + 频率
print("\n=== 混合策略 ===")
def predict_hybrid(hist, markov_probs, order, lb=30):
    n = len(hist)
    
    # Markov预测
    if n >= order:
        state = tuple(hist[i]['特码生肖'] for i in range(n-order, n))
        if state in markov_probs:
            markov_pred = max(markov_probs[state], key=markov_probs[state].get)
        else:
            markov_pred = None
    else:
        markov_pred = None
    
    # 窗口频率
    window = hist[max(0,n-lb):n]
    freq = {}
    for r in window:
        z = r['特码生肖']
        freq[z] = freq.get(z, 0) + 1
    freq_pred = max(freq, key=freq.get)
    
    # 综合
    if markov_pred and markov_pred == freq_pred:
        return markov_pred
    elif markov_pred and freq_pred:
        return markov_pred  # 优先Markov
    else:
        return freq_pred

# 测试混合
probs, order = build_markov_chain(hist, 2)
hits = 0
total = 0
for i in range(40, len(hist)):
    pred = predict_hybrid(hist[:i], probs, order, lb=30)
    actual_list = hist[i].get('开奖生肖', [])
    if pred in actual_list:
        hits += 1
    total += 1
print(f"混合(Markov+Freq): {hits}/{total} = {hits/total:.4f}")

# 动态选择策略
print("\n=== 动态策略选择 ===")
def predict_dynamic(hist, lookback=30):
    n = len(hist)
    
    # 策略1: 频率
    window = hist[max(0,n-lookback):n]
    freq = {}
    for r in window:
        z = r['特码生肖']
        freq[z] = freq.get(z, 0) + 1
    freq_pred = max(freq, key=freq.get)
    
    # 策略2: 最大遗漏
    gap = {}
    for z in ZODIACS:
        positions = [i for i,r in enumerate(window) if r['特码生肖']==z]
        gap[z] = len(window) - positions[-1] - 1 if positions else lookback
    gap_pred = max(gap, key=gap.get)
    
    # 策略3: 最近出现
    recent = {}
    for z in ZODIACS:
        positions = [i for i,r in enumerate(window) if r['特码生肖']==z]
        recent[z] = positions[-1] if positions else -1
    recent_pred = max(recent, key=recent.get)
    
    # 策略4: Markov 2阶
    if n >= 2:
        state = (hist[n-2]['特码生肖'], hist[n-1]['特码生肖'])
        probs_m2 = build_markov_chain(hist[:n], 2)[0]
        if state in probs_m2:
            markov_pred = max(probs_m2[state], key=probs_m2[state].get)
        else:
            markov_pred = None
    else:
        markov_pred = None
    
    # 投票
    votes = {}
    for pred in [freq_pred, gap_pred, recent_pred, markov_pred]:
        if pred:
            votes[pred] = votes.get(pred, 0) + 1
    
    return max(votes, key=votes.get)

hits = 0
total = 0
for i in range(30, len(hist)):
    pred = predict_dynamic(hist[:i], lookback=30)
    actual_list = hist[i].get('开奖生肖', [])
    if pred in actual_list:
        hits += 1
    total += 1
print(f"动态策略投票: {hits}/{total} = {hits/total:.4f}")

# 更复杂：考虑近期表现的自适应
print("\n=== 自适应策略 ===")
def predict_adaptive(hist, lookback=50):
    n = len(hist)
    window = hist[max(0,n-lookback):n]
    
    # 计算每个策略的近期命中率
    strategies = {}
    
    # 策略1: 频率
    freq = {}
    for r in window:
        z = r['特码生肖']
        freq[z] = freq.get(z, 0) + 1
    strategies['freq'] = max(freq, key=freq.get)
    
    # 策略2: 间隔（最大遗漏）
    gap = {}
    for z in ZODIACS:
        positions = [i for i,r in enumerate(window) if r['特码生肖']==z]
        gap[z] = len(window) - positions[-1] - 1 if positions else lookback
    strategies['gap'] = max(gap, key=gap.get)
    
    # 策略3: 最近出现
    recent = {}
    for z in ZODIACS:
        positions = [i for i,r in enumerate(window) if r['特码生肖']==z]
        recent[z] = positions[-1] if positions else -1
    strategies['recent'] = min(recent, key=recent.get)  # 最近出现的
    
    # 策略4: 趋势（间隔减少的生肖）
    trend = {}
    for z in ZODIACS:
        positions = [i for i,r in enumerate(window) if r['特码生肖']==z]
        if len(positions) >= 3:
            ints = [positions[i] - positions[i+1] for i in range(len(positions)-1)]
            trend[z] = -np.mean(ints)  # 负值表示间隔在减少
        else:
            trend[z] = 0
    strategies['trend'] = max(trend, key=trend.get)
    
    # 策略5: 均衡（综合评分）
    scores = {}
    for z in ZODIACS:
        positions = [i for i,r in enumerate(window) if r['特码生肖']==z]
        if positions:
            gap_val = len(window) - positions[-1] - 1
            freq_val = len(positions)
            scores[z] = freq_val * 0.6 - gap_val * 0.4
        else:
            scores[z] = -lookback
    strategies['score'] = max(scores, key=scores.get)
    
    # 输出所有策略预测
    preds = list(strategies.values())
    votes = {}
    for p in preds:
        votes[p] = votes.get(p, 0) + 1
    
    # 最多票
    return max(votes, key=votes.get)

hits = 0
total = 0
for i in range(50, len(hist)):
    pred = predict_adaptive(hist[:i], lookback=50)
    actual_list = hist[i].get('开奖生肖', [])
    if pred in actual_list:
        hits += 1
    total += 1
print(f"自适应5策略: {hits}/{total} = {hits/total:.4f}")
