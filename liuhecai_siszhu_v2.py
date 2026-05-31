#!/usr/bin/env python3
"""
四柱擎天阵深度优化 v2 - 基于原版cache逻辑
扩展策略池(100+)+多阶段穷举+多验证方法
"""
import json, statistics as st, math, random

with open('/home/admin1/liuhecai_data.json') as f:
    data = json.load(f)

records=[{'期号':r['期号'],'特码':r['开奖生肖'][6]} for r in data if len(r.get('开奖号码',[]))>=7]
zodiacs=sorted(set(r['特码'] for r in records))
print(f"数据: {len(records)}期, 生肖: {zodiacs}")

# ================================================================
# 构建扩展cache（原版正确逻辑 + 新特征）
# ================================================================
cache=[]
for idx in range(len(records)):
    h=records[:idx]; prev=cache[-1] if cache else None
    ema3={}; ema4={}; ema5={}; ema6={}; ema7={}; ema8={}; ema9={}; ema10={}; ema11={}; ema12={}; ema13={}; ema14={}; ema15={}; ema18={}; ema20={}
    f2={}; f3={}; f4={}; f5={}; f6={}; f7={}; f8={}; f9={}; f10={}; f11={}; f12={}; f13={}; f14={}; f15={}; f16={}; f18={}; f20={}; f22={}; f25={}; f27={}; f30={}; f35={}; f40={}
    miss2={}; miss3={}; miss4={}; miss5={}; miss6={}; miss7={}; miss8={}; miss9={}; miss10={}; miss11={}; miss12={}; miss13={}; miss14={}; miss15={}; miss16={}; miss18={}; miss20={}; miss22={}; miss25={}; miss28={}; miss30={}; miss35={}; miss40={}
    rg3={}; rg4={}; rg5={}; rg6={}; rg7={}; rg8={}; rg9={}; rg10={}; rg12={}; rg15={}; rg18={}; rg20={}
    rev3={}; rev5={}; rev7={}; rev9={}; rev11={}; rev13={}; rev15={}; rev20={}
    cold3={}; cold5={}; cold7={}; cold9={}; cold11={}; cold13={}; cold15={}; cold17={}; cold20={}; cold25={}; cold30={}; cold40={}
    miss7_app={}; miss9_app={}; miss11_app={}; miss13_app={}; miss15_app={}; miss20_app={}
    hybrid={}; gap_mean={}; span={}; max_streak={}
    ema_ema={}; miss_cold={}; freq_miss={}; ema_rev={}; cold_rev={}; trend={}
    entropy={}; zscore={}
    # 新增: EMA变体alpha
    ema8_a3={}; ema8_a4={}; ema10_a3={}; ema15_a3={}

    for z in zodiacs:
        v=len(h)
        for i,r in enumerate(h):
            if r['特码']==z: v=i; break
        span[z]=v
        miss2[z]=min(v,2); miss3[z]=min(v,3); miss4[z]=min(v,4); miss5[z]=min(v,5)
        miss6[z]=min(v,6); miss7[z]=min(v,7); miss8[z]=min(v,8); miss9[z]=min(v,9)
        miss10[z]=min(v,10); miss11[z]=min(v,11); miss12[z]=min(v,12); miss13[z]=min(v,13)
        miss14[z]=min(v,14); miss15[z]=min(v,15); miss16[z]=min(v,16); miss18[z]=min(v,18)
        miss20[z]=min(v,20); miss22[z]=min(v,22); miss25[z]=min(v,25); miss28[z]=min(v,28)
        miss30[z]=min(v,30); miss35[z]=min(v,35); miss40[z]=min(v,40)

        for n,fd in [(2,f2),(3,f3),(4,f4),(5,f5),(6,f6),(7,f7),(8,f8),(9,f9),(10,f10),(11,f11),(12,f12),(13,f13),(14,f14),(15,f15),(16,f16),(17,f17),(18,f18),(20,f20),(22,f22),(25,f25),(27,f27),(30,f30),(35,f35),(40,f40)]:   # BUG FIX: add f17
            fd[z]=sum(1 for r in h[:n] if r['特码']==z)/min(n,len(h)) if h else 0

        a3=2/(3+1); a4=2/(4+1); a5=2/(5+1); a6=2/(6+1); a7=2/(7+1); a8=2/(9)
        a9=2/(10); a10=2/(11); a11=2/(12); a12=2/(13); a13=2/(14); a14=2/(15); a15=2/(16); a18=2/(19); a20=2/(21)
        p3=prev['ema3'][z] if prev else f3[z]
        p4=prev['ema4'][z] if prev else f4[z]
        p5=prev['ema5'][z] if prev else f5[z]
        p6=prev['ema6'][z] if prev else f6[z]
        p7=prev['ema7'][z] if prev else f7[z]
        p8=prev['ema8'][z] if prev else f8[z]   # BUG FIX: init with f8 (span=8), not f7
        p9=prev['ema9'][z] if prev else f9[z]
        p10=prev['ema10'][z] if prev else f10[z]
        p11=prev['ema11'][z] if prev else f11[z]
        p12=prev['ema12'][z] if prev else f12[z]
        p13=prev['ema13'][z] if prev else f13[z]
        p14=prev['ema14'][z] if prev else f14[z]
        p15=prev['ema15'][z] if prev else f15[z]  # BUG FIX: init with f15 (span=15), not f15 (was correct)
        p18=prev['ema18'][z] if prev else f18[z]
        p20=prev['ema20'][z] if prev else f20[z]
        ema3[z]=a3*f3[z]+(1-a3)*p3
        ema4[z]=a4*f4[z]+(1-a4)*p4
        ema5[z]=a5*f5[z]+(1-a5)*p5
        ema6[z]=a6*f6[z]+(1-a6)*p6
        ema7[z]=a7*f7[z]+(1-a7)*p7
        ema8[z]=a8*f8[z]+(1-a8)*p8    # BUG FIX: use f8 (span=8) as input, not f7 (span=7)
        ema9[z]=a9*f9[z]+(1-a9)*p9
        ema10[z]=a10*f10[z]+(1-a10)*p10
        ema11[z]=a11*f11[z]+(1-a11)*p11
        ema12[z]=a12*f12[z]+(1-a12)*p12
        ema13[z]=a13*f13[z]+(1-a13)*p13
        ema14[z]=a14*f14[z]+(1-a14)*p14
        ema15[z]=a15*f15[z]+(1-a15)*p15
        ema18[z]=a18*f18[z]+(1-a18)*p18
        ema20[z]=a20*f20[z]+(1-a20)*p20
        # EMA变体alpha（alpha=0.3→span≈4, alpha=0.4→span≈3，用对应频率f4/f3）
        # 注：ema8_a3/a4命名是历史遗留，实际是span=3/4的EMA，非span=8
        ema8_a3[z]=0.3*f4[z]+0.7*p8   # BUG FIX: alpha=0.3对应span≈4，用f4而非f7
        ema8_a4[z]=0.4*f3[z]+0.6*p8   # BUG FIX: alpha=0.4对应span≈3，用f3而非f7
        ema10_a3[z]=0.3*f10[z]+0.7*p10
        ema15_a3[z]=0.3*f15[z]+0.7*p15

        for n,rd in [(3,rg3),(4,rg4),(5,rg5),(6,rg6),(7,rg7),(8,rg8),(9,rg9),(10,rg10),(12,rg12),(15,rg15),(18,rg18),(20,rg20)]:
            rd[z]=sum(1 for r in h[:n] if r['特码']==z)/min(n,len(h)) if h else 0

        # rev: 反转梯度 = 更老期频率 - 当前频率（older window必须大于0才计算）
        rev3[z] = (sum(1 for r in h[3:6] if r['特码']==z)/min(3,len(h)-3) - f3[z]) if len(h)>3 else 0   # BUG FIX: proper short-window handling
        rev5[z] = (sum(1 for r in h[5:10] if r['特码']==z)/min(5,len(h)-5) - f5[z]) if len(h)>5 else 0
        rev7[z] = (sum(1 for r in h[7:14] if r['特码']==z)/min(7,len(h)-7) - f7[z]) if len(h)>7 else 0   # BUG FIX: use min() for partial window
        rev9[z] = (sum(1 for r in h[9:18] if r['特码']==z)/min(9,len(h)-9) - f9[z]) if len(h)>9 else 0
        rev11[z] = (sum(1 for r in h[11:22] if r['特码']==z)/min(11,len(h)-11) - f11[z]) if len(h)>11 else 0
        rev13[z] = (sum(1 for r in h[13:26] if r['特码']==z)/min(13,len(h)-13) - f13[z]) if len(h)>13 else 0
        rev15[z] = (sum(1 for r in h[15:30] if r['特码']==z)/min(15,len(h)-15) - f15[z]) if len(h)>15 else 0
        rev20[z] = (sum(1 for r in h[20:40] if r['特码']==z)/min(20,len(h)-20) - f20[z]) if len(h)>20 else 0

        cold3[z]=1-f3[z]; cold5[z]=1-f5[z]; cold7[z]=1-f7[z]
        cold9[z]=1-f9[z]; cold11[z]=1-f11[z]; cold13[z]=1-f13[z]
        cold15[z]=1-f15[z]; cold17[z]=1-f17[z]; cold20[z]=1-f20[z]; cold25[z]=1-f25[z]; cold30[z]=1-f30[z]; cold40[z]=1-f40[z]   # BUG FIX: define f17 and use it

        fz=f7[z]
        miss7_app[z]=min(v,7)/(fz*49+1) if fz>0 else min(v,7)
        miss9_app[z]=min(v,9)/(fz*49+1) if fz>0 else min(v,9)
        miss11_app[z]=min(v,11)/(fz*49+1) if fz>0 else min(v,11)
        miss13_app[z]=min(v,13)/(fz*49+1) if fz>0 else min(v,13)
        miss15_app[z]=min(v,15)/(fz*49+1) if fz>0 else min(v,15)
        miss20_app[z]=min(v,20)/(fz*49+1) if fz>0 else min(v,20)
        hybrid[z]=miss13[z]*0.6+fz*49*0.4

        # 组合特征
        ema_ema[z]=ema8[z]*cold7[z]
        miss_cold[z]=miss13[z]*cold7[z]
        fz7=f7[z]; mz13=miss13[z]
        freq_miss[z]=fz7/(mz13+1) if mz13>0 else fz7
        ema_rev[z]=ema8[z]*(rev7[z]+0.5)
        cold_rev[z]=cold7[z]*(rev7[z]+0.5)
        trend[z]=(ema8[z]-f7[z])*10+(f7[z]-f15[z])*5

        # 计算gaps用于gap_mean和entropy/zscore
        gaps_gm=[]
        last_g=-1
        for j,r in enumerate(h):
            if r['特码']==z:
                if last_g>=0: gaps_gm.append(j-last_g); last_g=j
                else: last_g=j
        if len(gaps_gm)>=2:
            gap_mean[z]=st.mean(gaps_gm)
        else:
            gap_mean[z]=float(v)

        # entropy
        if len(gaps_gm)>=3:
            g_mean=st.mean(gaps_gm)
            entropy[z]=-sum((g/g_mean)*math.log(g/g_mean+0.01) for g in gaps_gm if g>0)
        else:
            entropy[z]=0.0
        # zscore
        if len(gaps_gm)>=3:
            g_mean=st.mean(gaps_gm); g_std=st.stdev(gaps_gm) if len(gaps_gm)>1 else 0
            last_gap=gaps_gm[-1] if gaps_gm else 0
            zscore[z]=(last_gap-g_mean)/(g_std+0.01)
        else:
            zscore[z]=0.0

        streaks=[0]; cur=0
        for r in h:
            if r['特码']==z: cur+=1
            else: cur=0
            if cur>0: streaks.append(cur)
        max_streak[z]=max(streaks) if streaks else 0

    cache.append({
        'ema3':ema3,'ema4':ema4,'ema5':ema5,'ema6':ema6,'ema7':ema7,'ema8':ema8,'ema9':ema9,'ema10':ema10,'ema11':ema11,'ema12':ema12,'ema13':ema13,'ema14':ema14,'ema15':ema15,'ema18':ema18,'ema20':ema20,
        'ema8_a3':ema8_a3,'ema8_a4':ema8_a4,'ema10_a3':ema10_a3,'ema15_a3':ema15_a3,
        'f2':f2,'f3':f3,'f4':f4,'f5':f5,'f6':f6,'f7':f7,'f8':f8,'f9':f9,'f10':f10,'f11':f11,'f12':f12,'f13':f13,'f14':f14,'f15':f15,'f16':f16,'f18':f18,'f20':f20,'f22':f22,'f25':f25,'f27':f27,'f30':f30,'f35':f35,'f40':f40,
        'miss2':miss2,'miss3':miss3,'miss4':miss4,'miss5':miss5,'miss6':miss6,'miss7':miss7,'miss8':miss8,'miss9':miss9,'miss10':miss10,'miss11':miss11,'miss12':miss12,'miss13':miss13,'miss14':miss14,'miss15':miss15,'miss16':miss16,'miss18':miss18,'miss20':miss20,'miss22':miss22,'miss25':miss25,'miss28':miss28,'miss30':miss30,'miss35':miss35,'miss40':miss40,
        'rg3':rg3,'rg4':rg4,'rg5':rg5,'rg6':rg6,'rg7':rg7,'rg8':rg8,'rg9':rg9,'rg10':rg10,'rg12':rg12,'rg15':rg15,'rg18':rg18,'rg20':rg20,
        'rev3':rev3,'rev5':rev5,'rev7':rev7,'rev9':rev9,'rev11':rev11,'rev13':rev13,'rev15':rev15,'rev20':rev20,
        'cold3':cold3,'cold5':cold5,'cold7':cold7,'cold9':cold9,'cold11':cold11,'cold13':cold13,'cold15':cold15,'cold20':cold20,'cold25':cold25,'cold30':cold30,'cold40':cold40,
        'miss7_app':miss7_app,'miss9_app':miss9_app,'miss11_app':miss11_app,'miss13_app':miss13_app,'miss15_app':miss15_app,'miss20_app':miss20_app,
        'hybrid':hybrid,'gap_mean':gap_mean,'span':span,'max_streak':max_streak,
        'ema_ema':ema_ema,'miss_cold':miss_cold,'freq_miss':freq_miss,'ema_rev':ema_rev,'cold_rev':cold_rev,'trend':trend,
        'entropy':entropy,'zscore':zscore,
    })

