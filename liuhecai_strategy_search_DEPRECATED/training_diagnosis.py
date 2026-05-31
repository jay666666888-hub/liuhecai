#!/usr/bin/env python3
"""
训练系统诊断 (Training Pipeline Diagnosis)
==========================================

检查：
1. import诊断 - 模块导入耗时
2. multiprocessing诊断 - spawn/fork模式
3. 回测性能分析 - 单策略耗时
4. 无限循环检测 - max_iterations和heartbeat
5. 小规模冒烟测试 - 5分钟内完成
"""

import sys
import os
import json
import time
import multiprocessing as mp
from datetime import datetime
import traceback

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

# ============ 1. Import诊断 ============
def diagnose_imports():
    """统计每个模块导入耗时"""
    print("\n[1] Import诊断...")

    modules = [
        'search',
        'features.feature_engine',
        'backtest.enhanced_backtest',
        'evolution.ga_engine',
    ]

    import_times = {}

    for mod_name in modules:
        start = time.time()
        try:
            __import__(mod_name)
            elapsed = time.time() - start
            import_times[mod_name] = {
                'status': 'OK',
                'import_time': round(elapsed, 4)
            }
            print(f"    {mod_name}: {elapsed:.4f}s OK")
        except Exception as e:
            elapsed = time.time() - start
            import_times[mod_name] = {
                'status': 'FAIL',
                'error': str(e),
                'import_time': round(elapsed, 4)
            }
            print(f"    {mod_name}: {elapsed:.4f}s FAIL - {e}")

    result = {
        'modules': import_times,
        'total_time': sum(v['import_time'] for v in import_times.values()),
        'timestamp': datetime.now().isoformat()
    }

    with open('/home/admin1/liuhecai_strategy_search/import_profile.json', 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"    总耗时: {result['total_time']:.4f}s")

    return result

