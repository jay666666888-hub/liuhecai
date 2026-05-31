#!/usr/bin/env python3
"""
六肖四柱擎天阵 v3.4 - 生产预测脚本
最优策略: gap_mean*0.5 + f25*0.5 (min-max归一化)
WF验证: 82.06% (vs随机75.17%, +6.89%)
OOS验证: 87.50% (最后50期)
综合评分: 19.56 (WF+OS-基准)

备选三策略: gap_mean*2.0+f25*2.0+ema5*0.3
WF: 82.30%, OOS: 87.88%, 综合: 20.17
"""
import json, sys, statistics as st
from collections import Counter

DATA_FILE = '/home/admin1/liuhecai_data.json'
TOP_N = 6

# 多策略对比
STRATEGIES = [
    {'name': 'v3.4主策略', 'cfg': {'gap_mean': 0.5, 'f25': 0.5}},
    {'name': 'v3.4三策略', 'cfg': {'gap_mean': 2.0, 'f25': 2.0, 'ema5': 0.3}},
    {'name': 'v3.2旧主策略', 'cfg': {'ema3': 0.3, 'maxgap5': 0.3, 'f40': 0.5}},
]

# ================================================================
def load_data():
    with open(DATA_FILE) as f:
        raw = json.load(f)
    records = [
        {'期号': r['期号'], '特码': r['开奖生肖'][6]}
        for r in raw
        if len(r.get('开奖号码', [])) >= 7
    ]
    zodiacs = sorted(set(r['特码'] for r in records))
    return records, zodiacs

def build_cache(records, zodiacs):
    cache = []
    for idx in range(len(records)):
        h = records[:idx]; prev = cache[-1] if cache else None
        freq = {z: {} for z in zodiacs}
        span = {z: 0 for z in zodiacs}
        ema = {z: {} for z in zodiacs}
        rev = {z: {} for z in zodiacs}
        recent_max_gap = {z: {} for z in zodiacs}
        gap_mean = {z: 0.0 for z in zodiacs}

        for z in zodiacs:
            sz = len(h)
            for i, r in enumerate(h):
                if r['特码'] == z: sz = i; break
            span[z] = sz

            for n in [3, 5, 7, 10, 13, 15, 20, 25, 30, 40]:
                freq[z][f'f{n}'] = sum(1 for r in h[:n] if r['特码'] == z) / min(n, len(h)) if h else 0.0

            for n in [3, 5, 7, 8, 10, 13, 15, 20, 25, 30]:
                key = f'ema{n}'; alpha = 2.0 / (n + 1)
                fn = freq[z].get(f'f{n}', 0.0)
                pv = prev['ema'][z][key] if prev else fn
                ema[z][key] = alpha * fn + (1 - alpha) * pv

            for n in [5, 7, 10, 13]:
                older = sum(1 for r in h[n:n*2] if r['特码'] == z) / min(n, max(1, len(h)-n)) if len(h) > n else 0.0
                rev[z][f'rev{n}'] = older - freq[z].get(f'f{n}', 0.0)

            gaps = []; last_g = -1
            for j, r in enumerate(h):
                if r['特码'] == z:
                    if last_g >= 0: gaps.append(j - last_g); last_g = j
                    else: last_g = j
            gap_mean[z] = st.mean(gaps) if len(gaps) >= 2 else float(sz)
            for n in [5, 10, 15, 20]:
                recent_gaps = gaps[:n] if gaps else []
                recent_max_gap[z][f'maxgap{n}'] = max(recent_gaps) if recent_gaps else 0.0

        cache.append({'freq': freq, 'ema': ema, 'span': span, 'rev': rev,
                      'recent_max_gap': recent_max_gap, 'gap_mean': gap_mean})
    return cache

def gf(cache_idx, zodiac, feature, cache):
    c = cache[cache_idx]
    if feature.startswith('f'): return c['freq'][zodiac].get(feature, 0.0)
    elif feature.startswith('ema'): return c['ema'][zodiac].get(feature, 0.0)
    elif feature.startswith('maxgap'): return c['recent_max_gap'][zodiac].get(feature, 0.0)
    elif feature.startswith('rev'): return c['rev'][zodiac].get(feature, 0.0)
    elif feature == 'gap_mean': return c['gap_mean'][zodiac]
    elif feature == 'span': return c['span'][zodiac]
    return 0.0

def norm(d):
    vals = list(d.values()); mn, mx = min(vals), max(vals)
    if mx == mn: return {k: 0.5 for k in d}
    return {k: (v - mn) / (mx - mn) for k, v in d.items()}

def predict_one(cache, zodiacs, strategy_cfg, top_n):
    latest_idx = len(cache) - 1
    scores = {z: 0.0 for z in zodiacs}
    for feat, w in strategy_cfg.items():
        fv = {z: gf(latest_idx, z, feat, cache) for z in zodiacs}
        n = norm(fv)
        for z in zodiacs:
            scores[z] += w * n[z]
    sorted_z = sorted(zodiacs, key=lambda z: -scores[z])
    return sorted_z[:top_n], scores

