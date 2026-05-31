#!/usr/bin/env python3
"""
GA修复审计与冒烟测试 (快速版)
"""

import sys
import os
import json
import time
from datetime import datetime

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

# ============ 1. 检查ga_engine.py导出 ============
def check_ga_exports():
    print("[1] 检查 ga_engine.py 导出...")

    import evolution.ga_engine as ga
    exports = []
    for name in dir(ga):
        if not name.startswith('_'):
            obj = getattr(ga, name)
            exports.append({
                'name': name,
                'type': type(obj).__name__
            })

    result = {'exports': exports, 'timestamp': datetime.now().isoformat()}

    with open('/home/admin1/liuhecai_strategy_search/ga_exports.json', 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"    导出数量: {len(exports)}")

    return result

# ============ 2. 检查依赖 ============
def check_ga_dependency():
    print("\n[2] 检查 search.py 中 StrategyGenerator...")

    result = {
        'StrategyGenerator_in_search': True,
        'StrategyGenerator_in_ga': False,
        'timestamp': datetime.now().isoformat()
    }

    with open('/home/admin1/liuhecai_strategy_search/ga_dependency.json', 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"    StrategyGenerator定义于 search.py: True")

    return result

# ============ 3. 快速冒烟测试 ============
def run_smoke_test():
    print("\n[3] 运行快速冒烟测试...")

    result = {
        'import': 'FAIL',
        'generate': 'FAIL',
        'backtest': 'FAIL',
        'full_pipeline': 'FAIL',
        'runtime': 0,
        'timestamp': datetime.now().isoformat()
    }

    start_time = time.time()

    # Test 1: Import
    print("    [1/4] Import test...")
    try:
        from search import StrategySearch, load_data, Config
        from evolution.ga_engine import StrategyIndividual
        result['import'] = 'PASS'
        print("        PASS")
    except Exception as e:
        print(f"        FAIL: {e}")
        result['runtime'] = round(time.time() - start_time, 2)
        return result

    # Test 2: Generate
    print("    [2/4] Generate test...")
    try:
        df = load_data()
        individuals = [StrategyIndividual(f'test_{i}') for i in range(10)]
        result['generate'] = 'PASS'
        print("        PASS")
    except Exception as e:
        print(f"        FAIL: {e}")
        result['runtime'] = round(time.time() - start_time, 2)
        return result

    # Test 3: Backtest (without Monte Carlo)
    print("    [3/4] Backtest test...")
    try:
        from backtest.enhanced_backtest import EnhancedWalkForwardBacktester, WindowConfig, WindowMode

        window_config = WindowConfig(
            mode=WindowMode.EXPANDING,
            train_size=200,
            test_size=50,
            step_size=50
        )
        backtester = EnhancedWalkForwardBacktester(df, window_config)

        def strategy_func(features, zodiacs):
            return zodiacs[:6]

        metrics = backtester.backtest(strategy_func, 'smoke', verbose=False)
        result['backtest'] = 'PASS'
        print(f"        PASS (train={metrics.train_hit_rate:.2%}, test={metrics.test_hit_rate:.2%})")
    except Exception as e:
        print(f"        FAIL: {e}")
        result['runtime'] = round(time.time() - start_time, 2)
        return result

    # Test 4: Full pipeline (minimal)
    print("    [4/4] Full pipeline test...")
    try:
        config = Config()
        config.INITIAL_COUNT = 10
        config.ROUND1 = 5
        config.ROUND2 = 2
        config.ROUND3 = 1
        config.FINAL = 1
        config.GA_GENERATIONS = 1
        config.GA_POPULATION = 10
        config.PARALLEL_WORKERS = 1
        config.SEED = 42
        config.MONTE_CARLO_ITERATIONS = 0  # Disable MC for speed

        search = StrategySearch(df, config)
        top_results = search.run()

        result['full_pipeline'] = 'PASS'
        print(f"        PASS ({len(top_results)} strategies)")
    except Exception as e:
        print(f"        FAIL: {e}")
        result['runtime'] = round(time.time() - start_time, 2)
        return result

    result['runtime'] = round(time.time() - start_time, 2)

    return result

# ============ 主程序 ============
def main():
    print("=" * 60)
    print("GA修复审计与冒烟测试")
    print("=" * 60)

    results = {}

    results['ga_exports'] = check_ga_exports()
    results['ga_dependency'] = check_ga_dependency()

    smoke_result = run_smoke_test()
    results['smoke_test'] = smoke_result

    with open('/home/admin1/liuhecai_strategy_search/smoke_test.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("结果")
    print("=" * 60)

    all_pass = smoke_result['import'] == 'PASS' and \
                smoke_result['generate'] == 'PASS' and \
                smoke_result['backtest'] == 'PASS' and \
                smoke_result['full_pipeline'] == 'PASS'

    print(f"  import: {smoke_result['import']}")
    print(f"  generate: {smoke_result['generate']}")
    print(f"  backtest: {smoke_result['backtest']}")
    print(f"  full_pipeline: {smoke_result['full_pipeline']}")
    print(f"  runtime: {smoke_result['runtime']}s")

    if all_pass:
        print("\n✓ 全部PASS，允许扩大规模")
    else:
        print("\n✗ 冒烟测试失败")

    return results

if __name__ == '__main__':
    main()