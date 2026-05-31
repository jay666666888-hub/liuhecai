#!/usr/bin/env python3
"""四柱擎天阵深度优化 v2 - 精简高效版"""
import json, math, random

with open('/home/admin1/liuhecai_data.json') as f:
    data = json.load(f)
records=[{'期号':r['期号'],'特码':r['开奖生肖'][6]} for r in data if len(r.get('开奖号码',[]))>=7]
zodiacs=sorted(set(r['特码'] for r in records))
print(f"{len(records)}期, {zodiacs}")

# 缓存
cache=[]
for idx in range(len(records)):
    h=records[:idx]; prev=cache[-1] if cache else None
    ema={}; f={}; miss={}; rg={}; rev={}; cold={}
    miss_app={}; hybrid={}; gap_mean={}; span={}; max_streak={}
    for z in zodiacs:
        v=len(h)
        for i,r in enumerate(h):
            if r['特码']==z: v=i; break
        span[z]=v
        miss_z={}; f_z={}
        for n in [3,5,7,9,11,13,15,20,25,30,35]:
            miss_z[f'miss{n}']=min(v,n)
        for n in [3,5,7,9,11,13,15,20,25,30,35]:
            f_z[f'f{n}']=sum(1 for r in h[:n] if r['特码']==z)/min(n,len(h)) if h else 0
        a8=2/9; a15=2/16; a10=2/11; a12=2/13; a6=2/7; a5=2/6; a3=2/4; a20=2/21
        p8=prev['ema'][z]['ema8'] if prev else f_z['f8']   # BUG FIX: init with f8 (span=8), not f7
        p15=prev['ema'][z]['ema15'] if prev else f_z['f15']  # init with f15 (span=15) ✓
        p10=prev['ema'][z]['ema10'] if prev else f_z['f10']  # BUG FIX: init with f10 (span=10), not f11
        p12=prev['ema'][z]['ema12'] if prev else f_z['f12']  # BUG FIX: init with f12 (span=12), not f13
        p6=prev['ema'][z]['ema6'] if prev else f_z['f6']    # BUG FIX: init with f6 (span=6), not f7
        p20=prev['ema'][z]['ema20'] if prev else f_z['f20']  # init with f20 ✓
        ema_z={'ema3':a3*f_z['f3']+(1-a3)*(prev['ema'][z]['ema3'] if prev else f_z['f3']),
               'ema5':a5*f_z['f5']+(1-a5)*(prev['ema'][z]['ema5'] if prev else f_z['f5']),
               'ema6':a6*f_z['f6']+(1-a6)*p6,   # BUG FIX: use p6 (initialized with f6)
               'ema8':a8*f_z['f8']+(1-a8)*p8,   # BUG FIX: use f8 (span=8), not f7
               'ema10':a10*f_z['f10']+(1-a10)*p10,  # BUG FIX: use f10 and p10 (span=10)
               'ema12':a12*f_z['f12']+(1-a12)*p12,  # BUG FIX: use f12 and p12 (span=12)
               'ema15':a15*f_z['f15']+(1-a15)*p15,
               'ema20':a20*f_z['f20']+(1-a20)*p20}
        ema[z]=ema_z; f[z]=f_z; miss[z]=miss_z
        rg_z={}; rev_z={}; cold_z={}
        for n in [3,5,7,9,11,13,15,20]:
            cold_z[f'cold{n}']=1-f_z.get(f'f{n}',0)
        for n in [3,5,7,9,11,13,15,20]:
            if len(h)>n:
                cur=sum(1 for r in h[:n] if r['特码']==z)/n
                old=sum(1 for r in h[n:n*2] if r['特码']==z)/n if len(h)>=n*2 else sum(1 for r in h[n:] if r['特码']==z)/max(1,len(h)-n)   # BUG FIX: partial window
                rev_z[f'rev{n}']=old-cur
            else: rev_z[f'rev{n}']=0
        for n in [3,5,7,9,11,13]:
            old_n=n
            if len(h)>n:
                older=sum(1 for r in h[n:n+old_n] if r['特码']==z)/min(old_n,len(h)-n) if len(h)>=n+old_n else 0
                cur=sum(1 for r in h[:n] if r['特码']==z)/min(n,len(h))
                rg_z[f'rg{n}']=older-cur
            else: rg_z[f'rg{n}']=0
        rg[z]=rg_z; rev[z]=rev_z; cold[z]=cold_z
        miss_app_z={}
        for n in [7,9,13,15]:
            fz=f_z.get(f'f{n}',0); mz=miss_z.get(f'miss{n}',0)
            miss_app_z[f'miss{n}_app']=mz/(fz*49+1) if fz>0 else mz
        miss_app[z]=miss_app_z
        fz=f_z['f7']; mz=miss_z['miss13']
        hybrid[z]=mz*0.6+fz*49*0.4
        if v>1:
            gaps=[]; last=-1
            for j,r in enumerate(h):
                if r['特码']==z:
                    if last>=0: gaps.append(j-last); last=j
            gap_mean[z]=sum(gaps)/len(gaps) if len(gaps)>=2 else float(v)
        else: gap_mean[z]=float(v)
        streaks=[0]; cur=0
        for r in h:
            if r['特码']==z: cur+=1
            else: cur=0
            if cur>0: streaks.append(cur)
        max_streak[z]=max(streaks) if streaks else 0
    cache.append({'ema':ema,'f':f,'miss':miss,'rg':rg,'rev':rev,'cold':cold,
                  'miss_app':miss_app,'hybrid':hybrid,'gap_mean':gap_mean,'span':span,'max_streak':max_streak})

