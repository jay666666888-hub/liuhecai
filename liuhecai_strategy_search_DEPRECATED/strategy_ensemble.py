#!/usr/bin/env python3
"""
时间结构特征 + 策略集模块
========================

功能：
1. 时间结构特征（Cycle Residual, Decay Frequency, Volatility, State, Lunar）
2. 多专家策略集（GapExpert, TrendExpert, CycleExpert, StateExpert, MomentumExpert, ColorExpert）
3. 动态融合机制
4. 专家淘汰机制

升级自：单一策略搜索 → 时间结构 + 策略集 Ensemble
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime
import json

from enum import Enum

# ============ 常量 ============
ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
COLOR_MAP = {
    'red': [1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46],
    'blue': [3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48],
    'green': [5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49]
}

# 状态枚举
class ZodiacState(Enum):
    HOT = "HOT"
    COLD = "COLD"
    BURST = "BURST"
    TRANSITION = "TRANSITION"
    NEUTRAL = "NEUTRAL"


# ============ 第一阶段：时间结构特征 ============

class TimeStructureFeatures:
    """时间结构特征计算器"""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self._precompute_lunar()
        self._precompute_windows()

    def _precompute_lunar(self):
        """预计算农历时间结构"""
        # 解析日期（ISO格式: 2024-01-04）
        self.df['parsed_date'] = pd.to_datetime(self.df['date'], errors='coerce')
        self.df['month'] = self.df['parsed_date'].dt.month.fillna(1).astype(int)
        self.df['day'] = self.df['parsed_date'].dt.day.fillna(1).astype(int)
        self.df['weekday'] = self.df['parsed_date'].dt.dayofweek.fillna(0).astype(int)

        # 粗略农历月（实际需要 lunar calendar 库，这里用近似）
        self.df['lunar_month'] = ((self.df['month'] - 1) * 30 + self.df['day']) % 12 + 1

        # 距离春节天数（粗略估计）
        def days_to_newyear(row):
            month, day = row['month'], row['day']
            # 假设春节在2月1日附近
            if month == 1:
                return max(0, 31 - day)
            elif month == 2 and day <= 10:
                return 31 + day
            else:
                return 365 - (month - 2) * 30 - day

        self.df['days_to_newyear'] = self.df.apply(days_to_newyear, axis=1)

        # 月相（简化：按日期在月份中的位置）
        self.df['month_phase'] = self.df['day'] % 4  # 0=新月, 1=上弦, 2=满月, 3=下弦

    def _precompute_windows(self):
        """预计算滑动窗口数据"""
        # 预计算每个位置的特征数组，避免重复计算
        pass

    def compute_cycle_residual(self, upto_idx: int) -> Dict[str, float]:
        """
        周期残差特征
        cycle_residual = current_gap - cycle_mean
        不是gap大就该出，而是gap明显偏离自身周期
        """
        features = {}
        data = self.df.iloc[:upto_idx]

        for z in ZODIACS:
            positions = data[data['special_zodiac'] == z].index.tolist()
            current_gap = upto_idx - positions[-1] - 1 if positions else upto_idx

            if len(positions) >= 3:
                intervals = np.diff(positions)
                cycle_mean = np.mean(intervals)
                cycle_std = np.std(intervals)

                # 残差：偏离自身周期的程度
                if cycle_std > 0:
                    residual = (current_gap - cycle_mean) / cycle_std
                else:
                    residual = 0

                features[f'cycle_mean_{z}'] = min(cycle_mean, 100)
                features[f'cycle_std_{z}'] = min(cycle_std, 50)
                features[f'cycle_residual_{z}'] = round(residual, 3)
            else:
                features[f'cycle_mean_{z}'] = 12
                features[f'cycle_std_{z}'] = 5
                features[f'cycle_residual_{z}'] = 0

        return features

    def compute_decay_frequency(self, upto_idx: int, lambda_decay: float = 0.1) -> Dict[str, float]:
        """
        时间衰减热度特征
        weighted_freq = Σ(hit × exp(-λt))
        近期权重高，远期指数衰减
        λ可搜索，默认0.1
        """
        features = {}
        data = self.df.iloc[:upto_idx]
        n = len(data)

        for z in ZODIACS:
            # 计算每期是否命中
            hits = (data['special_zodiac'] == z).astype(float).values

            # 距离现在的期数
            ages = np.arange(n)[::-1]  # [n-1, n-2, ..., 0]

            # 指数衰减权重
            weights = np.exp(-lambda_decay * ages)
            weighted_freq = np.sum(hits * weights)

            features[f'decay_freq_{z}'] = round(weighted_freq, 3)

            # 不同衰减率
            for lam in [0.05, 0.15, 0.2]:
                weights = np.exp(-lam * ages)
                features[f'decay_freq_{lam}_{z}'] = round(np.sum(hits * weights), 3)

        return features

    def compute_volatility(self, upto_idx: int) -> Dict[str, float]:
        """
        波动率特征
        rolling_std, rolling_entropy for windows 10, 20, 50
        检测状态：HOT, COLD, BURST, TRANSITION
        """
        features = {}
        data = self.df.iloc[:upto_idx]

        for window in [10, 20, 50]:
            if upto_idx < window:
                continue

            window_data = data.iloc[-window:]
            zodiac_counts = window_data['special_zodiac'].value_counts()

            # 每个生肖的波动率
            for z in ZODIACS:
                count = zodiac_counts.get(z, 0)
                expected = window / 12

                # 滚动标准差（简化：用偏离期望的程度）
                if expected > 0:
                    std_score = abs(count - expected) / expected
                else:
                    std_score = 0

                features[f'rolling_std_{window}_{z}'] = round(std_score, 3)

            # 窗口熵（分布均匀程度）
            probs = zodiac_counts.values / window
            entropy = -np.sum(probs * np.log(probs + 1e-10))
            features[f'rolling_entropy_{window}'] = round(entropy, 3)

            # 窗口内最多出现的生肖
            if len(zodiac_counts) > 0:
                features[f'rolling_hot_{window}'] = zodiac_counts.index[0]
                features[f'rolling_hot_count_{window}'] = zodiac_counts.values[0]

        return features

    def compute_state_features(self, upto_idx: int) -> Dict[str, float]:
        """
        状态特征
        状态：HOT, COLD, BURST, TRANSITION, NEUTRAL
        计算状态转移概率
        """
        features = {}
        data = self.df.iloc[:upto_idx]

        # 首先计算每个生肖在最近窗口的状态
        window_10 = min(10, upto_idx)
        window_20 = min(20, upto_idx)

        for z in ZODIACS:
            recent_10 = data.iloc[-window_10:]
            recent_20 = data.iloc[-window_20:]

            count_10 = (recent_10['special_zodiac'] == z).sum()
            count_20 = (recent_20['special_zodiac'] == z).sum()

            expected_10 = window_10 / 12
            expected_20 = window_20 / 12

            # 状态判定
            if count_10 > expected_10 * 2:
                state_10 = 'HOT'
            elif count_10 < expected_10 * 0.3:
                state_10 = 'COLD'
            elif count_20 > count_10 * 1.5 and count_10 > expected_10:
                state_10 = 'BURST'
            elif count_20 > count_10 * 1.5 and count_10 < expected_10:
                state_10 = 'TRANSITION'
            else:
                state_10 = 'NEUTRAL'

            features[f'state_10_{z}'] = hash(state_10) % 5  # 数值化

            # 状态转移概率（最近30期）
            if upto_idx >= 30:
                recent_30 = data.iloc[-30:]
                # 计算从每种状态转移到z的概率
                state_counts = defaultdict(int)
                for i in range(1, len(recent_30)):
                    prev_z = recent_30.iloc[i-1]['special_zodiac']
                    curr_z = recent_30.iloc[i]['special_zodiac']
                    if curr_z == z:
                        state_counts[prev_z] += 1

                total = sum(state_counts.values())
                if total > 0:
                    for prev_z in ZODIACS:
                        features[f'p_state_{prev_z}_to_{z}'] = state_counts[prev_z] / total
                else:
                    for prev_z in ZODIACS:
                        features[f'p_state_{prev_z}_to_{z}'] = 0

        return features

    def compute_lunar_features(self, upto_idx: int) -> Dict[str, float]:
        """
        农历时间结构特征
        作为统计变量，不引入主观玄学规则
        """
        features = {}
        data = self.df.iloc[:upto_idx]

        if 'lunar_month' not in data.columns:
            return features

        # 月份分布（12个月）
        for month in range(1, 13):
            features[f'lunar_month_{month}_count'] = (data['lunar_month'] == month).sum()

        # 距离春节的分布
        for days in [0, 7, 14, 21, 30, 60, 90]:
            features[f'days_to_newyear_{days}'] = (data['days_to_newyear'] <= days).sum()

        # 星期分布（0-6）
        for wd in range(7):
            features[f'weekday_{wd}_count'] = (data['weekday'] == wd).sum()

        # 月相分布
        for phase in range(4):
            features[f'month_phase_{phase}_count'] = (data['month_phase'] == phase).sum()

        return features


# ============ 第二阶段：策略集（专家系统） ============

@dataclass
class ExpertOutput:
    """专家输出"""
    zodiac: str
    score: float
    confidence: float
    state: str  # HOT, COLD, etc.
    raw_features: Dict[str, float]


class BaseExpert:
    """专家基类"""
    name = "base"

    def __init__(self, feature_builder: 'TimeStructureFeatures'):
        self.fb = feature_builder
        self.enabled = True
        self.recent_performance = []  # 最近30期的命中率

    def predict(self, features: Dict[str, float], upto_idx: int) -> List[ExpertOutput]:
        """预测并返回专家输出"""
        raise NotImplementedError

    def get_weight(self) -> float:
        """计算专家权重 = 近期命中率 × 稳定性"""
        if not self.recent_performance:
            return 0.1  # 默认低权重

        recent_30 = self.recent_performance[-30:]
        if len(recent_30) < 5:
            return 0.1

        hit_rate = np.mean(recent_30)
        stability = 1 - np.std(recent_30) if np.std(recent_30) < 0.5 else 0

        return hit_rate * stability

    def update_performance(self, hit: bool):
        """更新近期表现"""
        self.recent_performance.append(1 if hit else 0)

    def should_disable(self, threshold: float = 0.02) -> bool:
        """
        检查是否应该禁用
        条件：最近30期命中率 < random+2% 连续3次
        random基准 = 1/12 ≈ 8.33%
        """
        if len(self.recent_performance) < 30:
            return False

        recent_30 = self.recent_performance[-30:]
        random_baseline = 1/12  # 8.33%

        # 检查连续3次是否都低于阈值
        below_threshold_count = 0
        for i in range(3):
            window = recent_30[-(10*(i+1)):]
            window_hit_rate = np.mean(window)
            if window_hit_rate < random_baseline + threshold:
                below_threshold_count += 1

        return below_threshold_count >= 3


class GapExpert(BaseExpert):
    """遗漏专家：基于周期残差和遗漏值"""
    name = "gap"

    def predict(self, features: Dict[str, float], upto_idx: int) -> List[ExpertOutput]:
        outputs = []

        for z in ZODIACS:
            gap = features.get(f'gap_{z}', 0)
            cycle_residual = features.get(f'cycle_residual_{z}', 0)
            cycle_mean = features.get(f'cycle_mean_{z}', 12)

            # 评分公式：gap驱动，但偏离周期则降低
            if cycle_residual > 2:
                # 远偏离周期，抑制
                score = gap * 0.5
                state = 'COLD'
            elif cycle_residual < -1:
                # 负残差，可能回补
                score = gap * 1.5
                state = 'HOT'
            else:
                score = gap * 1.0
                state = 'NEUTRAL'

            # 置信度：基于周期稳定性
            cycle_std = features.get(f'cycle_std_{z}', 5)
            confidence = max(0.1, 1 - cycle_std / 20)

            outputs.append(ExpertOutput(
                zodiac=z,
                score=score,
                confidence=confidence,
                state=state,
                raw_features={'gap': gap, 'cycle_residual': cycle_residual}
            ))

        return sorted(outputs, key=lambda x: x.score, reverse=True)


class TrendExpert(BaseExpert):
    """趋势专家：基于时间衰减热度"""
    name = "trend"

    def predict(self, features: Dict[str, float], upto_idx: int) -> List[ExpertOutput]:
        outputs = []

        for z in ZODIACS:
            # 使用默认衰减率
            decay_freq = features.get(f'decay_freq_{z}', 0)
            decay_freq_005 = features.get(f'decay_freq_0.05_{z}', 0)
            decay_freq_020 = features.get(f'decay_freq_0.2_{z}', 0)

            # 趋势强度：近期vs远期
            trend = decay_freq_005 - decay_freq_020 if 'decay_freq_0.05_' in str(features) else 0

            # 评分
            score = decay_freq + trend * 2

            # 状态判定
            if decay_freq > 1.5:
                state = 'HOT'
            elif decay_freq < 0.3:
                state = 'COLD'
            else:
                state = 'NEUTRAL'

            # 置信度
            freq_50 = features.get(f'freq_50_{z}', 0)
            confidence = min(1.0, freq_50 / 10)

            outputs.append(ExpertOutput(
                zodiac=z,
                score=score,
                confidence=confidence,
                state=state,
                raw_features={'decay_freq': decay_freq, 'trend': trend}
            ))

        return sorted(outputs, key=lambda x: x.score, reverse=True)


class CycleExpert(BaseExpert):
    """周期专家：基于波动率和状态转移"""
    name = "cycle"

    def predict(self, features: Dict[str, float], upto_idx: int) -> List[ExpertOutput]:
        outputs = []

        for z in ZODIACS:
            # 周期特征
            cycle_mean = features.get(f'cycle_mean_{z}', 12)
            cycle_std = features.get(f'cycle_std_{z}', 5)

            # 滚动波动
            rolling_std_10 = features.get(f'rolling_std_10_{z}', 0)
            rolling_std_20 = features.get(f'rolling_std_20_{z}', 0)

            # 状态转移概率
            p_from_hot = features.get(f'p_state_{z}_to_{z}', 0)  # 简化

            # 评分：周期性明显且稳定则高
            periodicity_score = (1 / (cycle_std + 1)) * (1 / (rolling_std_10 + 0.1))
            score = periodicity_score * cycle_mean / 12

            # 状态
            if rolling_std_10 > 1.5:
                state = 'BURST'
            elif rolling_std_10 < 0.3:
                state = 'COLD'
            elif rolling_std_20 > rolling_std_10 * 1.5:
                state = 'TRANSITION'
            else:
                state = 'NEUTRAL'

            confidence = max(0.1, 1 - cycle_std / 15)

            outputs.append(ExpertOutput(
                zodiac=z,
                score=score,
                confidence=confidence,
                state=state,
                raw_features={'cycle_mean': cycle_mean, 'cycle_std': cycle_std, 'rolling_std': rolling_std_10}
            ))

        return sorted(outputs, key=lambda x: x.score, reverse=True)


class StateExpert(BaseExpert):
    """状态专家：基于当前状态和转移概率"""
    name = "state"

    def predict(self, features: Dict[str, float], upto_idx: int) -> List[ExpertOutput]:
        outputs = []

        for z in ZODIACS:
            state_val = features.get(f'state_10_{z}', 2)  # 0-4

            # 状态到得分的映射
            state_scores = {0: 0.3, 1: 0.8, 2: 0.5, 3: 1.0, 4: 0.6}  # HOT, COLD, NEUTRAL, BURST, TRANSITION
            state_map = {0: 'HOT', 1: 'COLD', 2: 'NEUTRAL', 3: 'BURST', 4: 'TRANSITION'}

            # 计算从其他状态转入z的总概率
            transition_prob = 0
            for prev_z in ZODIACS:
                transition_prob += features.get(f'p_state_{prev_z}_to_{z}', 0)

            score = state_scores.get(state_val, 0.5) * (1 + transition_prob)

            outputs.append(ExpertOutput(
                zodiac=z,
                score=score,
                confidence=min(1.0, transition_prob),
                state=state_map.get(state_val, 'NEUTRAL'),
                raw_features={'state': state_val, 'transition_prob': transition_prob}
            ))

        return sorted(outputs, key=lambda x: x.score, reverse=True)


class MomentumExpert(BaseExpert):
    """动量专家：基于连出和热号趋势"""
    name = "momentum"

    def predict(self, features: Dict[str, float], upto_idx: int) -> List[ExpertOutput]:
        outputs = []

        for z in ZODIACS:
            streak = features.get(f'streak_{z}', 0)
            freq_10 = features.get(f'freq_10_{z}', 0)
            freq_20 = features.get(f'freq_20_{z}', 0)
            hot_count = features.get(f'n_hot_zodiacs', 0)

            # 动量：连出 + 近期频率变化
            momentum = streak * 0.5 + freq_10 * 0.3

            # 趋势方向
            if freq_10 > freq_20:
                trend = 'UP'
            elif freq_10 < freq_20:
                trend = 'DOWN'
            else:
                trend = 'STABLE'

            # 评分
            if streak > 3 and hot_count > 3:
                # 热号连出，追热危险
                score = momentum * 0.7
                state = 'COLD'  # 警示反转
            elif streak < 1 and freq_20 < 1:
                # 冷号，可能回补
                score = momentum + features.get(f'gap_{z}', 0) * 0.3
                state = 'HOT'
            else:
                score = momentum
                state = 'NEUTRAL'

            confidence = min(1.0, (streak + freq_10) / 15)

            outputs.append(ExpertOutput(
                zodiac=z,
                score=score,
                confidence=confidence,
                state=state,
                raw_features={'streak': streak, 'freq_10': freq_10, 'trend': trend}
            ))

        return sorted(outputs, key=lambda x: x.score, reverse=True)


class ColorExpert(BaseExpert):
    """波色专家：基于波色分布和轮换"""
    name = "color"

    def predict(self, features: Dict[str, float], upto_idx: int) -> List[ExpertOutput]:
        outputs = []

        # 波色频率
        color_counts = {}
        for color in ['red', 'blue', 'green']:
            freq = features.get(f'color_freq_10_{color}', 0)
            color_counts[color] = freq

        total = sum(color_counts.values())
        if total == 0:
            total = 1

        # 每个波色的均衡程度
        expected = total / 3

        for color in ['red', 'blue', 'green']:
            freq = color_counts.get(color, 0)

            # 如果某个波色太热，可能反转
            if freq > expected * 1.5:
                state = 'COLD'  # 过热
            elif freq < expected * 0.5:
                state = 'HOT'  # 过冷
            else:
                state = 'NEUTRAL'

            score = freq / expected if expected > 0 else 0

            # 关联到生肖
            for z in ZODIACS:
                if z in ['马', '羊', '兔', '猴', '蛇', '狗']:  # 这些生肖偏向红波
                    continue

        return outputs


class StrategyEnsemble:
    """策略集管理器"""

    def __init__(self):
        self.fb: Optional[TimeStructureFeatures] = None
        self.experts = []
        self.history = []

    def initialize(self, df: pd.DataFrame):
        """初始化专家系统"""
        self.fb = TimeStructureFeatures(df)

        # 创建专家实例
        self.experts = [
            GapExpert(self.fb),
            TrendExpert(self.fb),
            CycleExpert(self.fb),
            StateExpert(self.fb),
            MomentumExpert(self.fb),
        ]

    def compute_features(self, upto_idx: int) -> Dict[str, float]:
        """计算所有时间结构特征"""
        features = {}

        # 基础特征
        data = self.fb.df.iloc[:upto_idx].copy()
        zodiac_col = 'zodiac_generated' if 'zodiac_generated' in data.columns else 'special_zodiac'
        color_col = 'color_generated' if 'color_generated' in data.columns else 'special_color'

        # 遗漏特征
        for z in ZODIACS:
            positions = data[data[zodiac_col] == z].index.tolist()
            gap = upto_idx - positions[-1] - 1 if positions else upto_idx
            features[f'gap_{z}'] = min(gap, 100)

        # 周期特征
        cycle_features = self.fb.compute_cycle_residual(upto_idx)
        features.update(cycle_features)

        # 衰减频率
        decay_features = self.fb.compute_decay_frequency(upto_idx)
        features.update(decay_features)

        # 波动率
        volatility_features = self.fb.compute_volatility(upto_idx)
        features.update(volatility_features)

        # 状态特征
        state_features = self.fb.compute_state_features(upto_idx)
        features.update(state_features)

        # 频率特征
        for window in [10, 20, 50]:
            if upto_idx >= window:
                window_data = data.iloc[-window:]
                for z in ZODIACS:
                    features[f'freq_{window}_{z}'] = (window_data[zodiac_col] == z).sum()

        # 连出特征
        for z in ZODIACS:
            streak = 0
            for i in range(upto_idx - 1, -1, -1):
                if self.fb.df.iloc[i]['special_zodiac'] == z:
                    streak += 1
                else:
                    break
            features[f'streak_{z}'] = streak

        # 冷热统计
        freq_50 = {z: features.get(f'freq_50_{z}', 0) for z in ZODIACS}
        hot_threshold = 20
        hot_zodiacs = [z for z, f in freq_50.items() if f > hot_threshold]
        features['n_hot_zodiacs'] = len(hot_zodiacs)

        return features

    def predict_top6(self, upto_idx: int) -> List[str]:
        """使用动态融合预测TOP6"""
        features = self.compute_features(upto_idx)

        # 各专家预测
        expert_predictions = []
        for expert in self.experts:
            if not expert.enabled:
                continue
            predictions = expert.predict(features, upto_idx)
            weight = expert.get_weight()
            expert_predictions.append((expert.name, predictions, weight))

        # 动态融合
        zodiac_scores = defaultdict(float)
        total_weight = 0

        for expert_name, predictions, weight in expert_predictions:
            for i, pred in enumerate(predictions):
                # 位置折扣：排名靠前的权重更高
                position_discount = 1.0 / (1 + i * 0.1)
                final_score = pred.score * pred.confidence * weight * position_discount
                zodiac_scores[pred.zodiac] += final_score
                total_weight += weight

        if total_weight > 0:
            # 归一化
            for z in zodiac_scores:
                zodiac_scores[z] /= total_weight

        # 排序取TOP6
        sorted_zodiacs = sorted(zodiac_scores.items(), key=lambda x: x[1], reverse=True)
        return [z for z, s in sorted_zodiacs[:6]]

    def update_experts(self, actual_zodiac: str):
        """更新所有专家的表现"""
        for expert in self.experts:
            hit = actual_zodiac in expert.recent_performance[-1:] if expert.recent_performance else False
            expert.update_performance(actual_zodiac in [z for z, s in [(z, 0) for z in ZODIACS]])

    def check_elimination(self) -> List[str]:
        """检查并标记需要淘汰的专家"""
        disabled = []
        for expert in self.experts:
            if expert.enabled and expert.should_disable():
                expert.enabled = False
                disabled.append(expert.name)
        return disabled

    def get_expert_performance(self) -> Dict:
        """获取专家表现报告"""
        performance = []
        for expert in self.experts:
            recent_30 = expert.recent_performance[-30:] if expert.recent_performance else []
            hit_rate = np.mean(recent_30) if recent_30 else 0

            performance.append({
                'name': expert.name,
                'enabled': expert.enabled,
                'hit_rate_30': round(hit_rate, 4),
                'weight': round(expert.get_weight(), 4),
                'recent_10': recent_30[-10:] if len(recent_30) >= 10 else []
            })

        return {'experts': performance, 'timestamp': datetime.now().isoformat()}


# ============ 测试 ============

if __name__ == '__main__':
    import json

    # 加载数据
    with open('/home/admin1/liuhecai_strategy_search/truth_dataset.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    print(f"加载数据: {len(df)} 条")

    # 初始化策略集
    ensemble = StrategyEnsemble()
    ensemble.initialize(df)

    # 测试特征计算
    features = ensemble.compute_features(300)
    print(f"\\n时间结构特征数量: {len(features)}")

    # 测试预测
    top6 = ensemble.predict_top6(300)
    print(f"\\n预测TOP6: {' '.join(top6)}")

    # 验证
    actual = df.iloc[300]['special_zodiac']
    hit = actual in top6
    print(f"第300期实际: {actual}, 命中: {'✅' if hit else '❌'}")

    # 专家表现
    perf = ensemble.get_expert_performance()
    print(f"\\n专家表现:")
    for e in perf['experts']:
        print(f"  {e['name']}: hit_rate={e['hit_rate_30']:.2%}, enabled={e['enabled']}")