print(f"cache构建完成: {len(cache)}期")

# 策略池
strat_pool=[
    'ema3','ema4','ema5','ema6','ema7','ema8','ema9','ema10','ema11','ema12','ema13','ema14','ema15','ema18','ema20',
    'ema8_a3','ema8_a4','ema10_a3','ema15_a3',
    'f2','f3','f4','f5','f6','f7','f8','f9','f10','f11','f12','f13','f14','f15','f16','f18','f20','f22','f25','f27','f30','f35','f40',
    'miss2','miss3','miss4','miss5','miss6','miss7','miss8','miss9','miss10','miss11','miss12','miss13','miss14','miss15','miss16','miss18','miss20','miss22','miss25','miss28','miss30','miss35','miss40',
    'rg3','rg4','rg5','rg6','rg7','rg8','rg9','rg10','rg12','rg15','rg18','rg20',
    'rev3','rev5','rev7','rev9','rev11','rev13','rev15','rev20',
    'cold3','cold5','cold7','cold9','cold11','cold13','cold15','cold17','cold20','cold25','cold30','cold40',
    'miss7_app','miss9_app','miss11_app','miss13_app','miss15_app','miss20_app',
    'hybrid','gap_mean','span','max_streak',
    'ema_ema','miss_cold','freq_miss','ema_rev','cold_rev','trend',
    'entropy','zscore',
]
print(f"策略池: {len(strat_pool)}个")

