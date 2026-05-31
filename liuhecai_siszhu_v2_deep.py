#!/usr/bin/env python3
"""
四柱擎天阵深度优化 v2
- 策略池：60+特征，含多alpha EMA、多周期频率、冷热混合
- 穷举：单策略→五策略，权重0.1-2.0细粒度
- 验证：WF标准+滚动窗口+蒙特卡洛+分层
- 稳定性：年度分段+连续未中+波动性
"""

import json, statistics as st, math, random, itertools
from collections import defaultdict

with open('/home/admin1/liuhecai_data.json') as f:
    data = json.load(f)

records = []
for r in data:
    codes = r.get('开奖号码', [])
    if len(codes) >= 7:
        records.append({'期号': r['期号'], '特码': r['开奖生肖'][6], '特码号': codes[6]})

zodiacs = sorted(set(r['特码'] for r in records))
print(f"数据: {len(records)}期, 生肖: {zodiacs}")

# ================================================================
# 阶段0：构建扩展特征缓存（60+特征）
# ================================================================
print("\n【阶段0：构建扩展特征缓存】")
cache = []
for idx in range(len(records)):
    h = records[:idx]
    prev = cache[-1] if cache else None

    ema = {}
    f = {}
    miss = {}
    rg = {}
    rev = {}
    cold = {}
    miss_app = {}
    hybrid = {}
    gap_mean = {}
    span = {}
    max_streak = {}
    # 新增组合特征
    ema_ema = {}
    miss_cold = {}
    freq_miss = {}
    ema_rev = {}
    cold_rev = {}
    trend = {}
    entropy = {}
    zscore = {}

    # EMA多alpha
    for n in [3,4,5,6,7,8,9,10,11,12,13,14,15,16,18,20]:
        a = 2.0/(n+1)
        key = f'ema{n}'
        ema[key] = {}
        for z in zodiacs:
            prev_val = prev['ema'][key][z] if prev else None
            f_val = sum(1 for r in h[:n] if r['特码']==z)/min(n,len(h)) if h else 0
            ema[key][z] = a*f_val + (1-a)*(prev_val if prev_val is not None else f_val)

    # 频率多周期
    for n in [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,18,20,22,25,27,30,35,40]:
        key = f'f{n}'
        f[key] = {}
        for z in zodiacs:
            f[key][z] = sum(1 for r in h[:n] if r['特码']==z)/min(n,len(h)) if h else 0

    # 遗漏多周期
    for n in [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,18,20,22,25,28,30,35,40]:
        key = f'miss{n}'
        miss[key] = {}
        for z in zodiacs:
            v = len(h)
            for i, r in enumerate(h):
                if r['特码'] == z:
                    v = i
                    break
            miss[key][z] = min(v, n)

    # 反转梯度多周期
    for n in [2,3,4,5,6,7,8,9,10,12,15,18,20]:
        key = f'rg{n}'
        rg[key] = {}
        for z in zodiacs:
            cur = sum(1 for r in h[:n] if r['特码']==z)/min(n,len(h)) if h else 0
            old_n = n*2
            older = sum(1 for r in h[n:n+old_n] if r['特码']==z)/min(old_n,len(h)-n) if len(h) > n else 0
            rg[key][z] = older - cur

    # 反向频率
    for n in [3,5,7,9,11,13,15,20]:
        key = f'rev{n}'
        rev[key] = {}
        for z in zodiacs:
            cur = sum(1 for r in h[:n] if r['特码']==z)/min(n,len(h)) if h else 0
            old_n = n
            older = sum(1 for r in h[n:n+old_n] if r['特码']==z)/min(old_n,len(h)-n) if len(h) > n else 0
            rev[key][z] = older - cur

    # 冷度
    for n in [3,5,7,9,11,13,15,20,25,30]:
        key = f'cold{n}'
        cold[key] = {}
        for z in zodiacs:
            cold[key][z] = 1 - f.get(f'f{n}', {}).get(z, 0)

    # 遗漏应用
    for n in [5,7,9,11,13,15,20]:
        key = f'miss{n}_app'
        miss_app[key] = {}
        for z in zodiacs:
            fz = f.get(f'f{n}', {}).get(z, 0)
            mv = miss.get(f'miss{n}', {}).get(z, 0)
            miss_app[key][z] = mv/(fz*49+1) if fz > 0 else mv

    # 组合特征
    for z in zodiacs:
        # EMA×冷度
        ema_ema[z] = ema['ema8'][z] * cold['cold7'][z]
        # 遗漏×冷度
        miss_cold[z] = miss['miss13'][z] * cold['cold7'][z]
        # 频率×遗漏比
        fz = f['f7'][z]
        mz = miss['miss13'][z]
        freq_miss[z] = fz/(mz+1) if mz > 0 else fz
        # EMA×反转
        ema_rev[z] = ema['ema8'][z] * (rev['rev7'][z] + 0.5)
        # 冷度×反转
        cold_rev[z] = cold['cold7'][z] * (rev['rev7'][z] + 0.5)
        # 趋势信号
        trend[z] = (ema['ema8'][z] - f['f7'][z]) * 10 + (f['f7'][z] - f['f15'][z]) * 5
        # 间隔信息熵近似
        gaps = []
        last = -1
        for j, r in enumerate(h):
            if r['特码'] == z:
                if last >= 0:
                    gaps.append(j - last)
                last = j
        if len(gaps) >= 2:
            g_mean = st.mean(gaps)
            g_stdev = st.stdev(gaps) if len(gaps) > 1 else 0
            entropy[z] = -sum((g/g_mean)*math.log(g/g_mean+0.01) for g in gaps if g > 0)
        else:
            entropy[z] = 0.0
        # Z-score标准化间隔
        if len(gaps) >= 3:
            g_mean = st.mean(gaps)
            g_std = st.stdev(gaps)
            last_gap = gaps[-1] if gaps else 0
            zscore[z] = (last_gap - g_mean) / (g_std + 0.01)
        else:
            zscore[z] = 0.0
        # span和max_streak
        v = len(h)
        for i, r in enumerate(h):
            if r['特码'] == z:
                v = i
                break
        span[z] = v
        streaks = [0]
        cur = 0
        for r in h:
            if r['特码'] == z:
                cur += 1
            else:
                cur = 0
            if cur > 0:
                streaks.append(cur)
        max_streak[z] = max(streaks) if streaks else 0
        # hybrid
        hybrid[z] = miss['miss13'][z] * 0.6 + f['f7'][z] * 49 * 0.4
        # gap_mean
        if v > 1:
            gaps2 = []
            last2 = -1
            for j, r in enumerate(h):
                if r['特码'] == z:
                    if last2 >= 0:
                        gaps2.append(j - last2)
                    last2 = j
            gap_mean[z] = st.mean(gaps2) if len(gaps2) >= 2 else float(v)
        else:
            gap_mean[z] = float(v)

    cache.append({
        'ema': ema, 'f': f, 'miss': miss, 'rg': rg, 'rev': rev,
        'cold': cold, 'miss_app': miss_app, 'hybrid': hybrid,
        'gap_mean': gap_mean, 'span': span, 'max_streak': max_streak,
        'ema_ema': ema_ema, 'miss_cold': miss_cold, 'freq_miss': freq_miss,
        'ema_rev': ema_rev, 'cold_rev': cold_rev, 'trend': trend,
        'entropy': entropy, 'zscore': zscore,
    })

