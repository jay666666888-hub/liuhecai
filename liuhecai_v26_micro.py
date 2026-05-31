#!/usr/bin/env python3
"""
V26 平特一肖 - 微观搜索
"""
import sys, random
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from predictor.data_fetcher import get_all_records, build_standard_records

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

def eval_(history, lb, g, f, s, t, v):
    n = len(history)
    if n < lb + 5:
        return 0
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
    return h/t_ if t_>0 else 0

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f"数据: {len(hist)}期")

best = 0
bp = {}

# 极小范围搜索
print("=== 微观搜索(500次) ===")
for _ in range(500):
    lb = random.randint(5, 50)
    g = random.uniform(-0.3, 1.2)
    f = random.uniform(-0.3, 1.2)
    s = random.uniform(-0.2, 0.6)
    t = random.uniform(-0.3, 1.2)
    v = random.uniform(-0.3, 1.2)
    r = eval_(hist, lb, g, f, s, t, v)
    if r > best:
        best = r
        bp = {"lb": lb, "g": g, "f": f, "s": s, "t": t, "v": v}
        print(f"New: lb={lb}, g={g:.3f}, f={f:.3f}, s={s:.3f}, t={t:.3f}, v={v:.3f} -> {r:.4f}")

print(f"\n最佳: {bp}, rate={best:.4f}")
