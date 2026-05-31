#!/usr/bin/env python3
"""用V7排名法批量回填全部历史预测，不覆盖已有记录"""
import json
from datetime import datetime

ZODIACS = ['鼠','牛','虎','兔','龍','蛇','馬','羊','猴','雞','狗','豬']

# 最优策略参数（来自skill）
WEIGHTS = {'gap': 2.7, 'recent3': 2.8, 'recent10': 0.8, 'recent30': 3.0}

def build_cache(records, idx):
    """计算指定idx时刻的各生肖特征"""
    cache = {}
    for z in ZODIACS:
        gap_list = []
        for i in range(idx-1, -1, -1):
            if records[i]['开奖生肖'][6] == z:
                gap_list.append(idx - i)
            if len(gap_list) >= 30:
                break
        cache[z] = {
            'gap': idx - records[idx-1]['idx'] if idx > 0 else 999 if records[idx-1]['开奖生肖'][6] == z else idx+1,
        }
    # gap: 距今多少期
    h = [records[i]['开奖生肖'][6] for i in range(idx)]
    for z in ZODIACS:
        found = False
        for i in range(len(h)-1, -1, -1):
            if h[i] == z:
                cache[z]['gap'] = len(h) - i
                found = True
                break
        if not found:
            cache[z]['gap'] = len(h) + 1
        # recent3/5/10/20/30
        recent = [r['开奖生肖'][6] for r in records[max(0,idx-30):idx]]
        for n in [3, 5, 10, 20, 30]:
            key = f'recent{n}'
            if key not in cache[z]:
                cache[z][key] = sum(1 for x in recent[-n:] if x == z)
        cache[z]['streak'] = 0
        for i in range(len(h)-1, -1, -1):
            if h[i] == z:
                cache[z]['streak'] += 1
            else:
                break

    # 重新计算gap
    for i in range(len(h)-1, -1, -1):
        cache[h[i]]['gap'] = len(h) - i
    for z in ZODIACS:
        if z not in [h[j] for j in range(len(h))]:
            cache[z]['gap'] = len(h) + 1
    return cache

def rank_scoring(cache):
    """排名法评分"""
    features = list(WEIGHTS.keys())
    ranks = {z: {f: 0 for f in features} for z in ZODIACS}
    for f in features:
        vals = [(z, cache[z][f]) for z in ZODIACS]
        vals.sort(key=lambda x: x[1], reverse=True)
        for i, (z, _) in enumerate(vals):
            ranks[z][f] = i
    return {z: sum(ranks[z][f] * WEIGHTS[f] for f in features) for z in ZODIACS}

# 加载数据
with open('/home/admin1/liuhecai_data.json') as f:
    all_data = json.load(f)

# 给数据加上idx
for i, rec in enumerate(all_data):
    rec['idx'] = i

# 加载历史
with open('/home/admin1/liuhecai_all_predictions.json') as f:
    history = json.load(f)

# 已有点：{(version, predicted_period): True}
existing = {(e['version'], e['predicted_period']) for e in history}
print(f"已有记录: {len(existing)}, 版本期号组合: {existing}")

# 逐期预测（从第30期开始，之前数据太少）
results = []
for idx in range(30, len(all_data)):
    rec = all_data[idx]
    period = rec['期号']
    actual = rec['开奖生肖'][6]

    # 预测下期（用idx的数据预测idx+1）
    if idx + 1 >= len(all_data):
        continue
    cache = build_cache(all_data, idx + 1)
    scores = rank_scoring(cache)
    top6 = [z for z, s in sorted(scores.items(), key=lambda x: -x[1])[:6]]

    key = ('v7', period)
    if key in existing:
        print(f"  跳过 v7 {period} (已有)")
        continue

    results.append({
        'timestamp': datetime.now().isoformat(),
        'version': 'v7',
        'strategy': f"排名法: {WEIGHTS}",
        'predicted_period': period,
        'predicted_top6': top6,
        'actual_period': period,
        'actual_zodiac': actual,
        'hit': actual in top6,
        'current_prediction_period': all_data[min(idx+2, len(all_data)-1)]['期号'] if idx+2 < len(all_data) else period,
        'current_top6': top6,
    })
    existing.add(key)

print(f"新增 v7 记录: {len(results)} 条")

# 合并
all_records = history + results
with open('/home/admin1/liuhecai_all_predictions.json', 'w') as f:
    json.dump(all_records, f, ensure_ascii=False, indent=2)

print(f"写入完成: 共 {len(all_records)} 条")
