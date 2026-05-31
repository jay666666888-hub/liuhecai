#!/usr/bin/env python3
"""
六肖四柱擎天阵 v3.3 - Percentile归一化穷举
关键改进：percentile归一化（81.31%）vs minmax（80.98%）
"""
import json, math, random, statistics as st
from collections import Counter

DATA_FILE = '/home/admin1/liuhecai_data.json'
RANDOM_SINGLE = 50.17
RANDOM_TWO_PERIOD = 75.17

with open(DATA_FILE) as f:
    raw = json.load(f)
records=[{'期号':r['期号'],'特码':r['开奖生肖'][6]} for r in raw if len(r.get('开奖号码',[]))>=7]
zodiacs=sorted(set(r['特码'] for r in records))

print(f"{'='*60}")
print(f"六肖四柱擎天阵 v3.3 - Percentile归一化穷举")
print(f"{'='*60}")
print(f"数据: {len(records)}期, 随机基准: {RANDOM_TWO_PERIOD:.2f}%")

# ================================================================
# Cache
# ================================================================
def build_cache():
    cache=[]
    for idx in range(len(records)):
        h=records[:idx]; prev=cache[-1] if cache else None
        freq={z:{} for z in zodiacs}; span={z:0 for z in zodiacs}
        ema={z:{} for z in zodiacs}; recent_max_gap={z:{} for z in zodiacs}
        rev={z:{} for z in zodiacs}; gap_mean={z:0.0 for z in zodiacs}
        stretch={z:0.0 for z in zodiacs}

        for z in zodiacs:
            sz=len(h)
            for i,r in enumerate(h):
                if r['特码']==z: sz=i; break
            span[z]=sz
            for n in [3,5,7,10,13,15,20,25,30,40]:
                freq[z][f'f{n}']=sum(1 for r in h[:n] if r['特码']==z)/min(n,len(h)) if h else 0.0
            for n in [3,5,7,8,10,13,15,20,25,30]:
                key=f'ema{n}'; alpha=2.0/(n+1); fn=freq[z].get(f'f{n}',0.0)
                pv=prev['ema'][z][key] if prev else fn
                ema[z][key]=alpha*fn+(1-alpha)*pv
            gaps=[]; last_g=-1
            for j,r in enumerate(h):
                if r['特码']==z:
                    if last_g>=0: gaps.append(j-last_g); last_g=j
                    else: last_g=j
            gm=st.mean(gaps) if len(gaps)>=2 else float(sz)
            gap_mean[z]=gm
            stretch[z]=sz/(gm+0.1)
            for n in [5,10,15,20]:
                rg=gaps[:n] if gaps else []
                recent_max_gap[z][f'maxgap{n}']=max(rg) if rg else 0.0
            for n in [5,7,10,13]:
                older=sum(1 for r in h[n:n*2] if r['特码']==z)/min(n,max(1,len(h)-n)) if len(h)>n else 0.0
                rev[z][f'rev{n}']=older-freq[z].get(f'f{n}',0.0)
        cache.append({'freq':freq,'ema':ema,'span':span,'recent_max_gap':recent_max_gap,'rev':rev,'gap_mean':gap_mean,'stretch':stretch})
    return cache

cache=build_cache()
print(f"Cache: {len(cache)}期")

def gf(i,z,feat):
    c=cache[i]
    if feat.startswith('f'): return c['freq'][z].get(feat,0.0)
    elif feat.startswith('ema'): return c['ema'][z].get(feat,0.0)
    elif feat.startswith('maxgap'): return c['recent_max_gap'][z].get(feat,0.0)
    elif feat.startswith('rev'): return c['rev'][z].get(feat,0.0)
    elif feat=='gap_mean': return c['gap_mean'][z]
    elif feat=='span': return c['span'][z]
    elif feat=='stretch': return c['stretch'][z]
    return 0.0

def norm_minmax(d):
    vals=list(d.values()); mn,mx=min(vals),max(vals)
    if mx==mn: return {k:0.5 for k in d}
    return {k:(v-mn)/(mx-mn) for k,v in d.items()}

def norm_percentile(d):
    vals=sorted(d.values()); n=len(vals)
    result={}
    for k,v in d.items():
        result[k]=(sum(1 for x in vals if x<v)+0.5*(sum(1 for x in vals if x==v)))/n
    return result

def top_n(scores,n): return [z for z,_ in sorted(scores.items(),key=lambda x:-x[1])[:n]]

# 支持混合归一化
def norm_of(d, fn):
    return fn(d)

