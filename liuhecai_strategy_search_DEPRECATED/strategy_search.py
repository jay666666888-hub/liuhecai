#!/usr/bin/env python3
"""
六合六肖策略自动搜索系统
========================
核心功能：
1. Walk Forward Analysis - 滚动窗口验证，防止数据泄露
2. 自动生成策略 - 随机组合多维度特征
3. 遗传算法进化 - 自动优化策略
4. 多目标评分 - 综合考虑命中率、稳定性、回撤等
5. 防过拟合 - 多重验证机制

数据源: /home/admin1/liuhecai_standard_v2.json
"""

import json
import os
import sys
import random
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# ============ 项目路径 ============
PROJECT_DIR = '/home/admin1/liuhecai_strategy_search'
DATA_FILE = '/home/admin1/liuhecai_standard_v2.json'

# ============ 配置 ============
@dataclass
class Config:
    # 策略搜索规模
    INITIAL_STRATEGIES: int = 10000      # 初始策略数量
    ROUND1 Survivors: int = 2000         # 第一轮幸存者
    ROUND2 Survivors: int = 500          # 第二轮幸存者
    ROUND3 Survivors: int = 100          # 第三轮幸存者
    FINAL_TOP: int = 50                 # 最终TOP50

    # Walk Forward窗口
    TRAIN_SIZE: int = 200                # 训练窗口
    TEST_SIZE: int = 50                 # 测试窗口

    # 遗传算法参数
    GENERATIONS: int = 20               # 进化代数
    POPULATION_SIZE: int = 500          # 种群大小
    MUTATION_RATE: float = 0.1          # 突变率
    CROSSOVER_RATE: float = 0.7         # 交叉率
    ELITE_RATE: float = 0.1             # 精英保留

    # 评分权重
    HIT_RATE_WEIGHT: float = 0.35
    STABILITY_WEIGHT: float = 0.30
    DRAWDOWN_WEIGHT: float = 0.20
    CONSISTENCY_WEIGHT: float = 0.15

    # 防过拟合阈值
    MAX_TRAIN_TEST_GAP: float = 0.25    # 训练/测试最大差距
    MIN_TEST_RATE: float = 0.40         # 测试最低命中率

CONFIG = Config()

# ============ 数据加载 ============
def load_data() -> pd.DataFrame:
    """加载并验证数据"""
    with open(DATA_FILE) as f:
        raw = json.load(f)

    df = pd.DataFrame(raw)
    df['period_int'] = df['period'].apply(lambda x: int(x))
    df = df.sort_values('period_int').reset_index(drop=True)

    print(f"[数据] 加载 {len(df)} 条记录")
    print(f"      期号范围: {df['period'].iloc[0]} ~ {df['period'].iloc[-1]}")

    return df

