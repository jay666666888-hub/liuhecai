#!/usr/bin/env python3
"""
多码预测器批量回测脚本

用法: python3 backtest_all_duoma.py
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from predictor.predictor_registry import PredictorRegistry
from predictor.data_fetcher import get_all_records, build_standard_records

def run_backtest(version, top_k=24):
    """对单个预测器运行回测"""
    predictor = PredictorRegistry.get(version)
    strategy = predictor.params.get("strategy", "freq_only")

    lookback = predictor.params.get("lookback", 50)

    hits = 0
    total = 0
    max_streak = 0
    streak = 0
    recent_results = []

    for i in range(lookback, len(standard)):
        history = standard[:i]
        result = predictor.predict(history, top_k=top_k)
        prediction = result.prediction
        current = standard[i]
        actual_number = current.get("特码号码")

        hit = actual_number in prediction if actual_number else False

        if hit:
            hits += 1
            streak = 0
        else:
            streak += 1
            max_streak = max(max_streak, streak)

        total += 1
        recent_results.append({"issue": current.get("期号"), "hit": hit})

    hit_rate = hits / total if total > 0 else 0
    recent_100 = recent_results[-100:] if len(recent_results) >= 100 else recent_results
    recent_100_rate = sum(1 for r in recent_100 if r["hit"]) / len(recent_100) if recent_100 else 0
    recent_50 = recent_results[-50:] if len(recent_results) >= 50 else recent_results
    recent_50_rate = sum(1 for r in recent_50 if r["hit"]) / len(recent_50) if recent_50 else 0

    return {
        "version": version,
        "strategy": strategy,
        "total": total,
        "hits": hits,
        "hit_rate": hit_rate,
        "recent_100_rate": recent_100_rate,
        "recent_50_rate": recent_50_rate,
        "max_streak": max_streak
    }

# 加载数据
print("加载历史数据...")
records = get_all_records([2024, 2025, 2026])
standard = build_standard_records(records)
print(f"总期数: {len(standard)}\n")

# 扫描并加载预测器
PredictorRegistry.scan()

# 需要测试的版本
versions_to_test = ["v40", "v41", "v42", "v43", "v44", "v45", "v46", "v47", "v48", "v49"]

results = []
for v in versions_to_test:
    print(f"测试 {v}...")
    r = run_backtest(v, 24)
    results.append(r)
    print(f"  策略: {r['strategy']}, 命中率: {r['hit_rate']*100:.2f}%, 最近100期: {r['recent_100_rate']*100:.2f}%, 最近50期: {r['recent_50_rate']*100:.2f}%, 最大连错: {r['max_streak']}")

print(f"\n{'='*60}")
print(f"{'版本':<8} {'策略':<15} {'命中率':<10} {'最近100期':<12} {'最近50期':<10} {'最大连错':<8}")
print(f"{'='*60}")
for r in results:
    print(f"{r['version']:<8} {r['strategy']:<15} {r['hit_rate']*100:.2f}%     {r['recent_100_rate']*100:.2f}%      {r['recent_50_rate']*100:.2f}%     {r['max_streak']:<8}")
print(f"{'='*60}")

# 找出最佳版本
best = max(results, key=lambda x: x['hit_rate'])
print(f"\n最佳版本: {best['version']} (命中率 {best['hit_rate']*100:.2f}%)")