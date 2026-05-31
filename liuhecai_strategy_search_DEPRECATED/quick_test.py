#!/usr/bin/env python3
"""
快速测试脚本 - 验证系统功能
"""

import sys
import os
import json

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

from features.feature_engine import FeatureBuilder
from backtest.enhanced_backtest import (
    EnhancedWalkForwardBacktester,
    WindowConfig, WindowMode,
    BaselineStrategies
)

def main():
    print("=" * 60)
    print("六合六肖策略搜索系统 - 快速测试")
    print("=" * 60)

    # 加载数据
    print("\n[1] 加载数据...")
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    import pandas as pd
    df = pd.DataFrame(data)
    print(f"    数据: {len(df)} 条 | {df['period'].iloc[0]} ~ {df['period'].iloc[-1]}")

    # 测试特征计算
    print("\n[2] 测试特征计算...")
    fb = FeatureBuilder(df)
    features = fb.compute_all_features(300)
    print(f"    生成特征: {len(features)} 个")

    # 测试Walk Forward
    print("\n[3] 测试Walk Forward回测...")
    config = WindowConfig(
        mode=WindowMode.EXPANDING,
        train_size=200,
        test_size=50,
        step_size=50
    )

    backtester = EnhancedWalkForwardBacktester(df, config)
    print(f"    窗口数: {len(backtester.windows)}")

    # 回测基线策略
    print("\n[4] 回测基线策略...")

    baselines = {
        '随机基准': BaselineStrategies.random_strategy,
        '频率策略': BaselineStrategies.frequency_strategy,
        '冷热策略': BaselineStrategies.hot_cold_strategy,
        '马尔可夫': BaselineStrategies.markov_strategy,
    }

    results = {}
    for name, func in baselines.items():
        metrics = backtester.backtest(func, name, verbose=True)
        results[name] = metrics.test_hit_rate
        print(f"    {name}: {metrics.test_hit_rate:.1%}")

    # 显示AI需要超过的基准
    print("\n[5] 基线对比基准:")
    print(f"    随机基准: 50.0%")
    print(f"    最佳基线: {max(results.values()):.1%}")
    print(f"    AI需要超过: {max(results.values()) + 0.05:.1%} 才能标记为有效")

    print("\n" + "=" * 60)
    print("快速测试完成！")
    print("=" * 60)
    print("\n运行完整搜索:")
    print("  cd /home/admin1/liuhecai_strategy_search")
    print("  source venv/bin/activate")
    print("  python3 search.py --initial 10000 --workers 4")

if __name__ == '__main__':
    main()