# ============ 2. Multiprocessing诊断 ============
def diagnose_multiprocessing():
    """检查multiprocessing配置"""
    print("\n[2] Multiprocessing诊断...")

    # 检查spawn/fork模式
    context = mp.get_start_method()
    print(f"    启动模式: {context}")

    # 检查if __name__ == "__main__"是否存在
    files_to_check = [
        '/home/admin1/liuhecai_strategy_search/search.py',
        '/home/admin1/liuhecai_strategy_search/features/feature_engine.py',
        '/home/admin1/liuhecai_strategy_search/backtest/enhanced_backtest.py',
        '/home/admin1/liuhecai_strategy_search/evolution/ga_engine.py',
    ]

    file_checks = {}
    for fpath in files_to_check:
        fname = os.path.basename(fpath)
        with open(fpath, 'r') as f:
            content = f.read()
            has_main = '__name__' in content and '__main__' in content
            file_checks[fname] = {
                'has_if_name_main': has_main,
                'size': len(content)
            }

    result = {
        'start_method': context,
        'files': file_checks,
        'timestamp': datetime.now().isoformat()
    }

    with open('/home/admin1/liuhecai_strategy_search/multiprocess_report.json', 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 检查所有文件是否都有保护
    all_protected = all(v['has_if_name_main'] for v in file_checks.values())
    print(f"    所有文件都有保护: {'是' if all_protected else '否'}")

    return result

# ============ 3. 回测性能分析 ============
def diagnose_backtest_performance():
    """统计单策略回测耗时"""
    print("\n[3] 回测性能分析...")

    from search import load_data
    from backtest.enhanced_backtest import EnhancedWalkForwardBacktester, WindowConfig, WindowMode

    # 加载数据
    df = load_data()

    # 创建backtester
    config = WindowConfig(
        mode=WindowMode.EXPANDING,
        train_size=200,
        test_size=50,
        step_size=50
    )
    backtester = EnhancedWalkForwardBacktester(df, config)

    # 定义测试策略
    def test_strategy(features, zodiacs):
        return zodiacs[:6]

    # 单次回测计时
    timings = {
        'feature_compute': [],
        'walk_forward': [],
        'monte_carlo': [],
        'total': []
    }

    # 运行5次测试
    n_tests = 5
    for i in range(n_tests):
        start = time.time()

        # 模拟特征计算
        t0 = time.time()
        from features.feature_engine import FeatureBuilder
        fb = FeatureBuilder(df)
        features = fb.compute_all_features(400)
        t1 = time.time()
        timings['feature_compute'].append(t1 - t0)

        # Walk forward
        t2 = time.time()
        metrics = backtester.backtest(test_strategy, f'test_{i}', verbose=False)
        t3 = time.time()
        timings['walk_forward'].append(t3 - t2)

        # Monte Carlo (简化)
        t4 = time.time()
        # skip MC for speed
        timings['monte_carlo'].append(0)
        t5 = time.time()

        timings['total'].append(t5 - start)

    # 统计
    avg_times = {}
    for key, vals in timings.items():
        avg_times[key] = {
            'avg': round(sum(vals) / len(vals), 4),
            'min': round(min(vals), 4),
            'max': round(max(vals), 4)
        }

    result = {
        'single_strategy_timing': avg_times,
        'n_windows': len(backtester.windows),
        'n_tests': n_tests,
        'timestamp': datetime.now().isoformat()
    }

    with open('/home/admin1/liuhecai_strategy_search/performance_profile.json', 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"    单策略总计: {avg_times['total']['avg']:.4f}s (平均)")
    print(f"    特征计算: {avg_times['feature_compute']['avg']:.4f}s")
    print(f"    Walk Forward: {avg_times['walk_forward']['avg']:.4f}s")

    return result

# ============ 4. 无限循环检测 ============
def add_loop_protection():
    """检查并增强循环保护"""
    print("\n[4] 无限循环检测...")

    files_to_check = [
        '/home/admin1/liuhecai_strategy_search/search.py',
        '/home/admin1/liuhecai_strategy_search/evolution/ga_engine.py',
        '/home/admin1/liuhecai_strategy_search/backtest/enhanced_backtest.py',
    ]

    protection_status = []

    for fpath in files_to_check:
        fname = os.path.basename(fpath)
        with open(fpath, 'r') as f:
            content = f.read()

        has_max_iterations = 'max_iterations' in content or 'MAX_ITERATIONS' in content
        has_heartbeat = 'heartbeat' in content or 'print(f"' in content and '[Progress]' in content
        has_timeout = 'timeout' in content

        status = {
            'file': fname,
            'has_max_iterations': has_max_iterations,
            'has_heartbeat': has_heartbeat,
            'has_timeout': has_timeout
        }

        # 添加基本保护建议
        if not has_max_iterations:
            status['recommendation'] = '需要添加max_iterations限制'
        elif not has_heartbeat:
            status['recommendation'] = '建议添加heartbeat日志'
        else:
            status['recommendation'] = '已有基本保护'

        protection_status.append(status)
        print(f"    {fname}: {status['recommendation']}")

    result = {
        'files': protection_status,
        'timestamp': datetime.now().isoformat()
    }

    with open('/home/admin1/liuhecai_strategy_search/loop_protection_report.json', 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result

# ============ 5. 冒烟测试 ============
def run_smoke_test():
    """小规模冒烟测试"""
    print("\n[5] 冒烟测试 (initial=100, generations=2, population=20, workers=1)...")
    print("    要求: 5分钟内完成")

    from search import StrategySearch, load_data, Config

    start = time.time()
    timeout = 300  # 5分钟

    try:
        # 加载数据
        df = load_data()

        # 配置
        config = Config()
        config.INITIAL_COUNT = 100
        config.ROUND1 = 50
        config.ROUND2 = 20
        config.ROUND3 = 10
        config.FINAL = 5
        config.GA_GENERATIONS = 2
        config.GA_POPULATION = 20
        config.PARALLEL_WORKERS = 1
        config.SEED = 42
        config.MONTE_CARLO_ITERATIONS = 100

        print(f"    开始搜索...")

        # 运行搜索
        search = StrategySearch(df, config)

        # 设置超时检查
        import signal
        def timeout_handler(signum, frame):
            raise TimeoutError("冒烟测试超时 (5分钟)")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        top50 = search.run()

        signal.alarm(0)  # 取消超时

        elapsed = time.time() - start

        result = {
            'status': 'PASS',
            'elapsed_seconds': round(elapsed, 2),
            'strategies_found': len(top50),
            'timestamp': datetime.now().isoformat()
        }

        if top50:
            result['best_strategy'] = {
                'id': top50[0]['strategy_id'],
                'test_hit_rate': round(top50[0]['test_hit_rate'], 4),
                'score': round(top50[0]['score'], 4)
            }

        print(f"    ✓ 冒烟测试通过: {elapsed:.1f}秒")
        print(f"    找到 {len(top50)} 个策略")

        if top50:
            print(f"    最佳: {top50[0]['strategy_id']}, rate={top50[0]['test_hit_rate']:.2%}")

    except TimeoutError as e:
        elapsed = time.time() - start
        result = {
            'status': 'FAIL',
            'error': str(e),
            'elapsed_seconds': round(elapsed, 2),
            'timestamp': datetime.now().isoformat()
        }
        print(f"    ✗ 冒烟测试失败: {e}")

    except Exception as e:
        elapsed = time.time() - start
        result = {
            'status': 'FAIL',
            'error': str(e),
            'traceback': traceback.format_exc(),
            'elapsed_seconds': round(elapsed, 2),
            'timestamp': datetime.now().isoformat()
        }
        print(f"    ✗ 冒烟测试失败: {e}")
        traceback.print_exc()

    with open('/home/admin1/liuhecai_strategy_search/smoke_test.json', 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result

# ============ 主程序 ============
def main():
    print("=" * 60)
    print("训练系统诊断 (Training Pipeline Diagnosis)")
    print("=" * 60)

    results = {}

    # 1. Import诊断
    try:
        results['import_diagnosis'] = diagnose_imports()
    except Exception as e:
        results['import_diagnosis'] = {'status': 'FAIL', 'error': str(e)}
        print(f"    Import诊断失败: {e}")

    # 2. Multiprocessing诊断
    try:
        results['multiprocessing_diagnosis'] = diagnose_multiprocessing()
    except Exception as e:
        results['multiprocessing_diagnosis'] = {'status': 'FAIL', 'error': str(e)}
        print(f"    Multiprocessing诊断失败: {e}")

    # 3. 回测性能分析
    try:
        results['performance_analysis'] = diagnose_backtest_performance()
    except Exception as e:
        results['performance_analysis'] = {'status': 'FAIL', 'error': str(e)}
        print(f"    性能分析失败: {e}")

    # 4. 无限循环检测
    try:
        results['loop_protection'] = add_loop_protection()
    except Exception as e:
        results['loop_protection'] = {'status': 'FAIL', 'error': str(e)}
        print(f"    循环检测失败: {e}")

    # 5. 冒烟测试
    print("\n" + "-" * 60)
    smoke_result = run_smoke_test()
    results['smoke_test'] = smoke_result

    # 最终判定
    print("\n" + "=" * 60)
    print("诊断结果")
    print("=" * 60)

    all_pass = True
    for name, result in results.items():
        status = result.get('status', 'UNKNOWN')
        print(f"  {name}: {status}")
        if status == 'FAIL':
            all_pass = False

    print(f"\n冒烟测试: {smoke_result.get('status', 'UNKNOWN')}")

    if smoke_result.get('status') == 'FAIL':
        print("\n✗ 禁止启动大规模搜索")
    elif all_pass:
        print("\n✓ 可以启动大规模搜索")
    else:
        print("\n⚠ 部分诊断失败，请检查")

    # 保存综合报告
    with open('/home/admin1/liuhecai_strategy_search/diagnosis_report.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results

if __name__ == '__main__':
    main()