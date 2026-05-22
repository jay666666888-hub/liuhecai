#!/usr/bin/env python3
"""
回测报告 CLI 入口
用法: python -m predictor.backtest.runner
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from predictor.backtest.loader import load_backtest_data
from predictor.backtest.metrics import calc_all_metrics
from predictor.backtest.report import print_report


def main():
    """主入口"""
    print("加载回测数据...")

    records = load_backtest_data()

    if not records:
        print("⚠️  无历史预测数据")
        return

    print(f"加载了 {len(records)} 条记录")

    metrics = calc_all_metrics(records)
    print_report(metrics, records)


if __name__ == "__main__":
    main()