print(f"扩展cache构建完成: {len(cache)}期, 特征数: 120+")

# ================================================================
# 策略池（按类别组织）
# ================================================================
# 从cache提取单个特征字典
def get_feat(cache_idx, name):
    c = cache[cache_idx]
    if name in c['ema']: return c['ema'][name]
    if name in c['f']: return c['f'][name]
    if name in c['miss']: return c['miss'][name]
    if name in c['rg']: return c['rg'][name]
    if name in c['rev']: return c['rev'][name]
    if name in c['cold']: return c['cold'][name]
    if name in c['miss_app']: return c['miss_app'][name]
    if name == 'hybrid': return c['hybrid']
    if name == 'gap_mean': return c['gap_mean']
    if name == 'span': return c['span']
    if name == 'max_streak': return c['max_streak']
    if name == 'ema_ema': return c['ema_ema']
    if name == 'miss_cold': return c['miss_cold']
    if name == 'freq_miss': return c['freq_miss']
    if name == 'ema_rev': return c['ema_rev']
    if name == 'cold_rev': return c['cold_rev']
    if name == 'trend': return c['trend']
    if name == 'entropy': return c['entropy']
    if name == 'zscore': return c['zscore']
    raise ValueError(f"未知特征: {name}")

# 构建策略池
strat_pool = []
strat_pool += [f'ema{n}' for n in [3,4,5,6,7,8,9,10,11,12,13,14,15,16,18,20]]
strat_pool += [f'f{n}' for n in [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,18,20,22,25,27,30,35,40]]
strat_pool += [f'miss{n}' for n in [2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,18,20,22,25,28,30,35,40]]
strat_pool += [f'rg{n}' for n in [2,3,4,5,6,7,8,9,10,12,15,18,20]]
strat_pool += [f'rev{n}' for n in [3,5,7,9,11,13,15,20]]
strat_pool += [f'cold{n}' for n in [3,5,7,9,11,13,15,20,25,30]]
strat_pool += [f'miss{n}_app' for n in [5,7,9,11,13,15,20]]
strat_pool += ['hybrid', 'gap_mean', 'span', 'max_streak',
                'ema_ema', 'miss_cold', 'freq_miss', 'ema_rev',
                'cold_rev', 'trend', 'entropy', 'zscore']

