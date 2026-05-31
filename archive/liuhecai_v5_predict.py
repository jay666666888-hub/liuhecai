#!/usr/bin/env python3
"""
澳门六合六肖预测系统 v5 - 防覆盖版
=========================================
核心策略: gap16*1.21 + gap10*1.66 + gap6*0.62 + r3*1.75 + streak*1.86

关键修复：永不重新计算已发送的预测
- 每次运行只预测"下期"（未开奖的）
- 已发送的预测存入状态文件，只读不覆盖
"""
import json, datetime as dt, fcntl, os
from collections import Counter

DATA_FILE = '/mnt/c/Users/Admin/liuhecai/liuhecai_data.json'
PREDICTION_FILE = '/home/admin1/liuhecai_latest_prediction.json'
STATE_FILE = '/home/admin1/liuhecai_v5_state.json'
ALL_HISTORY_FILE = '/home/admin1/liuhecai_all_predictions.json'
TOP_N = 6

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
                window = h[-n:] if len(h) >= n else h
                freq[z][f'f{n}'] = sum(1 for r in window if r['特码'] == z) / min(n, len(h)) if h else 0.0
        streak = {}
        for z in zodiacs:
            cnt = 0
            for r in h:
                if r['特码'] == z:
                    cnt += 1
                else:
                    break
            streak[z] = cnt
        interval_raw = {z: gap_arr[idx][z2i[z]] for z in zodiacs}
        gap_ge = {z: {thresh: 1.0 if interval_raw[z] >= thresh else 0.0
                       for thresh in [6, 8, 10, 12, 14, 16, 20]}
                  for z in zodiacs}
        cache.append({
            'freq': freq,
            'interval_raw': interval_raw,
            'gap_ge': gap_ge,
            'streak': streak,
        })
    return cache

def get_feature(idx, zodiac, feat, cache):
    c = cache[idx]
    if feat.startswith('r'):
        n = int(feat[1:])
        return c['freq'][zodiac].get(f'f{n}', 0.0)
    if feat.startswith('gap_ge'):
        thresh = int(feat.split('_')[1][2:])
        return c['gap_ge'][zodiac].get(thresh, 0.0)
    if feat == 'interval_raw':
        return c['interval_raw'][zodiac]
    if feat == 'streak':
        return float(c['streak'][zodiac])
    if feat.startswith('f'):
        return c['freq'][zodiac].get(feat, 0.0)
    return 0.0

def predict_top6_scores(cfg, cache, idx, zodiacs):
    return {z: sum(get_feature(idx, z, k, cache) * v for k, v in cfg.items()) for z in zodiacs}

def predict_top6(cfg, cache, idx, zodiacs):
    nf = predict_top6_scores(cfg, cache, idx, zodiacs)
    return sorted(zodiacs, key=lambda z: -nf[z])[:6]

def predict_for_period(cfg, cache, records, zodiacs, period_idx):
    """用records[:period_idx]的数据预测records[period_idx]的结果"""
    return predict_top6(cfg, cache, period_idx, zodiacs)

def predict_next(cfg, cache, records, zodiacs):
    """预测下期：只用截止到records的数据，不包含下期任何信息"""
    next_period = str(int(records[-1]['期号']) + 1) if str(records[-1]['期号']).isdigit() else None
    import copy
    extended_cache = copy.deepcopy(cache)
    last_interval = cache[-1]['interval_raw']
    dummy_entry = {
        'freq': {z: {'f1': 0.0, 'f2': 0.0, 'f3': 0.0} for z in zodiacs},
        'interval_raw': last_interval,
        'gap_ge': {z: {thresh: 1.0 if last_interval[z] >= thresh else 0.0 for thresh in [6, 8, 10, 12, 14, 16, 20]} for z in zodiacs},
        'streak': {z: 0 for z in zodiacs},
    }
    extended_cache.append(dummy_entry)
    top6 = predict_top6(cfg, extended_cache, len(records), zodiacs)
    scores = predict_top6_scores(cfg, extended_cache, len(records), zodiacs)
    return next_period, top6, scores

def wf_two_period(cfg, cache, records, zodiacs, start=30):
    hits = groups = 0
    i = start
    while i < len(records) - 1:
        hit1 = records[i]['特码'] in predict_top6(cfg, cache, i, zodiacs)
        hit2 = records[i + 1]['特码'] in predict_top6(cfg, cache, i + 1, zodiacs)
        groups += 1
        if hit1 or hit2:
            hits += 1
        i += 2
    return hits / groups * 100 if groups > 0 else 0, groups

def wf_single(cfg, cache, records, zodiacs, start=30):
    hits = total = 0
    for i in range(start, len(records)):
        if records[i]['特码'] in predict_top6(cfg, cache, i, zodiacs):
            hits += 1
        total += 1
    return hits / total * 100 if total > 0 else 0, total

