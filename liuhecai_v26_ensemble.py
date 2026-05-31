#!/usr/bin/env python3
"""
V26 平特一肖 - 集成预测
"""
import sys, random
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from predictor.data_fetcher import get_all_records, build_standard_records

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f"数据: {len(hist)}期")

# 评分函数
def compute_scores(window, params):
    scores = {}
    lb = params['lb']
    g = params['g']
    f = params['f']
    s = params['s']
    t = params['t']
    v = params['v']
    
    for z in ZODIACS:
        ps = [j for j,r in enumerate(window) if r['特码生肖']==z]
        if not ps:
            scores[z] = 0.0; continue
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
        scores[z] = g_s*g + f_s*f + s_s*s + t_s*t + v_s*v
    return scores

# 多个不同参数的模型
models = [
    {"lb": 16, "g": 0.535, "f": 0.987, "s": 0.193, "t": 0.113, "v": 0.548},
    {"lb": 30, "g": 0.603, "f": 0.474, "s": 0.092, "t": 1.566, "v": 1.869},
    {"lb": 20, "g": 0.5, "f": 0.5, "s": 0.1, "t": 1.0, "v": 1.0},
]

# 集成评估 - 使用投票
def eval_ensemble(history, models):
    n = len(history)
    lb = max(m['lb'] for m in models)
    if n < lb + 5:
        return 0
    h = t_ = 0
    for i in range(lb, n):
        window = history[max(0,i-lb):i]
        cur = history[i]
        
        # 每个模型投票
        votes = {}
        for m in models:
            scores = compute_scores(window, m)
            pred = max(scores, key=scores.get)
            votes[pred] = votes.get(pred, 0) + 1
        
        # 得票最多的预测
        p = max(votes, key=votes.get)
        if p in (cur.get('开奖生肖') or []): h += 1
        t_ += 1
    return h/t_ if t_>0 else 0

# 测试集成
print("=== 集成测试 ===")
rate = eval_ensemble(hist, models)
print(f"3模型集成: {rate:.4f}")

# 测试单个模型
for m in models:
    lb = m['lb']
    h = t_ = 0
    for i in range(lb, len(hist)):
        window = hist[max(0,i-lb):i]
        scores = compute_scores(window, m)
        p = max(scores, key=scores.get)
        if p in (hist[i].get('开奖生肖') or []): h += 1
        t_ += 1
    print(f"  lb={lb}: {h/t_:.4f}")