# ============ 特征工程 ============
class FeatureEngine:
    """特征工程引擎"""

    ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
    COLORS = {'red': [1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46],
              'blue': [3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48],
              'green': [5,6,11,16,17,21,22,27,28,32,33,38,39,43,44,49]}

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._build_basic_features()

    def _build_basic_features(self):
        """构建基础特征"""
        # 生肖编码
        zodiac_map = {z: i for i, z in enumerate(self.ZODIACS)}
        self.df['special_zodiac_code'] = self.df['special_zodiac'].map(zodiac_map)

        # 波色编码
        color_map = {'red': 0, 'blue': 1, 'green': 2}
        self.df['special_color_code'] = self.df['special_color'].map(color_map)

        # 号码特征
        self.df['special_num'] = self.df['special_number'].astype(int)
        self.df['parity'] = self.df['special_num'] % 2  # 单双
        self.df['size'] = (self.df['special_num'] > 24).astype(int)  # 大小
        self.df['tail'] = self.df['special_num'] % 10  # 尾数

    def compute_features(self, upto_idx: int) -> Dict:
        """
        计算截止到upto_idx的特征（不包含upto_idx，用于预测）
        返回特征字典
        """
        if upto_idx < 50:
            return {}

        data = self.df.iloc[:upto_idx]

        features = {}

        # ===== 遗漏特征 (Gap Features) =====
        for z in self.ZODIACS:
            positions = data[data['special_zodiac'] == z].index.tolist()
            if len(positions) > 0:
                last_pos = positions[-1]
                gap = upto_idx - last_pos - 1
            else:
                gap = upto_idx
            features[f'gap_{z}'] = min(gap, 100)  # 限制最大值

        # ===== 热度特征 (Frequency Features) =====
        for window in [5, 10, 20, 50]:
            if upto_idx >= window:
                window_data = data.iloc[-window:]
                for z in self.ZODIACS:
                    count = (window_data['special_zodiac'] == z).sum()
                    features[f'freq_{window}_{z}'] = count

        # ===== 连出特征 (Streak Features) =====
        for z in self.ZODIACS:
            streak = 0
            for i in range(upto_idx - 1, -1, -1):
                if self.df.iloc[i]['special_zodiac'] == z:
                    streak += 1
                else:
                    break
            features[f'streak_{z}'] = streak

        # ===== 波色特征 (Color Features) =====
        for window in [5, 10, 20]:
            if upto_idx >= window:
                window_data = data.iloc[-window:]
                for color in ['red', 'blue', 'green']:
                    count = (window_data['special_color'] == color).sum()
                    features[f'color_{window}_{color}'] = count

        # ===== 号码特征 (Number Features) =====
        if upto_idx >= 10:
            recent_nums = data['special_num'].tail(10).values
            features['num_mean'] = np.mean(recent_nums)
            features['num_std'] = np.std(recent_nums)
            features['num_parity_ratio'] = np.mean(recent_nums % 2)
            features['num_size_ratio'] = np.mean((recent_nums > 24).astype(int))

        # ===== 尾数特征 (Tail Features) =====
        if upto_idx >= 10:
            recent_tails = data['tail'].tail(10).values
            for t in range(10):
                features[f'tail_{t}_count'] = np.sum(recent_tails == t)

        # ===== 马尔可夫特征 (Markov Features) =====
        if upto_idx >= 20:
            transitions = defaultdict(int)
            for i in range(1, upto_idx):
                prev_z = data.iloc[i-1]['special_zodiac']
                curr_z = data.iloc[i]['special_zodiac']
                transitions[(prev_z, curr_z)] += 1

            for z1 in self.ZODIACS:
                for z2 in self.ZODIACS:
                    features[f'markov_{z1}_{z2}'] = transitions.get((z1, z2), 0)

        return features

    def get_top6_by_features(self, features: Dict) -> List[str]:
        """
        根据特征生成六肖
        使用权重计算得分
        """
        scores = {}
        for z in self.ZODIACS:
            score = 0

            # 遗漏得分 (遗漏越大，得分越高)
            gap_key = f'gap_{z}'
            if gap_key in features:
                score += features[gap_key] * 2.5

            # 热度得分
            for window in [10, 20]:
                freq_key = f'freq_{window}_{z}'
                if freq_key in features:
                    score += features[freq_key] * 0.5

            # 连出得分 (连出越少，得分越高，避免追热)
            streak_key = f'streak_{z}'
            if streak_key in features:
                score += max(0, (10 - features[streak_key])) * 1.5

            scores[z] = score

        # 按得分排序，取前6
        sorted_zodiacs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [z for z, s in sorted_zodiacs[:6]]

# ============ 策略定义 ============
@dataclass
class Strategy:
    """策略定义"""
    id: str
    weights: Dict[str, float]  # 特征权重
    features_used: List[str]   # 使用的特征列表
    generation: int = 0        # 进化代数

    def mutate(self):
        """策略突变"""
        if random.random() < CONFIG.MUTATION_RATE:
            keys = list(self.weights.keys())
            key = random.choice(keys)
            self.weights[key] = random.random()

    def crossover(self, other: 'Strategy') -> 'Strategy':
        """策略交叉"""
        child_weights = {}
        for k in self.weights:
            if random.random() < 0.5:
                child_weights[k] = self.weights[k]
            else:
                child_weights[k] = other.weights[k]

        return Strategy(
            id=f"gen{self.generation + 1}_{random.randint(1000,9999)}",
            weights=child_weights,
            features_used=list(set(self.features_used + other.features_used)),
            generation=self.generation + 1
        )

