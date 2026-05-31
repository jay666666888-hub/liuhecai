import json, statistics as st, itertools

with open('/home/admin1/liuhecai_data.json') as f:
    data = json.load(f)

records = []
for r in data:
    codes = r.get('开奖号码', [])
    if len(codes) >= 7:
        records.append({'期号': r['期号'], '特码': r['开奖生肖'][6], '特码号': codes[6]})

zodiacs = sorted(set(r['特码'] for r in records))
print(f"数据: {len(records)}期, 生肖: {zodiacs}")

# 构建cache
cache = []
for idx in range(len(records)):
    h = records[:idx]
    prev = cache[-1] if cache else None
    ema3={}; ema5={}; ema6={}; ema8={}; ema10={}; ema12={}; ema15={}
    f3={}; f4={}; f5={}; f6={}; f7={}; f8={}; f9={}; f10={}; f12={}; f15={}; f20={}; f25={}; f30={}
    miss3={}; miss5={}; miss7={}; miss9={}; miss10={}; miss11={}; miss12={}; miss13={}; miss15={}; miss18={}; miss20={}; miss25={}; miss30={}
    rg3={}; rg4={}; rg5={}; rg6={}; rg7={}; rg8={}; rg9={}; rg10={}; rg12={}; rg15={}
    rev3={}; rev5={}; rev7={}; rev10={}; rev15={}
    cold5={}; cold7={}; cold10={}; cold15={}; cold20={}; cold30={}
    miss7_app={}; miss9_app={}; miss11_app={}; miss13_app={}; miss15_app={}
    hybrid={}; gap_mean={}; span={}; max_streak={}

    for z in zodiacs:
        v = len(h)
        for i, r in enumerate(h):
            if r['特码'] == z: v = i; break
        span[z] = v
        miss3[z]=min(v,3); miss5[z]=min(v,5); miss7[z]=min(v,7)
        miss9[z]=min(v,9); miss10[z]=min(v,10); miss11[z]=min(v,11)
        miss12[z]=min(v,12); miss13[z]=min(v,13); miss15[z]=min(v,15)
        miss18[z]=min(v,18); miss20[z]=min(v,20); miss25[z]=min(v,25); miss30[z]=min(v,30)
        
        for n,fd in [(3,f3),(4,f4),(5,f5),(6,f6),(7,f7),(8,f8),(9,f9),(10,f10),(12,f12),(15,f15),(20,f20),(25,f25),(30,f30)]:
            fd[z]=sum(1 for r in h[:n] if r['特码']==z)/min(n,len(h)) if h else 0
        
        a3=2/(3+1); a5=2/(5+1); a6=2/(6+1); a8=2/(9); a10=2/(11); a12=2/(13); a15=2/(16)
        p3=prev['ema3'][z] if prev else f3[z]
        p5=prev['ema5'][z] if prev else f5[z]
        p6=prev['ema6'][z] if prev else f6[z]
        p8=prev['ema8'][z] if prev else f7[z]
        p10=prev['ema10'][z] if prev else f10[z]
        p12=prev['ema12'][z] if prev else f12[z]
        p15=prev['ema15'][z] if prev else f15[z]
        ema3[z]=a3*f3[z]+(1-a3)*p3
        ema5[z]=a5*f5[z]+(1-a5)*p5
        ema6[z]=a6*f6[z]+(1-a6)*p6
        ema8[z]=a8*f7[z]+(1-a8)*p8
        ema10[z]=a10*f10[z]+(1-a10)*p10
        ema12[z]=a12*f12[z]+(1-a12)*p12
        ema15[z]=a15*f15[z]+(1-a15)*p15
        
        for n,rd in [(3,rg3),(4,rg4),(5,rg5),(6,rg6),(7,rg7),(8,rg8),(9,rg9),(10,rg10),(12,rg12),(15,rg15)]:
            rd[z]=sum(1 for r in h[:n] if r['特码']==z)/min(n,len(h)) if h else 0
        
        if len(h)>3:
            older3=sum(1 for r in h[3:6] if r['特码']==z)/3.0 if len(h)>=6 else 0
            rev3[z]=older3-f3[z]
        else: rev3[z]=0
        if len(h)>5:
            older5=sum(1 for r in h[5:10] if r['特码']==z)/5.0 if len(h)>=10 else 0
            rev5[z]=older5-f5[z]
        else: rev5[z]=0
        if len(h)>7:
            older7=sum(1 for r in h[7:14] if r['特码']==z)/7.0 if len(h)>=14 else 0
            rev7[z]=older7-f7[z]
        else: rev7[z]=0
        if len(h)>10:
            older10=sum(1 for r in h[10:20] if r['特码']==z)/10.0 if len(h)>=20 else 0
            rev10[z]=older10-f10[z]
        else: rev10[z]=0
        if len(h)>15:
            older15=sum(1 for r in h[15:30] if r['特码']==z)/15.0 if len(h)>=30 else 0
            rev15[z]=older15-f15[z]
        else: rev15[z]=0
        
        cold5[z]=1-f5[z]; cold7[z]=1-f7[z]; cold10[z]=1-f10[z]
        cold15[z]=1-f15[z]; cold20[z]=1-f20[z]; cold30[z]=1-f30[z]
        
        fz=f7[z]
        miss7_app[z]=min(v,7)/(fz*49+1) if fz>0 else min(v,7)
        miss9_app[z]=min(v,9)/(fz*49+1) if fz>0 else min(v,9)
        miss11_app[z]=min(v,11)/(fz*49+1) if fz>0 else min(v,11)
        miss13_app[z]=min(v,13)/(fz*49+1) if fz>0 else min(v,13)
        miss15_app[z]=min(v,15)/(fz*49+1) if fz>0 else min(v,15)
        hybrid[z]=miss13[z]*0.6+fz*49*0.4
        
        if v>1:
            gaps=[]; last=-1
            for j,r in enumerate(h):
                if r['特码']==z:
                    if last>=0: gaps.append(j-last); last=j
            gap_mean[z]=st.mean(gaps) if len(gaps)>=2 else float(v)
        else:
            gap_mean[z]=float(v)
        
        streaks=[0]; cur=0
        for r in h:
            if r['特码']==z: cur+=1
            else: cur=0
            if cur>0: streaks.append(cur)
        max_streak[z]=max(streaks) if streaks else 0
    
    cache.append({
        'ema3':ema3,'ema5':ema5,'ema6':ema6,'ema8':ema8,'ema10':ema10,'ema12':ema12,'ema15':ema15,
        'f3':f3,'f4':f4,'f5':f5,'f6':f6,'f7':f7,'f8':f8,'f9':f9,'f10':f10,'f12':f12,'f15':f15,'f20':f20,'f25':f25,'f30':f30,
        'miss3':miss3,'miss5':miss5,'miss7':miss7,'miss9':miss9,'miss10':miss10,'miss11':miss11,'miss12':miss12,
        'miss13':miss13,'miss15':miss15,'miss18':miss18,'miss20':miss20,'miss25':miss25,'miss30':miss30,
        'rg3':rg3,'rg4':rg4,'rg5':rg5,'rg6':rg6,'rg7':rg7,'rg8':rg8,'rg9':rg9,'rg10':rg10,'rg12':rg12,'rg15':rg15,
        'rev3':rev3,'rev5':rev5,'rev7':rev7,'rev10':rev10,'rev15':rev15,
        'cold5':cold5,'cold7':cold7,'cold10':cold10,'cold15':cold15,'cold20':cold20,'cold30':cold30,
        'miss7_app':miss7_app,'miss9_app':miss9_app,'miss11_app':miss11_app,'miss13_app':miss13_app,'miss15_app':miss15_app,
        'hybrid':hybrid,'gap_mean':gap_mean,'span':span,'max_streak':max_streak,
    })

