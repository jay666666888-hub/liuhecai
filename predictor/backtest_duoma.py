#!/usr/bin/env python3
"""
多码预测器回测脚本

用法: python3 backtest_duoma.py [version] [top_k]

示例:
  python3 backtest_duoma.py v40 24
  python3 backtest_duoma.py v41 24
  python3 backtest_duoma.py v42 24
"""

import sys
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

def run_duoma_backtest(version: str = "v40", top_k: int = 24, strategy: str = None):
    """对多码预测器运行回测"""
    from predictor.predictor_registry import PredictorRegistry
    from predictor.data_fetcher import get_all_records, build_standard_records

    # 加载数据
    print(f"加载历史数据...")
    records = get_all_records([2024, 2025, 2026])
    standard = build_standard_records(records)
    print(f"总期数: {len(standard)}")

    # 扫描并加载预测器
    PredictorRegistry.scan()

    # 尝试获取预测器
    try:
        predictor = PredictorRegistry.get(version)
        print(f"已加载预测器: {version}")
    except Exception as e:
        print(f"无法加载 {version}: {e}")
        print(f"可用版本: {PredictorRegistry.list_versions()}")
        return

    print(f"predictor.params: {predictor.params}")
    print(f"predictor.DEFAULT_STRATEGY: {getattr(predictor, 'DEFAULT_STRATEGY', 'N/A')}")

    # 直接用 v40 的 predict() 方法，它内部硬编码了 strategy="freq_only"
    # 所以不需要从 params 读取 strategy
    lookback = predictor.params.get("lookback", 50)

    # 初始化变量
    hits = 0
    total = 0
    streak = 0
    max_streak = 0
    recent_results = []

    print(f"开始回测 (lookback={lookback})...")

    for i in range(lookback, len(standard)):
        history = standard[:i]

        # 预测 - v40.predict() 内部硬编码 strategy="freq_only"
        result = predictor.predict(history, top_k=top_k)
        prediction = result.prediction

        # 实际开奖结果
        current = standard[i]
        actual_number = current.get("特码号码")
        issue = current.get("期号")

        # 检查是否命中
        hit = actual_number in prediction if actual_number else False

        if hit:
            hits += 1
            streak = 0
        else:
            streak += 1
            max_streak = max(max_streak, streak)

        total += 1
        recent_results.append({
            "issue": issue,
            "hit": hit,
            "actual": actual_number,
            "prediction": prediction[:6] if prediction else [],  # 只保留前6个展示
        })

        if total % 100 == 0:
            print(f"  已处理 {total} 期, 当前命中率 {hits/total*100:.2f}%")

    # 计算统计
    hit_rate = hits / total if total > 0 else 0
    recent_100 = recent_results[-100:] if len(recent_results) >= 100 else recent_results
    recent_100_hits = sum(1 for r in recent_100 if r["hit"])
    recent_100_rate = recent_100_hits / len(recent_100) if recent_100 else 0
    recent_50 = recent_results[-50:] if len(recent_results) >= 50 else recent_results
    recent_50_hits = sum(1 for r in recent_50 if r["hit"])
    recent_50_rate = recent_50_hits / len(recent_50) if recent_50 else 0

    # 输出结果
    strategy_used = predictor.params.get("strategy", "freq_only")
    print(f"\n{'='*50}")
    print(f"回测结果: {version}")
    print(f"{'='*50}")
    print(f"策略: {strategy_used}")
    print(f"top_k: {top_k}")
    print(f"总期数: {total}")
    print(f"命中数: {hits}")
    print(f"命中率: {hit_rate*100:.2f}%")
    print(f"最近100期: {recent_100_rate*100:.2f}%")
    print(f"最近50期: {recent_50_rate*100:.2f}%")
    print(f"最大连错: {max_streak}")
    print(f"{'='*50}")

    return {
        "version": version,
        "strategy": strategy,
        "top_k": top_k,
        "total": total,
        "hits": hits,
        "hit_rate": hit_rate,
        "recent_100_rate": recent_100_rate,
        "recent_50_rate": recent_50_rate,
        "max_streak": max_streak,
    }


if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else "v40"
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    strategy = sys.argv[3] if len(sys.argv) > 3 else None

    result = run_duoma_backtest(version, top_k, strategy)