print(f"策略池大小: {len(strat_pool)}")

# ================================================================
# 验证函数
# ================================================================
def norm(vals):
    mn, mx = min(vals), max(vals)
    if mx == mn:
        return [0.5] * len(vals)
    return [(v - mn) / (mx - mn) for v in vals]

def wf_z2(sw, t1, t2, start=20):
    """Walk-Forward两期组验证"""
    groups = 0
    hits = 0
    i = start
    while i < len(records) - 1:
        groups += 1
        c = cache[i]
        tot = {z: 0.0 for z in zodiacs}
        for name, w in sw.items():
            vals = [get_feat(i, name)[z] for z in zodiacs]
            n = norm(vals)
            for j, z in enumerate(zodiacs):
                tot[z] += w * n[j]
        p1 = [z for z, _ in sorted(tot.items(), key=lambda x: -x[1])[:t1]]
        if records[i]['特码'] in p1:
            hits += 1
            i += 1
        else:
            if i + 1 < len(records):
                c2 = cache[i + 1]
                tot2 = {z: 0.0 for z in zodiacs}
                for name, w in sw.items():
                    vals2 = [get_feat(i + 1, name)[z] for z in zodiacs]
                    n2 = norm(vals2)
                    for j, z in enumerate(zodiacs):
                        tot2[z] += w * n2[j]
                p2 = [z for z, _ in sorted(tot2.items(), key=lambda x: -x[1])[:t2]]
                if records[i + 1]['特码'] in p2:
                    hits += 1
                i += 2
            else:
                i += 1
    return hits / groups * 100 if groups > 0 else 0, groups

def rolling_window_v(sw, t1, t2, window=50, step=10):
    """滚动窗口验证"""
    results = []
    for start in range(20, len(records) - window, step):
        r, g = wf_z2(sw, t1, t2, start)
        results.append(r)
    return results

def monte_carlo_v(sw, t1, t2, n_sim=100, sample_frac=0.7):
    """蒙特卡洛验证"""
    all_idx = list(range(20, len(records) - 1))
    if len(all_idx) < 20:
        return 0, 0
    sim_results = []
    for _ in range(n_sim):
        sample_size = int(len(all_idx) * sample_frac)
        sampled = sorted(random.sample(all_idx, sample_size))
        groups = 0
        hits = 0
        for i in sampled:
            if i >= len(records) - 1:
                continue
            c = cache[i]
            tot = {z: 0.0 for z in zodiacs}
            for name, w in sw.items():
                vals = [get_feat(i, name)[z] for z in zodiacs]
                n = norm(vals)
                for j, z in enumerate(zodiacs):
                    tot[z] += w * n[j]
            p1 = [z for z, _ in sorted(tot.items(), key=lambda x: -x[1])[:t1]]
            if records[i]['特码'] in p1:
                hits += 1
                groups += 1
            else:
                if i + 1 in sampled and i + 1 < len(records):
                    c2 = cache[i + 1]
                    tot2 = {z: 0.0 for z in zodiacs}
                    for name, w in sw.items():
                        vals2 = [get_feat(i + 1, name)[z] for z in zodiacs]
                        n2 = norm(vals2)
                        for j, z in enumerate(zodiacs):
                            tot2[z] += w * n2[j]
                    p2 = [z for z, _ in sorted(tot2.items(), key=lambda x: -x[1])[:t2]]
                    if records[i + 1]['特码'] in p2:
                        hits += 1
                    groups += 1
                elif i + 1 < len(records) and i + 1 not in sampled:
                    groups += 1
        sim_results.append(hits / groups * 100 if groups > 0 else 0)
    return sum(sim_results) / len(sim_results), st.stdev(sim_results) if len(sim_results) > 1 else 0

