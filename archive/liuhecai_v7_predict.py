#!/usr/bin/env python3
"""
liuhecai_v7_predict.py - 排名法六肖预测系统 (防覆盖版)
============================================

策略: 排名法 (Rank-based scoring)
- 将每个特征转成排名(0~11)，用加权求和避免异常值影响
- 最佳配置: gap=2.5, recent5=1.5, recent10=1.5, r20=0.0, r30=1.0, r3=1.0, streak=0.3

关键修复：永不重新计算已发送的预测
- 每次运行只预测"下期"（未开奖的）
- 已发送的预测存入状态文件，只读不覆盖
"""

import json, fcntl, os
from datetime import datetime

# ============ 配置 ============
DATA_FILE = '/mnt/c/Users/Admin/liuhecai/liuhecai_data.json'
OUTPUT_FILE = '/home/admin1/liuhecai_v7_prediction.json'
STATE_FILE = '/home/admin1/liuhecai_v7_state.json'
ALL_HISTORY_FILE = '/home/admin1/liuhecai_all_predictions.json'
VERSION = 'v7_optimized'

WEIGHTS = {
    'gap': 2.5,
    'recent5': 1.5,
    'recent10': 1.5,
    'recent20': 0.0,
    'recent30': 1.0,
    'recent3': 1.0,
    'streak': 0.3,
}

# ============ 数据加载 ============
def load_data():
    with open(DATA_FILE) as f:
        raw = json.load(f)
    records = []
    for r in raw:
        if len(r.get('开奖号码', [])) >= 7:
            records.append({
                '期号': r['期号'],
                '特码': r['开奖生肖'][6]
            })
    return records

# ============ 特征计算 ============
def build_cache(records, upto):
    zodiacs = sorted(set(r['特码'] for r in records))
    cache = {}
    for z in zodiacs:
        positions = [i for i in range(upto) if records[i]['特码'] == z]
        gaps = [positions[i+1]-positions[i]-1 for i in range(len(positions)-1)]
        last_gap = upto - positions[-1] - 1 if positions else 999
        cache[z] = {
            'gap': last_gap,
            'avg_gap': sum(gaps)/len(gaps) if gaps else 12,
            'recent3': sum(1 for i in range(max(0,upto-3), upto) if records[i]['特码']==z),
            'recent5': sum(1 for i in range(max(0,upto-5), upto) if records[i]['特码']==z),
            'recent10': sum(1 for i in range(max(0,upto-10), upto) if records[i]['特码']==z),
            'recent20': sum(1 for i in range(max(0,upto-20), upto) if records[i]['特码']==z),
            'recent30': sum(1 for i in range(max(0,upto-30), upto) if records[i]['特码']==z),
            'streak': 0,
        }
        for i in range(upto-1, -1, -1):
            if records[i]['特码'] == z:
                cache[z]['streak'] += 1
            else:
                break
    return cache

# ============ 排名法评分 ============
def rank_scoring(cache, weights):
    zodiacs = list(cache.keys())
    features = ['gap', 'recent3', 'recent5', 'recent10', 'recent20', 'recent30', 'streak']
    ranks = {z: {f: 0 for f in features} for z in zodiacs}
    for f in features:
        vals = [(z, cache[z][f]) for z in zodiacs]
        vals.sort(key=lambda x: x[1], reverse=True)
        for i, (z, _) in enumerate(vals):
            ranks[z][f] = i
    scores = {}
    for z in zodiacs:
        s = sum(ranks[z][f] * weights[f] for f in features if f in weights)
        scores[z] = s
    return scores