print(f"cache构建完成: {len(cache)}期")

def norm(vals):
    mn,mx=min(vals),max(vals)
    if mx==mn: return [0.5]*len(vals)
    return [(v-mn)/(mx-mn) for v in vals]

def wf_z2(sw, t1, t2, start=20):
    groups=0;hits=0;i=start
    while i<len(records)-1:
        groups+=1
        c=cache[i];tot={z:0.0 for z in zodiacs}
        for name,w in sw.items():
            vals=[c[name][z] for z in zodiacs];n=norm(vals)
            for j,z in enumerate(zodiacs): tot[z]+=w*n[j]
        p1=[z for z,_ in sorted(tot.items(),key=lambda x:-x[1])[:t1]]
        if records[i]['特码'] in p1: hits+=1; i+=1
        else:
            if i+1<len(records):
                c2=cache[i+1];tot2={z:0.0 for z in zodiacs}
                for name,w in sw.items():
                    vals2=[c2[name][z] for z in zodiacs];n2=norm(vals2)
                    for j,z in enumerate(zodiacs): tot2[z]+=w*n2[j]
                p2=[z for z,_ in sorted(tot2.items(),key=lambda x:-x[1])[:t2]]
                if records[i+1]['特码'] in p2: hits+=1
                i+=2
            else: i+=1
    return hits/groups*100,groups