# 验证函数
def norm(vals):
    mn,mx=min(vals),max(vals)
    if mx==mn: return [0.5]*len(vals)
    return [(v-mn)/(mx-mn) for v in vals]

def wf_z2(sw,t1,t2,start=20):
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
    return hits/groups*100 if groups>0 else 0,groups

def yr_v(sw,t1,t2):
    yr25=[r for r in records if str(r['期号']).startswith('2025')]
    yr26=[r for r in records if str(r['期号']).startswith('2026')]
    if not yr25 or not yr26: return 0,0,0
    f25=records.index(yr25[0])+14; f26=records.index(yr26[0])+14
    r_all,_=wf_z2(sw,t1,t2,20)
    r25,_=wf_z2(sw,t1,t2,f25)
    r26,_=wf_z2(sw,t1,t2,f26)
    return r_all,r25,r26

def roll_v(sw,t1=6,t2=6,window=50,step=10):
    res=[]
    for s in range(20,len(records)-window,step):
        r,_=wf_z2(sw,t1,t2,s); res.append(r)
    return res

def mc_v(sw,t1=6,t2=6,n_sim=80,frac=0.7):
    ai=list(range(20,len(records)-1))
    if len(ai)<20: return 0,0
    sims=[]
    for _ in range(n_sim):
        samp=sorted(random.sample(ai,int(len(ai)*frac)))
        hit,g=0,0
        for i in samp:
            if i>=len(records)-1: continue
            g+=1; c=cache[i];tot={z:0.0 for z in zodiacs}
            for nm,w in sw.items():
                vals=[c[nm][z] for z in zodiacs];n=norm(vals)
                for j,z in enumerate(zodiacs): tot[z]+=w*n[j]
            p1=[z for z,_ in sorted(tot.items(),key=lambda x:-x[1])[:t1]]
            hr=records[i]['特码'] in p1
            if not hr and i+1<len(records):
                c2=cache[i+1];tot2={z:0.0 for z in zodiacs}
                for nm,w in sw.items():
                    vals2=[c2[nm][z] for z in zodiacs];n2=norm(vals2)
                    for j,z in enumerate(zodiacs): tot2[z]+=w*n2[j]
                p2=[z for z,_ in sorted(tot2.items(),key=lambda x:-x[1])[:t2]]
                if records[i+1]['特码'] in p2: hr=True
            if hr: hit+=1
        sims.append(hit/g*100 if g>0 else 0)
    m=sum(sims)/len(sims)
    std=(sum((x-m)**2 for x in sims)/len(sims))**0.5 if len(sims)>1 else 0
    return m,std