def gf(i,name):
    c=cache[i]
    if name.startswith('ema'): return c['ema'][name]
    if name.startswith('f'): return {z:c['f'][z].get(name,0) for z in zodiacs}
    if name.startswith('miss') and '_app' in name: return {z:c['miss_app'][z].get(name,0) for z in zodiacs}
    if name.startswith('miss'): return {z:c['miss'][z].get(name,0) for z in zodiacs}
    if name.startswith('rg'): return {z:c['rg'][z].get(name,0) for z in zodiacs}
    if name.startswith('rev'): return {z:c['rev'][z].get(name,0) for z in zodiacs}
    if name.startswith('cold'): return {z:c['cold'][z].get(name,0) for z in zodiacs}
    if name=='hybrid': return c['hybrid']
    if name=='gap_mean': return c['gap_mean']
    if name=='span': return c['span']
    if name=='max_streak': return c['max_streak']
    raise ValueError(name)

def norm(d):
    vals=list(d.values()); mn,mx=min(vals),max(vals)
    if mx==mn: return {k:0.5 for k in d}
    return {k:(v-mn)/(mx-mn) for k,v in d.items()}

def wf(sw,t1=6,t2=6,start=20):
    g,h=0,0; i=start
    while i<len(records)-1:
        g+=1; tot={z:0.0 for z in zodiacs}
        for nm,w in sw.items():
            n=norm(gf(i,nm))
            for z in zodiacs: tot[z]+=w*n[z]
        p1=[z for z,_ in sorted(tot.items(),key=lambda x:-x[1])[:t1]]
        hit=records[i]['特码'] in p1
        if hit: h+=1; i+=1
        else:
            if i+1<len(records):
                tot2={z:0.0 for z in zodiacs}
                for nm,w in sw.items():
                    n2=norm(gf(i+1,nm))
                    for z in zodiacs: tot2[z]+=w*n2[z]
                p2=[z for z,_ in sorted(tot2.items(),key=lambda x:-x[1])[:t2]]
                if records[i+1]['特码'] in p2: h+=1
                i+=2
            else: i+=1
    return h/g*100 if g>0 else 0,g

def roll(sw,t1=6,t2=6,w=50,step=10):
    return [wf(sw,t1,t2,s)[0] for s in range(20,len(records)-w,step)]

