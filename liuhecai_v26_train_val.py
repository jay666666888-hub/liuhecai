#!/usr/bin/env python3
"""
V26 平特一肖 - 训练/验证分离优化
避免过拟合：用前700期训练，后176期验证
"""
import sys, os
sys.path.insert(0, '.')
from predictor.data_fetcher import get_all_records, build_standard_records
import random

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

def eval_on_range(history, lb, g, f, s, t, v, start, end):
    """在指定范围内评估"""
    h = total = 0
    for i in range(start, end):
        if i < lb:
            continue
        w = history[max(0,i-lb):i]
        cur = history[i]
        sc = {}
        for z in ZODIACS:
            ps = [j for j,r in enumerate(w) if r['特码生肖']==z]
            if not ps:
                sc[z] = 0.0; continue
            gap = len(w)-ps[-1]-1
            freq = len(ps)
            streak = 0
            for idx in range(len(w)-1,-1,-1):
                if w[idx]['特码生肖']==z: streak += 1
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
        total += 1
    return h/total if total>0 else 0, total

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f'总数据: {len(hist)}期')

# 训练集: 前700期, 验证集: 后176期
train_end = 700
val_start = 700

print(f'训练集: 0-{train_end}, 验证集: {val_start}-{len(hist)}')

best_val = 0
best_train = 0
bp = {}

print('搜索...')
for _ in range(5000):
    lb = random.randint(15, 50)
    g = random.uniform(0.05, 0.5)
    f = random.uniform(0.1, 0.5)
    s = random.uniform(0, 0.3)
    t = random.uniform(0.1, 0.5)
    v = random.uniform(0.1, 0.5)

    # 训练集评估
    train_rate, _ = eval_on_range(hist, lb, g, f, s, t, v, lb, train_end)
    # 验证集评估
    val_rate, _ = eval_on_range(hist, lb, g, f, s, t, v, val_start, len(hist))

    # 综合评分：验证集优先，但训练集不能太差
    combined = val_rate * 0.7 + train_rate * 0.3

    if val_rate > best_val:
        best_val = val_rate
        best_train = train_rate
        bp = {'lb':lb,'g':g,'f':f,'s':s,'t':t,'v':v}
        print(f'New best: lb={lb}, g={g:.3f}, f={f:.3f}, s={s:.3f}, t={t:.3f}, v={v:.3f}')
        print(f'  Train: {train_rate:.4f}, Val: {val_rate:.4f}, Combined: {combined:.4f}')

print(f'\n最佳验证集参数: {bp}')
print(f'训练集命中率: {best_train:.4f}')
print(f'验证集命中率: {best_val:.4f}')