# ============ 策略生成器 ============
class StrategyGenerator:
    """自动生成策略"""

    FEATURE_TEMPLATES = {
        'gap': ['gap_{z}' for z in FeatureEngine.ZODIACS],
        'freq_10': ['freq_10_{z}' for z in FeatureEngine.ZODIACS],
        'freq_20': ['freq_20_{z}' for z in FeatureEngine.ZODIACS],
        'freq_50': ['freq_50_{z}' for z in FeatureEngine.ZODIACS],
        'streak': ['streak_{z}' for z in FeatureEngine.ZODIACS],
        'color_5': ['color_5_red', 'color_5_blue', 'color_5_green'],
        'color_10': ['color_10_red', 'color_10_blue', 'color_10_green'],
        'num_stats': ['num_mean', 'num_std', 'num_parity_ratio', 'num_size_ratio'],
        'tail': [f'tail_{t}_count' for t in range(10)],
    }

    @classmethod
    def generate_random_strategy(cls, n_features: int = 20) -> Strategy:
        """生成随机策略"""
        # 随机选择特征
        all_features = []
        for template_name, features in cls.FEATURE_TEMPLATES.items():
            all_features.extend(features)

        selected = random.sample(all_features, min(n_features, len(all_features)))
        weights = {f: random.random() for f in selected}

        return Strategy(
            id=f"init_{random.randint(10000, 99999)}",
            weights=weights,
            features_used=selected,
            generation=0
        )

    @classmethod
    def generate_initial_population(cls, n: int = CONFIG.INITIAL_STRATEGIES) -> List[Strategy]:
        """生成初始策略种群"""
        print(f"[策略生成] 生成 {n} 个初始策略...")
        strategies = []
        for i in range(n):
            n_features = random.randint(10, 30)
            strategies.append(cls.generate_random_strategy(n_features))
            if (i + 1) % 2000 == 0:
                print(f"  已生成 {i+1}/{n}")
        return strategies

# ============ 回测引擎 ============
@dataclass
class BacktestResult:
    """回测结果"""
    strategy_id: str
    train_hit_rate: float = 0
    test_hit_rate: float = 0
    total_tests: int = 0
    hits: int = 0
    consecutive_hits: List[int] = field(default_factory=list)
    max_consecutive: int = 0
    max_drawdown: int = 0
    stability: float = 0  # 方差稳定性
    consistency: float = 0  # 每期一致性
    score: float = 0

    def is_valid(self) -> bool:
        """检查是否通过防过拟合检验"""
        # 训练/测试差距不能太大
        if self.train_hit_rate - self.test_hit_rate > CONFIG.MAX_TRAIN_TEST_GAP:
            return False
        # 测试命中率不能太低
        if self.test_hit_rate < CONFIG.MIN_TEST_RATE:
            return False
        return True

