#!/usr/bin/env python3
"""
Walk Forward 回测引擎
=====================

核心功能：
1. 滚动窗口验证 - 防止数据泄露
2. 多指标评估 - 命中率、稳定性、回撤等
3. 防过拟合检测

窗口策略：
- 训练200期，测试50期
- 滚动前进，直到数据结束
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import json
from features.feature_engine import FeatureBuilder, ZodiacScorer

@dataclass
class BacktestResult:
    """回测结果数据类"""
    strategy_id: str
    strategy_name: str = ""

    # 整体统计
    total_windows: int = 0
    total_tests: int = 0
    total_hits: int = 0

    # 训练/测试分开统计
    train_hit_rates: List[float] = field(default_factory=list)
    test_hit_rates: List[float] = field(default_factory=list)

    # 综合得分
    train_hit_rate: float = 0
    test_hit_rate: float = 0
    stability: float = 0
    max_drawdown: int = 0
    max_consecutive: int = 0
    consistency: float = 0
    sharpe_ratio: float = 0
    score: float = 0

    # 每期详细结果
    period_results: List[Dict] = field(default_factory=list)

    def is_valid(self, max_gap: float = 0.25, min_test_rate: float = 0.40) -> bool:
        """验证策略是否有效（防过拟合）"""
        # 训练/测试差距检验
        if self.train_hit_rate - self.test_hit_rate > max_gap:
            return False

        # 测试命中率下限
        if self.test_hit_rate < min_test_rate:
            return False

        return True

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'total_windows': self.total_windows,
            'train_hit_rate': round(self.train_hit_rate, 4),
            'test_hit_rate': round(self.test_hit_rate, 4),
            'stability': round(self.stability, 4),
            'max_drawdown': self.max_drawdown,
            'max_consecutive': self.max_consecutive,
            'consistency': round(self.consistency, 4),
            'sharpe_ratio': round(self.sharpe_ratio, 4),
            'score': round(self.score, 4),
        }


class WalkForwardBacktester:
    """Walk Forward 回测器"""

    def __init__(self, df: pd.DataFrame,
                 train_size: int = 200,
                 test_size: int = 50,
                 min_train_size: int = 100):
        """
        初始化回测器

        Args:
            df: 开奖数据DataFrame
            train_size: 训练窗口大小
            test_size: 测试窗口大小
            min_train_size: 最小训练数据量
        """
        self.df = df
        self.train_size = train_size
        self.test_size = test_size
        self.min_train_size = min_train_size

        self.feature_builder = FeatureBuilder(df)
        self.zodiac_scorer = ZodiacScorer(self.feature_builder)

        # 构建滚动窗口
        self.windows = self._build_windows()

    def _build_windows(self) -> List[Tuple[int, int, int]]:
        """
        构建所有滚动窗口

        Returns:
            List of (train_end_idx, test_start_idx, test_end_idx)
        """
        windows = []
        total = len(self.df)

        start = self.min_train_size
        while start + self.test_size <= total:
            train_end = start
            test_start = start
            test_end = start + self.test_size
            windows.append((train_end, test_start, test_end))
            start += self.test_size

        return windows

    def backtest_strategy(self, strategy_id: str,
                          strategy_func,  # 策略函数，接收features返回top6
                          verbose: bool = False) -> BacktestResult:
        """
        对单个策略执行Walk Forward回测

        Args:
            strategy_id: 策略ID
            strategy_func: 策略函数(features) -> List[str] (六肖列表)

        Returns:
            BacktestResult
        """
        if len(self.windows) < 3:
            return BacktestResult(strategy_id=strategy_id)

        train_rates = []
        test_rates = []
        period_results = []

        for window_idx, (train_end, test_start, test_end) in enumerate(self.windows):
            # ========== 训练阶段 ==========
            # 用train_end之前的数据训练
            train_features = self.feature_builder.compute_all_features(train_end)

            # 验证训练集命中率（回测）
            train_hits = 0
            train_start = max(0, train_end - self.train_size)
            for i in range(train_start, train_end):
                actual = self.df.iloc[i]['special_zodiac']
                pred = strategy_func(train_features)
                if actual in pred:
                    train_hits += 1

            train_rate = train_hits / (train_end - train_start) if train_end > train_start else 0
            train_rates.append(train_rate)

            # ========== 测试阶段 ==========
            # 用train_end时的特征预测test_start到test_end的数据
            test_hits = 0
            test_results = []  # 每期是否命中

            for i in range(test_start, test_end):
                actual = self.df.iloc[i]['special_zodiac']
                # 用训练结束时的特征（假装不知道未来）
                pred = strategy_func(train_features)

                hit = actual in pred
                test_hits += hit
                test_results.append(1 if hit else 0)

                period_results.append({
                    'period': self.df.iloc[i]['period'],
                    'predicted': pred,
                    'actual': actual,
                    'hit': hit,
                    'window': window_idx
                })

            test_rate = test_hits / self.test_size
            test_rates.append(test_rate)

        # ========== 计算统计指标 ==========

        # 综合命中率
        avg_train = np.mean(train_rates) if train_rates else 0
        avg_test = np.mean(test_rates) if test_rates else 0

        # 稳定性（1 - 测试期次间方差）
        std_test = np.std(test_rates) if len(test_rates) > 1 else 0
        stability = 1 - std_test

        # 最大连续命中/未命中
        max_consec_yes, max_consec_no = self._calc_consecutive(test_results)

        # 最大回撤（连续未命中）
        max_drawdown = max_consec_no

        # 一致性（平均每期是否命中）
        consistency = np.mean(test_results)

        # 夏普比率（假设无风险利率为0）
        if len(test_rates) > 1 and np.std(test_rates) > 0:
            sharpe = (np.mean(test_rates) - 0.5) / np.std(test_rates) * np.sqrt(len(test_rates))
        else:
            sharpe = 0

        # 综合评分
        score = self._calc_score(avg_test, stability, max_drawdown, consistency)

        result = BacktestResult(
            strategy_id=strategy_id,
            total_windows=len(self.windows),
            total_tests=len(period_results),
            total_hits=sum(1 for r in period_results if r['hit']),
            train_hit_rates=train_rates,
            test_hit_rates=test_rates,
            train_hit_rate=avg_train,
            test_hit_rate=avg_test,
            stability=stability,
            max_drawdown=max_drawdown,
            max_consecutive=max_consec_yes,
            consistency=consistency,
            sharpe_ratio=sharpe,
            score=score,
            period_results=period_results
        )

        if verbose:
            print(f"  策略 {strategy_id}:")
            print(f"    训练命中率: {avg_train:.1%}")
            print(f"    测试命中率: {avg_test:.1%}")
            print(f"    稳定性: {stability:.3f}")
            print(f"    最大回撤: {max_drawdown}期")
            print(f"    综合得分: {score:.3f}")

        return result

    def _calc_consecutive(self, results: List[int]) -> Tuple[int, int]:
        """计算最大连续命中/未命中"""
        max_yes, max_no = 0, 0
        cnt_yes, cnt_no = 0, 0

        for r in results:
            if r == 1:
                cnt_yes += 1
                cnt_no = 0
                max_yes = max(max_yes, cnt_yes)
            else:
                cnt_no += 1
                cnt_yes = 0
                max_no = max(max_no, cnt_no)

        return max_yes, max_no

    def _calc_score(self, test_rate: float, stability: float,
                    max_drawdown: int, consistency: float,
                    w_hit: float = 0.35,
                    w_stability: float = 0.30,
                    w_drawdown: float = 0.20,
                    w_consistency: float = 0.15) -> float:
        """计算综合评分"""
        # 回撤得分（回撤越小越好）
        drawdown_score = max(0, 1 - max_drawdown / self.test_size)

        score = (test_rate * w_hit +
                stability * w_stability +
                drawdown_score * w_drawdown +
                consistency * w_consistency)

        return score

    def get_baseline_result(self) -> BacktestResult:
        """
        获取随机基准的回测结果（用于对比）
        随机选择6个生肖的命中率期望是50%
        """
        def random_strategy(features):
            zodiacs = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
            return list(np.random.choice(zodiacs, 6, replace=False))

        return self.backtest_strategy("BASELINE_RANDOM", random_strategy)

    def run_batch(self, strategies: List[Tuple[str, callable]], verbose: bool = False) -> List[BacktestResult]:
        """
        批量回测多个策略

        Args:
            strategies: List of (strategy_id, strategy_func)

        Returns:
            List of BacktestResult
        """
        results = []
        for i, (sid, func) in enumerate(strategies):
            result = self.backtest_strategy(sid, func, verbose=verbose)
            results.append(result)

            if verbose and (i + 1) % 10 == 0:
                print(f"  已完成 {i+1}/{len(strategies)}")

        return results


# 预定义策略函数
class BuiltinStrategies:
    """内置策略函数"""

    @staticmethod
    def gap_strategy(features: Dict) -> List[str]:
        """遗漏策略：遗漏越大，得分越高"""
        scores = {}
        for z in ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']:
            gap = features.get(f'gap_{z}', 0)
            scores[z] = gap
        sorted_z = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [z for z, s in sorted_z[:6]]

    @staticmethod
    def frequency_strategy(features: Dict) -> List[str]:
        """频率策略：近期出现越多，得分越高"""
        scores = {}
        for z in ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']:
            freq = features.get('freq_50_' + z, 0)
            scores[z] = freq
        sorted_z = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [z for z, s in sorted_z[:6]]

    @staticmethod
    def combined_strategy(features: Dict) -> List[str]:
        """组合策略：遗漏 + 频率"""
        scores = {}
        for z in ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']:
            gap = features.get(f'gap_{z}', 0)
            freq = features.get('freq_50_' + z, 0)
            # 遗漏权重2.5，频率权重0.5
            scores[z] = gap * 2.5 + freq * 0.5
        sorted_z = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [z for z, s in sorted_z[:6]]

    @staticmethod
    def cold_strategy(features: Dict) -> List[str]:
        """冷门策略：遗漏大 + 频率低"""
        scores = {}
        for z in ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']:
            gap = features.get(f'gap_{z}', 0)
            freq = features.get('freq_50_' + z, 0)
            # 冷门 = 遗漏大 + 频率低
            scores[z] = gap - freq * 0.5
        sorted_z = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [z for z, s in sorted_z[:6]]

    @staticmethod
    def hot_strategy(features: Dict) -> List[str]:
        """热门策略：遗漏小 + 频率高"""
        scores = {}
        for z in ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']:
            gap = features.get(f'gap_{z}', 0)
            freq = features.get('freq_50_' + z, 0)
            # 热门 = 遗漏小 + 频率高
            scores[z] = freq * 0.5 - gap * 0.5
        sorted_z = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [z for z, s in sorted_z[:6]]


if __name__ == '__main__':
    # 测试
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    print(f"加载数据: {len(df)} 条")

    # 初始化回测器
    backtester = WalkForwardBacktester(df, train_size=200, test_size=50)

    print(f"滚动窗口数: {len(backtester.windows)}")

    # 测试内置策略
    strategies = [
        ('GAP', BuiltinStrategies.gap_strategy),
        ('FREQ', BuiltinStrategies.frequency_strategy),
        ('COMBINED', BuiltinStrategies.combined_strategy),
        ('COLD', BuiltinStrategies.cold_strategy),
        ('HOT', BuiltinStrategies.hot_strategy),
    ]

    print("\n回测内置策略:")
    for sid, func in strategies:
        result = backtester.backtest_strategy(sid, func, verbose=True)
        valid = result.is_valid()
        print(f"  {sid}: 测试={result.test_hit_rate:.1%}, 稳定性={result.stability:.3f}, 有效={'✅' if valid else '❌'}")

    # 随机基准
    baseline = backtester.get_baseline_result()
    print(f"\n随机基准: 测试={baseline.test_hit_rate:.1%}")