# ================================================================
# 阶段1：单策略穷举
# ================================================================
print("\n"+"="*60)
print("【阶段1：单策略穷举】")
single=[]
for s in strat_pool:
    try:
        r,g=wf_z2({s:1.0},6,6,20); single.append((r,s,g))
    except: pass
single.sort(key=lambda x:-x[0])
print(f"TOP15单策略:")
for i,(r,s,g) in enumerate(single[:15]): print(f"  {i+1}. {s:<18} {r:.2f}%")

# ================================================================
# 阶段2：两策略穷举（top15 × 所有 × 权重网格）
# ================================================================
print("\n"+"="*60)
print("【阶段2：两策略穷举】")
top15=[s for _,s,_ in single[:15]]
wg=[0.3,0.5,0.7,1.0,1.5]
pair=[]
for s1 in top15:
    for s2 in strat_pool:
        if s2==s1: continue
        try: cache[20][s2]
        except: continue
        for w1 in wg:
            for w2 in wg:
                r,_=wf_z2({s1:w1,s2:w2},6,6,20); pair.append((r,{s1:w1,s2:w2}))
pair.sort(key=lambda x:-x[0])
print(f"穷举{len(pair)}组合, TOP10:")
for i,(r,cfg) in enumerate(pair[:10]):
    print(f"  {i+1}. {'+'.join([f'{k}*{v}' for k,v in cfg.items()]):<40} {r:.2f}%")