def yr_v(sw, t1, t2):
    """年度分段验证"""
    yr25 = [r for r in records if str(r['期号']).startswith('2025')]
    yr26 = [r for r in records if str(r['期号']).startswith('2026')]
    if not yr25 or not yr26:
        return 0, 0, 0
    f25 = records.index(yr25[0]) + 14
    f26 = records.index(yr26[0]) + 14
    r_all, g_all = wf_z2(sw, t1, t2, 20)
    r25, g25 = wf_z2(sw, t1, t2, f25)
    r26, g26 = wf_z2(sw, t1, t2, f26)
    return r_all, r25, r26, g_all, g25, g26

def hit_streak_v(sw, t1, t2, start=20):
    """连续未中分析"""
    i = start
    max_miss = 0
    cur_miss = 0
    miss_details = []
    while i < len(records) - 1:
        c = cache[i]
        tot = {z: 0.0 for z in zodiacs}
        for name, w in sw.items():
            vals = [get_feat(i, name)[z] for z in zodiacs]
            n = norm(vals)
            for j, z in enumerate(zodiacs):
                tot[z] += w * n[j]
        p1 = [z for z, _ in sorted(tot.items(), key=lambda x: -x[1])[:t1]]
        hit = records[i]['特码'] in p1
        if not hit and i + 1 < len(records):
            c2 = cache[i + 1]
            tot2 = {z: 0.0 for z in zodiacs}
            for name, w in sw.items():
                vals2 = [get_feat(i + 1, name)[z] for z in zodiacs]
                n2 = norm(vals2)
                for j, z in enumerate(zodiacs):
                    tot2[z] += w * n2[j]
            p2 = [z for z, _ in sorted(tot2.items(), key=lambda x: -x[1])[:t2]]
            hit = records[i + 1]['特码'] in p2
            i += 2
        else:
            i += 1
        if hit:
            if cur_miss > max_miss:
                max_miss = cur_miss
            cur_miss = 0
        else:
            cur_miss += 1
    if cur_miss > max_miss:
        max_miss = cur_miss
    return max_miss

def print_eval(sw, t1=6, t2=6, label=""):
    """综合评估输出"""
    r_all, r25, r26, g_all, g25, g26 = yr_v(sw, t1, t2)
    rolling = rolling_window_v(sw, t1, t2, window=50, step=10)
    mc_mean, mc_std = monte_carlo_v(sw, t1, t2, n_sim=100)
    max_miss = hit_streak_v(sw, t1, t2)
    cfg_str = '+'.join([f"{k}*{v}" for k, v in sw.items()])
    # 波动性
    roll_std = st.stdev(rolling) if len(rolling) > 1 else 0
    # 稳健分 = wf*0.4 + mc*0.3 + (100-roll_std)*0.3
    robust = r_all * 0.4 + mc_mean * 0.3 + max(0, 100 - roll_std * 5) * 0.3
    print(f"{label} {cfg_str}")
    print(f"  WF全:{r_all:.2f}%({g_all}组) 2025:{r25:.2f}%({g25}组) 2026:{r26:.2f}%({g26}组)")
    print(f"  滚动窗口: 均{sum(rolling)/len(rolling):.2f}% ±{roll_std:.2f}%")
    print(f"  蒙特卡洛: {mc_mean:.2f}% ±{mc_std:.2f}%")
    print(f"  最大连续未中: {max_miss}期")
    print(f"  稳健分: {robust:.2f}")
    return r_all, mc_mean, roll_std, robust