def wf(cfg, norm_map=None, start=20):
    if norm_map is None:
        norm_map={}
    groups=hits=0; i=start
    while i<len(records)-1:
        groups+=1
        scores1={z:0.0 for z in zodiacs}
        for feat,w in cfg.items():
            fv={z:gf(i,z,feat) for z in zodiacs}
            nf=norm_map.get(feat, norm_minmax)
            n=norm_of(fv,nf)
            for z in zodiacs: scores1[z]+=w*n[z]
        p1=top_n(scores1,6)
        if records[i]['特码'] in p1: hits+=1; i+=1
        else:
            if i+1<len(records):
                scores2={z:0.0 for z in zodiacs}
                for feat,w in cfg.items():
                    fv2={z:gf(i+1,z,feat) for z in zodiacs}
                    nf2=norm_map.get(feat, norm_minmax)
                    n2=norm_of(fv2,nf2)
                    for z in zodiacs: scores2[z]+=w*n2[z]
                p2=top_n(scores2,6)
                if records[i+1]['特码'] in p2: hits+=1
            i+=2
    return (hits/groups*100 if groups>0 else 0.0, groups)

def annual(cfg, norm_map=None):
    idx25=next((i for i,r in enumerate(records) if r['期号']=='2025001'),None)
    idx26=next((i for i,r in enumerate(records) if r['期号']=='2026001'),None)
    s25=max(20,(idx25 or 0)+20) if idx25 is not None else 20
    s26=max(20,(idx26 or 0)+20) if idx26 is not None else 20
    ov,_=wf(cfg,norm_map,20)
    y25,_=wf(cfg,norm_map,s25) if idx25 is not None else (0,0)
    y26,_=wf(cfg,norm_map,s26) if idx26 is not None else (0,0)
    return ov,y25,y26

def last50(cfg, norm_map=None):
    return wf(cfg,norm_map,max(20,len(records)-50))[0]

def roll(cfg, norm_map=None):
    res=[wf(cfg,norm_map,s)[0] for s in range(20,len(records)-50,10)]
    m=sum(res)/len(res) if res else 0
    std=(sum((x-m)**2 for x in res)/len(res))**0.5 if len(res)>1 else 0
    return m,std

# ================================================================
# 策略池
# ================================================================
POOL=[]
POOL+=[f'ema{n}' for n in [3,5,7,8,10,13,15,20,25,30]]
POOL+=[f'f{n}' for n in [3,5,7,10,13,15,20,25,30,40]]
POOL+=['gap_mean','span','stretch']
POOL+=[f'rev{n}' for n in [5,7,10,13,15]]
POOL+=[f'maxgap{n}' for n in [5,10,15,20]]

def independent(s1,s2):
    if s1==s2: return False
    for n in [3,5,7,8,10,13,15,20,25,30]:
        if s1==f'ema{n}' and s2==f'f{n}': return False
        if s2==f'ema{n}' and s1==f'f{n}': return False
    return True

print(f"策略池: {len(POOL)}特征")

# ================================================================
# 单策略穷举
# ================================================================
print(f"\n[1/4] 单策略穷举(percentile)...")
single=[]
for s in POOL:
    try:
        r,g=wf({s:1.0},{'*':norm_percentile},20)
        if g>200: single.append((r,s,g))
    except: pass
single.sort(key=lambda x:-x[0])

print(f"  TOP15单策略:")
for i,(r,s,g) in enumerate(single[:15]):
    lift=r-RANDOM_TWO_PERIOD
    print(f"    {i+1:>2}. {s:<12} {r:>6.2f}% ({lift:+.2f}%)")

# ================================================================
# 两策略穷举(percentile)
# ================================================================
print(f"\n[2/4] 两策略穷举(percentile)...")
top10=[s for _,s,_ in single[:10]]
wg=[0.3,0.5,0.7,1.0,1.5,2.0]
pct_map={'*':norm_percentile}

pair=[]
for s1 in top10:
    for s2 in POOL:
        if not independent(s1,s2): continue
        for w1 in wg:
            for w2 in wg:
                cfg={s1:w1,s2:w2}
                try:
                    r,_=wf(cfg,pct_map,20)
                    pair.append((r,cfg))
                except: pass

pair.sort(key=lambda x:-x[0])
print(f"  穷举{len(pair)}组合, TOP20:")

print(f"  {'#':<3} {'WF%':>7} {'vs随机':>8} {'2025':>7} {'2026':>7} {'ROLL均值':>9} {'波动':>7} {'最后50':>8} 配置")
print(f"  {'-'*85}")

evals=[]
for i,(r,cfg) in enumerate(pair[:25]):
    ov,y25,y26=annual(cfg,pct_map)
    rm,rs=roll(cfg,pct_map)
    l50=last50(cfg,pct_map)
    lift=r-RANDOM_TWO_PERIOD
    cfg_str='+'.join([f'{k}*{v}' for k,v in cfg.items()])
    if len(cfg_str)>55: cfg_str=cfg_str[:52]+'...'
    print(f"  {i+1:<3} {r:>6.2f}% {lift:>+7.2f}% {y25:>6.2f}% {y26:>6.2f}% {rm:>8.2f}% {rs:>6.2f} {l50:>7.2f}% {cfg_str}")
    evals.append({'cfg':cfg,'wf':r,'ov':ov,'y25':y25,'y26':y26,'rm':rm,'rs':rs,'l50':l50,'nmap':dict(pct_map)})