def yr_v(sw, t1, t2):
    yr25=[r for r in records if str(r['期号']).startswith('2025')]
    yr26=[r for r in records if str(r['期号']).startswith('2026')]
    f25=records.index(yr25[0])+14
    f26=records.index(yr26[0])+14
    r_all=wf_z2(sw,t1,t2,20)[0]
    r25=wf_z2(sw,t1,t2,f25)[0]
    r26=wf_z2(sw,t1,t2,f26)[0]
    return r_all,r25,r26

# ================================================================
# 第一阶段：单策略穷举
# ================================================================
all_strats = sorted([
    'ema3','ema5','ema6','ema8','ema10','ema12','ema15',
    'f3','f4','f5','f6','f7','f8','f9','f10','f12','f15','f20','f25','f30',
    'miss3','miss5','miss7','miss9','miss10','miss11','miss12','miss13','miss15','miss18','miss20','miss25','miss30',
    'rg3','rg4','rg5','rg6','rg7','rg8','rg9','rg10','rg12','rg15',
    'rev3','rev5','rev7','rev10','rev15',
    'cold5','cold7','cold10','cold15','cold20','cold30',
    'miss7_app','miss9_app','miss11_app','miss13_app','miss15_app',
    'hybrid','gap_mean','span','max_streak',
])

print(f"策略总数: {len(all_strats)}")
print("\n【第一阶段：单策略穷举】")
best_single = 0; results_single = []
for s in all_strats:
    r,g = wf_z2({s:1.0}, 6, 6, 20)
    results_single.append((r,s,g))
    if r > best_single: best_single=r

results_single.sort(key=lambda x:-x[0])
print(f"最佳单策略前10:")
for r,s,g in results_single[:10]:
    print(f"  {s}: {r:.2f}% ({g}组)")

# ================================================================
# 第二阶段：两策略穷举
# ================================================================
print("\n【第二阶段：两策略穷举】")
best_2 = best_single; best_2_results = []

for i,s1 in enumerate(all_strats):
    for s2 in all_strats[i+1:]:
        for w1,w2 in [(1.0,0.5),(1.0,1.0),(1.5,0.5),(1.0,0.3),(0.5,1.0),(2.0,1.0)]:
            cfg = {s1:w1, s2:w2}
            r,g = wf_z2(cfg, 6, 6, 20)
            best_2_results.append((r,cfg,g))
            if r > best_2: best_2=r

best_2_results.sort(key=lambda x:-x[0])
print(f"最佳两策略前10:")
for r,cfg,g in best_2_results[:10]:
    cfg_str = '+'.join([f"{k}*{v}" for k,v in cfg.items()])
    print(f"  {cfg_str}: {r:.2f}% ({g}组)")

# ================================================================
# 第三阶段：三策略穷举
# ================================================================
print("\n【第三阶段：三策略穷举】")
top5_single = [s for _,s,_ in results_single[:5]]
best_3 = best_2; best_3_results = []
count = 0