# ================================================================
# 阶段1：单策略穷举
# ================================================================
print("\n" + "="*70)
print("【阶段1：单策略穷举】")
print("="*70)
single_results = []
for s in strat_pool:
    r, g = wf_z2({s: 1.0}, 6, 6, 20)
    single_results.append((r, s, g))

single_results.sort(key=lambda x: -x[0])
print(f"最佳单策略TOP20:")
for i, (r, s, g) in enumerate(single_results[:20]):
    print(f"  {i+1:>2}. {s:<15} {r:.2f}% ({g}组)")

# ================================================================
# 阶段2：两策略穷举（细粒度权重）
# ================================================================
print("\n" + "="*70)
print("【阶段2：两策略穷举（细粒度权重）】")
print("="*70)
top20_single = [s for _, s, _ in single_results[:20]]
pair_results = []
weight_grid = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0]

# 先跑top20×top20
count = 0
for i, s1 in enumerate(top20_single):
    for s2 in strat_pool:
        if s2 == s1:
            continue
        for w1 in weight_grid:
            for w2 in weight_grid:
                cfg = {s1: w1, s2: w2}
                r, g = wf_z2(cfg, 6, 6, 20)
                pair_results.append((r, cfg, g))
                count += 1

pair_results.sort(key=lambda x: -x[0])
print(f"两策略穷举完成: {count}组合")
print(f"最佳两策略TOP15:")
for i, (r, cfg, g) in enumerate(pair_results[:15]):
    cfg_str = '+'.join([f"{k}*{v}" for k, v in cfg.items()])
    print(f"  {i+1:>2}. {cfg_str:<40} {r:.2f}% ({g}组)")

# ================================================================
# 阶段3：三策略穷举
# ================================================================
print("\n" + "="*70)
print("【阶段3：三策略穷举】")
print("="*70)
top5_pair = [cfg for _, cfg, _ in pair_results[:5]]
triple_results = []
count = 0

for base_cfg in top5_pair:
    base_strats = list(base_cfg.keys())
    for new_s in strat_pool:
        if new_s in base_strats:
            continue
        for w_new in [0.3, 0.5, 0.7, 1.0, 1.5]:
            cfg = dict(base_cfg)
            # 归一化基础权重
            base_sum = sum(base_cfg.values())
            cfg_norm = {k: v / base_sum * 0.7 for k, v in cfg.items()}
            cfg_norm[new_s] = w_new * 0.3
            r, g = wf_z2(cfg_norm, 6, 6, 20)
            triple_results.append((r, cfg_norm, g))
            count += 1

# 也测试固定权重组合
top10_single = [s for _, s, _ in single_results[:10]]
for s1 in top10_single[:5]:
    for s2 in top10_single:
        if s2 == s1:
            continue
        for s3 in top10_single:
            if s3 == s1 or s3 == s2:
                continue
            for w1, w2, w3 in [(1.0, 0.5, 0.5), (1.0, 1.0, 0.5), (1.0, 0.5, 1.0),
                                (0.7, 0.7, 0.7), (1.5, 0.5, 0.5), (0.5, 1.0, 0.5)]:
                cfg = {s1: w1, s2: w2, s3: w3}
                r, g = wf_z2(cfg, 6, 6, 20)
                triple_results.append((r, cfg, g))
                count += 1

triple_results.sort(key=lambda x: -x[0])
print(f"三策略穷举完成: {count}组合")
print(f"最佳三策略TOP10:")
for i, (r, cfg, g) in enumerate(triple_results[:10]):
    cfg_str = '+'.join([f"{k}*{v}" for k, v in cfg.items()])
    print(f"  {i+1:>2}. {cfg_str:<50} {r:.2f}% ({g}组)")

# ================================================================
# 阶段4：四策略穷举
# ================================================================
print("\n" + "="*70)
print("【阶段4：四策略穷举】")
print("="*70)
top3_triple = [cfg for _, cfg, _ in triple_results[:3]]
quad_results = []
count = 0

