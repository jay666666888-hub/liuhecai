#!/usr/bin/env python3
"""用V7排名法批量回填全部历史，不覆盖已有记录"""
import json, importlib.util
from datetime import datetime

# 加载 v7_predict 模块
spec = importlib.util.spec_from_file_location('v7_mod', '/home/admin1/liuhecai_v7_predict.py')
v7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v7)

# 加载 v5_predict 模块
spec5 = importlib.util.spec_from_file_location('v5_mod', '/home/admin1/liuhecai_v5_predict.py')
v5 = importlib.util.module_from_spec(spec5)
spec5.loader.exec_module(v5)

# 用 v7 自己的 load_data 方式加载数据
raw_data = v7.load_data()  # v7 自己转换好的 records（用特码生肖作为'特码'）
records5, zodiacs5 = v5.load_data()  # v5 的 records

n = len(raw_data)
print(f"总数据: {n} 期")

# 加载历史
with open('/home/admin1/liuhecai_all_predictions.json') as f:
    history = json.load(f)

# 已有点：{(version, predicted_period): True}
existing = {(e['version'], e['predicted_period']) for e in history}
print(f"已有记录: {len(existing)} 条")

# V7 回填：从第30期开始预测（验证起点），用 rank_scoring 预测当期
new_v7 = []
for idx in range(30, n):
    period = raw_data[idx]['期号']
    actual = raw_data[idx]['特码']
    key = ('v7', period)

    if key in existing:
        continue

    cache = v7.build_cache(raw_data, idx)  # 不含当期，模拟生产预测当期
    scores = v7.rank_scoring(cache, v7.WEIGHTS)
    top6 = [z for z, s in sorted(scores.items(), key=lambda x: -x[1])[:6]]

    # 下期期号
    next_period = raw_data[idx + 1]['期号'] if idx + 1 < n else period

    new_v7.append({
        'timestamp': datetime.now().isoformat(),
        'version': 'v7',
        'strategy': f"排名法: {v7.WEIGHTS}",
        'predicted_period': period,
        'predicted_top6': top6,
        'actual_period': period,
        'actual_zodiac': actual,
        'hit': actual in top6,
        'current_prediction_period': next_period,
        'current_top6': top6,
    })
    existing.add(key)

print(f"V7 新增: {len(new_v7)} 条")

# V5 回填（布尔法策略）
# V5 策略: gwf1_g12*0.1 + gap_ge10*0.1 + gap_ge16*0.8
# V5 也用类似方法回填（布尔特征）
def v5_predict(all_data, idx):
    """用 idx 数据预测 idx 的六肖"""
    records = all_data
    upto = idx + 1
    zodiacs = list(set(r['开奖生肖'][6] for r in records[:upto]))
    cache = {}
    for z in zodiacs:
        positions = [i for i in range(upto) if records[i]['开奖生肖'][6] == z]
        gaps = [positions[i+1]-positions[i]-1 for i in range(len(positions)-1)]
        last_gap = upto - positions[-1] - 1 if positions else 999
        cache[z] = {
            'gap': last_gap,
            'recent3': sum(1 for i in range(max(0,upto-3), upto) if records[i]['开奖生肖'][6]==z),
            'recent5': sum(1 for i in range(max(0,upto-5), upto) if records[i]['开奖生肖'][6]==z),
            'recent10': sum(1 for i in range(max(0,upto-10), upto) if records[i]['开奖生肖'][6]==z),
            'recent20': sum(1 for i in range(max(0,upto-20), upto) if records[i]['开奖生肖'][6]==z),
            'recent30': sum(1 for i in range(max(0,upto-30), upto) if records[i]['开奖生肖'][6]==z),
            'streak': 0,
        }
        for i in range(upto-1, -1, -1):
            if records[i]['开奖生肖'][6] == z:
                cache[z]['streak'] += 1
            else:
                break

    # gwf1: 上一期开出的生肖
    gwf1 = 1 if idx > 0 and records[idx]['开奖生肖'][6] else 0
    # gap_ge10/ge16
    gap_ge10 = {z: int(cache[z]['gap'] >= 10) for z in zodiacs}
    gap_ge16 = {z: int(cache[z]['gap'] >= 16) for z in zodiacs}

    scores = {}
    for z in zodiacs:
        scores[z] = gwf1 * 0.1 + gap_ge10[z] * 0.1 + gap_ge16[z] * 0.8

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])[:6]]

new_v5 = []
# V5 用自己的 build_cache（全量预计算）再逐期预测
cache5 = v5.build_cache(records5, zodiacs5)
v5_cfg = {'gwf1_g12': 0.1, 'gap_ge10': 0.1, 'gap_ge16': 0.8}

for idx in range(30, n):
    period = records5[idx]['期号']
    actual = records5[idx]['特码']
    key = ('v5', period)

    if key in existing:
        continue

    top6 = v5.predict_top6(v5_cfg, cache5, idx, zodiacs5)
    next_period = records5[idx + 1]['期号'] if idx + 1 < n else period

    new_v5.append({
        'timestamp': datetime.now().isoformat(),
        'version': 'v5',
        'strategy': 'gwf1_g12*0.1 + gap_ge10*0.1 + gap_ge16*0.8',
        'predicted_period': period,
        'predicted_top6': top6,
        'actual_period': period,
        'actual_zodiac': actual,
        'hit': actual in top6,
        'current_prediction_period': next_period,
        'current_top6': top6,
    })
    existing.add(key)

print(f"V5 新增: {len(new_v5)} 条")

# 合并
all_records = history + new_v5 + new_v7
with open('/home/admin1/liuhecai_all_predictions.json', 'w') as f:
    json.dump(all_records, f, ensure_ascii=False, indent=2)

print(f"写入完成: 共 {len(all_records)} 条")

# 统计
v5_total = sum(1 for r in all_records if r['version'] == 'v5')
v5_hits = sum(1 for r in all_records if r['version'] == 'v5' and r['hit'])
v7_total = sum(1 for r in all_records if r['version'] == 'v7')
v7_hits = sum(1 for r in all_records if r['version'] == 'v7' and r['hit'])
print(f"V5: {v5_hits}/{v5_total} = {v5_hits/v5_total*100:.1f}%")
print(f"V7: {v7_hits}/{v7_total} = {v7_hits/v7_total*100:.1f}%")
