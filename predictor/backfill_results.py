#!/usr/bin/env python3
"""
补录历史开奖结果 - 为账本中所有缺失的结果添加记录
"""

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.ledger import PredictionLedger


def backfill_results():
    """补录所有缺失的开奖结果"""
    print("开始补录历史开奖结果...")

    # 获取API数据
    records = get_all_records([2024, 2025, 2026], force_refresh=True)
    standard = build_standard_records(records)
    print(f"API数据: {len(standard)} 期")

    # 加载账本
    ledger = PredictionLedger()

    # 获取已有结果
    existing_issues = {r['issue'] for r in ledger.results}
    print(f"已有结果: {len(existing_issues)} 期")

    # 需要补录的结果
    to_add = []
    for r in standard:
        issue = r['期号']
        if issue not in existing_issues:
            # 找到对应的预测
            predictions = [p for p in ledger.predictions if p['issue'] == issue]
            if predictions:
                prediction = predictions[-1]  # 最新预测
                top6 = prediction['prediction']
                actual = r['特码生肖']
                hit = actual in top6
                to_add.append({
                    'issue': issue,
                    'actual': actual,
                    'hit': hit,
                    'prediction_id': prediction['id']
                })

    print(f"需要补录: {len(to_add)} 期")

    if not to_add:
        print("无需补录")
        return

    # 添加结果
    for item in to_add:
        try:
            ledger.add_result(
                issue=item['issue'],
                actual=item['actual'],
                hit=item['hit'],
                prediction_id=item['prediction_id']
            )
            print(f"补录结果 {item['issue']}: {item['actual']} {'✓' if item['hit'] else '✗'}")
        except Exception as e:
            print(f"补录失败 {item['issue']}: {e}")

    # 打印统计
    stats = ledger.get_stats()
    print(f"\n账本统计: {stats['total_predictions']} 预测, {stats['total_results']} 结果, {stats['hit_rate']:.2%} 命中率")


if __name__ == "__main__":
    backfill_results()