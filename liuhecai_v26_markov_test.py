#!/usr/bin/env python3
"""
V26 平特一肖 - 完整Markov测试
"""
import sys, random
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from predictor.data_fetcher import get_all_records, build_standard_records

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f"数据: {len(hist)}期")

# Markov 3阶 - 完整测试
def build_markov(hist, n):
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
        probs[state] = {z: c/total for z, c in trans.items()}
    
    return probs

def predict_markov(hist, n, probs):
    m = len(hist)
    if m < n:
        return random.choice(ZODIACS)
    state = tuple(hist[i]['特码生肖'] for i in range(m-n, m))
    if state in probs and probs[state]:
        return max(probs[state], key=probs[state].get)
    return random.choice(ZODIACS)

# 用全部数据构建Markov，测试全部数据
print("=== Markov 3阶全量测试 ===")
probs = build_markov(hist, 3)
print(f"状态数: {len(probs)}")

hits = 0
total = 0
for i in range(3, len(hist)):
    pred = predict_markov(hist, 3, probs)
    actual_list = hist[i].get('开奖生肖', [])
    if pred in actual_list:
        hits += 1
    total += 1
print(f"全量测试: {hits}/{total} = {hits/total:.4f}")

# 步行验证（每步重建）
print("\n=== Markov 3阶步行验证 ===")
hits = 0
total = 0
for i in range(50, len(hist)):
    probs_i = build_markov(hist[:i], 3)
    pred = predict_markov(hist[:i], 3, probs_i)
    actual_list = hist[i].get('开奖生肖', [])
    if pred in actual_list:
        hits += 1
    total += 1
print(f"步行验证: {hits}/{total} = {hits/total:.4f}")

# 用前700期构建，测后177期
print("\n=== 训练/测试分离 ===")
probs_train = build_markov(hist[:700], 3)
print(f"训练状态数: {len(probs_train)}")

hits = 0
total = 0
for i in range(700, len(hist)):
    pred = predict_markov(hist[:i], 3, probs_train)
    actual_list = hist[i].get('开奖生肖', [])
    if pred in actual_list:
        hits += 1
    total += 1
print(f"测试集(700-): {hits}/{total} = {hits/total:.4f}")

# 扩展训练数据
for train_end in [500, 600, 700, 800]:
    probs_train = build_markov(hist[:train_end], 3)
    hits = 0
    total = 0
    for i in range(train_end, len(hist)):
        pred = predict_markov(hist[:i], 3, probs_train)
        actual_list = hist[i].get('开奖生肖', [])
        if pred in actual_list:
            hits += 1
        total += 1
    print(f"训练到{train_end}, 测试{train_end}-end: {hits}/{total} = {hits/total:.4f}")