def mc(sw,t1=6,t2=6,n=50,frac=0.7):
    ai=list(range(20,len(records)-1))
    if len(ai)<20: return 0,0
    sims=[]
    for _ in range(n):
        samp=sorted(random.sample(ai,int(len(ai)*frac)))
        hit,g=0,0
        for i in samp:
            if i>=len(records)-1: continue
            g+=1; tot={z:0.0 for z in zodiacs}
            for nm,w in sw.items():
                n=norm(gf(i,nm))
                for z in zodiacs: tot[z]+=w*n[z]
            p1=[z for z,_ in sorted(tot.items(),key=lambda x:-x[1])[:t1]]
            hit_r=records[i]['特码'] in p1
            if not hit_r and i+1<len(records):
                tot2={z:0.0 for z in zodiacs}
                for nm,w in sw.items():
                    n2=norm(gf(i+1,nm))
                    for z in zodiacs: tot2[z]+=w*n2[z]
                p2=[z for z,_ in sorted(tot2.items(),key=lambda x:-x[1])[:t2]]
                if records[i+1]['特码'] in p2: hit_r=True
            if hit_r: hit+=1
        sims.append(hit/g*100 if g>0 else 0)
    m=sum(sims)/len(sims)
    std=(sum((x-m)**2 for x in sims)/len(sims))**0.5 if len(sims)>1 else 0
    return m,std

def yr(sw,t1=6,t2=6):
    y25=[r for r in records if str(r['期号']).startswith('2025')]
    y26=[r for r in records if str(r['期号']).startswith('2026')]
    if not y25 or not y26: return 0,0,0
    f25=records.index(y25[0])+14; f26=records.index(y26[0])+14
    ra,_=wf(sw,t1,t2,20); r25,_=wf(sw,t1,t2,f25); r26,_=wf(sw,t1,t2,f26)
    return ra,r25,r26

strat_pool=['ema3','ema5','ema6','ema8','ema10','ema12','ema15','ema20']
strat_pool+=[f'f{n}' for n in [3,5,7,9,11,13,15,20,25,30,35]]
strat_pool+=[f'miss{n}' for n in [3,5,7,9,11,13,15,20,25,30,35]]
strat_pool+=[f'rg{n}' for n in [3,5,7,9,11,13]]
strat_pool+=[f'rev{n}' for n in [3,5,7,9,11,13,15]]
strat_pool+=[f'cold{n}' for n in [3,5,7,9,11,13,15,20]]
strat_pool+=[f'miss{n}_app' for n in [7,9,13,15]]
strat_pool+=['hybrid','gap_mean','span','max_streak']

# 阶段1：单策略
print("\n【阶段1】")
single=[]
for s in strat_pool:
    try: r,g=wf({s:1.0},6,6,20)
    except: continue
    single.append((r,s,g))
single.sort(key=lambda x:-x[0])
print(f"TOP15单策略:")
for i,(r,s,g) in enumerate(single[:15]): print(f"  {i+1}. {s:<15} {r:.2f}%")

# 阶段2：两策略
print("\n【阶段2】")
top10=[s for _,s,_ in single[:10]]
wg=[0.3,0.5,0.7,1.0,1.5]
pair=[]
for s1 in top10:
    for s2 in strat_pool:
        if s2==s1: continue
        try: gf(20,s2)
        except: continue
        for w1 in wg:
            for w2 in wg:
                r,_=wf({s1:w1,s2:w2},6,6,20); pair.append((r,{s1:w1,s2:w2}))
pair.sort(key=lambda x:-x[0])
print(f"穷举{len(pair)}组合, TOP10:")
for i,(r,cfg) in enumerate(pair[:10]):
    print(f"  {i+1}. {'+'.join([f'{k}*{v}' for k,v in cfg.items()]):<40} {r:.2f}%")

# 阶段3：三策略
print("\n【阶段3】")
top3p=[cfg for _,cfg in pair[:3]]
triple=[]
for base in top3p:
    bk=list(base.keys())
    for ns in strat_pool:
        if ns in bk: continue
        try: gf(20,ns)
        except: continue
        for wn in [0.3,0.5,1.0]:
            cfg=dict(base); bs=sum(cfg.values())
            cn={k:v/bs*0.7 for k,v in cfg.items()}; cn[ns]=wn*0.3
            r,_=wf(cn,6,6,20); triple.append((r,cn))