class BacktestEngine:
    """回测引擎 - 使用Walk Forward Analysis"""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.feature_engine = FeatureEngine(df)
        self.results = {}

    def run_walk_forward(self, strategy: Strategy, verbose: bool = False) -> BacktestResult:
        """
        执行Walk Forward Analysis
        滚动窗口：训练200期，测试50期
        """
        total_periods = len(self.df)
        test_windows = []

        # 构建滚动窗口
        start_idx = CONFIG.TRAIN_SIZE
        while start_idx + CONFIG.TEST_SIZE <= total_periods:
            train_end = start_idx
            test_start = start_idx
            test_end = start_idx + CONFIG.TEST_SIZE
            test_windows.append((train_end, test_start, test_end))
            start_idx += CONFIG.TEST_SIZE

        if len(test_windows) < 3:
            return BacktestResult(strategy_id=strategy.id)

        # 执行回测
        train_rates = []
        test_rates = []
        test_results = []  # 每期是否命中

        for train_end, test_start, test_end in test_windows:
            # 训练：使用0到train_end的数据
            train_features = self.feature_engine.compute_features(train_end)
            train_top6 = self._predict_with_features(train_features, strategy)

            # 验证训练集命中率
            train_hits = 0
            for i in range(train_end - CONFIG.TRAIN_SIZE, train_end):
                actual = self.df.iloc[i]['special_zodiac']
                if actual in train_top6:
                    train_hits += 1
            train_rate = train_hits / CONFIG.TRAIN_SIZE
            train_rates.append(train_rate)

            # 测试：使用test_start到test_end的数据
            test_hits = 0
            for i in range(test_start, test_end):
                actual = self.df.iloc[i]['special_zodiac']
                # 用train_end时的特征预测（假装不知道未来）
                pred_features = self.feature_engine.compute_features(train_end)
                pred_top6 = self._predict_with_features(pred_features, strategy)

                if actual in pred_top6:
                    test_hits += 1
                    test_results.append(1)
                else:
                    test_results.append(0)

            test_rate = test_hits / CONFIG.TEST_SIZE
            test_rates.append(test_rate)

        # 计算统计
        avg_train_rate = np.mean(train_rates)
        avg_test_rate = np.mean(test_rates)

        # 连胜连败分析
        max_consecutive = self._calc_max_consecutive(test_results)
        max_drawdown = self._calc_max_drawdown(test_results)

        # 稳定性（测试期间方差）
        stability = 1 - np.std(test_rates) if len(test_rates) > 1 else 0

        # 一致性（每期是否稳定命中）
        consistency = np.mean(test_results)

        # 综合评分
        score = (avg_test_rate * CONFIG.HIT_RATE_WEIGHT +
                stability * CONFIG.STABILITY_WEIGHT +
                (1 - max_drawdown / CONFIG.TEST_SIZE) * CONFIG.DRAWDOWN_WEIGHT +
                consistency * CONFIG.CONSISTENCY_WEIGHT)

        result = BacktestResult(
            strategy_id=strategy.id,
            train_hit_rate=avg_train_rate,
            test_hit_rate=avg_test_rate,
            total_tests=len(test_windows),
            hits=sum(test_results),
            consecutive_hits=test_results,
            max_consecutive=max_consecutive,
            max_drawdown=max_drawdown,
            stability=stability,
            consistency=consistency,
            score=score
        )

        self.results[strategy.id] = result

        if verbose:
            print(f"  策略 {strategy.id}: 训练={avg_train_rate:.1%}, 测试={avg_test_rate:.1%}, 得分={score:.3f}")

        return result

    def _predict_with_features(self, features: Dict, strategy: Strategy) -> List[str]:
        """根据策略权重预测六肖"""
        scores = {}
        for z in FeatureEngine.ZODIACS:
            score = 0
            # 遗漏
            gap_key = f'gap_{z}'
            if gap_key in features and gap_key in strategy.weights:
                score += features[gap_key] * strategy.weights[gap_key]

            # 热度
            for window in [10, 20]:
                freq_key = f'freq_{window}_{z}'
                if freq_key in features and freq_key in strategy.weights:
                    score += features[freq_key] * strategy.weights[freq_key]

            # 连出
            streak_key = f'streak_{z}'
            if streak_key in features and streak_key in strategy.weights:
                score += max(0, 10 - features[streak_key]) * strategy.weights[streak_key]

            # 波色
            for color in ['red', 'blue', 'green']:
                color_key = f'color_10_{color}'
                if color_key in features and color_key in strategy.weights:
                    if self._zodiac_matches_color(z, color):
                        score += features[color_key] * strategy.weights[color_key]

            scores[z] = score

        sorted_zodiacs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [z for z, s in sorted_zodiacs[:6]]

    def _zodiac_matches_color(self, zodiac: str, color: str) -> bool:
        """检查生肖是否属于波色"""
        color_nums = FeatureEngine.COLORS[color]
        zodiac_nums = self._get_zodiac_numbers(zodiac)
        return any(n in color_nums for n in zodiac_nums)

    def _get_zodiac_numbers(self, zodiac: str) -> List[int]:
        """获取生肖对应的号码"""
        mapping = {
            '鼠': [2,14,26,38], '牛': [1,13,25,37,49], '虎': [12,24,36,48],
            '兔': [11,23,35,47], '龍': [10,22,34,46], '蛇': [9,21,33,45],
            '马': [8,20,32,44], '羊': [7,19,31,43], '猴': [6,18,30,42],
            '雞': [5,17,29,41], '狗': [4,16,28,40], '豬': [3,15,27,39]
        }
        return mapping.get(zodiac, [])

    def _calc_max_consecutive(self, results: List[int]) -> int:
        """计算最大连续命中"""
        max_cnt = 0
        cnt = 0
        for r in results:
            if r == 1:
                cnt += 1
                max_cnt = max(max_cnt, cnt)
            else:
                cnt = 0
        return max_cnt

    def _calc_max_drawdown(self, results: List[int]) -> int:
        """计算最大连续未命中"""
        max_dd = 0
        cnt = 0
        for r in results:
            if r == 0:
                cnt += 1
                max_dd = max(max_dd, cnt)
            else:
                cnt = 0
        return max_dd

