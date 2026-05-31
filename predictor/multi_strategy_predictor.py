#!/usr/bin/env python3
"""
澳门六合 - 多策略预测器 (v5/v7/v12统一)
统一入口，输出到各版本账本

DEPRECATED

Used by:
- v5 predictor (build_cache_v5, predict_v5_next)
- v7 predictor (predict_v7)

Do not create new dependencies on this module.
All logic should live in predictors/active/vN/predictor.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from predictor.data_fetcher import get_all_records, build_standard_records

# ============ v5 策略 ============
V5_WEIGHTS = {'gap_ge16': 1.21, 'gap_ge10': 1.66, 'gap_ge6': 0.62, 'r3': 1.75, 'streak': 1.86}

def build_cache_v5(records, zodiacs):
    """v5特征缓存"""
    N = len(zodiacs)
    z2i = {z: i for i, z in enumerate(zodiacs)}
    actuals = [r['特码生肖'] for r in records]

    interval = [0] * N
    gap_arr = [[0.0] * N for _ in range(len(records))]
    for idx in range(len(records)):
        for j in range(N):
            gap_arr[idx][j] = float(interval[j])
        zi = z2i[actuals[idx]]
        interval[zi] = 0
        for j in range(N):
            interval[j] = min(interval[j] + 1, 999)

    cache = []
    for idx in range(len(records)):
        h = records[:idx]
        freq = {z: {} for z in zodiacs}
        for n in [1, 2, 3, 5, 7, 10, 15, 20, 25, 40]:
            for z in zodiacs:
                window = h[-n:] if len(h) >= n else h
                freq[z][f'f{n}'] = sum(1 for r in window if r['特码生肖'] == z) / min(n, len(h)) if h else 0.0
        streak = {}
        for z in zodiacs:
            cnt = 0
            for r in h:
                if r['特码生肖'] == z:
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

def predict_v5_next(cache, zodiacs):
    """v5预测下期（用dummy entry扩展cache）"""
    last_interval = cache[-1]['interval_raw']
    dummy_entry = {
        'freq': {z: {'f1': 0.0, 'f2': 0.0, 'f3': 0.0} for z in zodiacs},
        'interval_raw': last_interval,
        'gap_ge': {z: {thresh: 1.0 if last_interval[z] >= thresh else 0.0 for thresh in [6, 8, 10, 12, 14, 16, 20]} for z in zodiacs},
        'streak': {z: 0 for z in zodiacs},
    }
    extended_cache = cache + [dummy_entry]
    idx = len(cache)

    def get_feature(zodiac, feat):
        c = extended_cache[idx]
        if feat.startswith('r'):
            n = int(feat[1:])
            return c['freq'][zodiac].get(f'f{n}', 0.0)
        if feat.startswith('gap_ge'):
            thresh = int(feat.split('_')[1][2:])
            return c['gap_ge'][zodiac].get(thresh, 0.0)
        if feat == 'streak':
            return float(c['streak'][zodiac])
        return 0.0

    nf = {z: sum(get_feature(z, k) * v for k, v in V5_WEIGHTS.items()) for z in zodiacs}
    return sorted(zodiacs, key=lambda z: -nf[z])[:6]

# ============ v7 策略 ============
V7_WEIGHTS = {'gap': 2.5, 'recent5': 1.5, 'recent10': 1.5, 'recent20': 0.0, 'recent30': 1.0, 'recent3': 1.0, 'streak': 0.3}

def build_cache_v7(records, upto):
    """v7特征缓存"""
    zodiacs = sorted(set(r['特码生肖'] for r in records))
    cache = {}
    for z in zodiacs:
        positions = [i for i in range(upto) if records[i]['特码生肖'] == z]
        gaps = [positions[i+1]-positions[i]-1 for i in range(len(positions)-1)]
        last_gap = upto - positions[-1] - 1 if positions else 999
        cache[z] = {
            'gap': last_gap,
            'recent3': sum(1 for i in range(max(0,upto-3), upto) if records[i]['特码生肖']==z),
            'recent5': sum(1 for i in range(max(0,upto-5), upto) if records[i]['特码生肖']==z),
            'recent10': sum(1 for i in range(max(0,upto-10), upto) if records[i]['特码生肖']==z),
            'recent20': sum(1 for i in range(max(0,upto-20), upto) if records[i]['特码生肖']==z),
            'recent30': sum(1 for i in range(max(0,upto-30), upto) if records[i]['特码生肖']==z),
            'streak': 0,
        }
        for i in range(upto-1, -1, -1):
            if records[i]['特码生肖'] == z:
                cache[z]['streak'] += 1
            else:
                break
    return cache

def rank_scoring_v7(cache, weights):
    """v7排名法"""
    zodiacs = list(cache.keys())
    features = list(weights.keys())
    ranks = {z: {f: 0 for f in features} for z in zodiacs}
    for f in features:
        vals = [(z, cache[z][f]) for z in zodiacs]
        vals.sort(key=lambda x: x[1], reverse=True)
        for i, (z, _) in enumerate(vals):
            ranks[z][f] = i
    return {z: sum(ranks[z][f] * weights[f] for f in features) for z in zodiacs}

def predict_v7(records, n_train=None):
    """v7预测"""
    if n_train is None:
        n_train = len(records)
    cache = build_cache_v7(records, n_train)
    scores = rank_scoring_v7(cache, V7_WEIGHTS)
    zodiacs = list(cache.keys())
    ranked = sorted(zodiacs, key=lambda z: scores[z], reverse=True)
    return ranked[:6], scores

# ============ v12 策略 (从现有predictor) ============
from predictor.six_zodiac_predictor import predict_top6

V12_PARAMS = {
    "lookback": 11,
    "pattern_weight": 1.45,
    "gap_weight": 0.098,
    "trend_weight": 0.267,
    "variance_weight": 0.177,
    "alt_mode": "trend"
}

# ============ 主程序 ============
LEDGER_V5 = "version_book/v5/backtest_ledger.jsonl"
LEDGER_V7 = "version_book/v7/backtest_ledger.jsonl"
LEDGER_V12 = "version_book/v12/backtest_ledger.jsonl"

def load_existing_issues(ledger_path):
    issues = set()
    if os.path.exists(ledger_path):
        with open(ledger_path, 'r') as f:
            for line in f:
                rec = json.loads(line)
                issues.add(rec['issue'])
    return issues

def write_prediction(ledger_path, issue, version, prediction, actual=None, hit=None):
    record_id = f"{issue}_{version}"
    # 检查是否已存在（方案A：写入去重）
    if os.path.exists(ledger_path):
        with open(ledger_path, 'r') as f:
            for line in f:
                rec = json.loads(line)
                if rec.get('id') == record_id:
                    # 已存在，跳过写入
                    return rec
    record = {
        "id": record_id,
        "issue": issue,
        "version": version,
        "model": f"{version}_pattern",
        "prediction": prediction,
        "actual": actual,
        "hit": hit,
        "created_at": datetime.now().isoformat(),
        "source": "live",
        "status": "verified" if actual is not None else "pending"
    }
    with open(ledger_path, 'a') as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record

def verify_and_update(ledger_path, pending_issue, actual):
    updated_lines = []
    found = False
    hit = None
    with open(ledger_path, 'r') as f:
        for line in f:
            rec = json.loads(line)
            if rec.get('issue') == pending_issue and rec.get('source') == 'live' and rec.get('actual') is None:
                rec['actual'] = actual
                rec['hit'] = actual in rec['prediction']
                rec['verified_at'] = datetime.now().isoformat()
                rec['status'] = 'verified'
                found = True
                hit = rec['hit']
            updated_lines.append(rec)
    if found:
        with open(ledger_path, 'w') as f:
            for rec in updated_lines:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return found, hit

def run_all_strategies():
    """运行v5/v7/v12所有策略"""
    print("=" * 60)
    print("澳门六合 - 多策略预测")
    print("=" * 60)

    # 加载数据
    records = get_all_records([2024, 2025, 2026])
    standard = build_standard_records(records)
    zodiacs = sorted(set(r['特码生肖'] for r in standard))

    print(f"数据: {len(standard)}期")

    latest = standard[-1]
    latest_issue = latest["期号"]
    latest_actual = latest["特码生肖"]
    print(f"最新: {latest_issue} ({latest_actual})")

    # 构建v5缓存
    cache_v5 = build_cache_v5(standard, zodiacs)

    # 对每个版本验证并预测
    for ledger_path, version, predict_fn in [
        (LEDGER_V5, "v5", lambda: predict_v5_next(cache_v5, zodiacs)),
        (LEDGER_V7, "v7", lambda: predict_v7(standard)[0]),
        (LEDGER_V12, "v12", lambda: predict_top6(standard, V12_PARAMS, "pattern_based")),
    ]:
        existing = load_existing_issues(ledger_path)

        if latest_issue in existing:
            print(f"✓ {version} {latest_issue} 已验证")
        else:
            pending = None
            if os.path.exists(ledger_path):
                with open(ledger_path, 'r') as f:
                    for line in f:
                        rec = json.loads(line)
                        if rec.get('source') == 'live' and rec.get('actual') is None:
                            pending = rec
                            break

            if pending:
                found, hit = verify_and_update(ledger_path, latest_issue, latest_actual)
                if found:
                    print(f"✓ {version} 验证 {latest_issue}: 预测{pending['prediction']}, 实际{latest_actual}, {'✓' if hit else '✗'}")

        # 预测下期
        next_issue = str(int(latest_issue) + 1)
        top6 = predict_fn()
        write_prediction(ledger_path, next_issue, version, top6)
        print(f"✓ {version} 预测 {next_issue}: {' '.join(top6)}")

    print("=" * 60)

if __name__ == "__main__":
    run_all_strategies()