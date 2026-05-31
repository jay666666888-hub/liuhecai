#!/usr/bin/env python3
"""
V26 平特一肖 - Meta-Learner寻找策略切换时机
"""
import sys, random
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from predictor.data_fetcher import get_all_records, build_standard_records
import numpy as np

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f"数据: {len(hist)}期")

# 策略定义
def strategy_freq(window):
    freq = {}
    for r in window:
        z = r['特码生肖']
        freq[z] = freq.get(z, 0) + 1
    return max(freq, key=freq.get)

def strategy_gap(window):
    gap = {}
    for z in ZODIACS:
        positions = [i for i,r in enumerate(window) if r['特码生肖']==z]
        gap[z] = len(window) - positions[-1] - 1 if positions else len(window)
    return max(gap, key=gap.get)

def strategy_recent(window):
    recent = {}
    for z in ZODIACS:
        positions = [i for i,r in enumerate(window) if r['特码生肖']==z]
        recent[z] = positions[-1] if positions else -1
    return min(recent, key=recent.get)  # 最近出现的

def strategy_interval(window):
    """选择间隔最稳定的"""
    best_z = ZODIACS[0]
    best_score = -999
    for z in ZODIACS:
        positions = [i for i,r in enumerate(window) if r['特码生肖']==z]
        if len(positions) >= 3:
            ints = [positions[i] - positions[i+1] for i in range(len(positions)-1)]
            score = -np.std(ints)  # 越小越稳定
            if score > best_score:
                best_score = score
                best_z = z
    return best_z

strategies = {
    'freq': strategy_freq,
    'gap': strategy_gap,
    'recent': strategy_recent,
    'interval': strategy_interval
}

# 计算每个策略的近期表现
def get_recent_performance(hist, end, lookback, n_strategies=4):
    """返回每个策略在过去n_lookback期的命中率"""
    window = hist[max(0, end-n_strategies):end]
    results = {name: [] for name in strategies}
    
    for i in range(n_strategies, len(window)):
        w = window[:i]
        actual = window[i].get('开奖生肖', [])
        for name, strat in strategies.items():
            pred = strat(w)
            results[name].append(1 if pred in actual else 0)
    
    perf = {}
    for name, res in results.items():
        if res:
            perf[name] = sum(res) / len(res)
        else:
            perf[name] = 0.5
    return perf

# Meta策略：用近期表现决定当前策略
def predict_meta(hist, lookback=30, n_recent=20):
    n = len(hist)
    window = hist[max(0,n-lookback):n]
    
    # 获取近期表现
    recent_perf = get_recent_performance(hist, n, n_recent)
    
    # 选择最佳策略
    best_strat = max(recent_perf, key=recent_perf.get)
    
    return strategies[best_strat](window)

# 测试Meta策略
print("=== Meta策略测试 ===")
for n_recent in [5, 10, 20, 30]:
    hits = 0
    total = 0
    for i in range(50, len(hist)):
        pred = predict_meta(hist[:i], lookback=30, n_recent=n_recent)
        actual_list = hist[i].get('开奖生肖', [])
        if pred in actual_list:
            hits += 1
        total += 1
    print(f"Meta策略(n_recent={n_recent}): {hits}/{total} = {hits/total:.4f}")

# 评分投票：加权平均
print("\n=== 加权投票 ===")
def predict_weighted_vote(hist, lookback=30, n_recent=20):
    n = len(hist)
    window = hist[max(0,n-lookback):n]
    
    # 获取近期表现作为权重
    recent_perf = get_recent_performance(hist, n, n_recent)
    
    # 每个策略投票
    votes = {}
    for name, strat in strategies.items():
        pred = strat(window)
        weight = recent_perf.get(name, 0.5)
        votes[pred] = votes.get(pred, 0) + weight
    
    return max(votes, key=votes.get)

for n_recent in [5, 10, 20, 30]:
    hits = 0
    total = 0
    for i in range(50, len(hist)):
        pred = predict_weighted_vote(hist[:i], lookback=30, n_recent=n_recent)
        actual_list = hist[i].get('开奖生肖', [])
        if pred in actual_list:
            hits += 1
        total += 1
    print(f"加权投票(n_recent={n_recent}): {hits}/{total} = {hits/total:.4f}")

# 动态调整lookback
print("\n=== 动态Lookback ===")
def predict_dynamic_lookback(hist):
    n = len(hist)
    
    # 测试不同lookback
    lookbacks = [10, 20, 30, 50, 80]
    results = {}
    
    for lb in lookbacks:
        window = hist[max(0,n-lb):n]
        freq = {}
        for r in window:
            z = r['特码生肖']
            freq[z] = freq.get(z, 0) + 1
        pred = max(freq, key=freq.get)
        results[pred] = results.get(pred, 0) + 1
    
    return max(results, key=results.get)

hits = 0
total = 0
for i in range(80, len(hist)):
    pred = predict_dynamic_lookback(hist[:i])
    actual_list = hist[i].get('开奖生肖', [])
    if pred in actual_list:
        hits += 1
    total += 1
print(f"动态Lookback: {hits}/{total} = {hits/total:.4f}")

# 简单投票（无权重）
print("\n=== 简单投票 ===")
def predict_simple_vote(hist, lookback=30):
    n = len(hist)
    window = hist[max(0,n-lookback):n]
    
    votes = {}
    for name, strat in strategies.items():
        pred = strat(window)
        votes[pred] = votes.get(pred, 0) + 1
    
    return max(votes, key=votes.get)

hits = 0
total = 0
for i in range(30, len(hist)):
    pred = predict_simple_vote(hist[:i])
    actual_list = hist[i].get('开奖生肖', [])
    if pred in actual_list:
        hits += 1
    total += 1
print(f"简单投票: {hits}/{total} = {hits/total:.4f}")