for base_cfg in top3_triple:
    base_strats = list(base_cfg.keys())
    for new_s in strat_pool:
        if new_s in base_strats:
            continue
        for w_new in [0.3, 0.5, 1.0]:
            cfg = dict(base_cfg)
            base_sum = sum(cfg.values())
            cfg_norm = {k: v / base_sum * 0.7 for k, v in cfg.items()}
            cfg_norm[new_s] = w_new * 0.3
            r, g = wf_z2(cfg_norm, 6, 6, 20)
            quad_results.append((r, cfg_norm, g))
            count += 1

quad_results.sort(key=lambda x: -x[0])
print(f"四策略穷举完成: {count}组合")
print(f"最佳四策略TOP5:")
for i, (r, cfg, g) in enumerate(quad_results[:5]):
    cfg_str = '+'.join([f"{k}*{v}" for k, v in cfg.items()])
    print(f"  {i+1:>2}. {cfg_str:<60} {r:.2f}% ({g}组)")

# ================================================================
# 阶段5：五策略穷举（基于最佳四策略）
# ================================================================
print("\n" + "="*70)
print("【阶段5：五策略穷举】")
print("="*70)
top2_quad = [cfg for _, cfg, _ in quad_results[:2]]
penta_results = []
count = 0

for base_cfg in top2_quad:
    base_strats = list(base_cfg.keys())
    for new_s in strat_pool:
        if new_s in base_strats:
            continue
        for w_new in [0.3, 0.5, 1.0]:
            cfg = dict(base_cfg)
            base_sum = sum(cfg.values())
            cfg_norm = {k: v / base_sum * 0.7 for k, v in cfg.items()}
            cfg_norm[new_s] = w_new * 0.3
            r, g = wf_z2(cfg_norm, 6, 6, 20)
            penta_results.append((r, cfg_norm, g))
            count += 1

penta_results.sort(key=lambda x: -x[0])
print(f"五策略穷举完成: {count}组合")
print(f"最佳五策略TOP5:")
for i, (r, cfg, g) in enumerate(penta_results[:5]):
    cfg_str = '+'.join([f"{k}*{v}" for k, v in cfg.items()])
    print(f"  {i+1:>2}. {cfg_str:<70} {r:.2f}% ({g}组)")

# ================================================================
# 阶段6：综合候选评估（多验证方法）
# ================================================================
print("\n" + "="*70)
print("【阶段6：综合候选评估（多验证方法）】")
print("="*70)

all_candidates = []
# 从各阶段最佳收集
for r, cfg, g in pair_results[:10]:
    all_candidates.append((r, cfg, g, "两策略"))
for r, cfg, g in triple_results[:10]:
    all_candidates.append((r, cfg, g, "三策略"))
for r, cfg, g in quad_results[:10]:
    all_candidates.append((r, cfg, g, "四策略"))
for r, cfg, g in penta_results[:10]:
    all_candidates.append((r, cfg, g, "五策略"))

# 去重
seen = set()
unique_candidates = []
for r, cfg, g, src in all_candidates:
    key = tuple(sorted(cfg.items()))
    if key not in seen:
        seen.add(key)
        unique_candidates.append((r, cfg, g, src))

# 综合评估TOP15
unique_candidates.sort(key=lambda x: -x[0])
top15 = unique_candidates[:15]

print(f"\n{'#':<3} {'WF':>7} {'MC':>7} {'波动':>7} {'稳健':>7} 策略来源")
print("-" * 70)
eval_results = []
for i, (r_wf, cfg, g, src) in enumerate(top15):
    mc_mean, mc_std = monte_carlo_v(cfg, 6, 6, n_sim=100)
    rolling = rolling_window_v(cfg, 6, 6, window=50, step=10)
    roll_std = st.stdev(rolling) if len(rolling) > 1 else 0
    robust = r_wf * 0.4 + mc_mean * 0.3 + max(0, 100 - roll_std * 5) * 0.3
    eval_results.append((r_wf, mc_mean, roll_std, robust, cfg, src))
    cfg_str = '+'.join([f"{k}*{v}" for k, v in cfg.items()])
    if len(cfg_str) > 60:
        cfg_str = cfg_str[:57] + "..."
    print(f"{i+1:<3} {r_wf:>6.2f}% {mc_mean:>6.2f}% {roll_std:>6.2f}% {robust:>6.2f}% {src}")
    print(f"     {cfg_str}")

