#!/usr/bin/env python3
"""
V26 平特一肖 - 探索最佳单策略
"""
import sys, random
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from predictor.data_fetcher import get_all_records, build_standard_records

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f"数据: {len(hist)}期")

# 纯频率法
def eval_freq(history, lb):
    n = len(history)
    if n < lb + 5:
        return 0
    h = t_ = 0
    for i in range(lb, n):
        window = history[max(0,i-lb):i]
        cur = history[i]
        freq = {}
        for r in window:
            z = r['特码生肖']
            freq[z] = freq.get(z, 0) + 1
        p = max(freq, key=freq.get)
        if p in (cur.get('开奖生肖') or []): h += 1
        t_ += 1
    return h/t_ if t_>0 else 0

# 最大遗漏法
def eval_gap(history, lb):
    n = len(history)
    if n < lb + 5:
        return 0
    h = t_ = 0
    for i in range(lb, n):
        window = history[max(0,i-lb):i]
        cur = history[i]
        gap = {}
        for z in ZODIACS:
            positions = [j for j,r in enumerate(window) if r['特码生肖']==z]
            gap[z] = len(window) - positions[-1] - 1 if positions else 999
        p = max(gap, key=gap.get)
        if p in (cur.get('开奖生肖') or []): h += 1
        t_ += 1
    return h/t_ if t_>0 else 0

# 综合评分法
def eval_score(history, lb, g, f, s, t, v):
    n = len(history)
    if n < lb + 5:
        return 0
    h = t_ = 0
    for i in range(lb, n):
        window = history[max(0,i-lb):i]
        cur = history[i]
        sc = {}
        for z in ZODIACS:
            ps = [j for j,r in enumerate(window) if r['特码生肖']==z]
            if not ps:
                sc[z] = 0.0; continue
            gap = len(window)-ps[-1]-1
            freq = len(ps)
            streak = 0
            for idx in range(len(window)-1,-1,-1):
                if window[idx]['特码生肖']==z: streak += 1
                else: break
            ints = [ps[j]-ps[j+1] for j in range(len(ps)-1)]
            g_s = min(gap,50)/50
            f_s = freq/lb
            s_s = min(streak,5)/5
            t_s = v_s = 0.5
            if len(ints)>=2:
                trend = ints[0]-ints[1]
                t_s = max(0,min(trend,10))/10
                av = sum(ints)/len(ints)
                var = sum((x-av)**2 for x in ints)/len(ints)
                v_s = 1/(1+var/10)
            sc[z] = g_s*g + f_s*f + s_s*s + t_s*t + v_s*v
        p = max(sc, key=sc.get)
        if p in (cur.get('开奖生肖') or []): h += 1
        t_ += 1
    return h/t_ if t_>0 else 0

print("=== 纯频率法 lb扫描 ===")
for lb in range(5, 61, 5):
    rate = eval_freq(hist, lb)
    print(f"lb={lb}: {rate:.4f}")

print("\n=== 最大遗漏法 lb扫描 ===")
for lb in range(5, 61, 5):
    rate = eval_gap(hist, lb)
    print(f"lb={lb}: {rate:.4f}")

print("\n=== 随机基准 ===")
import random
random.seed(42)
total = 0
for _ in range(1000):
    correct = 0
    for i in range(20, len(hist)):
        pred = random.choice(ZODIACS)
        if pred in (hist[i].get('开奖生肖') or []): correct += 1
    total += correct / (len(hist) - 20)
print(f"随机: {total/1000:.4f}")

# 综合评分法搜索
print("\n=== 综合评分法搜索 ===")
best = 0
bp = {}
for _ in range(2000):
    lb = random.randint(5, 60)
    g = random.uniform(-0.5, 1.5)
    f = random.uniform(-0.5, 1.5)
    s = random.uniform(-0.3, 0.8)
    t = random.uniform(-0.5, 1.5)
    v = random.uniform(-0.5, 1.5)
    r = eval_score(hist, lb, g, f, s, t, v)
    if r > best:
        best = r
        bp = {"lb":lb, "g":g, "f":f, "s":s, "t":t, "v":v}

print(f"最佳综合: {bp}, rate={best:.4f}")