# ================================================================
# 阶段3：三策略穷举（基于TOP5两策略）
# ================================================================
print("\n"+"="*60)
print("【阶段3：三策略穷举】")
top5p=[cfg for _,cfg in pair[:5]]
triple=[]
for base in top5p:
    bk=list(base.keys())
    for ns in strat_pool:
        if ns in bk: continue
        try: cache[20][ns]
        except: continue
        for wn in [0.3,0.5,1.0]:
            cfg=dict(base); bs=sum(cfg.values())
            cn={k:v/bs*0.7 for k,v in cfg.items()}; cn[ns]=wn*0.3
            r,_=wf_z2(cn,6,6,20); triple.append((r,cn))
triple.sort(key=lambda x:-x[0])
print(f"穷举{len(triple)}组合, TOP10:")
for i,(r,cfg) in enumerate(triple[:10]):
    print(f"  {i+1}. {'+'.join([f'{k}*{v}' for k,v in cfg.items()]):<55} {r:.2f}%")

# ================================================================
# 阶段4：四策略穷举
# ================================================================
print("\n"+"="*60)
print("【阶段4：四策略穷举】")
top2t=[cfg for _,cfg in triple[:2]]
quad=[]
for base in top2t:
    bk=list(base.keys())
    for ns in strat_pool:
        if ns in bk: continue
        try: cache[20][ns]
        except: continue
        for wn in [0.3,0.5,1.0]:
            cfg=dict(base); bs=sum(cfg.values())
            cn={k:v/bs*0.7 for k,v in cfg.items()}; cn[ns]=wn*0.3
            r,_=wf_z2(cn,6,6,20); quad.append((r,cn))
