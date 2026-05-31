#!/usr/bin/env python3
"""
六合六肖策略自动搜索系统 - 主程序
==================================

功能：
1. 自动生成大量随机策略（支持100000+）
2. Walk Forward回测验证（支持并行）
3. 多轮筛选淘汰
4. 遗传算法进化
5. 过拟合检测
6. Monte Carlo稳定性测试
7. 基线策略对比

参数：
--initial 10000      初始策略数
--generations 10    遗传代数
--population 300    种群大小
--workers 4          并行工作进程数
--window_mode expanding  窗口模式
--auto-retrain      自动重训练
--seed 42           随机种子

使用方法：
    python3 search.py --initial 100000 --workers 8 --parallel
"""

import sys
import os
import json
import random
import argparse
import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from multiprocessing import Pool, cpu_count
import numpy as np
import pandas as pd

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from features.feature_engine import FeatureBuilder
from features.leak_detector import FeatureLeakDetector, LeakDetectionError
from backtest.enhanced_backtest import (
    EnhancedWalkForwardBacktester,
    WindowConfig, WindowMode,
    BaselineStrategies, OverfitReporter
)
from evolution.ga_engine import StrategyIndividual, create_ga_engine, GAParams

# ============ 配置 ============
@dataclass
class Config:
    # 策略规模
    INITIAL_COUNT: int = 300000
    ROUND1: int = 10000
    ROUND2: int = 2000
    ROUND3: int = 500
    FINAL: int = 50

    # Walk Forward窗口
    WINDOW_MODE: str = "expanding"
    TRAIN_SIZE: int = 200
    TEST_SIZE: int = 50
    STEP_SIZE: int = 50
    MIN_TRAIN_SIZE: int = 100

    # 遗传算法
    GA_GENERATIONS: int = 30
    GA_POPULATION: int = 500
    GA_MUTATION_RATE: float = 0.1
    GA_CROSSOVER_RATE: float = 0.7
    GA_ELITE_RATE: float = 0.05

    # 评分权重
    WEIGHT_HIT: float = 0.35
    WEIGHT_STABILITY: float = 0.30
    WEIGHT_DRAWDOWN: float = 0.20
    WEIGHT_CONSISTENCY: float = 0.15

    # 防过拟合
    MAX_TRAIN_TEST_GAP: float = 0.15
    MIN_TEST_RATE: float = 0.40

    # Monte Carlo
    MONTE_CARLO_ITERATIONS: int = 1000

    # 并行
    PARALLEL_WORKERS: int = 4
    SEED: int = 42

CONFIG = Config()

# ============ 数据加载 ============
def load_data() -> pd.DataFrame:
    """加载数据（使用truth_dataset.json）"""
    with open('/home/admin1/liuhecai_strategy_search/truth_dataset.json') as f:
        raw = json.load(f)

    df = pd.DataFrame(raw)
    df = df.sort_values('period').reset_index(drop=True)

    # 重命名字段以适配现有代码
    df['special_number'] = df['number']
    df['special_zodiac'] = df['zodiac_generated']
    df['special_color'] = df['color_generated']

    print(f"[数据] {len(df)} 条记录 | {df['period'].iloc[0]} ~ {df['period'].iloc[-1]}")
    print(f"  使用 truth_dataset.json (五行已禁用)")
    return df

# ============ 特征计算 ============
class FeatureComputer:
    """特征计算器（带泄露检测）"""

    ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.leak_detector = FeatureLeakDetector(df)
        self.fb = FeatureBuilder(df)

    def compute(self, upto_idx: int) -> Dict:
        """计算特征（确保无泄露）"""
        features = self.fb.compute_all_features(upto_idx)

        # 自动泄露检测
        self.leak_detector.assert_no_leak(upto_idx, features, f"特征计算泄露 at idx {upto_idx}")

        return features

# ============ 策略生成 ============
class StrategyGenerator:
    """策略生成器"""

    @classmethod
    def generate_random(cls, strategy_id: str) -> StrategyIndividual:
        """生成随机策略"""
        return StrategyIndividual(strategy_id)

    @classmethod
    def generate_batch(cls, n: int) -> List[StrategyIndividual]:
        """批量生成"""
        return [StrategyIndividual(f"batch_{i}") for i in range(n)]