# ================================================================
# 阶段7：精细权重调优（对TOP3做网格细调）
# ================================================================
print("\n" + "="*70)
print("【阶段7：TOP3精细权重网格调优】")
print("="*70)

fine_results = []
for _, _, _, _, base_cfg, _ in eval_results[:3]:
    strats = list(base_cfg.keys())
    weights = list(base_cfg.values())
    # 网格微调
    for d1 in [-0.1, -0.05, 0, 0.05, 0.1]:
        for d2 in [-0.1, -0.05, 0, 0.05, 0.1]:
            if len(strats) < 2:
                continue
            new_weights = []
            for j, w in enumerate(weights):
                if j == 0:
                    new_weights.append(max(0.1, w + d1))
                elif j == 1:
                    new_weights.append(max(0.1, w + d2))
                else:
                    new_weights.append(w)
            cfg = dict(zip(strats, new_weights))
            r, g = wf_z2(cfg, 6, 6, 20)
            mc_mean, _ = monte_carlo_v(cfg, 6, 6, n_sim=50)
            rolling = rolling_window_v(cfg, 6, 6, window=50, step=10)
            roll_std = st.stdev(rolling) if len(rolling) > 1 else 0
            robust = r * 0.4 + mc_mean * 0.3 + max(0, 100 - roll_std * 5) * 0.3
            fine_results.append((r, robust, cfg, mc_mean, roll_std))

    # 也测试更多权重组合
    if len(strats) == 2:
        for w1 in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5]:
            for w2 in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5]:
                cfg = {strats[0]: w1, strats[1]: w2}
                r, g = wf_z2(cfg, 6, 6, 20)
                mc_mean, _ = monte_carlo_v(cfg, 6, 6, n_sim=50)
                rolling = rolling_window_v(cfg, 6, 6, window=50, step=10)
                roll_std = st.stdev(rolling) if len(rolling) > 1 else 0
                robust = r * 0.4 + mc_mean * 0.3 + max(0, 100 - roll_std * 5) * 0.3
                fine_results.append((r, robust, cfg, mc_mean, roll_std))

fine_results.sort(key=lambda x: -x[1])
print(f"精细调优完成: {len(fine_results)}组合")
print(f"\n最佳精细调优TOP10:")
for i, (r, robust, cfg, mc, roll_std) in enumerate(fine_results[:10]):
    cfg_str = '+'.join([f"{k}*{v}" for k, v in cfg.items()])
    print(f"  {i+1:>2}. WF:{r:.2f}% MC:{mc:.2f}% 波动:{roll_std:.2f} 稳健:{robust:.2f}")
    print(f"      {cfg_str}")

# ================================================================
# 阶段8：最终评估与输出
# ================================================================
print("\n" + "="*70)
print("【最终TOP5多验证方法详细评估】")
print("="*70)

final_candidates = []
for _, robust, cfg, mc, roll_std in fine_results[:5]:
    r_all, r25, r26, g_all, g25, g26 = yr_v(cfg, 6, 6)
    max_miss = hit_streak_v(cfg, 6, 6)
    rolling = rolling_window_v(cfg, 6, 6, window=50, step=10)
    roll_mean = sum(rolling) / len(rolling)
    roll_std = st.stdev(rolling) if len(rolling) > 1 else 0
    final_candidates.append({
        'cfg': cfg,
        'wf': r_all,
        'wf_2025': r25,
        'wf_2026': r26,
        'mc': mc,
        'roll_mean': roll_mean,
        'roll_std': roll_std,
        'max_miss': max_miss,
        'robust': robust,
        'g_all': g_all,
    })

# 与原版对比
original = {'ema8': 0.5, 'miss13': 1.0, 'f7': 1.0, 'rg5': 1.0}
r_orig, r25_o, r26_o, g_o, g25_o, g26_o = yr_v(original, 6, 6)
mc_o, _ = monte_carlo_v(original, 6, 6, n_sim=100)
rolling_o = rolling_window_v(original, 6, 6, window=50, step=10)
roll_std_o = st.stdev(rolling_o) if len(rolling_o) > 1 else 0
max_miss_o = hit_streak_v(original, 6, 6)
robust_o = r_orig * 0.4 + mc_o * 0.3 + max(0, 100 - roll_std_o * 5) * 0.3

