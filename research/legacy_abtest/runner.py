#!/usr/bin/env python3
"""
AB测试 CLI 入口
用法: python -m predictor.abtest.runner
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from predictor.abtest.loader import load_all_strategies
from predictor.abtest.metrics import rank_strategies
from predictor.abtest.report import print_report
from predictor.config import load_strategy


def main():
    """主入口"""
    print("加载策略数据...")

    all_data = load_all_strategies()
    print(f"加载了 {len(all_data)} 个策略")

    print("计算排名...")
    rankings = rank_strategies(all_data)

    # 获取当前活跃策略
    current_strategy_name = load_strategy().get("version", "unknown")

    print_report(rankings, current_strategy_name, all_data)


if __name__ == "__main__":
    main()