def recent_performance(cfg, cache, records, zodiacs, n=20):
    if len(records) < n:
        n = len(records)
    start = len(records) - n
    hits = sum(1 for i in range(start, len(records)) if records[i]['特码'] in predict_top6(cfg, cache, i, zodiacs))
    return hits / n * 100, n

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def append_history(version, verified_period, verified_top6, verified_actual, verified_hit, pending_period, pending_top6):
    lock_file = ALL_HISTORY_FILE + '.lock'
    with open(lock_file, 'w') as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            all_history = []
            if os.path.exists(ALL_HISTORY_FILE):
                with open(ALL_HISTORY_FILE, encoding='utf-8') as f:
                    all_history = json.load(f)
            existing_keys = {(e['version'], str(e.get('verified_period') or e.get('predicted_period'))) for e in all_history}
            new_key = (version, str(verified_period))
            if new_key not in existing_keys:
                all_history.append({
                    'timestamp': dt.datetime.now().isoformat(),
                    'version': version,
                    'strategy': 'gap16*1.21 + gap10*1.66 + gap6*0.62 + r3*1.75 + streak*1.86',
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

def find_record(records, period_str):
    for r in records:
        if str(r['期号']) == str(period_str):
            return r
    return None

def main():
    records, zodiacs = load_data()
    cache = build_cache(records, zodiacs)
    latest = records[-1]
    prev_r = records[-2] if len(records) >= 2 else None
    cfg = {'gap_ge16': 1.21, 'gap_ge10': 1.66, 'gap_ge6': 0.62, 'r3': 1.75, 'streak': 1.86}

    state = load_state()
    last_verified = state.get('last_verified_period')  # 已验证到的期号
    pending_period = state.get('pending_period')        # 上一轮预测的期号（未验证）
    pending_top6 = state.get('pending_top6', [])

    print(f"\n{'='*55}")
    print(f"  澳门六合六肖预测系统 v5 (防覆盖版)")
    print(f"  {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}")
    print(f"\n📊 数据: {len(records)}期")
    print(f"   最新: {latest['期号']} ({latest['特码']})")
    print(f"   状态: last_verified={last_verified}, pending={pending_period}")

    # WF验证
    wf2, tg = wf_two_period(cfg, cache, records, zodiacs, 30)
    wf1, t1 = wf_single(cfg, cache, records, zodiacs, 30)
    l50, _ = recent_performance(cfg, cache, records, zodiacs, 50)
    r20, _ = recent_performance(cfg, cache, records, zodiacs, 20)
    yr26_idx = next((i for i, r in enumerate(records) if str(r['期号']).startswith('2026')), 0)
    wf2_26, _ = wf_two_period(cfg, cache, records, zodiacs, yr26_idx)
    wf1_26, _ = wf_single(cfg, cache, records, zodiacs, yr26_idx)

    print(f"\n📊 验证数据:")
    print(f"   全期单期={wf1:.2f}% 两期={wf2:.2f}%")
    print(f"   2026单期={wf1_26:.2f}% 两期={wf2_26:.2f}%")
    print(f"   L50={l50:.2f}% R20={r20:.2f}%")

    verified_period = None
    verified_top6 = []
    verified_actual = ''
    verified_hit = None
    new_pending_period = None
    new_pending_top6 = []
    new_scores = {}

    latest_int = int(latest['期号'])
    last_verified_int = int(last_verified) if last_verified else None
    pending_int = int(pending_period) if pending_period else None

    if last_verified is None:
        # ===== 首次运行：验证最新期，预测下期 =====
        # 用截止到latest之前的数据预测latest，用latest的实际结果验证
        # predict_for_period 用 records[:idx] 的数据预测 records[idx] 的结果
        latest_idx = len(records) - 1
        latest_top6 = predict_top6(cfg, cache, latest_idx, zodiacs)
        latest_hit = latest['特码'] in latest_top6
        print(f"\n📋 首次验证 {latest['期号']}期:")
        print(f"   预测={' '.join(latest_top6)} 实际={latest['特码']} → {'✅' if latest_hit else '❌'}")

        verified_period = latest['期号']
        verified_top6 = latest_top6
        verified_actual = latest['特码']
        verified_hit = latest_hit

        # 预测下期
        next_period, next_top6, scores = predict_next(cfg, cache, records, zodiacs)
        print(f"\n🎯 {next_period}期 预测六肖: {' '.join(next_top6)}")

        new_pending_period = next_period
        new_pending_top6 = next_top6
        new_scores = scores

        # 更新状态
        state['last_verified_period'] = latest['期号']
        state['last_verified_top6'] = latest_top6
        state['last_verified_hit'] = latest_hit
        state['last_verified_actual'] = latest['特码']
        state['pending_period'] = next_period
        state['pending_top6'] = next_top6
        state['last_updated'] = dt.datetime.now().isoformat()
        save_state(state)

        # 追加历史
        append_history('v5', verified_period, verified_top6, verified_actual, verified_hit, next_period, next_top6)

    elif pending_period is not None:
        # ===== 有pending预测，检查是否需要验证或重新预测 =====
        if latest_int > last_verified_int:
            # 有新数据到达
            if pending_int == latest_int:
                # pending正好是最新一期，可以验证
                pending_hit = latest['特码'] in pending_top6
                print(f"\n📋 验证 {pending_period}期:")
                print(f"   预测={' '.join(pending_top6)} 实际={latest['特码']} → {'✅' if pending_hit else '❌'}")

                verified_period = pending_period
                verified_top6 = pending_top6
                verified_actual = latest['特码']
                verified_hit = pending_hit

                # 预测下期
                next_period, next_top6, scores = predict_next(cfg, cache, records, zodiacs)
                print(f"\n🎯 {next_period}期 预测六肖: {' '.join(next_top6)}")

                new_pending_period = next_period
                new_pending_top6 = next_top6
                new_scores = scores

                # 更新状态
                state['last_verified_period'] = pending_period
                state['last_verified_top6'] = pending_top6
                state['last_verified_hit'] = pending_hit
                state['last_verified_actual'] = latest['特码']
                state['pending_period'] = next_period
                state['pending_top6'] = next_top6
                state['last_updated'] = dt.datetime.now().isoformat()
                save_state(state)

                append_history('v5', verified_period, verified_top6, verified_actual, verified_hit, next_period, next_top6)

            elif pending_int < latest_int:
                # pending已过期（跳期），跳过验证，直接预测下期
                print(f"\n📋 {pending_period}期已过期（数据跳期），跳过验证")
                next_period, next_top6, scores = predict_next(cfg, cache, records, zodiacs)
                print(f"\n🎯 {next_period}期 预测六肖: {' '.join(next_top6)}")

                new_pending_period = next_period
                new_pending_top6 = next_top6
                new_scores = scores

                state['pending_period'] = next_period
                state['pending_top6'] = next_top6
                state['last_updated'] = dt.datetime.now().isoformat()
                save_state(state)
            else:
                # pending > latest，不应该发生（等待新数据）
                print(f"\n📋 等待新数据...")
                verified_period = last_verified
                verified_top6 = state.get('last_verified_top6', [])
                verified_actual = state.get('last_verified_actual', '')
                verified_hit = state.get('last_verified_hit')
                new_pending_period = pending_period
                new_pending_top6 = pending_top6
        else:
            # 没有新数据，保持不变
            print(f"\n📋 无新数据")
            print(f"   已验证: {last_verified}期，预测中: {pending_period}期")
            verified_period = last_verified
            verified_top6 = state.get('last_verified_top6', [])
            verified_actual = state.get('last_verified_actual', '')
            verified_hit = state.get('last_verified_hit')
            new_pending_period = pending_period
            new_pending_top6 = pending_top6

    else:
        # 有last_verified但没有pending，需要预测
        next_period, next_top6, scores = predict_next(cfg, cache, records, zodiacs)
        print(f"\n🎯 {next_period}期 预测六肖: {' '.join(next_top6)}")
        new_pending_period = next_period
        new_pending_top6 = next_top6
        new_scores = scores
        state['pending_period'] = next_period
        state['pending_top6'] = next_top6
        state['last_updated'] = dt.datetime.now().isoformat()
        save_state(state)

    # 保存最新预测（用于飞书卡片）
    result = {
        'verified_period': str(verified_period) if verified_period else None,
        'verified_top6': verified_top6,
        'verified_actual': verified_actual,
        'verified_hit': verified_hit,
        'pending_period': str(new_pending_period) if new_pending_period else None,
        'pending_top6': new_pending_top6,
        '预测时间': dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '策略': 'gap16*1.21 + gap10*1.66 + gap6*0.62 + r3*1.75 + streak*1.86',
        'scores': {z: round(new_scores.get(z, 0), 4) for z in zodiacs} if new_scores else {},
        'verification': {
            'wf_single_all': round(wf1, 2),
            'wf_two_all': round(wf2, 2),
            'wf_single_2026': round(wf1_26, 2),
            'wf_two_2026': round(wf2_26, 2),
            'l50': round(l50, 2),
            'r20': round(r20, 2),
        },
        'version': 'v5',
    }

    with open(PREDICTION_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n⚠️  预测仅供参考，请理性对待博彩")
    print(f"{'='*55}")

    return result

if __name__ == '__main__':
    main()