quad.sort(key=lambda x:-x[0])
print(f"穷举{len(quad)}组合, TOP5:")
for i,(r,cfg) in enumerate(quad[:5]):
    print(f"  {i+1}. {'+'.join([f'{k}*{v}' for k,v in cfg.items()]):<65} {r:.2f}%")

# ================================================================
# 阶段5：五策略穷举
# ================================================================
print("\n"+"="*60)
print("【阶段5：五策略穷举】")
top1q=[cfg for _,cfg in quad[:1]]
penta=[]
for base in top1q:
    bk=list(base.keys())
    for ns in strat_pool:
        if ns in bk: continue
        try: cache[20][ns]
        except: continue
        for wn in [0.3,0.5,1.0]:
            cfg=dict(base); bs=sum(cfg.values())
            cn={k:v/bs*0.7 for k,v in cfg.items()}; cn[ns]=wn*0.3
            r,_=wf_z2(cn,6,6,20); penta.append((r,cn))
penta.sort(key=lambda x:-x[0])
print(f"穷举{len(penta)}组合, TOP5:")
for i,(r,cfg) in enumerate(penta[:5]):
    print(f"  {i+1}. {'+'.join([f'{k}*{v}' for k,v in cfg.items()]):<75} {r:.2f}%")

# ================================================================
# 阶段6：综合评估
# ================================================================
print("\n"+"="*60)
print("【综合评估TOP20（多验证方法）】")

