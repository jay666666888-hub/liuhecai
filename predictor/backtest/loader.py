#!/usr/bin/env python3
"""
数据加载层：统一历史预测记录
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HISTORY_FILE = os.path.join(BASE_DIR, "liuhecai_prediction_history.json")


def load_prediction_history() -> List[Dict]:
    """加载预测历史记录"""
    if not os.path.exists(HISTORY_FILE):
        return []

    with open(HISTORY_FILE) as f:
        data = json.load(f)

    # 转换为统一格式
    records = []
    for item in data:
        record = {
            "issue": item.get("期号", ""),
            "prediction": item.get("top6", []),
            "actual": item.get("actual", ""),
            "hit": item.get("hit", False),
            "timestamp": item.get("timestamp", ""),
        }
        records.append(record)

    return records


def merge_with_verification(records: List[Dict]) -> List[Dict]:
    """合并验证状态（pending_period 标记为待验证）"""
    from predictor.config import load_verification_state

    state = load_verification_state()
    pending_period = state.get("pending_period")
    pending_top6 = state.get("pending_top6", [])

    # 标记待验证的记录
    for record in records:
        if record["issue"] == pending_period:
            record["prediction"] = pending_top6
            record["pending"] = True
        else:
            record["pending"] = False

    return records


def get_recent_records(records: List[Dict], n: int) -> List[Dict]:
    """获取最近 n 条记录"""
    return records[-n:] if len(records) >= n else records


def load_backtest_data() -> List[Dict]:
    """加载完整的回测数据（主入口）"""
    records = load_prediction_history()

    if not records:
        return []

    # 按期号排序
    records.sort(key=lambda x: x["issue"])

    # 合并验证状态
    records = merge_with_verification(records)

    return records


if __name__ == "__main__":
    data = load_backtest_data()
    print(f"加载了 {len(data)} 条记录")
    if data:
        print(f"最新: {data[-1]}")