# ================================================================
# 三策略穷举
# ================================================================
print(f"\n[3/4] 三策略穷举...")
top5pairs=[pair[i][1] for i in range(min(10,len(pair)))]
triple=[]
for base in top5pairs:
    s1,s2=list(base.keys())[:2]
    for s3 in POOL:
        if s3 in (s1,s2): continue
        if not independent(s1,s3) or not independent(s2,s3): continue
        for w in [0.3,0.5,0.7,1.0]:
            cfg={s1:base[s1],s2:base[s2],s3:w}
            try:
                r,_=wf(cfg,pct_map,20)
                triple.append((r,cfg))
            except: pass

triple.sort(key=lambda x:-x[0])
print(f"  三策略TOP10:")
for i,(r,cfg) in enumerate(triple[:10]):
    lift=r-RANDOM_TWO_PERIOD
    cfg_str='+'.join([f'{k}*{v}' for k,v in cfg.items()])
    if len(cfg_str)>55: cfg_str=cfg_str[:52]+'...'
    print(f"    {i+1:>2}. {r:>6.2f}% ({lift:+.2f}%) {cfg_str}")

# ================================================================
#稳健性评分
# ================================================================
print(f"\n[4/4] 稳健性评估...")

all_evals=evals.copy()
for i,(r,cfg) in enumerate(triple[:15]):
    ov,y25,y26=annual(cfg,pct_map)
    rm,rs=roll(cfg,pct_map)
    l50=last50(cfg,pct_map)
    all_evals.append({'cfg':cfg,'wf':r,'ov':ov,'y25':y25,'y26':y26,'rm':rm,'rs':rs,'l50':l50,'nmap':dict(pct_map)})

R=RANDOM_TWO_PERIOD
def rob(ev):
    wf_rel=max(0,ev['wf']-R)/10*0.25
    y25_rel=max(0,ev['y25']-R)/10*0.15
    y26_rel=max(0,ev['y26']-R)/10*0.15
    l50_rel=max(0,ev.get('l50',0)-R)/10*0.25
    roll_penalty=ev['rs']/5*0.10
    return wf_rel+y25_rel+y26_rel+l50_rel-roll_penalty

for ev in all_evals:
    ev['rob']=rob(ev)
all_evals.sort(key=lambda x:-x['rob'])

print(f"\n  稳健性TOP15:")
print(f"  {'#':<3} {'WF%':>7} {'2025':>7} {'2026':>7} {'最后50':>8} {'波动':>7} {'稳健分':>8} 配置")
print(f"  {'-'*85}")
for i,ev in enumerate(all_evals[:15]):
    cfg_str='+'.join([f'{k}*{v}' for k,v in ev['cfg'].items()])
    if len(cfg_str)>55: cfg_str=cfg_str[:52]+'...'
    print(f"  {i+1:<3} {ev['wf']:>6.2f}% {ev['y25']:>6.2f}% {ev['y26']:>6.2f}% {ev.get('l50',0):>7.2f}% {ev['rs']:>6.2f} {ev['rob']:>7.4f} {cfg_str}")

BEST=all_evals[0]
BEST_STR='+'.join([f'{k}*{v}' for k,v in BEST['cfg'].items()])

print(f"\n{'='*60}")
print(f"★★★ v3.3 最终选定策略 ★★★")
print(f"{'='*60}")
print(f"  归一化: Percentile (所有特征)")
print(f"  配置: {BEST_STR}")
print(f"  WF:   {BEST['wf']:.2f}% (vs随机{R:.2f}%, +{BEST['wf']-R:.2f}%)")
print(f"  2025: {BEST['y25']:.2f}%")
print(f"  2026: {BEST['y26']:.2f}%")
print(f"  最后50期: {BEST.get('l50',0):.2f}%")
print(f"  滚动波动: {BEST['rs']:.2f}%")

# 保存
result={
    'version':'v3.3_percentile',
    'best_cfg':BEST['cfg'],
    'best_str':BEST_STR,
    'wf':BEST['wf'],
    'y25':BEST['y25'],
    'y26':BEST['y26'],
    'last50':BEST.get('l50',0),
    'roll_mean':BEST['rm'],
    'roll_std':BEST['rs'],
    'robust_score':BEST['rob'],
    'random_single':RANDOM_SINGLE,
    'random_two_period':RANDOM_TWO_PERIOD,
    'norm':'percentile',
    'total':len(records),
    'single_top15':[(s,r) for r,s,g in single[:15]],
}
with open('/home/admin1/liuhecai_siszhu_v3_result.json','w',encoding='utf-8') as f:
    json.dump(result,f,ensure_ascii=False,indent=2)
print(f"\n✅ 已保存")
print(f"\n⚠️ 历史回测不代表未来效果")