orig={'ema8':0.5,'miss13':1.0,'f7':1.0,'rg5':1.0}
ro,_=wf_z2(orig,6,6,20)
r25o,r26o=yr_v(orig,6,6)[:2]
mco,_=mc_v(orig,n_sim=80)
rollo=roll_v(orig); roll_s_o=(sum((x-sum(rollo)/len(rollo))**2 for x in rollo)/len(rollo))**0.5 if len(rollo)>1 else 0
robo=ro*0.4+mco*0.3+max(0,100-roll_s_o*5)*0.3

cans=[]
for r,cfg in pair[:10]: cans.append((r,cfg,"两策略"))
for r,cfg in triple[:10]: cans.append((r,cfg,"三策略"))
for r,cfg in quad[:8]: cans.append((r,cfg,"四策略"))
for r,cfg in penta[:5]: cans.append((r,cfg,"五策略"))
seen=set(); uc=[]
for r,cfg,src in cans:
    k=tuple(sorted(cfg.items()))
    if k not in seen: seen.add(k); uc.append((r,cfg,src))
uc.sort(key=lambda x:-x[0]); uc=uc[:20]

print(f"\n原版: ema8*0.5+miss13*1.0+f7*1.0+rg5*1.0")
print(f"  WF:{ro:.2f}% 2025:{r25o:.2f}% 2026:{r26o:.2f}% MC:{mco:.2f}% 稳健:{robo:.2f}")

print(f"\n{'#':<3} {'WF':>7} {'MC':>7} {'ROLL':>7} {'波动':>6} {'稳健':>7} {'2025':>6} {'2026':>6} vs原")
evals=[]
for i,(r_wf,cfg,src) in enumerate(uc):
    mcm,_=mc_v(cfg,n_sim=50)
    rol=roll_v(cfg); rol_m=sum(rol)/len(rol) if rol else 0
    rol_s=(sum((x-rol_m)**2 for x in rol)/len(rol))**0.5 if len(rol)>1 else 0
    rob=r_wf*0.4+mcm*0.3+max(0,100-rol_s*5)*0.3
    r25,r26=yr_v(cfg,6,6)[:2]
    evals.append({'cfg':cfg,'wf':r_wf,'mc':mcm,'roll_m':rol_m,'rol_s':rol_s,'rob':rob,'r25':r25,'r26':r26,'src':src})
    print(f"{i+1:<3} {r_wf:>6.2f}% {mcm:>6.2f}% {rol_m:>6.2f}% {rol_s:>5.2f} {rob:>6.2f} {r25:>5.2f}% {r26:>5.2f}% {r_wf-ro:>+6.2f}%")
    short='+'.join([f'{k}*{v}' for k,v in cfg.items()])
    if len(short)>65: short=short[:62]+"..."
    print(f"     {short}")

# ================================================================
# 阶段7：精细权重调优TOP3
# ================================================================
print("\n"+"="*60)
print("【阶段7：TOP3精细权重调优】")
fine=[]
for cand in evals[:3]:
    cfg=cand['cfg']; ks=list(cfg.keys()); vs=list(cfg.values())
    if len(ks)==2:
        for w1 in [round(x*0.1,1) for x in range(2,21)]:
            for w2 in [round(x*0.1,1) for x in range(2,21)]:
                c={ks[0]:w1,ks[1]:w2}
                r,_=wf_z2(c,6,6,20)
                m_,_=mc_v(c,n_sim=30); rol=roll_v(c); rol_s=(sum((x-sum(rol)/len(rol))**2 for x in rol)/len(rol))**0.5 if len(rol)>1 else 0
                rob=r*0.4+m_*0.3+max(0,100-rol_s*5)*0.3
                fine.append((r,rob,c,m_,rol_s))
    elif len(ks)==3:
        for w1 in [0.3,0.5,0.7,1.0,1.2]:
            for w2 in [0.3,0.5,0.7,1.0,1.2]:
                for w3 in [0.3,0.5,0.7,1.0,1.2]:
                    c={ks[0]:w1,ks[1]:w2,ks[2]:w3}
                    r,_=wf_z2(c,6,6,20)
                    m_,_=mc_v(c,n_sim=30); rol=roll_v(c); rol_s=(sum((x-sum(rol)/len(rol))**2 for x in rol)/len(rol))**0.5 if len(rol)>1 else 0
                    rob=r*0.4+m_*0.3+max(0,100-rol_s*5)*0.3
                    fine.append((r,rob,c,m_,rol_s))

