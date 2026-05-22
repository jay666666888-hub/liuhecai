#!/usr/bin/env python3
"""
澳门六合预测系统 - 主入口
每日 21:35 cron 触发
"""

import json
import sys
import os
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, build_standard_records, extract_zodiac_mapping
from predictor.predictor import run_prediction_pipeline, predict_next
from predictor.config import load_strategy, save_strategy
from predictor.notification import send_notification

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "liuhecai_prediction.json")


def main():
    print(f"=== 澳门六合预测系统 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")

    # 1. 获取数据
    print("\n[1/4] 获取数据...")
    records = get_all_records([2024, 2025])
    standard_records = build_standard_records(records, extract_zodiac_mapping(records))
    print(f"  数据: {len(standard_records)} 期")

    # 2. 运行预测
    print("\n[2/4] 运行预测...")
    result = run_prediction_pipeline()

    latest = standard_records[-1]
    print(f"  最新期号: {latest['期号']} ({latest['特码生肖']})")

    if result.get("verified_period"):
        hit = "✅" if result["verified_hit"] else "❌"
        print(f"  验证 {result['verified_period']}: {result['verified_actual']} {hit}")

    print(f"  预测 {result['pending_period']}: {' '.join(result['pending_top6'])}")

    # 3. 保存结果
    print("\n[3/4] 保存结果...")
    output = {
        "version": datetime.now().isoformat(),
        "strategy": load_strategy().get("version"),
        "verified_period": result.get("verified_period"),
        "verified_hit": result.get("verified_hit"),
        "verified_actual": result.get("verified_actual"),
        "pending_period": result.get("pending_period"),
        "pending_top6": result.get("pending_top6"),
        "total_records": result.get("total_records"),
        "timestamp": datetime.now().isoformat(),
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {OUTPUT_FILE}")

    # 4. 推送通知
    print("\n[4/4] 推送通知...")
    send_notification(output)

    print("\n=== 完成 ===")
    return output


if __name__ == "__main__":
    main()