# ============ 遗传算法引擎 ============
class EvolutionEngine:
    """遗传算法进化引擎"""

    def __init__(self, backtest_engine: BacktestEngine):
        self.backtest_engine = backtest_engine
        self.population = []
        self.generation = 0

    def initialize(self, n: int = CONFIG.POPULATION_SIZE):
        """初始化种群"""
        self.population = StrategyGenerator.generate_initial_population(n)

    def evolve(self) -> List[Strategy]:
        """执行一代进化"""
        # 评估所有策略
        results = []
        for i, strategy in enumerate(self.population):
            result = self.backtest_engine.run_walk_forward(strategy)
            if result.is_valid():
                results.append((strategy, result))
            if (i + 1) % 100 == 0:
                print(f"  评估进度: {i+1}/{len(self.population)}")

        # 按评分排序
        results.sort(key=lambda x: x[1].score, reverse=True)

        # 精英保留
        n_elite = int(CONFIG.POPULATION_SIZE * CONFIG.ELITE_RATE)
        elite = [s for s, r in results[:n_elite]]

        # 选择、交配、突变
        new_population = elite.copy()
        while len(new_population) < CONFIG.POPULATION_SIZE:
            # 选择
            if len(results) >= 2:
                parent1 = self._tournament_select(results)
                parent2 = self._tournament_select(results)

                # 交叉
                if random.random() < CONFIG.CROSSOVER_RATE:
                    child = parent1.crossover(parent2)
                else:
                    child = Strategy(
                        id=f"gen{self.generation}_{random.randint(1000,9999)}",
                        weights=parent1.weights.copy(),
                        features_used=parent1.features_used.copy(),
                        generation=self.generation + 1
                    )

                # 突变
                child.mutate()
                new_population.append(child)

        self.population = new_population[:CONFIG.POPULATION_SIZE]
        self.generation += 1

        return elite

    def _tournament_select(self, results: List[Tuple[Strategy, BacktestResult]]) -> Strategy:
        """锦标赛选择"""
        tournament_size = 5
        selected = random.sample(results, min(tournament_size, len(results)))
        selected.sort(key=lambda x: x[1].score, reverse=True)
        return selected[0][0]

# ============ 多轮筛选 ============
class StrategySelector:
    """多轮筛选器"""

    def __init__(self, backtest_engine: BacktestEngine):
        self.backtest_engine = backtest_engine

    def round_filter(self, strategies: List[Strategy], target: int, round_num: int) -> List[Strategy]:
        """
        执行一轮筛选
        返回top target个策略
        """
        print(f"\n[第{round_num}轮筛选] {len(strategies)} -> {target}")

        results = []
        for strategy in strategies:
            result = self.backtest_engine.run_walk_forward(strategy, verbose=False)
            results.append((strategy, result))

        # 过滤无效策略
        valid_results = [(s, r) for s, r in results if r.is_valid()]

        if len(valid_results) == 0:
            print(f"  警告: 无有效策略幸存!")
            return []

        # 按评分排序
        valid_results.sort(key=lambda x: x[1].score, reverse=True)

        print(f"  有效策略: {len(valid_results)}/{len(results)}")
        print(f"  TOP3 得分: {valid_results[0][1].score:.3f}, {valid_results[1][1].score:.3f}, {valid_results[2][1].score:.3f}")

        return [s for s, r in valid_results[:target]]

    def full_selection(self, initial_strategies: int = CONFIG.INITIAL_STRATEGIES) -> List[Tuple[Strategy, BacktestResult]]:
        """
        完整筛选流程
        100000 -> 10000 -> 1000 -> 100 -> TOP50
        """
        # 第一轮：生成初始策略
        strategies = StrategyGenerator.generate_initial_population(initial_strategies)

        # 第二轮：评估所有策略（10000 -> 2000）
        print(f"\n[开始筛选] 初始策略: {len(strategies)}")
        strategies = self.round_filter(strategies, CONFIG.ROUND1_SURVIVORS, 1)

        # 第三轮：继续筛选（2000 -> 500）
        if len(strategies) >= CONFIG.ROUND2_SURVIVORS:
            strategies = self.round_filter(strategies, CONFIG.ROUND2_SURVIVORS, 2)

        # 第四轮：继续筛选（500 -> 100）
        if len(strategies) >= CONFIG.ROUND3_SURVIVORS:
            strategies = self.round_filter(strategies, CONFIG.ROUND3_SURVIVORS, 3)

        # 第五轮：最终TOP50
        strategies = self.round_filter(strategies, CONFIG.FINAL_TOP, 4)

        # 最后一轮详细评估
        final_results = []
        for strategy in strategies:
            result = self.backtest_engine.run_walk_forward(strategy, verbose=True)
            final_results.append((strategy, result))

        final_results.sort(key=lambda x: x[1].score, reverse=True)

        return final_results

