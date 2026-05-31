#!/usr/bin/env python3
"""
策略执行器
==========

用于加载策略并执行预测
"""

import json
import sys
from typing import List, Dict

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

from features.feature_engine import FeatureBuilder

class StrategyExecutor:
    """策略执行器"""

    ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']

    def __init__(self, strategy_file: str = None):
        self.strategies = []
        if strategy_file:
            self.load_strategies(strategy_file)
        self.fb = None

    def load_strategies(self, filepath: str):
        """加载策略文件"""
        with open(filepath) as f:
            data = json.load(f)

        self.strategies = data
        print(f"[加载] {len(self.strategies)} 个策略")

    def predict(self, df, strategy_id: str = None) -> List[Dict]:
        """
        执行预测

        Args:
            df: 开奖数据DataFrame
            strategy_id: 可选，指定策略ID

        Returns:
            预测结果列表
        """
        if not self.fb:
            self.fb = FeatureBuilder(df)

        # 计算特征
        features = self.fb.compute_all_features(len(df))

        results = []

        for strategy in self.strategies:
            if strategy_id and strategy['id'] != strategy_id:
                continue

            top6 = self._predict_with_strategy(features, strategy['weights'])

            results.append({
                'strategy_id': strategy['id'],
                'top6': top6,
                'score': strategy.get('score', 0)
            })

        return results

    def _predict_with_strategy(self, features: Dict, weights: Dict) -> List[str]:
        """根据策略权重预测六肖"""
        scores = {}

        for z in self.ZODIACS:
            score = 0

            # 遗漏
            gap_key = f'gap_{z}'
            if gap_key in weights:
                score += features.get(gap_key, 0) * weights[gap_key]

            # 频率
            for window in [10, 20, 50]:
                freq_key = f'freq_{window}_{z}'
                if freq_key in weights:
                    score += features.get(freq_key, 0) * weights[freq_key]

            # 连出
            streak_key = f'streak_{z}'
            if streak_key in weights:
                streak = features.get(streak_key, 0)
                score += max(0, 10 - streak) * weights[streak_key]

            # 波色
            for color in ['red', 'blue', 'green']:
                color_key = f'color_freq_10_{color}'
                if color_key in weights:
                    score += features.get(color_key, 0) * weights[color_key]

            scores[z] = score

        sorted_z = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [z for z, s in sorted_z[:6]]

    def predict_with_all(self, df) -> List[Dict]:
        """使用所有策略预测"""
        return self.predict(df)


if __name__ == '__main__':
    import pandas as pd

    # 加载数据
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    print(f"数据: {len(df)} 条")

    # 加载策略
    executor = StrategyExecutor('/home/admin1/liuhecai_strategy_search/strategies.json')

    # 执行预测
    results = executor.predict_with_all(df)

    print("\n预测结果 (TOP 10):")
    for r in results[:10]:
        print(f"  {r['strategy_id']}: {' '.join(r['top6'])} (score: {r['score']:.3f})")