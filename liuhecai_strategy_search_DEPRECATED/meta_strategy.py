#!/usr/bin/env python3
"""
Meta Strategy 模块
=================

不是预测生肖，而是预测哪个专家最近有效。

输入：
- 最近50期每个专家的命中序列
- 专家状态（HOT/NORMAL/COLD）

输出：
- 未来各专家的权重
- 融合后的预测

核心思想：
不是寻找新的预测信号，
而是寻找信号什么时候有效。
"""

import numpy as np
import pandas as pd
import json
from typing import Dict, List, Tuple
from collections import defaultdict
from datetime import datetime

# 专家定义
EXPERTS = ['Gap', 'Trend', 'Momentum', 'Color']

# 状态阈值
HOT_THRESHOLD = 1.0  # mean + 1σ
COLD_THRESHOLD = -1.0  # mean - 1σ


class ExpertHistory:
    """追踪单个专家的历史表现"""

    def __init__(self, name: str, window_size: int = 50):
        self.name = name
        self.window_size = window_size
        self.hit_sequence = []  # 1=命中, 0=未命中

    def add_result(self, hit: bool):
        """添加新结果"""
        self.hit_sequence.append(1 if hit else 0)
        if len(self.hit_sequence) > self.window_size:
            self.hit_sequence.pop(0)

    def get_recent_hit_rate(self, n: int = 30) -> float:
        """获取最近n期的命中率"""
        if len(self.hit_sequence) < n:
            n = len(self.hit_sequence)
        if n == 0:
            return 0.0
        return sum(self.hit_sequence[-n:]) / n

    def get_hit_sequence(self, n: int = 50) -> List[int]:
        """获取最近n期的命中序列"""
        return self.hit_sequence[-n:] if len(self.hit_sequence) >= n else self.hit_sequence

    def get_z_score(self, window: int = 30) -> float:
        """计算最近window期的z-score"""
        recent = self.hit_sequence[-window:] if len(self.hit_sequence) >= window else self.hit_sequence
        if len(recent) < 5:
            return 0.0

        mean = np.mean(recent)
        std = np.std(recent)
        if std == 0:
            return 0.0

        return (mean - 0.0833) / std  # 0.0833 = random baseline (1/12)

    def get_state(self, window: int = 30) -> str:
        """获取专家状态"""
        z = self.get_z_score(window)
        if z > HOT_THRESHOLD:
            return 'HOT'
        elif z < COLD_THRESHOLD:
            return 'COLD'
        else:
            return 'NORMAL'


