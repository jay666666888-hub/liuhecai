#!/usr/bin/env python3
"""
澳门六合预测系统 - 主入口
每日 21:35 cron 触发

⚠️ DEPRECATED (2026-05-25)
此文件已被 scripts/run_pipeline.py 替代。
统一入口：使用 Orchestrator，数据源为 aggregated_live.jsonl
保留此文件仅用于向后兼容。
"""

import json
import sys
import os
import traceback
from datetime import datetime
from typing import Optional

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.six_zodiac_predictor import run_prediction_pipeline, predict_next
from predictor.config import load_strategy, save_strategy
from predictor.notification import send_notification

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "liuhecai_prediction.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def get_log_file() -> str:
    """获取当日日志文件"""
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"liuhecai_{today}.log")


def log(message: str, level: str = "INFO") -> None:
    """结构化日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)

    # 写入日志文件
    log_file = get_log_file()
    with open(log_file, "a") as f:
        f.write(log_line + "\n")


def main() -> Optional[dict]:
    """主流程（带异常处理和日志）"""
    log("=" * 50)
    log("澳门六合预测系统启动")
    log("=" * 50)

    result = None

    try:
        # 1. 获取数据
        log("[1/4] 获取数据...")
        records = get_all_records([2024, 2025, 2026])
        standard_records = build_standard_records(records)
        log(f"  数据: {len(standard_records)} 期")
        log(f"  输入数据: 最新期号={records[-1]['expect']}, 特码={records[-1]['zodiac'].split(',')[6]}")

        # 2. 运行预测
        log("[2/4] 运行预测...")
        result = run_prediction_pipeline()

        latest = standard_records[-1]
        log(f"  最新期号: {latest['期号']} ({latest['特码生肖']})")

        if result.get("verified_period"):
            hit = "✅" if result["verified_hit"] else "❌"
            log(f"  验证 {result['verified_period']}: {result['verified_actual']} {hit}")

        log(f"  预测输出: period={result['pending_period']}, top6={' '.join(result['pending_top6'])}")

        # 3. 保存结果
        log("[3/4] 保存结果...")
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
        log(f"  已保存: {OUTPUT_FILE}")

        # 4. 推送通知
        log("[4/4] 推送通知...")
        push_success = send_notification(output)
        log(f"  推送决策: {'成功' if push_success else '失败/跳过'}")

        log("=" * 50)
        log("完成")
        log("=" * 50)

    except Exception as e:
        log(f"异常: {e}", "ERROR")
        log(f"堆栈: {traceback.format_exc()}", "ERROR")
        log("继续下一轮...", "WARN")
        return None

    return result


if __name__ == "__main__":
    main()