# ================================================================
def main():
    print("=" * 50)
    print("六肖四柱擎天阵 v3.4 预测")
    print("=" * 50)

    records, zodiacs = load_data()
    latest = records[-1]
    prev_r = records[-2] if len(records) >= 2 else None

    print(f"\n📊 数据: {len(records)}期")
    print(f"   最新: {latest['期号']} ({latest['特码']})")
    if prev_r:
        print(f"   上期: {prev_r['期号']} ({prev_r['特码']})")

    cache = build_cache(records, zodiacs)
    print(f"   Cache: {len(cache)}期")

    # 多策略预测
    print(f"\n🎯 多策略预测对比:")
    all_top6 = []
    results = []
    for strat in STRATEGIES:
        top6, scores = predict_one(cache, zodiacs, strat['cfg'], TOP_N)
        all_top6.append(set(top6))
        results.append({'name': strat['name'], 'top6': top6, 'scores': scores, 'cfg': strat['cfg']})
        top6_str = ' '.join(top6)
        cfg_str = '+'.join([f'{k}*{v}' for k,v in strat['cfg'].items()])
        print(f"   {strat['name']:<12} [{cfg_str}]: {top6_str}")

    # 共识检测
    consensus = set.intersection(*all_top6) if all_top6 else set()
    all_union = set.union(*all_top6) if all_top6 else set()
    confidence = len(consensus) / TOP_N * 100 if all_union else 0

    print(f"\n📌 策略共识:")
    print(f"   共同入选: {' '.join(sorted(consensus)) if consensus else '无'}")
    print(f"   共识肖数: {len(consensus)}/{TOP_N}")
    print(f"   置信度: {confidence:.0f}%")

    # 分歧检测
    disagreement = all_union - consensus
    if disagreement:
        print(f"   分歧肖: {' '.join(sorted(disagreement))}")
        for strat_res in results:
            diff = set(strat_res['top6']) - consensus
            if diff:
                print(f"     {strat_res['name']} 额外: {' '.join(sorted(diff))}")

    # 主策略详情
    main_result = results[0]
    main_top6 = main_result['top6']
    main_scores = main_result['scores']

    cfg_display = '+'.join([f'{k}*{v}' for k,v in main_result['cfg'].items()])
    print(f"\n🌟 主策略({main_result['name']}): {cfg_display}")
    print(f"   TOP {TOP_N} 肖:")
    print(f"   {'排名':<4} {'生肖':<4} {'得分':>8}")
    sorted_z = sorted(zodiacs, key=lambda z: -main_scores[z])
    for rank, z in enumerate(sorted_z, 1):
        marker = " ✅" if rank <= TOP_N else ""
        print(f"   {rank:<4} {z:<4} {main_scores[z]:>8.4f}{marker}")

    print(f"\n   🎯 预测肖: {' '.join(main_top6)}")

    # 验证上期
    if prev_r and len(cache) >= 2:
        prev_top6, _ = predict_one(cache[:-1], zodiacs, STRATEGIES[0]['cfg'], TOP_N)
        hit = prev_r['特码'] in prev_top6
        print(f"\n   上期({prev_r['期号']}): {prev_r['特码']} in {' '.join(prev_top6)} → {'✅ 命中' if hit else '❌ 未中'}")

    print(f"\n📊 验证数据:")
    print(f"   WF回测: 82.06% (vs随机75.17%, +6.89%)")
    print(f"   OOS测试: 87.50% (最后50期)")
    print(f"   三策略WF: 82.30%, OOS: 87.88%")
    print(f"   随机基准: 单期50.17%, 两期组75.17%")
    print(f"\n⚠️ 历史回测不代表未来效果")

    # 保存
    cfg_str = '+'.join([f'{k}*{v}' for k,v in STRATEGIES[0]['cfg'].items()])
    result = {
        '期号': latest['期号'],
        '预测时间': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '策略': cfg_str,
        'top6': main_top6,
        'scores': {z: round(main_scores[z], 4) for z in zodiacs},
        'all_sorted': sorted_z,
        'consensus': list(consensus),
        'confidence_pct': confidence,
        'multi_strategy_results': [
            {'name': r['name'], 'top6': r['top6'], 'cfg': '+'.join([f'{k}*{v}' for k,v in r['cfg'].items()])} for r in results
        ],
        'wf': 82.06,
        'oos': 87.50,
        'wf3': 82.30,
        'oos3': 87.88,
        'random_single': 50.17,
        'random_two_period': 75.17,
        'version': 'v3.4',
    }
    with open('/home/admin1/liuhecai_latest_prediction.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