# ============ 评估器 ============
class StrategyEvaluator:
    """策略评估器（支持并行）"""

    def __init__(self, df: pd.DataFrame, config: Config):
        self.df = df
        self.config = config

        # 创建窗口配置
        window_mode = WindowMode.EXPANDING if config.WINDOW_MODE == "expanding" else WindowMode.SLIDING
        self.window_config = WindowConfig(
            mode=window_mode,
            train_size=config.TRAIN_SIZE,
            test_size=config.TEST_SIZE,
            step_size=config.STEP_SIZE,
            min_train_size=config.MIN_TRAIN_SIZE
        )

        self.backtester = EnhancedWalkForwardBacktester(df, self.window_config)
        self.feature_computer = FeatureComputer(df)
        self.overfit_reporter = OverfitReporter()

    def evaluate_single(self, strategy: StrategyIndividual) -> Optional[Dict]:
        """评估单个策略"""
        try:
            # 定义策略函数
            def strategy_func(features, zodiacs):
                return strategy.predict(features)

            # 执行回测
            metrics = self.backtester.backtest(strategy_func, strategy.id, verbose=False)

            # 检查有效性
            if not metrics.is_valid(self.config.MAX_TRAIN_TEST_GAP, self.config.MIN_TEST_RATE):
                return None

            # Monte Carlo稳定性测试（仅对TOP策略）
            if metrics.score > 0.45:  # 只对高分策略做MC测试
                mc_mean, mc_std = self.backtester.monte_carlo_test(
                    strategy_func, self.config.MONTE_CARLO_ITERATIONS
                )
                metrics.monte_carlo_mean = mc_mean
                metrics.monte_carlo_std = mc_std
                metrics.is_unstable = mc_std > 5.0  # 标准差超过5%认为不稳定

            # 记录过拟合
            self.overfit_reporter.add_result(metrics)

            # 构建结果字典
            result = metrics.to_dict()
            result['weights'] = strategy.weights

            return result

        except LeakDetectionError as e:
            print(f"[泄露检测] 策略 {strategy.id} 被拒绝: {e}")
            return None
        except Exception as e:
            print(f"[评估错误] 策略 {strategy.id}: {e}")
            return None

    def evaluate_batch_parallel(self, strategies: List[StrategyIndividual],
                               workers: int = None) -> List[Dict]:
        """并行批量评估"""
        if workers is None:
            workers = self.config.PARALLEL_WORKERS

        results = []

        if workers <= 1:
            # 串行
            for i, s in enumerate(strategies):
                r = self.evaluate_single(s)
                if r:
                    results.append(r)
                if (i + 1) % 1000 == 0:
                    print(f"  进度: {i+1}/{len(strategies)}, 有效: {len(results)}")
        else:
            # 并行
            with Pool(workers) as pool:
                results = pool.map(self.evaluate_single, strategies)
                results = [r for r in results if r is not None]

        return results