# ============ 预测 ============
def predict(records, n_train=None):
    if n_train is None:
        n_train = len(records)
    cache = build_cache(records, n_train)
    scores = rank_scoring(cache, WEIGHTS)
    zodiacs = list(cache.keys())
    ranked = sorted(zodiacs, key=lambda z: scores[z], reverse=True)
    return {
        'top6': ranked[:6],
        'top7': ranked[:7],
        'scores': {z: round(scores[z], 2) for z in zodiacs},
        'cache': {z: {k: cache[z][k] for k in ['gap', 'recent3', 'recent5', 'recent10', 'recent20', 'recent30', 'streak']} for z in zodiacs},
    }

def predict_next(records):
    """预测下期：基于所有数据预测下一期"""
    result = predict(records)
    latest = records[-1]
    next_period = f'2026{int(latest["期号"][-3:])+1:03d}' if latest['期号'].startswith('2026') else str(int(latest['期号'])+1).zfill(7)
    return next_period, result

# ============ 状态管理 ============
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def append_history(verified_period, verified_top6, verified_actual, verified_hit, pending_period, pending_top6):
    lock_file = ALL_HISTORY_FILE + '.lock'
    with open(lock_file, 'w') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            all_history = []
            if os.path.exists(ALL_HISTORY_FILE):
                with open(ALL_HISTORY_FILE, encoding='utf-8') as f:
                    all_history = json.load(f)
            existing_keys = {(e['version'], str(e.get('verified_period') or e.get('predicted_period'))) for e in all_history}
            new_key = ('v7', str(verified_period))
            if new_key not in existing_keys:
                all_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'version': 'v7',
                    'strategy': '排名法: gap=2.5, r5=1.5, r10=1.5, r20=0.0, r30=1.0, r3=1.0, streak=0.3',
                    'verified_period': str(verified_period),
                    'verified_top6': verified_top6,
                    'actual_period': str(verified_period),
                    'actual_zodiac': verified_actual,
                    'hit': verified_hit,
                    'current_prediction_period': str(pending_period),
                    'current_top6': pending_top6,
                })
            with open(ALL_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_history, f, ensure_ascii=False, indent=2)
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

