#!/usr/bin/env python3
"""
补录历史预测 - 为账本中所有缺失的期号生成预测
"""

import json
from datetime import datetime

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.six_zodiac_predictor import build_cache, predict_top6
from predictor.ledger import PredictionLedger
from predictor.config import load_strategy


def backfill_predictions():
    """补录所有缺失的预测"""
    print("开始补录历史预测...")

    # 获取API数据
    records = get_all_records([2024, 2025, 2026], force_refresh=True)
    standard = build_standard_records(records)
    print(f"API数据: {len(standard)} 期")

    # 加载策略
    strategy = load_strategy()
    weights = strategy.get('weights', {})
    feature_type = strategy.get('feature_type', 'binary')
    print(f"策略类型: {feature_type}")

    # 加载账本
    ledger = PredictionLedger()
    existing_issues = {p['issue'] for p in ledger.predictions}
    print(f"已有预测: {len(existing_issues)} 期")

    # 需要补录的期号
    needed = []
    for r in standard:
        if r['期号'] not in existing_issues:
            needed.append(r['期号'])

    print(f"需要补录: {len(needed)} 期")
    print(f"缺口期号: {needed[:5]}... {needed[-5:]}")

    if not needed:
        print("无需补录")
        return

    # 逐期生成预测
    # 由于预测需要历史数据，我们按顺序处理
    # 对于每个缺失的期号，我们使用它之前的数据来预测
    results = []
    for i, r in enumerate(standard):
        issue = r['期号']
        if issue in existing_issues:
            continue

        # 使用这个期号之前的数据（不包含当前期）
        history_data = standard[:i]
        if len(history_data) < 10:
            # 数据太少，跳过
            continue

        # 构建缓存
        n = len(history_data)
        cache = build_cache(history_data, n)
        zodiacs = list(cache.keys())

        # 预测六肖
        top6 = predict_top6(history_data, weights, feature_type)

        # 添加到账本
        created_at = datetime.now().isoformat()
        try:
            record = ledger.add_prediction(
                issue=issue,
                top6=top6,
                version="v12",
                strategy="backfill",
                created_at=created_at
            )
            results.append(f"补录 {issue}: {top6}")
        except Exception as e:
            print(f"补录失败 {issue}: {e}")

    print(f"\n补录完成: {len(results)} 条")
    for r in results[:10]:
        print(f"  {r}")
    if len(results) > 10:
        print(f"  ... 还有 {len(results) - 10} 条")

    # 打印统计
    stats = ledger.get_stats()
    print(f"\n账本统计: {stats['total_predictions']} 预测, {stats['total_results']} 结果, {stats['hit_rate']:.2%} 命中率")


if __name__ == "__main__":
    backfill_predictions()