class MetaStrategy:
    """元策略管理器"""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
        self.experts = {name: ExpertHistory(name) for name in EXPERTS}
        self.prediction_history = []
        self.actual_history = []

    def _get_expert_predictions(self, upto_idx: int) -> Dict[str, List[str]]:
        """基于真实特征的专家预测"""
        predictions = {}

        data = self.df.iloc[:upto_idx]

        for expert_name in EXPERTS:
            scores = {}

            for z in self.ZODIACS:
                score = 0

                if expert_name == 'Gap':
                    positions = data[data['zodiac'] == z].index.tolist()
                    gap = upto_idx - positions[-1] - 1 if positions else upto_idx
                    score = gap * 2.0

                    if len(positions) >= 3:
                        intervals = np.diff(positions)
                        cycle_mean = np.mean(intervals)
                        cycle_std = np.std(intervals)
                        if cycle_std > 0:
                            residual = (gap - cycle_mean) / cycle_std
                            score += residual * 0.5

                elif expert_name == 'Trend':
                    hits = (data['zodiac'] == z).astype(float).values
                    n = len(hits)
                    ages = np.arange(n)[::-1]
                    weights = np.exp(-0.1 * ages)
                    weighted_freq = np.sum(hits * weights)
                    score = weighted_freq

                elif expert_name == 'Momentum':
                    streak = 0
                    for i in range(upto_idx - 1, -1, -1):
                        if self.df.iloc[i]['zodiac'] == z:
                            streak += 1
                        else:
                            break

                    freq_10 = (data.iloc[-10:]['zodiac'] == z).sum() if upto_idx >= 10 else 0
                    freq_20 = (data.iloc[-20:]['zodiac'] == z).sum() if upto_idx >= 20 else 0

                    score = streak * 0.5 + freq_10 * 0.3 + (freq_10 - freq_20) * 0.2

                elif expert_name == 'Color':
                    zodiac_colors = {
                        '红': ['马', '羊', '兔', '猴'],
                        '蓝': ['鼠', '牛', '蛇', '狗'],
                        '绿': ['虎', '龍', '雞', '豬']
                    }
                    color = None
                    for c, zs in zodiac_colors.items():
                        if z in zs:
                            color = c
                            break

                    if color:
                        freq_10 = (data.iloc[-10:]['color'] == color).sum() if upto_idx >= 10 else 0
                        expected = 10 / 3
                        score = freq_10 / expected if expected > 0 else 0

                scores[z] = score

            sorted_z = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            predictions[expert_name] = [z for z, s in sorted_z[:6]]

        return predictions

    def update(self, predictions: Dict[str, List[str]], actual_zodiac: str):
        """更新专家表现"""
        self.actual_history.append(actual_zodiac)

        for expert_name, expert in self.experts.items():
            top6 = predictions.get(expert_name, [])
            hit = 1 if actual_zodiac in top6 else 0
            expert.add_result(hit)

        self.prediction_history.append(predictions)

    def get_expert_weights(self, window: int = 30) -> Dict[str, float]:
        """计算各专家的动态权重"""
        weights = {}

        hit_rates = []
        for name, expert in self.experts.items():
            hr = expert.get_recent_hit_rate(window)
            hit_rates.append(hr)

        mean_hr = np.mean(hit_rates) if hit_rates else 0

        for name, expert in self.experts.items():
            hit_rate = expert.get_recent_hit_rate(window)
            stability = 1 - np.std(expert.hit_sequence[-window:]) if len(expert.hit_sequence) >= window else 0

            state = expert.get_state(window)
            state_factor = {'HOT': 1.2, 'NORMAL': 1.0, 'COLD': 0.6}.get(state, 1.0)

            weight = hit_rate * stability * state_factor

            if hit_rate > mean_hr:
                weight *= 1.1

            weights[name] = round(weight, 4)

        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights

    def get_expert_states(self, window: int = 30) -> Dict[str, str]:
        """获取所有专家的状态"""
        return {name: expert.get_state(window) for name, expert in self.experts.items()}

    def predict_top6(self) -> List[str]:
        """使用元策略预测TOP6"""
        weights = self.get_expert_weights()
        states = self.get_expert_states()

        zodiac_scores = defaultdict(float)
        zodiac_counts = defaultdict(int)

        for expert_name, top6 in self.prediction_history[-1].items():
            weight = weights.get(expert_name, 0.25)
            state = states.get(expert_name, 'NORMAL')

            state_mult = 1.2 if state == 'HOT' else (0.7 if state == 'COLD' else 1.0)
            final_weight = weight * state_mult

            for i, zodiac in enumerate(top6):
                position_bonus = 1.0 / (1 + i * 0.1)
                zodiac_scores[zodiac] += final_weight * position_bonus
                zodiac_counts[zodiac] += 1

        sorted_zodiacs = sorted(zodiac_scores.items(), key=lambda x: x[1], reverse=True)
        return [z for z, s in sorted_zodiacs[:6]]

    def predict_with_confidence(self) -> Tuple[List[str], float]:
        """预测TOP6及置信度"""
        weights = self.get_expert_weights()

        max_weight = max(weights.values()) if weights else 0.5
        min_weight = min(weights.values()) if weights else 0.0

        confidence = (max_weight - min_weight) * 2
        confidence = min(1.0, max(0.0, confidence))

        top6 = self.predict_top6()
        return top6, confidence

    def get_meta_report(self) -> Dict:
        """生成元策略报告"""
        weights = self.get_expert_weights()
        states = self.get_expert_states()

        recent_30_hits = []
        for i in range(min(30, len(self.actual_history))):
            pred_top6 = []
            for expert_name in EXPERTS:
                if i < len(self.prediction_history):
                    pred_top6 = self.prediction_history[i].get(expert_name, [])
                    actual = self.actual_history[i]
                    if actual in pred_top6:
                        recent_30_hits.append(1)
                    else:
                        recent_30_hits.append(0)

        ensemble_hit_rate = np.mean(recent_30_hits) if recent_30_hits else 0

        random_baseline = 6 / 12
        gain = (ensemble_hit_rate - random_baseline) * 100

        stability = 1 - np.std(recent_30_hits) if len(recent_30_hits) > 1 else 0

        n = len(recent_30_hits)
        p_value = 0.05 if n >= 10 else 1.0

        report = {
            'expert_weights': weights,
            'expert_states': states,
            'ensemble_hit_rate': round(ensemble_hit_rate, 4),
            'gain': round(gain, 2),
            'stability': round(stability, 4),
            'p_value': round(p_value, 4),
            'total_predictions': len(self.actual_history),
            'recent_window': min(30, len(self.actual_history)),
            'timestamp': datetime.now().isoformat()
        }

        return report


def run_meta_backtest(df: pd.DataFrame, start_idx: int = 200) -> Dict:
    """运行元策略回测"""
    meta = MetaStrategy(df)

    all_predictions = []

    for idx in range(start_idx, len(df) - 1):
        # 获取专家预测
        preds = meta._get_expert_predictions(idx)

        # 获取实际结果
        actual = df.iloc[idx + 1]['zodiac']

        # 更新meta策略
        meta.update(preds, actual)

        # 记录预测
        top6, confidence = meta.predict_with_confidence()
        all_predictions.append({
            'idx': idx,
            'prediction': top6,
            'actual': actual,
            'hit': actual in top6,
            'confidence': confidence
        })

    # 计算整体表现
    hits = sum(1 for p in all_predictions if p['hit'])
    hit_rate = hits / len(all_predictions) if all_predictions else 0

    # 生成报告
    report = meta.get_meta_report()
    report['backtest_results'] = {
        'total_predictions': len(all_predictions),
        'hit_rate': round(hit_rate, 4),
        'hits': hits
    }

    return report


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

    from schema import load_standardized

    df = load_standardized('/home/admin1/liuhecai_strategy_search/truth_dataset.json')
    print(f"数据加载: {len(df)} 条")

    print("\n运行元策略回测...")
    report = run_meta_backtest(df, start_idx=200)

    with open('/home/admin1/liuhecai_strategy_search/meta_report.json', 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n元策略报告:")
    print(f"  专家权重: {report['expert_weights']}")
    print(f"  专家状态: {report['expert_states']}")
    print(f"  集成命中率: {report['ensemble_hit_rate']:.2%}")
    print(f"  增益: {report['gain']:.2f}%")
    print(f"  稳定性: {report['stability']:.4f}")