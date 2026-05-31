#!/usr/bin/env python3
"""
澳门六合六肖策略监控 - 预测分布 + 置换检验
每20-30期做一次置换检验，监控预测分布漂移
"""
import json, random, math, datetime as dt
from collections import Counter
from itertools import combinations

DATA_FILE = '/home/admin1/liuhecai_data.json'
PRED_FILE = '/home/admin1/liuhecai_latest_prediction.json'
MONITOR_FILE = '/home/admin1/liuhecai_monitor.json'
HISTORY_FILE = '/home/admin1/liuhecai_prediction_history.json'

TOP_N = 6
PERMUTATION_ROUNDS = 20  # 置换检验轮数
PERMUTATION_INTERVAL = 25  # 每25期做一次置换检验

# ========== 核心预测逻辑（复用v5策略）==========

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
    N = len(zodiacs)
    z2i = {z: i for i, z in enumerate(zodiacs)}
    actuals = [r['特码'] for r in records]

    interval = [0] * N
    gap_arr = [[0.0] * N for _ in range(len(records))]
    for idx in range(len(records)):
        for j in range(N):
            gap_arr[idx][j] = float(interval[j])
        zi = z2i[actuals[idx]]
        interval[zi] = 0
        for j in range(N):
            interval[j] = min(interval[j] + 1, 999)

    for idx in range(len(records)):
        h = records[:idx]
        freq = {z: {} for z in zodiacs}
        for n in [1, 2, 3, 5, 7, 10, 15, 20, 25, 40]:
            for z in zodiacs:
                freq[z][f'f{n}'] = sum(1 for r in h[:n] if r['特码'] == z) / min(n, len(h)) if h else 0.0

        interval_raw = {z: gap_arr[idx][z2i[z]] for z in zodiacs}
        gap_ge = {z: {thresh: 1.0 if interval_raw[z] >= thresh else 0.0
                       for thresh in [6, 8, 10, 12, 14, 16, 20]
                       } for z in zodiacs}
        gwf1_g12 = {z: freq[z]['f1'] * (2.5 if interval_raw[z] >= 12 else 1.0) for z in zodiacs}

        cache.append({
            'freq': freq,
            'interval_raw': interval_raw,
            'gap_ge': gap_ge,
            'gwf1_g12': gwf1_g12,
        })
    return cache

def get_feature(idx, zodiac, feat, cache):
    c = cache[idx]
    if feat.startswith('f'):
        return c['freq'][zodiac].get(feat, 0.0)
    if feat == 'gwf1_g12':
        return c['gwf1_g12'][zodiac]
    if feat.startswith('gap_ge'):
        thresh = int(feat.split('_')[1][2:])
        return c['gap_ge'][zodiac].get(thresh, 0.0)
    if feat == 'interval_raw':
        return c['interval_raw'][zodiac]
    return 0.0

def predict_top6_scores(cfg, cache, idx, zodiacs):
    fv = {z: sum(get_feature(idx, z, k, cache) * v for k, v in cfg.items()) for z in zodiacs}
    return fv

def predict_top6(cfg, cache, idx, zodiacs):
    nf = predict_top6_scores(cfg, cache, idx, zodiacs)
    return sorted(zodiacs, key=lambda z: -nf[z])[:6]

# ========== 监控功能 ==========

def calc_entropy(counts, total):
    """计算分布熵（越高越分散）"""
    probs = [c / total for c in counts if c > 0]
    return -sum(p * math.log2(p) for p in probs if p > 0)

def prediction_distribution_monitor(pred_history, zodiacs, window=50):
    """监控预测分布是否漂移（是否越来越集中于某几个生肖）"""
    if len(pred_history) < 10:
        return None

    recent = pred_history[-window:] if len(pred_history) >= window else pred_history

    # 统计各生肖被预测次数
    dist = Counter()
    for p in recent:
        for z in p['top6']:
            dist[z] += 1

    total_choices = len(recent) * 6
    n_zodiac = len(zodiacs)
    expected_per_zodiac = total_choices / n_zodiac

    # 计算分散度指标
    counts = [dist.get(z, 0) for z in zodiacs]
    entropy = calc_entropy(counts, total_choices)
    max_count = max(counts)
    min_count = min(counts)
    concentration_ratio = max_count / expected_per_zodiac  # 集中度（1.0=均匀，越高越集中）

    # 找出过度预测和过低预测的生肖
    over_pred = [z for z in zodiacs if dist.get(z, 0) > expected_per_zodiac * 1.3]
    under_pred = [z for z in zodiacs if dist.get(z, 0) < expected_per_zodiac * 0.7]

    return {
        'entropy': round(entropy, 3),
        'concentration_ratio': round(concentration_ratio, 2),
        'max_count': max_count,
        'min_count': min_count,
        'over_predicted': over_pred,
        'under_predicted': under_pred,
        'distribution': dict(dist),
        'window': len(recent),
    }

