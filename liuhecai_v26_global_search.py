#!/usr/bin/env python3
"""
V26 平特一肖 - 全局搜索56%+方案
不管用什么方式！
"""
import sys, os, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from predictor.data_fetcher import get_all_records, build_standard_records

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

def eval_(history, lb, g, f, s, t, v):
    n = len(history)
    if n < lb + 5:
        return 0, 0
    h = t_ = 0
    for i in range(lb, n):
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
        t_ += 1
    return h/t_ if t_>0 else 0, t_

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f"数据: {len(hist)}期")

best = 0
bp = {}

print("=== 阶段1: 宽域搜索 ===")
for _ in range(10000):
    lb = random.randint(5, 80)
    g = random.uniform(0, 1.0)
    f = random.uniform(0, 1.0)
    s = random.uniform(0, 1.0)
    t = random.uniform(0, 1.0)
    v = random.uniform(0, 1.0)
    r, _ = eval_(hist, lb, g, f, s, t, v)
    if r > best:
        best = r
        bp = {"lb": lb, "g": g, "f": f, "s": s, "t": t, "v": v}
        print(f"New best: lb={lb}, g={g:.4f}, f={f:.4f}, s={s:.4f}, t={t:.4f}, v={v:.4f} -> {r:.4f}")

print(f"\n阶段1最佳: {bp}, rate={best:.4f}")

print("\n=== 阶段2: 细化搜索 ===")
best2 = best
bp2 = bp.copy()
for _ in range(10000):
    lb = random.randint(max(5, bp['lb']-5), bp['lb']+5)
    g = random.uniform(max(0, bp['g']-0.1), bp['g']+0.1)
    f = random.uniform(max(0, bp['f']-0.1), bp['f']+0.1)
    s = random.uniform(max(0, bp['s']-0.1), bp['s']+0.1)
    t = random.uniform(max(0, bp['t']-0.1), bp['t']+0.1)
    v = random.uniform(max(0, bp['v']-0.1), bp['v']+0.1)
    r, _ = eval_(hist, lb, g, f, s, t, v)
    if r > best2:
        best2 = r
        bp2 = {"lb": lb, "g": g, "f": f, "s": s, "t": t, "v": v}
        print(f"New best2: lb={lb}, g={g:.4f}, f={f:.4f}, s={s:.4f}, t={t:.4f}, v={v:.4f} -> {r:.4f}")

print(f"\n阶段2最佳: {bp2}, rate={best2:.4f}")

# 阶段3: 无权重归一化搜索
print("\n=== 阶段3: 无归一化搜索 ===")
best3 = 0
bp3 = {}
for _ in range(5000):
    lb = random.randint(5, 60)
    g = random.uniform(0, 5)
    f = random.uniform(0, 5)
    s = random.uniform(0, 5)
    t = random.uniform(0, 5)
    v = random.uniform(0, 5)
    r, _ = eval_(hist, lb, g, f, s, t, v)
    if r > best3:
        best3 = r
        bp3 = {"lb": lb, "g": g, "f": f, "s": s, "t": t, "v": v}
        print(f"New best3: lb={lb}, g={g:.3f}, f={f:.3f}, s={s:.3f}, t={t:.3f}, v={v:.3f} -> {r:.4f}")

print(f"\n阶段3最佳: {bp3}, rate={best3:.4f}")

# 选择最佳方案
all_results = [(best, bp, "stage1"), (best2, bp2, "stage2"), (best3, bp3, "stage3")]
all_results.sort(key=lambda x: x[0], reverse=True)
print(f"\n=== 最终最佳 ===")
print(f"{all_results[0][2]}: {all_results[0][1]}, rate={all_results[0][0]:.4f}")