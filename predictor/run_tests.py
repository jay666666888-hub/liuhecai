#!/usr/bin/env python3
"""
测试运行器 - 替代 pytest
当 pytest 不可用时使用此脚本运行测试

用法:
    python3 run_tests.py
    python3 run_tests.py test_zodiac_mapping
    python3 -m pytest tests/test_zodiac_mapping.py  # 如果安装了 pytest
"""

import sys
import os

# 获取项目根目录 (predictor 的父目录)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


def run_test_module(module_name):
    """运行指定测试模块"""
    try:
        module = __import__(f'tests.{module_name}', fromlist=[''])
        print(f"\n{'='*60}")
        print(f"运行测试: {module_name}")
        print('='*60)

        # 获取所有 test_ 开头的函数
        test_funcs = [name for name in dir(module) if name.startswith('test_')]

        passed = 0
        failed = 0

        for func_name in test_funcs:
            func = getattr(module, func_name)
            try:
                print(f"\n--- {func_name} ---")
                func()
                print(f"✓ {func_name}")
                passed += 1
            except AssertionError as e:
                print(f"✗ {func_name}: {e}")
                failed += 1
            except Exception as e:
                print(f"✗ {func_name}: 异常 {e}")
                failed += 1

        print(f"\n{'='*60}")
        print(f"结果: {passed} 通过, {failed} 失败")
        print('='*60)

        return failed == 0

    except ImportError as e:
        print(f"无法导入测试模块: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("运行所有测试")
    print("="*60)

    test_modules = [
        'test_zodiac_mapping',
        'test_backtest_integrity',
        'test_data_consistency',
    ]

    total_passed = 0
    total_failed = 0

    for module_name in test_modules:
        try:
            module = __import__(f'tests.{module_name}', fromlist=[''])
            test_funcs = [name for name in dir(module) if name.startswith('test_')]

            for func_name in test_funcs:
                func = getattr(module, func_name)
                try:
                    print(f"  {module_name}.{func_name} ... ", end='', flush=True)
                    func()
                    print("✓")
                    total_passed += 1
                except AssertionError as e:
                    print(f"✗ ({str(e)[:50]}...)")
                    total_failed += 1
                except Exception as e:
                    print(f"✗ (异常)")
                    total_failed += 1

        except ImportError as e:
            print(f"  {module_name}: 无法导入 ({e})")

    print("\n" + "="*60)
    print(f"总计: {total_passed} 通过, {total_failed} 失败")
    print('='*60)

    return total_failed == 0


if __name__ == '__main__':
    if len(sys.argv) > 1:
        module_name = sys.argv[1].replace('.py', '').replace('test_', '')
        if not module_name.startswith('test_'):
            module_name = 'test_' + module_name
        success = run_test_module(module_name)
    else:
        success = run_all_tests()

    sys.exit(0 if success else 1)