triple.sort(key=lambda x:-x[0])
print(f"穷举{len(triple)}组合, TOP10:")
for i,(r,cfg) in enumerate(triple[:10]):
    print(f"  {i+1}. {'+'.join([f'{k}*{v}' for k,v in cfg.items()]):<50} {r:.2f}%")

# 阶段4：四策略
print("\n【阶段4】")
top2t=[cfg for _,cfg in triple[:2]]
quad=[]
for base in top2t:
    bk=list(base.keys())
    for ns in strat_pool:
        if ns in bk: continue
        try: gf(20,ns)
        except: continue
        for wn in [0.3,0.5,1.0]:
            cfg=dict(base); bs=sum(cfg.values())
            cn={k:v/bs*0.7 for k,v in cfg.items()}; cn[ns]=wn*0.3
            r,_=wf(cn,6,6,20); quad.append((r,cn))
quad.sort(key=lambda x:-x[0])
print(f"穷举{len(quad)}组合, TOP5:")
for i,(r,cfg) in enumerate(quad[:5]):
    print(f"  {i+1}. {'+'.join([f'{k}*{v}' for k,v in cfg.items()]):<60} {r:.2f}%")

# 综合评估TOP15
print("\n【综合评估TOP15】")
cans=[]
for r,cfg in pair[:8]: cans.append((r,cfg,"两策略"))
for r,cfg in triple[:8]: cans.append((r,cfg,"三策略"))
for r,cfg in quad[:5]: cans.append((r,cfg,"四策略"))
seen=set(); uc=[]
for r,cfg,src in cans:
    k=tuple(sorted(cfg.items()))
    if k not in seen: seen.add(k); uc.append((r,cfg,src))
uc.sort(key=lambda x:-x[0]); uc=uc[:15]

orig={'ema8':0.5,'miss13':1.0,'f7':1.0,'rg5':1.0}
ro,_=wf(orig,6,6,20)
r25o,r26o=yr(orig)[:2]
mco,_=mc(orig,n=80)
rollo=roll(orig); roll_s_o=(sum((x-sum(rollo)/len(rollo))**2 for x in rollo)/len(rollo))**0.5 if len(rollo)>1 else 0
robo=ro*0.4+mco*0.3+max(0,100-roll_s_o*5)*0.3

print(f"\n{'#':<3} {'WF':>7} {'MC':>7} {'ROLL':>7} {'波动':>6} {'稳健':>7} {'2025':>6} {'2026':>6} vs原")
evals=[]
for i,(r_wf,cfg,src) in enumerate(uc):
    mcm,_=mc(cfg,n=50)
    rol=roll(cfg); rol_m=sum(rol)/len(rol) if rol else 0
    rol_s=(sum((x-rol_m)**2 for x in rol)/len(rol))**0.5 if len(rol)>1 else 0
    rob=r_wf*0.4+mcm*0.3+max(0,100-rol_s*5)*0.3
    r25,r26=yr(cfg)[:2]
    evals.append({'cfg':cfg,'wf':r_wf,'mc':mcm,'roll_m':rol_m,'rol_s':rol_s,'rob':rob,'r25':r25,'r26':r26,'src':src})
    print(f"{i+1:<3} {r_wf:>6.2f}% {mcm:>6.2f}% {rol_m:>6.2f}% {rol_s:>5.2f} {rob:>6.2f} {r25:>5.2f}% {r26:>5.2f}% {r_wf-ro:>+6.2f}%")
    print(f"     {'+'.join([f'{k}*{v}' for k,v in cfg.items()]):<65} {src}")