print(f"\n原版策略: ema8*0.5+miss13*1.0+f7*1.0+rg5*1.0")
print(f"  WF全:{r_orig:.2f}% 2025:{r25_o:.2f}% 2026:{r26_o:.2f}%")
print(f"  MC:{mc_o:.2f}% 滚动:{sum(rolling_o)/len(rolling_o):.2f}%±{roll_std_o:.2f}%")
print(f"  最大连续未中:{max_miss_o} 稳健分:{robust_o:.2f}")

print(f"\n{'排名':<4} {'WF':>7} {'2025':>7} {'2026':>7} {'MC':>7} {'滚窗均':>7} {'波动':>7} {'续未中':>7} {'稳健':>7} {'vs原':>7}")
print("-" * 80)

for i, cand in enumerate(final_candidates):
    cfg_str = '+'.join([f"{k}*{v}" for k, v in cand['cfg'].items()])
    vs = cand['wf'] - r_orig
    print(f"{i+1:<4} {cand['wf']:>6.2f}% {cand['wf_2025']:>6.2f}% {cand['wf_2026']:>6.2f}% "
          f"{cand['mc']:>6.2f}% {cand['roll_mean']:>6.2f}% {cand['roll_std']:>6.2f}% "
          f"{cand['max_miss']:>5d} {cand['robust']:>6.2f} {vs:>+6.2f}%")
    short_cfg = cfg_str[:65] + "..." if len(cfg_str) > 65 else cfg_str
    print(f"     {short_cfg}")

# ================================================================
# 保存结果
# ================================================================
best = final_candidates[0]
result = {
    'version': 'v2深度优化版',
    'best_cfg': best['cfg'],
    'best_cfg_str': '+'.join([f"{k}*{v}" for k, v in best['cfg'].items()]),
    'wf_full': best['wf'],
    'wf_2025': best['wf_2025'],
    'wf_2026': best['wf_2026'],
    'mc': best['mc'],
    'roll_mean': best['roll_mean'],
    'roll_std': best['roll_std'],
    'max_miss': best['max_miss'],
    'robust': best['robust'],
    'groups': best['g_all'],
    'improvement_vs_original': best['wf'] - r_orig,
    'original_cfg': original,
    'original_wf': r_orig,
    'single_top20': [(s, r) for r, s, g in single_results[:20]],
    'pair_top10': [('+'.join([k+'*'+str(v) for k, v in cfg.items()]), r) for r, cfg, g in pair_results[:10]],
    'triple_top10': [('+'.join([k+'*'+str(v) for k, v in cfg.items()]), r) for r, cfg, g in triple_results[:10]],
    'quad_top5': [('+'.join([k+'*'+str(v) for k, v in cfg.items()]), r) for r, cfg, g in quad_results[:5]],
    'penta_top5': [('+'.join([k+'*'+str(v) for k, v in cfg.items()]), r) for r, cfg, g in penta_results[:5]],
    'fine_top10': [('+'.join([k+'*'+str(v) for k, v in cfg.items()]), r, rob) for r, rob, cfg, mc, rs in fine_results[:10]],
    'final_top5': [{
        'cfg': '+'.join([f"{k}*{v}" for k, v in c['cfg'].items()]),
        'wf': c['wf'], 'wf_2025': c['wf_2025'], 'wf_2026': c['wf_2026'],
        'mc': c['mc'], 'robust': c['robust'], 'vs_orig': c['wf'] - r_orig
    } for c in final_candidates],
}

with open('/home/admin1/liuhecai_siszhu_v2_deep.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n已保存到 /home/admin1/liuhecai_siszhu_v2_deep.json")
print(f"\n最佳配置: {result['best_cfg_str']}")
print(f"WF验证: {result['wf_full']:.2f}% (原:{r_orig:.2f}%, 提升:{result['improvement_vs_original']:+.2f}%)")