def permutation_test(cfg, cache, records, zodiacs, start=30, n_rounds=20):
    """
    置换检验：打乱特码序列，对比真实命中率与随机基准
    """
    # 限制样本量以提高效率
    end_idx = min(len(records), start + 150)
    if end_idx - start < 80:
        return None  # 样本太少

    actuals = [r['特码'] for r in records[start:end_idx]]

    # 真实命中率
    real_hits = sum(
        1 for i in range(start, end_idx)
        if records[i]['特码'] in predict_top6(cfg, cache, i, zodiacs)
    )
    real_rate = real_hits / (end_idx - start) * 100

    # 随机打乱N轮
    perm_rates = []
    for _ in range(n_rounds):
        shuffled = actuals.copy()
        random.shuffle(shuffled)
        # 临时替换特码（不修改原始数据，只是模拟）
        orig = [r['特码'] for r in records[start:end_idx]]
        for i, r in enumerate(records[start:end_idx]):
            r['特码'] = shuffled[i]
        # 重新计算命中率
        fake_hits = sum(
            1 for i in range(start, end_idx)
            if records[i]['特码'] in predict_top6(cfg, cache, i, zodiacs)
        )
        perm_rates.append(fake_hits / (end_idx - start) * 100)
        # 恢复
        for i, r in enumerate(records[start:end_idx]):
            r['特码'] = orig[i]

    avg_perm = sum(perm_rates) / len(perm_rates)
    advantage = real_rate - avg_perm

    return {
        'real_rate': round(real_rate, 2),
        'perm_avg': round(avg_perm, 2),
        'perm_rates': [round(r, 2) for r in perm_rates],
        'advantage': round(advantage, 2),
        'sample_size': end_idx - start,
        'n_rounds': n_rounds,
        'verdict': '有真实预测能力' if advantage > 8 else ('边缘' if advantage > 3 else '接近随机'),
    }

def load_monitor_history():
    if os.path.exists(MONITOR_FILE):
        with open(MONITOR_FILE) as f:
            return json.load(f)
    return {'runs': [], 'last_permutation': 0}

import os

def save_monitor(monitor):
    with open(MONITOR_FILE, 'w', encoding='utf-8') as f:
        json.dump(monitor, f, ensure_ascii=False, indent=2)

def main():
    cfg = {'gwf1_g12': 0.1, 'gap_ge10': 0.1, 'gap_ge16': 0.8}
    records, zodiacs = load_data()
    cache = build_cache(records, zodiacs)

    monitor = load_monitor_history()
    now = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total_periods = len(records)

    # 1. 加载预测历史
    pred_history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, encoding='utf-8') as f:
            pred_history = json.load(f)

    # 2. 预测分布监控
    dist_result = prediction_distribution_monitor(pred_history, zodiacs)

    # 3. 置换检验（每25期一次）
    needs_perm_test = (total_periods - monitor.get('last_permutation', 0)) >= PERMUTATION_INTERVAL
    perm_result = None
    if needs_perm_test:
        perm_result = permutation_test(cfg, cache, records, zodiacs, n_rounds=PERMUTATION_ROUNDS)
        monitor['last_permutation'] = total_periods

    # 4. 汇总结果
    run = {
        'time': now,
        'total_periods': total_periods,
        'dist': dist_result,
        'perm': perm_result,
    }
    monitor['runs'].append(run)

    # 只保留最近20次监控记录
    monitor['runs'] = monitor['runs'][-20:]

    save_monitor(monitor)

    # 输出摘要
    print(f"\n{'='*55}")
    print(f"  澳门六合策略监控报告")
    print(f"  {now}")
    print(f"{'='*55}")
    print(f"\n📊 数据量: {total_periods}期")

    if dist_result:
        print(f"\n🔍 预测分布监控 (近{dist_result['window']}期):")
        print(f"   熵值: {dist_result['entropy']} (越高越分散)")
        print(f"   集中度: {dist_result['concentration_ratio']}x (1.0=均匀)")
        print(f"   过度预测: {dist_result['over_predicted']}")
        print(f"   过低预测: {dist_result['under_predicted']}")
        print(f"   最多: {dist_result['max_count']}次 最少: {dist_result['min_count']}次")
    else:
        print(f"\n🔍 预测分布: 数据不足（{len(pred_history)}期）")

    if perm_result:
        print(f"\n🎲 置换检验 ({perm_result['sample_size']}期样本, {perm_result['n_rounds']}轮):")
        print(f"   真实命中率: {perm_result['real_rate']}%")
        print(f"   随机基准: {perm_result['perm_avg']}%")
        print(f"   优势差值: +{perm_result['advantage']}%")
        print(f"   结论: {perm_result['verdict']}")
    elif needs_perm_test:
        print(f"\n🎲 置换检验: 样本不足")
    else:
        print(f"\n🎲 置换检验: 距上次{monitor.get('last_permutation',0)}期，还需{PERMUTATION_INTERVAL - (total_periods - monitor.get('last_permutation', 0))}期")

    print(f"\n{'='*55}")

    return monitor

if __name__ == '__main__':
    main()
