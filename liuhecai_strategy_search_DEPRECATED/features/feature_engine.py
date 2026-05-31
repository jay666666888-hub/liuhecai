#!/usr/bin/env python3
"""
特征工程模块
============

功能：
1. 构建所有可用特征
2. 特征选择与组合
3. 特征重要性分析

特征类型：
- 遗漏特征 (Gap)
- 热度特征 (Frequency)
- 连出特征 (Streak)
- 波色特征 (Color)
- 号码特征 (Number)
- 尾数特征 (Tail)
- 马尔可夫特征 (Markov)
- 周期特征 (Cycle)
- 五行特征 (WuXing)
- 生肖关联度 (Zodiac Correlation)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from collections import defaultdict

class FeatureBuilder:
    """特征构建器"""

    ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']

    # 波色对应（固定）
    COLOR_MAP = {
        'red': [1,2,7,8,12,13,18,19,23,24,29,30,34,35,40,45,46],
        'blue': [3,4,9,10,14,15,20,25,26,31,36,37,41,42,47,48],
        'green': [5,6,11,16,17,21,22,27,28,32,33,38,39,43,44,49]
    }

    # 五行对应（已禁用 - 覆盖率仅67%）
    # WUXING_MAP = {...}

    # 禁用特征列表
    DISABLED_FEATURES = ['wuxing']

    def __init__(self, df: pd.DataFrame, disable_features: List[str] = None):
        self.df = df
        self.disable_features = disable_features or self.DISABLED_FEATURES
        self._prepare_data()

    def _prepare_data(self):
        """数据预处理"""
        # 生肖编码
        zodiac_to_idx = {z: i for i, z in enumerate(self.ZODIACS)}
        self.df['zodiac_idx'] = self.df['special_zodiac'].map(zodiac_to_idx)

        # 波色编码
        color_to_idx = {'red': 0, 'blue': 1, 'green': 2}
        self.df['color_idx'] = self.df['special_color'].map(color_to_idx)

        # 号码处理
        self.df['num'] = self.df['special_number'].astype(int)
        self.df['num_tail'] = self.df['num'] % 10
        self.df['num_parity'] = self.df['num'] % 2
        self.df['num_size'] = (self.df['num'] > 24).astype(int)

    def compute_all_features(self, upto_idx: int, check_leak: bool = True) -> Dict[str, float]:
        """
        计算截止到upto_idx的所有特征

        重要：upto_idx是不包含的，只用之前的数据预测

        Args:
            upto_idx: 预测目标索引（特征只使用到这个索引之前的数据）
            check_leak: 是否进行泄露检测断言
        """
        if upto_idx < 30:
            return {}

        # 泄露检测断言：确保不会使用未来数据
        if check_leak:
            assert upto_idx <= len(self.df), f"Leak detected: upto_idx={upto_idx} > data_len={len(self.df)}"
            assert upto_idx > 0, "upto_idx must be positive"

        data = self.df.iloc[:upto_idx].copy()
        features = {}

        # ===================== 基础特征 =====================

        # 1. 遗漏特征 (Gap) - 每个生肖的遗漏值
        for z in self.ZODIACS:
            positions = data[data['special_zodiac'] == z].index.tolist()
            if len(positions) > 0:
                gap = upto_idx - positions[-1] - 1
            else:
                gap = upto_idx
            features[f'gap_{z}'] = min(gap, 100)

        # 2. 平均遗漏
        gaps = [features[f'gap_{z}'] for z in self.ZODIACS]
        features['avg_gap'] = np.mean(gaps)
        features['max_gap'] = max(gaps)
        features['min_gap'] = min(gaps)

        # 3. 遗漏标准差
        features['std_gap'] = np.std(gaps)

        # ===================== 热度特征 =====================

        # 窗口热度
        for window in [5, 10, 20, 50]:
            if upto_idx >= window:
                window_data = data.iloc[-window:]
                for z in self.ZODIACS:
                    count = (window_data['special_zodiac'] == z).sum()
                    features[f'freq_{window}_{z}'] = count

                # 波色热度
                for color in ['red', 'blue', 'green']:
                    count = (window_data['special_color'] == color).sum()
                    features[f'color_freq_{window}_{color}'] = count

        # ===================== 连出特征 =====================

        for z in self.ZODIACS:
            streak = 0
            for i in range(upto_idx - 1, -1, -1):
                if self.df.iloc[i]['special_zodiac'] == z:
                    streak += 1
                else:
                    break
            features[f'streak_{z}'] = streak

        # ===================== 周期特征 =====================

        # 生肖周期（平均出现间隔）
        for z in self.ZODIACS:
            positions = data[data['special_zodiac'] == z].index.tolist()
            if len(positions) >= 2:
                intervals = np.diff(positions)
                features[f'period_avg_{z}'] = np.mean(intervals)
                features[f'period_std_{z}'] = np.std(intervals)
            else:
                features[f'period_avg_{z}'] = 12
                features[f'period_std_{z}'] = 0

        # ===================== 号码特征 =====================

        if upto_idx >= 10:
            recent = data.iloc[-10:]['num'].values

            # 基本统计
            features['num_mean'] = np.mean(recent)
            features['num_std'] = np.std(recent)
            features['num_median'] = np.median(recent)

            # 单双比例
            features['parity_ratio'] = np.mean(recent % 2)

            # 大小比例
            features['size_ratio'] = np.mean((recent > 24).astype(int))

            # 尾数分布
            for t in range(10):
                features[f'tail_{t}_freq'] = np.sum(recent % 10 == t)

            # AC值（理论上用于衡量号码分散程度）
            unique_nums = len(set(recent))
            features['num_diversity'] = unique_nums / 10

        # ===================== 马尔可夫特征 =====================

        if upto_idx >= 20:
            # 状态转移矩阵
            transitions = defaultdict(lambda: defaultdict(int))
            for i in range(1, upto_idx):
                prev_z = self.df.iloc[i-1]['special_zodiac']
                curr_z = self.df.iloc[i]['special_zodiac']
                transitions[prev_z][curr_z] += 1

            # 计算转移概率
            for z1 in self.ZODIACS:
                total = sum(transitions[z1].values())
                if total > 0:
                    for z2 in self.ZODIACS:
                        features[f'markov_p_{z1}_{z2}'] = transitions[z1][z2] / total

            # 自转移概率（连续出现）
            for z in self.ZODIACS:
                if z in transitions and z in transitions[z]:
                    total = sum(transitions[z].values())
                    if total > 0:
                        features[f'self_loop_{z}'] = transitions[z][z] / total

        # ===================== 五行特征（已禁用）=====================
        # 五行映射覆盖率仅67%，部分号码缺失，禁止使用
        # if 'wuxing' not in self.disable_features:
        #     for wx, nums in self.WUXING_MAP.items():
        #         count = sum(1 for n in data.iloc[-20:]['num'] if n in nums)
        #         features[f'wuxing_{wx}_freq'] = count

        # ===================== 冷热分析 =====================

        # 冷号（遗漏大的）
        cold_threshold = np.mean([features.get(f'gap_{z}', 0) for z in self.ZODIACS]) * 1.5
        cold_zodiacs = [z for z in self.ZODIACS if features.get(f'gap_{z}', 0) > cold_threshold]
        features['n_cold_zodiacs'] = len(cold_zodiacs)

        # 热号（出现多的）
        hot_threshold = 20  # 50期中出现超过20次
        hot_zodiacs = [z for z in self.ZODIACS if features.get(f'freq_50_{z}', 0) > hot_threshold]
        features['n_hot_zodiacs'] = len(hot_zodiacs)

        return features

    def get_feature_names(self) -> List[str]:
        """获取所有特征名称"""
        names = []

        # 遗漏特征
        names.extend([f'gap_{z}' for z in self.ZODIACS])
        names.extend(['avg_gap', 'max_gap', 'min_gap', 'std_gap'])

        # 热度特征
        for window in [5, 10, 20, 50]:
            names.extend([f'freq_{window}_{z}' for z in self.ZODIACS])
            names.extend([f'color_freq_{window}_{c}' for c in ['red', 'blue', 'green']])

        # 连出特征
        names.extend([f'streak_{z}' for z in self.ZODIACS])

        # 周期特征
        names.extend([f'period_avg_{z}' for z in self.ZODIACS])
        names.extend([f'period_std_{z}' for z in self.ZODIACS])

        # 号码特征
        names.extend(['num_mean', 'num_std', 'num_median', 'parity_ratio', 'size_ratio',
                      'num_diversity', 'tail_0_freq', 'tail_1_freq', 'tail_2_freq', 'tail_3_freq',
                      'tail_4_freq', 'tail_5_freq', 'tail_6_freq', 'tail_7_freq', 'tail_8_freq', 'tail_9_freq'])

        # 马尔可夫特征
        names.extend([f'markov_p_{z1}_{z2}' for z1 in self.ZODIACS for z2 in self.ZODIACS])
        names.extend([f'self_loop_{z}' for z in self.ZODIACS])

        # 五行特征（已禁用 - 覆盖率仅67%）
        # names.extend([f'wuxing_{wx}_freq' for wx in ['金', '木', '水', '火', '土']])

        # 冷热
        names.extend(['n_cold_zodiacs', 'n_hot_zodiacs'])

        return names


class FeatureSelector:
    """特征选择器"""

    @staticmethod
    def select_by_variance(features_dict: Dict[str, float], threshold: float = 0.01) -> Dict[str, float]:
        """剔除方差过小的特征"""
        if not features_dict:
            return {}

        values = list(features_dict.values())
        if len(values) < 2:
            return features_dict

        mean_val = np.mean(values)
        std_val = np.std(values)

        if std_val < threshold:
            return {}

        return features_dict

    @staticmethod
    def normalize_features(features: Dict[str, float]) -> Dict[str, float]:
        """标准化特征"""
        if not features:
            return {}

        values = list(features.values())
        mean_val = np.mean(values)
        std_val = np.std(values)

        if std_val < 0.001:
            return {k: 0 for k in features}

        return {k: (v - mean_val) / std_val for k, v in features.items()}


class ZodiacScorer:
    """生肖评分器 - 基于特征计算每个生肖的得分"""

    def __init__(self, feature_builder: FeatureBuilder):
        self.fb = feature_builder

    def score(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        根据特征计算每个生肖的得分
        返回12个生肖的得分
        """
        scores = {}

        for z in self.fb.ZODIACS:
            score = 0

            # 1. 遗漏得分（遗漏越大，得分越高，理论上是回补机会）
            gap = features.get(f'gap_{z}', 0)
            score += gap * 2.0

            # 2. 周期得分（周期接近平均值更有规律）
            period_avg = features.get(f'period_avg_{z}', 12)
            if period_avg > 0:
                expected_interval = 12 / 1.2  # 理论周期
                period_score = 1 - abs(period_avg - expected_interval) / expected_interval
                score += period_score * 1.5

            # 3. 连出惩罚（连出越多越可能是热号反转）
            streak = features.get(f'streak_{z}', 0)
            score -= streak * 0.5

            # 4. 频率得分（近期活跃度）
            for window in [10, 20, 50]:
                freq = features.get(f'freq_{window}_{z}', 0)
                # 期望频率
                expected = window / 12
                if freq < expected:
                    score += (expected - freq) * 0.3  # 低于期望加分
                else:
                    score += (freq - expected) * 0.1  # 高于期望少加分

            # 5. 自转移概率（连续出现的惯性）
            self_loop = features.get(f'self_loop_{z}', 0)
            score -= self_loop * 2  # 自循环高意味着趋势强，追热危险

            # 6. 冷热综合
            n_cold = features.get('n_cold_zodiacs', 0)
            n_hot = features.get('n_hot_zodiacs', 0)
            if n_cold > 6:  # 冷号多，回补可能性大
                if gap > 15:
                    score += 2

            scores[z] = score

        return scores

    def get_top6(self, features: Dict[str, float]) -> List[str]:
        """获取得分最高的前6个生肖"""
        scores = self.score(features)
        sorted_zodiacs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [z for z, s in sorted_zodiacs[:6]]

    def get_top9(self, features: Dict[str, float]) -> List[str]:
        """获取得分最高的前9个生肖（九肖）"""
        scores = self.score(features)
        sorted_zodiacs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [z for z, s in sorted_zodiacs[:9]]


# 测试
if __name__ == '__main__':
    import json

    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    fb = FeatureBuilder(df)
    zs = ZodiacScorer(fb)

    # 测试特征计算
    features = fb.compute_all_features(300)  # 用前300期计算特征
    print(f"共生成 {len(features)} 个特征")

    # 测试六肖预测
    top6 = zs.get_top6(features)
    top9 = zs.get_top9(features)

    print(f"TOP6: {' '.join(top6)}")
    print(f"TOP9: {' '.join(top9)}")

    # 验证命中率
    actual = df.iloc[300]['special_zodiac']
    hit6 = actual in top6
    hit9 = actual in top9

    print(f"第300期实际生肖: {actual}")
    print(f"六肖命中: {'✅' if hit6 else '❌'}")
    print(f"九肖命中: {'✅' if hit9 else '❌'}")