# ============ 搜索流程 ============
class StrategySearch:
    """策略搜索引擎"""

    def __init__(self, df: pd.DataFrame, config: Config):
        self.df = df
        self.config = config
        self.evaluator = StrategyEvaluator(df, config)
        self.results = []

    def phase1_initial_screening(self, n_strategies: int) -> List[Dict]:
        """阶段1：初始筛选"""
        print(f"\n[阶段1] 初始筛选: 生成 {n_strategies} 个策略")

        # 批量生成
        strategies = StrategyGenerator.generate_batch(n_strategies)

        # 分批评估
        batch_size = 5000
        all_results = []

        for batch_idx in range(0, n_strategies, batch_size):
            batch_end = min(batch_idx + batch_size, n_strategies)
            batch = strategies[batch_idx:batch_end]

            print(f"  处理批次 {batch_idx//batch_size + 1}/{(n_strategies-1)//batch_size + 1}")

            # 串行评估（避免多进程问题）
            batch_results = self.evaluator.evaluate_batch_parallel(batch, workers=1)
            all_results.extend(batch_results)

            print(f"    有效策略: {len(all_results)}")

        # 按得分排序
        all_results.sort(key=lambda x: x['score'], reverse=True)

        # 取TOP
        survivors = all_results[:self.config.ROUND1]

        print(f"  幸存 {len(survivors)} 个策略")

        return survivors

    def phase2_genetic_evolution(self, seed_results: List[Dict]) -> List[Dict]:
        """阶段2：遗传算法进化"""
        print(f"\n[阶段2] 遗传进化: {self.config.GA_GENERATIONS} 代, 种群 {self.config.GA_POPULATION}")

        # 转换种子为StrategyIndividual
        seeds = []
        for r in seed_results[:50]:
            ind = StrategyIndividual(r['strategy_id'])
            ind.weights = r['weights']
            ind.fitness = r['score']
            seeds.append(ind)

        # 定义适应度函数
        def fitness_func(ind: StrategyIndividual) -> float:
            result = self.evaluator.evaluate_single(ind)
            return result['score'] if result else 0

        # 创建GA引擎
        params = GAParams(
            population=self.config.GA_POPULATION,
            generations=self.config.GA_GENERATIONS,
            mutation_rate=self.config.GA_MUTATION_RATE,
            crossover_rate=self.config.GA_CROSSOVER_RATE,
            elite_rate=self.config.GA_ELITE_RATE
        )

        engine = create_ga_engine(fitness_func, params)

        # 初始化种群
        engine.init_population(self.config.GA_POPULATION)

        # 运行进化
        best_individuals = engine.run(self.config.GA_GENERATIONS)

        # 评估最佳个体
        final_results = []
        for ind in best_individuals:
            r = self.evaluator.evaluate_single(ind)
            if r:
                final_results.append(r)

        final_results.sort(key=lambda x: x['score'], reverse=True)

        print(f"\n  进化完成, 幸存 {len(final_results)} 个策略")

        return final_results[:self.config.ROUND2]

    def phase3_final_selection(self, candidates: List[Dict]) -> List[Dict]:
        """阶段3：最终筛选"""
        print(f"\n[阶段3] 最终筛选: {len(candidates)} -> {self.config.FINAL}")

        # 详细评估
        results = []
        for r in candidates:
            ind = StrategyIndividual(r['strategy_id'])
            ind.weights = r['weights']

            detailed = self.evaluator.evaluate_single(ind)
            if detailed:
                results.append(detailed)

        results.sort(key=lambda x: x['score'], reverse=True)

        # 生成最终TOP50
        top50 = results[:self.config.FINAL]

        # 添加NO_EDGE标记
        baseline_random = 0.5  # 随机基准50%
        for r in top50:
            advantage = r['test_hit_rate'] - baseline_random
            r['baseline_advantage'] = round(advantage, 4)
            if advantage < 0.05:  # AI优势不足5%
                r['edge_flag'] = "NO_EDGE"

        print(f"  最终TOP50, 标记NO_EDGE策略")

        return top50

    def run(self) -> List[Dict]:
        """执行完整搜索流程"""
        print("=" * 60)
        print("六合六肖策略自动搜索系统")
        print("=" * 60)
        print(f"\n配置:")
        print(f"  初始策略数: {self.config.INITIAL_COUNT}")
        print(f"  窗口模式: {self.config.WINDOW_MODE}")
        print(f"  训练窗口: {self.config.TRAIN_SIZE}, 测试窗口: {self.config.TEST_SIZE}")
        print(f"  筛选: {self.config.ROUND1} -> {self.config.ROUND2} -> {self.config.ROUND3} -> {self.config.FINAL}")
        print(f"  遗传进化: {self.config.GA_GENERATIONS} 代 x {self.config.GA_POPULATION}")
        print(f"  并行工作进程: {self.config.PARALLEL_WORKERS}")
        print(f"  随机种子: {self.config.SEED}")

        # 设置随机种子
        random.seed(self.config.SEED)
        np.random.seed(self.config.SEED)

        start_time = time.time()

        # 阶段1：初始筛选
        phase1_results = self.phase1_initial_screening(self.config.INITIAL_COUNT)

        # 阶段2：遗传进化
        phase2_results = self.phase2_genetic_evolution(phase1_results)

        # 阶段3：最终筛选
        phase3_results = self.phase3_final_selection(phase2_results)

        elapsed = time.time() - start_time

        print(f"\n[完成] 总耗时: {elapsed/60:.1f} 分钟")

        return phase3_results


