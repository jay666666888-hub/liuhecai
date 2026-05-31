#!/usr/bin/env python3
"""生成 dashboard 数据：包含 V5+V7 历史预测和统计"""
import json
from collections import defaultdict

ZODIACS = ['鼠','牛','虎','兔','龍','蛇','馬','羊','猴','雞','狗','豬']
EMOJI = {'鼠':'🐭','牛':'🐮','虎':'🐯','兔':'🐰','龍':'🐲','蛇':'🐍',
         '马':'🐴','馬':'🐴','羊':'🐑','猴':'🐵','雞':'🐔','狗':'🐕','豬':'🐷'}
RANDOM_SINGLE = 50.17
RANDOM_TWO = 75.17

# 加载数据
with open('/home/admin1/liuhecai_data.json') as f:
    all_data = json.load(f)

# 加载 V5 和 V7 最新预测
with open('/home/admin1/liuhecai_latest_prediction.json') as f:
    v5_latest = json.load(f)
with open('/home/admin1/liuhecai_v7_prediction.json') as f:
    v7_latest = json.load(f)
with open('/home/admin1/liuhecai_all_predictions.json') as f:
    history = json.load(f)

# 历史字典：期号 -> {v5_pred, v7_pred, actual}
hist_map = {}
for e in history:
    p = e['actual_period']
    if p not in hist_map:
        hist_map[p] = {}
    if e['version'] == 'v5':
        hist_map[p]['v5_top6'] = e.get('predicted_top6') or e.get('verified_top6', [])
        hist_map[p]['v5_hit'] = e['hit']
        hist_map[p]['v5_actual'] = e['actual_zodiac']
    elif e['version'] == 'v7':
        hist_map[p]['v7_top6'] = e.get('predicted_top6') or e.get('verified_top6', [])
        hist_map[p]['v7_hit'] = e['hit']
        hist_map[p]['v7_actual'] = e['actual_zodiac']

# 取最近30期（已开期号，从数据末尾取）
recent30 = []
for rec in reversed(all_data[-60:]):
    period = rec['期号']
    actual = rec['开奖生肖'][6] if rec.get('开奖生肖') else None
    if not actual:
        continue
    entry = {
        'period': period,
        'actual': actual,
        'v5_top6': hist_map.get(period, {}).get('v5_top6', []),
        'v5_hit': hist_map.get(period, {}).get('v5_hit', None),
        'v7_top6': hist_map.get(period, {}).get('v7_top6', []),
        'v7_hit': hist_map.get(period, {}).get('v7_hit', None),
    }
    recent30.append(entry)
    if len(recent30) >= 30:
        break

recent30.reverse()  # 旧到新

# 统计 V5
v5_hits = sum(1 for e in recent30 if e['v5_hit'] is True)
v5_total = sum(1 for e in recent30 if e['v5_hit'] is not None)
v5_rate = v5_hits / v5_total * 100 if v5_total else 0

# 统计 V7
v7_hits = sum(1 for e in recent30 if e['v7_hit'] is True)
v7_total = sum(1 for e in recent30 if e['v7_hit'] is not None)
v7_rate = v7_hits / v7_total * 100 if v7_total else 0

# 当前最新一期（已开）
latest = all_data[-1]
curr_period = latest['期号']
curr_actual = latest['开奖生肖'][6]

# 下期
next_period = f"2026{int(curr_period[-3:])+1:03d}"

# 输出
out = {
    'v5': {
        'strategy': v5_latest.get('策略', ''),
        'curr_period': v5_latest.get('curr_period', curr_period),
        'curr_top6': v5_latest.get('curr_top6', []),
        'curr_actual': v5_latest.get('curr_actual', ''),
        'curr_hit': v5_latest.get('curr_hit', None),
        'next_period': v5_latest.get('next_period', next_period),
        'next_top6': v5_latest.get('next_top6', []),
    },
    'v7': {
        'strategy': v7_latest.get('strategy', ''),
        'curr_period': v7_latest.get('期号', ''),
        'curr_top6': v7_latest.get('prev_top6', []),
        'curr_actual': v7_latest.get('prev_actual', ''),
        'curr_hit': v7_latest.get('prev_hit', None),
        'next_period': v7_latest.get('预测期号', next_period),
        'next_top6': v7_latest.get('推荐6肖', []),
    },
    'stats': {
        'v5_total': v5_total,
        'v5_hits': v5_hits,
        'v5_rate': round(v5_rate, 2),
        'v7_total': v7_total,
        'v7_hits': v7_hits,
        'v7_rate': round(v7_rate, 2),
        'random_single': RANDOM_SINGLE,
        'random_two': RANDOM_TWO,
    },
    'recent30': recent30,
    'updated': curr_period,
    'next_period': next_period,
}

with open('/home/admin1/liuhecai_dashboard_data.json', 'w') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"生成完成: V5历史{v5_total}条({v5_hits}命中) V7历史{v7_total}条({v7_hits}命中) 最近期号{curr_period}")