# ============ 主程序 ============
def main():
    print("=" * 60)
    print("六合六肖策略自动搜索系统")
    print("=" * 60)

    # 加载数据
    df = load_data()

    # 初始化引擎
    backtest_engine = BacktestEngine(df)
    selector = StrategySelector(backtest_engine)

    # 执行筛选
    print("\n[阶段1] 生成初始策略...")
    initial_strategies = StrategyGenerator.generate_initial_population(CONFIG.INITIAL_STRATEGIES)

    print("\n[阶段2] 开始多轮筛选...")
    print(f"  配置: TRAIN_SIZE={CONFIG.TRAIN_SIZE}, TEST_SIZE={CONFIG.TEST_SIZE}")
    print(f"  筛选: {CONFIG.INITIAL_STRATEGIES} -> {CONFIG.ROUND1_SURVIVORS} -> {CONFIG.ROUND2_SURVIVORS} -> {CONFIG.ROUND3_SURVIVORS} -> {CONFIG.FINAL_TOP}")

    # 第一轮筛选
    print("\n[第1轮] 筛选 10000 -> 2000")
    round1_results = []
    batch_size = 1000
    for i in range(0, len(initial_strategies), batch_size):
        batch = initial_strategies[i:i+batch_size]
        print(f"  处理批次 {i//batch_size + 1}/{(len(initial_strategies)-1)//batch_size + 1}")
        for strategy in batch:
            result = backtest_engine.run_walk_forward(strategy)
            if result.is_valid():
                round1_results.append((strategy, result))

        # 进度显示
        print(f"  当前有效: {len(round1_results)}")

    # 取TOP2000
    round1_results.sort(key=lambda x: x[1].score, reverse=True)
    survivors = [s for s, r in round1_results[:CONFIG.ROUND1_SURVIVORS]]
    print(f"  幸存: {len(survivors)} 个策略")

    # 第二轮筛选
    print("\n[第2轮] 筛选 2000 -> 500")
    round2_results = []
    for i, strategy in enumerate(survivors):
        result = backtest_engine.run_walk_forward(strategy)
        if result.is_valid():
            round2_results.append((strategy, result))
        if (i + 1) % 200 == 0:
            print(f"  进度: {i+1}/{len(survivors)}")

    round2_results.sort(key=lambda x: x[1].score, reverse=True)
    survivors = [s for s, r in round2_results[:CONFIG.ROUND2_SURVIVORS]]
    print(f"  幸存: {len(survivors)} 个策略")

    # 第三轮筛选
    print("\n[第3轮] 筛选 500 -> 100")
    round3_results = []
    for strategy in survivors:
        result = backtest_engine.run_walk_forward(strategy)
        if result.is_valid():
            round3_results.append((strategy, result))

    round3_results.sort(key=lambda x: x[1].score, reverse=True)
    survivors = [s for s, r in round3_results[:CONFIG.ROUND3_SURVIVORS]]
    print(f"  幸存: {len(survivors)} 个策略")

    # 第四轮：最终TOP50
    print("\n[第4轮] 最终 TOP50")
    final_results = []
    for strategy in survivors:
        result = backtest_engine.run_walk_forward(strategy, verbose=True)
        final_results.append((strategy, result))

    final_results.sort(key=lambda x: x[1].score, reverse=True)
    top50 = final_results[:CONFIG.FINAL_TOP]

    # 输出结果
    print("\n" + "=" * 60)
    print("TOP 50 策略排名")
    print("=" * 60)

    output = []
    for rank, (strategy, result) in enumerate(top50, 1):
        print(f"\n#{rank:2d} | 策略ID: {strategy.id}")
        print(f"     训练命中率: {result.train_hit_rate:.1%}")
        print(f"     测试命中率: {result.test_hit_rate:.1%}")
        print(f"     稳定性: {result.stability:.3f}")
        print(f"     最大回撤: {result.max_drawdown}期")
        print(f"     综合得分: {result.score:.3f}")

        output.append({
            'rank': rank,
            'strategy_id': strategy.id,
            'train_hit_rate': round(result.train_hit_rate, 3),
            'test_hit_rate': round(result.test_hit_rate, 3),
            'stability': round(result.stability, 3),
            'max_drawdown': result.max_drawdown,
            'max_consecutive': result.max_consecutive,
            'score': round(result.score, 3),
            'weights': strategy.weights
        })

    # 保存结果
    result_file = f"{PROJECT_DIR}/top50_strategies.json"
    with open(result_file, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[完成] 结果已保存到: {result_file}")

    return top50

if __name__ == '__main__':
    results = main()