# 精细调优TOP3
print("\n【精细权重调优TOP3】")
fine=[]
for cand in evals[:3]:
    cfg=cand['cfg']; ks=list(cfg.keys()); vs=list(cfg.values())
    if len(ks)==2:
        for w1 in [round(x*0.1,1) for x in range(2,16)]:
            for w2 in [round(x*0.1,1) for x in range(2,16)]:
                c={ks[0]:w1,ks[1]:w2}
                r,_=wf(c,6,6,20)
                m_,_=mc(c,n=30); rol=roll(c); rol_s=(sum((x-sum(rol)/len(rol))**2 for x in rol)/len(rol))**0.5 if len(rol)>1 else 0
                rob=r*0.4+m_*0.3+max(0,100-rol_s*5)*0.3
                fine.append((r,rob,c,m_,rol_s))
    elif len(ks)==3:
        for w1 in [0.3,0.5,0.7,1.0,1.2]:
            for w2 in [0.3,0.5,0.7,1.0,1.2]:
                for w3 in [0.3,0.5,0.7,1.0,1.2]:
                    c={ks[0]:w1,ks[1]:w2,ks[2]:w3}
                    r,_=wf(c,6,6,20)
                    m_,_=mc(c,n=30); rol=roll(c); rol_s=(sum((x-sum(rol)/len(rol))**2 for x in rol)/len(rol))**0.5 if len(rol)>1 else 0
                    rob=r*0.4+m_*0.3+max(0,100-rol_s*5)*0.3
                    fine.append((r,rob,c,m_,rol_s))

fine.sort(key=lambda x:-x[1])
print(f"\nTOP10精细:")
for i,(r,rob,c,m_,rs) in enumerate(fine[:10]):
    r25,r26=yr(c)[:2]
    print(f"  {i+1}. WF:{r:.2f}% MC:{m_:.2f}% 波动:{rs:.2f} 稳健:{rob:.2f} 2025:{r25:.2f}% 2026:{r26:.2f}%")
    print(f"      {'+'.join([f'{k}*{v}' for k,v in c.items()])}")

# 最终输出
print("\n【最终结果】")
final=[]
for i,(r,rob,c,m_,rs) in enumerate(fine[:5]):
    r25,r26=yr(c)[:2]; vs=r-ro
    final.append({'cfg':c,'wf':r,'r25':r25,'r26':r26,'mc':m_,'rob':rob,'vs':vs})
    print(f"\n  {i+1}. {'+'.join([f'{k}*{v}' for k,v in c.items()])}")
    print(f"     WF:{r:.2f}% vs原:{vs:+.2f}% | 2025:{r25:.2f}% 2026:{r26:.2f}% | MC:{m_:.2f}% 稳健:{rob:.2f}")

best=final[0]
res={'version':'v2_deep','best_cfg':best['cfg'],'best_str':'+'.join([f'{k}*{v}' for k,v in best['cfg'].items()]),
     'wf':best['wf'],'r25':best['r25'],'r26':best['r26'],'mc':best['mc'],'rob':best['rob'],'vs':best['vs'],
     'orig':orig,'orig_wf':ro,'single_top15':[(s,r) for r,s,g in single[:15]],
     'pair_top10':[('+'.join([k+'*'+str(v) for k,v in cfg.items()]),r) for r,cfg in pair[:10]],
     'triple_top10':[('+'.join([k+'*'+str(v) for k,v in cfg.items()]),r) for r,cfg in triple[:10]],
     'quad_top5':[('+'.join([k+'*'+str(v) for k,v in cfg.items()]),r) for r,cfg in quad[:5]],
     'fine_top10':[('+'.join([k+'*'+str(v) for k,v in c.items()]),r,rob) for r,rob,c,m_,rs in fine[:10]],
     'final_top5':[{'cfg':'+'.join([f'{k}*{v}' for k,v in f['cfg'].items()]),'wf':f['wf'],'r25':f['r25'],'r26':f['r26'],'mc':f['mc'],'rob':f['rob'],'vs':f['vs']} for f in final]}
with open('/home/admin1/liuhecai_siszhu_v2_deep.json','w',encoding='utf-8') as f:
    json.dump(res,f,ensure_ascii=False,indent=2)
print(f"\n已保存 /home/admin1/liuhecai_siszhu_v2_deep.json")
print(f"\n★★★ 最佳: {res['best_str']}")
print(f"★★★ WF:{res['wf']:.2f}% (原:{ro:.2f}%, 提升:{res['vs']:+.2f}%)")
print(f"★★★ 稳健:{res['rob']:.2f} (原:{robo:.2f})")