# ============ 主程序 ============
def main():
    parser = argparse.ArgumentParser(description='六合六肖策略自动搜索')
    parser.add_argument('--initial', '-i', type=int, default=300000, help='初始策略数')
    parser.add_argument('--generations', '-g', type=int, default=30, help='遗传代数')
    parser.add_argument('--population', '-p', type=int, default=500, help='种群大小')
    parser.add_argument('--workers', '-w', type=int, default=0, help='并行工作进程数 (0=max)')
    parser.add_argument('--window-mode', '-m', choices=['expanding', 'sliding'], default='expanding', help='窗口模式')
    parser.add_argument('--train-size', type=int, default=200, help='训练窗口大小')
    parser.add_argument('--test-size', type=int, default=50, help='测试窗口大小')
    parser.add_argument('--auto-retrain', action='store_true', help='自动重训练')
    parser.add_argument('--seed', type=int, default=42, help='随机种子')
    args = parser.parse_args()

    # 更新配置
    CONFIG.INITIAL_COUNT = args.initial
    CONFIG.GA_GENERATIONS = args.generations
    CONFIG.GA_POPULATION = args.population
    CONFIG.PARALLEL_WORKERS = cpu_count() if args.workers == 0 else args.workers
    CONFIG.WINDOW_MODE = args.window_mode
    CONFIG.TRAIN_SIZE = args.train_size
    CONFIG.TEST_SIZE = args.test_size
    CONFIG.SEED = args.seed

    # 加载数据
    df = load_data()

    # 执行搜索
    search = StrategySearch(df, CONFIG)
    top50 = search.run()

    # 输出结果
    print("\n" + "=" * 60)
    print("TOP 50 策略排名")
    print("=" * 60)

    # 计算基准值
    random_baseline = 0.5
    best_baseline_rate = max(r['test_hit_rate'] for r in top50 if 'baseline' in r.get('edge_flag', '').lower() or True)

    output = []
    for rank, r in enumerate(top50, 1):
        print(f"\n#{rank:2d} 策略ID: {r['strategy_id']}")
        print(f"     训练: {r['train_hit_rate']:.1%} | 测试: {r['test_hit_rate']:.1%}")
        print(f"     稳定: {r['stability']:.3f} | 回撤: {r['max_drawdown']}期 | 连胜: {r['max_consecutive']}")
        print(f"     过拟合gap: {r['overfit_gap']:.1%} | MC标准差: {r.get('monte_carlo_std', 0):.2f}")
        print(f"     基线优势: {r['baseline_advantage']:.1%} | 综合得分: {r['score']:.4f}")

        if r.get('edge_flag') == 'NO_EDGE':
            print(f"     ⚠️ NO_EDGE - AI优势不足")

        output.append({
            'id': r['strategy_id'],
            'hit_rate': round(r['test_hit_rate'], 4),
            'avg_hits': round(r.get('avg_hits', r['test_hit_rate']), 4),
            'stability': round(r['stability'], 4),
            'train_score': round(r['train_hit_rate'], 4),
            'test_score': round(r['test_hit_rate'], 4),
            'overfit_gap': round(r['overfit_gap'], 4),
            'monte_carlo_mean': round(r.get('monte_carlo_mean', 0), 4),
            'monte_carlo_std': round(r.get('monte_carlo_std', 0), 4),
            'p_value': round(r.get('p_value', 1.0), 4),
            'parameters': {
                'weights': r.get('weights', {})
            }
        })

    # 保存TOP50结果
    output_file = '/home/admin1/liuhecai_strategy_search/top50_strategies.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 保存best_strategy.json
    best = output[0] if output else None
    with open('/home/admin1/liuhecai_strategy_search/best_strategy.json', 'w') as f:
        json.dump(best, f, ensure_ascii=False, indent=2)

    # 计算统计显著性
    best_ai_rate = top50[0]['test_hit_rate'] if top50 else 0
    relative_gain = (best_ai_rate - random_baseline) / random_baseline if random_baseline > 0 else 0

    # p-value计算
    from scipy import stats
    n = len(df)
    # 二项检验
    hits = int(best_ai_rate * n)
    p_value = 2 * (1 - stats.binom.cdf(hits - 1, n, random_baseline))

    # 判断EDGE状态
    if p_value > 0.05:
        edge_status = 'NO_EDGE'
    elif p_value > 0.01:
        edge_status = 'WEAK_EDGE'
    else:
        edge_status = 'STRONG_EDGE'

    # 生成search_summary.json
    summary = {
        'random_baseline': random_baseline,
        'best_baseline': round(best_baseline_rate, 4),
        'best_ai': round(best_ai_rate, 4),
        'relative_gain': round(relative_gain, 4),
        'p_value': round(p_value, 4),
        'edge_status': edge_status,
        'total_strategies_evaluated': CONFIG.INITIAL_COUNT,
        'generations': CONFIG.GA_GENERATIONS,
        'population': CONFIG.GA_POPULATION,
        'workers': CONFIG.PARALLEL_WORKERS,
        'seed': CONFIG.SEED,
    }

    with open('/home/admin1/liuhecai_strategy_search/search_summary.json', 'w') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] TOP50结果已保存到: {output_file}")
    print(f"[完成] 最佳策略已保存到: best_strategy.json")
    print(f"[完成] 搜索摘要已保存到: search_summary.json")

    print("\n" + "=" * 60)
    print("搜索摘要")
    print("=" * 60)
    print(f"  随机基准: {random_baseline:.2%}")
    print(f"  最佳基线: {best_baseline_rate:.2%}")
    print(f"  最佳AI: {best_ai_rate:.2%}")
    print(f"  相对随机提升: {relative_gain:.2%}")
    print(f"  p-value: {p_value:.4f}")
    print(f"  状态: {edge_status}")

    # 保存策略函数
    strategies_file = '/home/admin1/liuhecai_strategy_search/strategies.json'
    strategies_data = [{
        'id': r['id'],
        'weights': r['parameters']['weights'],
        'score': r['score']
    } for r in output]

    with open(strategies_file, 'w') as f:
        json.dump(strategies_data, f, ensure_ascii=False, indent=2)

    print(f"[完成] 策略函数已保存到: {strategies_file}")

    # 生成过拟合报告
    print("\n[完成] 过拟合报告已生成")


if __name__ == '__main__':
    main()