for s1 in top5_single:
    for s2 in all_strats:
        if s2 == s1: continue
        for s3 in all_strats:
            if s3 == s1 or s3 == s2: continue
            for w1,w2,w3 in [(1.0,0.5,0.5),(1.0,1.0,0.5),(1.0,0.5,1.0),(1.0,1.0,1.0),(1.5,0.5,0.5),(1.0,0.3,0.3)]:
                cfg = {s1:w1, s2:w2, s3:w3}
                r,g = wf_z2(cfg, 6, 6, 20)
                best_3_results.append((r,cfg,g))
                if r > best_3: best_3=r

best_3_results.sort(key=lambda x:-x[0])
print(f"三策略穷举完成，最佳前5:")
for r,cfg,g in best_3_results[:5]:
    cfg_str = '+'.join([f"{k}*{v}" for k,v in cfg.items()])
    print(f"  {cfg_str}: {r:.2f}% ({g}组)")

# ================================================================
# 第四阶段：四策略穷举（基于最佳三策略扩展）
# ================================================================
print("\n【第四阶段：四策略穷举】")
top3_cfgs = [cfg for _,cfg,_ in best_3_results[:3]]
best_4 = best_3

for base_cfg in top3_cfgs:
    base_strats = list(base_cfg.keys())
    for new_s in all_strats:
        if new_s in base_strats: continue
        for w_new in [0.3, 0.5, 1.0]:
            cfg = dict(base_cfg)
            cfg[new_s] = w_new
            r,g = wf_z2(cfg, 6, 6, 20)
            if r > best_4: best_4=r; best_4_cfg=cfg

# 汇总TOP候选
print("\n【候选TOP15年度稳定性】")
all_candidates = [(r,cfg) for r,cfg,_ in best_2_results[:8]]
all_candidates += [(r,cfg) for r,cfg,_ in best_3_results[:5]]
all_candidates.sort(key=lambda x:-x[0])
top15 = all_candidates[:15]

print(f"{'#':<3} {'策略':<65} {'全量':>7} {'2025':>7} {'2026':>7}")
print("-"*90)
for i,(r_all,cfg) in enumerate(top15):
    r25,r26 = yr_v(cfg,6,6)[1:]
    cfg_str = '+'.join([f"{k}*{v}" for k,v in cfg.items()])
    print(f"{i+1:<3} {cfg_str:<65} {r_all:>6.2f}% {r25:>6.2f}% {r26:>6.2f}%")

# 最终最佳
final_cfg = top15[0][1]
r_all,r25,r26 = yr_v(final_cfg, 6, 6)
cfg_str = '+'.join([f"{k}*{v}" for k,v in final_cfg.items()])
original = {'ema8': 0.5, 'miss13': 1.0, 'f7': 1.0, 'rg5': 1.0}
r_o,r_o25,r_o26 = yr_v(original, 6, 6)

print(f"\n【最终最佳】")
print(f"  新最佳: {cfg_str}")
print(f"  全量: {r_all:.2f}%  2025: {r25:.2f}%  2026: {r26:.2f}%")
print(f"  原版: {'+'.join([k+'*'+str(v) for k,v in original.items()])}")
print(f"  全量: {r_o:.2f}%  2025: {r_o25:.2f}%  2026: {r_o26:.2f}%")
print(f"  提升: {r_all-r_o:+.2f}%")

result = {
    'final_cfg': final_cfg,
    'cfg_str': cfg_str,
    'full': r_all, '2025': r25, '2026': r26,
    'original': original,
    'original_full': r_o, 'original_2025': r_o25, 'original_2026': r_o26,
    'improvement': r_all - r_o,
    'single_top10': [(s,r) for r,s,g in results_single[:10]],
    'pair_top5': [('+'.join([k+'*'+str(v) for k,v in cfg.items()]),r) for r,cfg,g in best_2_results[:5]],
    'triple_top5': [('+'.join([k+'*'+str(v) for k,v in cfg.items()]),r) for r,cfg,g in best_3_results[:5]],
}
with open('/home/admin1/liuhecai_siszhu_optimized.json','w',encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("\n已保存到 /home/admin1/liuhecai_siszhu_optimized.json")