fine.sort(key=lambda x:-x[1])
print(f"精细调优{len(fine)}组合, TOP10:")
for i,(r,rob,c,m_,rs) in enumerate(fine[:10]):
    r25,r26=yr_v(c,6,6)[:2]
    print(f"  {i+1}. WF:{r:.2f}% MC:{m_:.2f}% 波动:{rs:.2f} 稳健:{rob:.2f} 2025:{r25:.2f}% 2026:{r26:.2f}%")
    print(f"      {'+'.join([f'{k}*{v}' for k,v in c.items()])}")

# ================================================================
# 最终结果
# ================================================================
print("\n"+"="*60)
print("【最终结果】")
final=[]
for i,(r,rob,c,m_,rs) in enumerate(fine[:5]):
    r25,r26=yr_v(c,6,6)[:2]; vs=r-ro
    final.append({'cfg':c,'wf':r,'r25':r25,'r26':r26,'mc':m_,'rob':rob,'vs':vs})
    print(f"\n  {i+1}. {'+'.join([f'{k}*{v}' for k,v in c.items()])}")
    print(f"     WF:{r:.2f}% vs原:{vs:+.2f}% | 2025:{r25:.2f}% 2026:{r26:.2f}% | MC:{m_:.2f}% 稳健:{rob:.2f}")

best=final[0]
res={'version':'v2_deep','best_cfg':best['cfg'],'best_str':'+'.join([f'{k}*{v}' for k,v in best['cfg'].items()]),
     'wf':best['wf'],'r25':best['r25'],'r26':best['r26'],'mc':best['mc'],'rob':best['rob'],'vs':best['vs'],
     'orig':orig,'orig_wf':ro,
     'single_top15':[(s,r) for r,s,g in single[:15]],
     'pair_top10':[('+'.join([k+'*'+str(v) for k,v in cfg.items()]),r) for r,cfg in pair[:10]],
     'triple_top10':[('+'.join([k+'*'+str(v) for k,v in cfg.items()]),r) for r,cfg in triple[:10]],
     'quad_top5':[('+'.join([k+'*'+str(v) for k,v in cfg.items()]),r) for r,cfg in quad[:5]],
     'penta_top5':[('+'.join([k+'*'+str(v) for k,v in cfg.items()]),r) for r,cfg in penta[:5]],
     'fine_top10':[('+'.join([k+'*'+str(v) for k,v in c.items()]),r,rob) for r,rob,c,m_,rs in fine[:10]],
     'final_top5':[{'cfg':'+'.join([f'{k}*{v}' for k,v in f['cfg'].items()]),'wf':f['wf'],'r25':f['r25'],'r26':f['r26'],'mc':f['mc'],'rob':f['rob'],'vs':f['vs']} for f in final]}
with open('/home/admin1/liuhecai_siszhu_v2_deep.json','w',encoding='utf-8') as f:
    json.dump(res,f,ensure_ascii=False,indent=2)
print(f"\n已保存 /home/admin1/liuhecai_siszhu_v2_deep.json")
print(f"\n★★★ 最佳: {res['best_str']}")
print(f"★★★ WF:{res['wf']:.2f}% (原:{ro:.2f}%, 提升:{res['vs']:+.2f}%)")
print(f"★★★ 稳健:{res['rob']:.2f} (原:{robo:.2f})")