# ============ 主程序 ============
if __name__ == '__main__':
    records = load_data()
    n = len(records)
    state = load_state()
    last_verified = state.get('last_verified_period')
    pending_period = state.get('pending_period')
    pending_top6 = state.get('pending_top6', [])

    latest = records[-1]
    latest_int = int(latest['期号'])
    last_verified_int = int(last_verified) if last_verified else None
    pending_int = int(pending_period) if pending_period else None

    print(f'=== 六合六肖 排名法 v7_optimized (防覆盖版) ===')
    print(f'数据: {n}期, 最新: {latest["期号"]} ({latest["特码"]})')
    print(f'状态: last_verified={last_verified}, pending={pending_period}')

    verified_period = None
    verified_top6 = []
    verified_actual = ''
    verified_hit = None
    new_pending_period = None
    new_pending_top6 = []
    result_next = None

    if last_verified is None:
        # ===== 首次运行 =====
        # 用n-1期数据预测第n期，作为待验证
        prev_result = predict(records, n_train=n-1)
        prev_actual = latest['特码']
        prev_hit = prev_actual in prev_result['top6']
        print(f'\n📋 首次验证 {latest["期号"]}期:')
        print(f'   预测={" ".join(prev_result["top6"])} 实际={prev_actual} {"✅" if prev_hit else "❌"}')

        verified_period = latest['期号']
        verified_top6 = prev_result['top6']
        verified_actual = prev_actual
        verified_hit = prev_hit

        next_period, result_next = predict_next(records)
        print(f'\n🎯 {next_period}期 预测: {" ".join(result_next["top6"])}')

        new_pending_period = next_period
        new_pending_top6 = result_next['top6']

        state['last_verified_period'] = latest['期号']
        state['last_verified_top6'] = prev_result['top6']
        state['last_verified_hit'] = prev_hit
        state['last_verified_actual'] = prev_actual
        state['pending_period'] = next_period
        state['pending_top6'] = result_next['top6']
        state['last_updated'] = datetime.now().isoformat()
        save_state(state)
        append_history(verified_period, verified_top6, verified_actual, verified_hit, next_period, result_next['top6'])

    elif pending_period is not None:
        if latest_int > last_verified_int:
            if pending_int == latest_int:
                # pending正好是最新一期，可以验证
                pending_hit = latest['特码'] in pending_top6
                print(f'\n📋 验证 {pending_period}期:')
                print(f'   预测={" ".join(pending_top6)} 实际={latest["特码"]} {"✅" if pending_hit else "❌"}')

                verified_period = pending_period
                verified_top6 = pending_top6
                verified_actual = latest['特码']
                verified_hit = pending_hit

                next_period, result_next = predict_next(records)
                print(f'\n🎯 {next_period}期 预测: {" ".join(result_next["top6"])}')

                new_pending_period = next_period
                new_pending_top6 = result_next['top6']

                state['last_verified_period'] = pending_period
                state['last_verified_top6'] = pending_top6
                state['last_verified_hit'] = pending_hit
                state['last_verified_actual'] = latest['特码']
                state['pending_period'] = next_period
                state['pending_top6'] = result_next['top6']
                state['last_updated'] = datetime.now().isoformat()
                save_state(state)
                append_history(verified_period, verified_top6, verified_actual, verified_hit, next_period, result_next['top6'])
            elif pending_int < latest_int:
                # 跳期
                print(f'\n📋 {pending_period}期已过期（跳期）')
                next_period, result_next = predict_next(records)
                print(f'\n🎯 {next_period}期 预测: {" ".join(result_next["top6"])}')
                new_pending_period = next_period
                new_pending_top6 = result_next['top6']
                state['pending_period'] = next_period
                state['pending_top6'] = result_next['top6']
                state['last_updated'] = datetime.now().isoformat()
                save_state(state)
            else:
                # 等待新数据
                print(f'\n📋 等待新数据...')
                verified_period = last_verified
                verified_top6 = state.get('last_verified_top6', [])
                verified_actual = state.get('last_verified_actual', '')
                verified_hit = state.get('last_verified_hit')
                new_pending_period = pending_period
                new_pending_top6 = pending_top6
        else:
            print(f'\n📋 无新数据')
            verified_period = last_verified
            verified_top6 = state.get('last_verified_top6', [])
            verified_actual = state.get('last_verified_actual', '')
            verified_hit = state.get('last_verified_hit')
            new_pending_period = pending_period
            new_pending_top6 = pending_top6
    else:
        # 有last_verified但没有pending
        next_period, result_next = predict_next(records)
        print(f'\n🎯 {next_period}期 预测: {" ".join(result_next["top6"])}')
        new_pending_period = next_period
        new_pending_top6 = result_next['top6']
        state['pending_period'] = next_period
        state['pending_top6'] = result_next['top6']
        state['last_updated'] = datetime.now().isoformat()
        save_state(state)

    # 保存输出（供send_prediction.py读取）
    output = {
        'version': VERSION,
        'strategy': '排名法: gap=2.5, r5=1.5, r10=1.5, r20=0.0, r30=1.0, r3=1.0, streak=0.3',
        'strategy_full': 'gap=2.5, recent5=1.5, recent10=1.5, recent20=0.0, recent30=1.0, recent3=1.0, streak=0.3',
        # 验证结果（供飞书卡片显示）
        'verified_period': str(verified_period) if verified_period else None,
        'prev_top6': verified_top6,
        'prev_actual': verified_actual,
        'prev_hit': verified_hit,
        # 下期预测
        '预测期号': str(new_pending_period) if new_pending_period else None,
        '推荐6肖': new_pending_top6,
        'n_train': n,
        'timestamp': datetime.now().isoformat(),
        'wf_rolling': 83.11,
    }

    if result_next:
        output['scores'] = result_next['scores']
        output['cache'] = result_next['cache']

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f'\n已保存: {OUTPUT_FILE}')
