#!/usr/bin/env python3
"""
Walk-forward 回测运行器
- 逐期进行回测预测，并记录结果到 version_book/{version}/backtest_ledger.jsonl
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Dict

# 添加路径（支持直接运行和模块导入）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.six_zodiac_predictor import predict_top6


# 版本配置
VERSIONS = {
    "v9": {
        "strategy_type": "pattern_based",
        "params": {
            "lookback": 13,
            "pattern_weight": 2.0,
            "gap_weight": 0.04,
            "trend_weight": 0.08,
            "variance_weight": 0.25,
            "alt_mode": "strict"
        },
        "notes": "原始v9版本，二元特征"
    },
    "v10": {
        "strategy_type": "pattern_based",
        "params": {
            "lookback": 13,
            "pattern_weight": 3.5,
            "gap_weight": 0.07,
            "trend_weight": 0.15,
            "variance_weight": 0.4,
            "alt_mode": "strict"
        },
        "notes": "参数优化版本"
    },
    "v11": {
        "strategy_type": "pattern_based",
        "params": {
            "lookback": 8,
            "pattern_weight": 2.65,
            "gap_weight": 0.056,
            "trend_weight": 0.099,
            "variance_weight": 0.304,
            "alt_mode": "strict"
        },
        "notes": "随机搜索找到的最佳参数"
    },
    "v12": {
        "strategy_type": "pattern_based",
        "params": {
            "lookback": 11,
            "pattern_weight": 1.45,
            "gap_weight": 0.098,
            "trend_weight": 0.267,
            "variance_weight": 0.177,
            "alt_mode": "trend"
        },
        "notes": "大规模随机搜索找到的新最佳参数"
    }
}


def get_version_dir(version: str) -> str:
    """获取版本目录路径"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    version_dir = os.path.join(base_dir, "version_book", version)
    os.makedirs(version_dir, exist_ok=True)
    return version_dir


def get_ledger_path(version: str) -> str:
    """获取账本文件路径"""
    return os.path.join(get_version_dir(version), "backtest_ledger.jsonl")


def write_backtest_record(version: str, record: Dict) -> None:
    """逐条写入回测记录到 JSONL 文件

    Args:
        version: 版本标识（如 "v12"）
        record: 回测记录字典
    """
    ledger_path = get_ledger_path(version)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_walkforward_backtest(
    standard: List[Dict],
    version: str,
    lookback: int,
    params: Dict,
    feature_type: str = "pattern_based"
) -> List[Dict]:
    """执行 walk-forward 回测

    对每一期使用其之前的历史数据进行预测，并与实际开奖结果对比。

    Args:
        standard: 标准化的历史记录列表（已按时间正序排列）
        version: 版本标识
        lookback: 最小历史期数（需要至少这么多期才能开始预测）
        params: 预测参数
        feature_type: 特征类型

    Returns:
        所有回测记录的列表
    """
    records = []

    for i in range(lookback, len(standard)):
        # 历史数据：不包括当前期
        history = standard[:i]

        # 预测
        top6 = predict_top6(history, params, feature_type)

        # 实际开奖结果
        current = standard[i]
        actual = current["特码生肖"]
        hit = actual in top6

        # 构建记录
        record = {
            "id": f"{current['期号']}_{version}",
            "issue": current["期号"],
            "version": version,
            "model": f"{version}_zigzag",
            "prediction": top6,
            "actual": actual,
            "hit": hit,
            "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "source": "backtest"
        }

        records.append(record)

        # 写入 JSONL
        write_backtest_record(version, record)

    return records


def generate_backtest_ledger(version: str = "v12") -> List[Dict]:
    """生成回测账本的主入口

    1. 获取所有历史数据
    2. 构建标准化记录
    3. 执行 walk-forward 回测
    4. 保存结果到 version_book/{version}/backtest_ledger.jsonl

    Args:
        version: 版本标识，默认为 "v12"

    Returns:
        所有回测记录的列表
    """
    if version not in VERSIONS:
        raise ValueError(f"未知版本: {version}，可用版本: {list(VERSIONS.keys())}")

    config = VERSIONS[version]

    print(f"开始生成回测账本: {version}")
    print(f"策略类型: {config['strategy_type']}")
    print(f"参数: {config['params']}")
    print(f"备注: {config['notes']}")

    # 获取所有历史数据
    print("获取历史数据...")
    raw_records = get_all_records([2024, 2025, 2026])
    print(f"原始记录: {len(raw_records)} 条")

    # 构建标准化记录
    standard = build_standard_records(raw_records)
    print(f"标准化记录: {len(standard)} 条")

    # 清空旧账本（如果存在）
    ledger_path = get_ledger_path(version)
    if os.path.exists(ledger_path):
        os.remove(ledger_path)
        print(f"已清空旧账本: {ledger_path}")

    # 执行 walk-forward 回测
    lookback = config["params"]["lookback"]
    params = config["params"]
    feature_type = config["strategy_type"]

    print(f"开始 walk-forward 回测 (lookback={lookback})...")
    records = run_walkforward_backtest(
        standard=standard,
        version=version,
        lookback=lookback,
        params=params,
        feature_type=feature_type
    )

    # 统计结果
    hits = sum(1 for r in records if r["hit"])
    total = len(records)
    hit_rate = hits / total * 100 if total > 0 else 0

    print(f"\n回测完成!")
    print(f"总期数: {total}")
    print(f"命中数: {hits}")
    print(f"命中率: {hit_rate:.2f}%")
    print(f"结果已写入: {ledger_path}")

    return records


if __name__ == "__main__":
    generate_backtest_ledger("v12")