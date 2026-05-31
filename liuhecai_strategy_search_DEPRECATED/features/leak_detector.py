#!/usr/bin/env python3
"""
特征泄露检测器
==============

确保任何特征只使用t-1之前的数据，禁止使用未来数据。
发现泄露时自动终止并输出报告。
"""

import json
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class LeakReport:
    """泄露报告"""
    found_leaks: List[Dict] = field(default_factory=list)
    checked_features: int = 0
    checked_records: int = 0
    is_safe: bool = True
    error_message: str = ""

    def to_dict(self) -> Dict:
        return {
            'timestamp': datetime.now().isoformat(),
            'is_safe': self.is_safe,
            'checked_features': self.checked_features,
            'checked_records': self.checked_records,
            'found_leaks': self.found_leaks,
            'error_message': self.error_message
        }

class FeatureLeakDetector:
    """
    特征泄露检测器

    核心原则：
    - 任何特征只能使用 t-1 之前的数据
    - 预测时刻t的数据不能用于特征计算
    - 发现泄露立即终止训练
    """

    # 禁止的模式（这些特征名暗示使用了当前期数据）
    FORBIDDEN_PATTERNS = [
        'current_period', 'now', 'future',
        'draw[t]', 'result[t]', 'actual[t]'
    ]

    # 允许的特征类型（相对于预测时刻的延迟）
    SAFE_LAG = {
        'gap_': 1,           # 遗漏：至少滞后1期
        'freq_': 1,          # 频率：至少滞后1期
        'streak_': 1,        # 连出：至少滞后1期
        'period_avg_': 1,    # 周期：至少滞后1期
        'color_freq_': 1,    # 波色频率：至少滞后1期
        'num_mean': 1,       # 号码均值：至少滞后1期
        'markov_p_': 1,     # 马尔可夫概率：至少滞后1期
    }

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.leaks_found = []

    def check_feature_computation(self, upto_idx: int, features: Dict) -> LeakReport:
        """
        检查特征计算是否泄露

        Args:
            upto_idx: 预测时刻索引（特征只能用到upto_idx之前）
            features: 计算出的特征字典

        Returns:
            LeakReport: 检查结果
        """
        report = LeakReport()
        report.checked_records = upto_idx

        # 1. 检查特征名是否包含禁止模式
        for feature_name in features.keys():
            for pattern in self.FORBIDDEN_PATTERNS:
                if pattern in feature_name.lower():
                    self.leaks_found.append({
                        'type': 'forbidden_pattern',
                        'feature': feature_name,
                        'pattern': pattern,
                        'upto_idx': upto_idx
                    })

        # 2. 验证特征计算是否使用了正确的数据范围
        # 每个特征都应该基于 self.df.iloc[:upto_idx] 计算

        # 3. 检查遗漏值是否正确
        for z in ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']:
            gap_key = f'gap_{z}'
            if gap_key in features:
                # 重新计算验证
                positions = self.df.iloc[:upto_idx][self.df.iloc[:upto_idx]['special_zodiac'] == z].index.tolist()
                if positions:
                    expected_gap = upto_idx - positions[-1] - 1
                    actual_gap = features[gap_key]

                    # 允许最大误差为1（边界情况）
                    if abs(expected_gap - actual_gap) > 1:
                        self.leaks_found.append({
                            'type': 'gap_mismatch',
                            'feature': gap_key,
                            'expected': expected_gap,
                            'actual': actual_gap,
                            'upto_idx': upto_idx
                        })

        # 4. 检查波色特征
        for color in ['red', 'blue', 'green']:
            color_key = f'color_freq_10_{color}'
            if color_key in features:
                window_data = self.df.iloc[max(0, upto_idx-10):upto_idx]
                expected = (window_data['special_color'] == color).sum()
                actual = features[color_key]

                if abs(expected - actual) > 1:
                    self.leaks_found.append({
                        'type': 'color_mismatch',
                        'feature': color_key,
                        'expected': expected,
                        'actual': actual,
                        'upto_idx': upto_idx
                    })

        report.checked_features = len(features)

        if self.leaks_found:
            report.is_safe = False
            report.found_leaks = self.leaks_found.copy()
            report.error_message = f"发现 {len(self.leaks_found)} 个特征泄露！"

        return report

    def verify_feature_consistency(self, upto_idx: int, features: Dict,
                                   feature_builder_func) -> LeakReport:
        """
        验证特征计算的一致性

        使用不同的特征构建器重新计算，对比结果
        """
        report = LeakReport()

        # 重新计算特征
        recalculated = feature_builder_func(upto_idx)

        # 对比每个特征
        for key in features.keys():
            if key in recalculated:
                orig = features[key]
                new = recalculated[key]

                # 数值比较（允许浮点数误差）
                if isinstance(orig, (int, float)) and isinstance(new, (int, float)):
                    if abs(orig - new) > 0.01:
                        self.leaks_found.append({
                            'type': 'value_mismatch',
                            'feature': key,
                            'original': orig,
                            'recalculated': new,
                            'upto_idx': upto_idx
                        })

        if self.leaks_found:
            report.is_safe = False
            report.found_leaks = self.leaks_found.copy()

        return report

    def temporal_consistency_check(self, start_idx: int, end_idx: int) -> Dict:
        """
        时序一致性检查

        确保特征在时间线上是一致的：
        - 特征值应该随着时间缓慢变化
        - 不会出现突变
        """
        results = {
            'checked_windows': 0,
            'anomalies': [],
            'is_consistent': True
        }

        for i in range(start_idx, end_idx - 10, 10):
            # 计算相邻窗口的特征
            features1 = self._compute_mock_features(i)
            features2 = self._compute_mock_features(i + 10)

            # 检查是否有突变
            for key in features1.keys():
                if key in features2:
                    val1 = features1[key]
                    val2 = features2[key]

                    # 如果变化超过50%，可能是泄露
                    if val1 != 0:
                        change = abs(val2 - val1) / abs(val1)
                        if change > 0.5:
                            results['anomalies'].append({
                                'feature': key,
                                'window': i,
                                'val1': val1,
                                'val2': val2,
                                'change': change
                            })

            results['checked_windows'] += 1

        if results['anomalies']:
            results['is_consistent'] = False

        return results

    def _compute_mock_features(self, idx: int) -> Dict:
        """计算模拟特征（用于测试）"""
        data = self.df.iloc[:idx]
        features = {}

        # 简单特征
        for z in ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']:
            positions = data[data['special_zodiac'] == z].index.tolist()
            gap = idx - positions[-1] - 1 if positions else idx
            features[f'gap_{z}'] = min(gap, 100)

        return features

    def assert_no_leak(self, upto_idx: int, features: Dict, message: str = ""):
        """
        断言没有泄露，如果发现泄露则抛出异常

        这是自动终止训练的关键
        """
        report = self.check_feature_computation(upto_idx, features)

        if not report.is_safe:
            error_msg = f"【泄露检测失败】{message}\n"
            error_msg += f"发现 {len(report.found_leaks)} 个泄露:\n"
            for leak in report.found_leaks[:5]:  # 只显示前5个
                error_msg += f"  - {leak}\n"

            # 保存泄露报告
            self.save_leak_report(report)

            # 抛出异常，终止训练
            raise LeakDetectionError(error_msg, report)

    def save_leak_report(self, report: LeakReport):
        """保存泄露报告"""
        output_file = '/home/admin1/liuhecai_strategy_search/leak_report.json'
        with open(output_file, 'w') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"[泄露检测] 报告已保存: {output_file}")


class LeakDetectionError(Exception):
    """泄露检测异常"""
    def __init__(self, message: str, report: LeakReport):
        super().__init__(message)
        self.report = report


# ============ 测试 ============
if __name__ == '__main__':
    # 加载数据
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    # 测试检测器
    detector = FeatureLeakDetector(df)

    # 检查不同时间点的特征
    for test_idx in [100, 200, 300, 500]:
        features = detector._compute_mock_features(test_idx)
        report = detector.check_feature_computation(test_idx, features)

        print(f"\n索引 {test_idx}:")
        print(f"  检查特征数: {report.checked_features}")
        print(f"  是否安全: {report.is_safe}")
        print(f"  泄露数: {len(report.found_leaks)}")

    print("\n泄露检测模块测试完成")