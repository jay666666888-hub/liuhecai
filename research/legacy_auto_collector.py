#!/usr/bin/env python3
"""
澳门六合 - 自动开奖结果采集与账本更新
定时任务：每30分钟检查一次开奖结果
"""

import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, build_standard_records, get_special_zodiac
from predictor.ledger import PredictionLedger


def collect_and_update() -> dict:
    """
    采集开奖结果并更新账本

    Returns:
        更新结果字典
    """
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] 开始开奖结果采集...")

    # 1. 获取最新数据
    records = get_all_records([2024, 2025, 2026], force_refresh=True)
    standard_records = build_standard_records(records)

    if not standard_records:
        return {"status": "error", "message": "无法获取数据"}

    latest = standard_records[-1]
    latest_period = latest["期号"]
    latest_zodiac = latest["特码生肖"]

    print(f"  最新期号: {latest_period}, 特码: {latest_zodiac}")

    # 2. 加载账本
    ledger = PredictionLedger()

    # 3. 检查是否有待验证预测
    pending = ledger.get_pending_predictions()

    if not pending:
        print("  无待验证预测")
        return {"status": "no_pending", "latest_period": latest_period}

    # 找到匹配待验证期的预测
    matched_prediction = None
    for p in pending:
        if p["issue"] == latest_period:
            matched_prediction = p
            break

    if not matched_prediction:
        # 最新期号大于待验证期，可能是跳期
        latest_num = int(latest_period)
        for p in pending:
            if int(p["issue"]) < latest_num:
                # 跳期了，标记为未命中
                print(f"  跳期检测: {p['issue']} < {latest_period}, 标记为未验证")
                # 不删除预测，只是标记（账本规则不允许删除）
            else:
                matched_prediction = p
                break

    if not matched_prediction:
        print(f"  待验证期 {pending[0]['issue']} != 最新期 {latest_period}, 等待中")
        return {
            "status": "waiting",
            "latest_period": latest_period,
            "pending_period": pending[0]["issue"]
        }

    # 4. 验证预测
    prediction_id = matched_prediction["id"]
    predicted_top6 = matched_prediction["prediction"]
    predicted_period = matched_prediction["issue"]

    hit = latest_zodiac in predicted_top6

    print(f"  验证预测 {prediction_id}:")
    print(f"    预测: {predicted_top6}")
    print(f"    结果: {latest_zodiac} {'✅ 命中' if hit else '❌ 未命中'}")

    # 5. 添加结果到账本
    result_record = ledger.add_result(
        issue=latest_period,
        actual=latest_zodiac,
        hit=hit,
        prediction_id=prediction_id,
        resolved_at=timestamp
    )

    print(f"  结果已记录: {result_record['id']}")

    # 6. 生成新预测（更新pending）
    from predictor.predictor import predict_next

    next_period, next_top6, scores = predict_next(standard_records)

    print(f"  下期预测: {next_period} -> {next_top6}")

    # 7. 添加新预测到账本
    new_prediction = ledger.add_prediction(
        issue=next_period,
        top6=next_top6,
        version="v12",
        strategy="unified_weights",
        created_at=timestamp
    )

    print(f"  新预测已添加: {new_prediction['id']}")

    # 8. 打印统计
    stats = ledger.get_stats()
    print(f"  账本统计: {stats['total_predictions']} 预测, {stats['total_results']} 结果, {stats['hit_rate']:.2%} 命中率")

    return {
        "status": "success",
        "verified_period": latest_period,
        "verified_hit": hit,
        "verified_actual": latest_zodiac,
        "new_prediction_period": next_period,
        "new_prediction_top6": next_top6,
        "stats": stats
    }


def main():
    """主入口"""
    try:
        result = collect_and_update()
        print(f"\n结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        return result
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    main()