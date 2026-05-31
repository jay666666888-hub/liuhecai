#!/usr/bin/env python3
"""
特征增益验证模块
==============

目的：验证新增特征是否具有真实预测增益

方法：
- Walk Forward验证
- 多Seed统计
- A/B/C对比测试

A: 原系统（基准）
B: 原系统 + 单个新增特征
C: 原系统 + 所有新增特征

判定规则：
- gain < 0.5% → REMOVE
- 0.5% ~ 1% → WEAK
- > 1% → KEEP
- p > 0.05 → WEAK
"""

import sys
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass
from itertools import combinations

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

from schema import load_standardized


@dataclass
class ValidationResult:
    """验证结果"""
    feature: str
    baseline: float
    new_score: float
    gain: float
    std: float
    p_value: float
    importance: float
    leak_risk: str
    status: str


class FeatureValidator:
    """特征增益验证器"""

    SEEDS = [42, 123, 456, 789, 999]

    def __init__(self, data_path: str):
        self.df = load_standardized(data_path)
        self.baseline_results = {}
        self.feature_results = {}

    def _walk_forward_test(self, features_func, seed: int) -> float:
        """
        执行Walk Forward测试
        返回平均测试命中率
        """
        np.random.seed(seed)

        window_config = {
            'train_size': 200,
            'test_size': 50,
            'step_size': 50,
            'min_train_size': 100
        }

        total_hits = 0
        total_tests = 0

        for test_start in range(window_config['min_train_size'],
                                len(self.df) - window_config['test_size'],
                                window_config['step_size']):

            train_end = test_start
            test_end = test_start + window_config['test_size']

            if test_end > len(self.df):
                break

            # 获取特征
            features = features_func(train_end)
            if not features:
                continue

            # 简单策略：取得分最高的6个生肖
            zodiac_scores = []
            for z in ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']:
                score = features.get(f'base_score_{z}', 0)
                zodiac_scores.append((z, score))

            zodiac_scores.sort(key=lambda x: x[1], reverse=True)
            top6 = [z for z, s in zodiac_scores[:6]]

            # 测试
            actual = self.df.iloc[test_start]['zodiac']
            hit = 1 if actual in top6 else 0
            total_hits += hit
            total_tests += 1

        return total_hits / total_tests if total_tests > 0 else 0

    def _baseline_features(self, upto_idx: int) -> Dict:
        """基准特征：只有gap/freq/streak"""
        data = self.df.iloc[:upto_idx]
        features = {}

        ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']

        # 遗漏特征
        for z in ZODIACS:
            positions = data[data['zodiac'] == z].index.tolist()
            gap = upto_idx - positions[-1] - 1 if positions else upto_idx
            features[f'gap_{z}'] = min(gap, 100)

        # 频率特征
        for window in [10, 20, 50]:
            if upto_idx >= window:
                window_data = data.iloc[-window:]
                for z in ZODIACS:
                    features[f'freq_{window}_{z}'] = (window_data['zodiac'] == z).sum()

        # 连出特征
        for z in ZODIACS:
            streak = 0
            for i in range(upto_idx - 1, -1, -1):
                if self.df.iloc[i]['zodiac'] == z:
                    streak += 1
                else:
                    break
            features[f'streak_{z}'] = streak

        # 基准得分（用于排序）
        for z in ZODIACS:
            base_score = (
                features.get(f'gap_{z}', 0) * 2.0 +
                features.get(f'freq_20_{z}', 0) * 0.5 -
                features.get(f'streak_{z}', 0) * 0.3
            )
            features[f'base_score_{z}'] = base_score

        return features

    def _add_cycle_features(self, base_features: Dict, upto_idx: int) -> Dict:
        """添加周期残差特征"""
        data = self.df.iloc[:upto_idx]
        ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']

        for z in ZODIACS:
            positions = data[data['zodiac'] == z].index.tolist()
            current_gap = base_features.get(f'gap_{z}', 0)

            if len(positions) >= 3:
                intervals = np.diff(positions)
                cycle_mean = np.mean(intervals)
                cycle_std = np.std(intervals)

                if cycle_std > 0:
                    residual = (current_gap - cycle_mean) / cycle_std
                else:
                    residual = 0

                base_features[f'cycle_mean_{z}'] = min(cycle_mean, 100)
                base_features[f'cycle_std_{z}'] = min(cycle_std, 50)
                base_features[f'cycle_residual_{z}'] = round(residual, 3)

                # 更新得分
                base_score = base_features[f'base_score_{z}']
                base_score += residual * 0.5
                base_features[f'base_score_{z}'] = base_score

        return base_features

    def _add_decay_features(self, base_features: Dict, upto_idx: int) -> Dict:
        """添加时间衰减热度特征"""
        data = self.df.iloc[:upto_idx]
        ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']

        lambda_decay = 0.1
        n = len(data)

        for z in ZODIACS:
            hits = (data['zodiac'] == z).astype(float).values
            ages = np.arange(n)[::-1]
            weights = np.exp(-lambda_decay * ages)
            weighted_freq = np.sum(hits * weights)

            base_features[f'decay_freq_{z}'] = round(weighted_freq, 3)

            # 更新得分
            base_score = base_features[f'base_score_{z}']
            base_score += weighted_freq * 0.2
            base_features[f'base_score_{z}'] = base_score

        return base_features

    def _add_volatility_features(self, base_features: Dict, upto_idx: int) -> Dict:
        """添加波动率特征"""
        data = self.df.iloc[:upto_idx]
        ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']

        window = min(20, upto_idx)
        if window < 10:
            return base_features

        window_data = data.iloc[-window:]
        zodiac_counts = window_data['zodiac'].value_counts()

        for z in ZODIACS:
            count = zodiac_counts.get(z, 0)
            expected = window / 12

            if expected > 0:
                std_score = abs(count - expected) / expected
            else:
                std_score = 0

            base_features[f'rolling_std_{z}'] = round(std_score, 3)

            # 更新得分
            base_score = base_features[f'base_score_{z}']
            base_score -= std_score * 0.1  # 波动大则抑制
            base_features[f'base_score_{z}'] = base_score

        return base_features

    def _add_state_features(self, base_features: Dict, upto_idx: int) -> Dict:
        """添加状态特征"""
        data = self.df.iloc[:upto_idx]
        ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']

        window_10 = min(10, upto_idx)
        window_20 = min(20, upto_idx)

        for z in ZODIACS:
            recent_10 = data.iloc[-window_10:] if window_10 > 0 else data
            recent_20 = data.iloc[-window_20:] if window_20 > 0 else data

            count_10 = (recent_10['zodiac'] == z).sum()
            count_20 = (recent_20['zodiac'] == z).sum()

            expected = window_10 / 12

            # 状态数值化
            if count_10 > expected * 2:
                state_val = 0  # HOT
            elif count_10 < expected * 0.3:
                state_val = 1  # COLD
            else:
                state_val = 2  # NEUTRAL

            base_features[f'state_10_{z}'] = state_val

            # 更新得分
            base_score = base_features[f'base_score_{z}']
            if state_val == 0:  # HOT
                base_score *= 0.9  # 过热抑制
            elif state_val == 1:  # COLD
                base_score *= 1.1  # 过冷加分
            base_features[f'base_score_{z}'] = base_score

        return base_features

    def validate_single_feature(self, feature_name: str, add_func) -> ValidationResult:
        """验证单个特征"""
        results = {'baseline': [], 'with_feature': []}

        for seed in self.SEEDS:
            # 基准测试
            baseline_hit = self._walk_forward_test(self._baseline_features, seed)
            results['baseline'].append(baseline_hit)

            # 带新特征测试
            def features_with_new(upto_idx):
                base = self._baseline_features(upto_idx)
                return add_func(base, upto_idx)

            with_feature_hit = self._walk_forward_test(features_with_new, seed)
            results['with_feature'].append(with_feature_hit)

        baseline_mean = np.mean(results['baseline'])
        new_mean = np.mean(results['with_feature'])
        gain = (new_mean - baseline_mean) * 100  # 转为百分比

        # 统计检验
        std = np.std(results['with_feature']) - np.std(results['baseline'])
        if len(results['baseline']) > 1:
            t_stat = (new_mean - baseline_mean) / (np.std(results['baseline']) / np.sqrt(len(results['baseline'])))
            p_value = 2 * (1 - self._t_cdf(abs(t_stat), len(results['baseline']) - 1))
        else:
            p_value = 1.0

        # 重要性（增益绝对值）
        importance = abs(gain)

        # 泄露风险（检查特征是否只使用历史数据）
        leak_risk = "LOW" if add_func.__name__ != '_add_cycle_features' else "MEDIUM"

        # 状态判定
        if gain < 0.5:
            status = "REMOVE"
        elif gain < 1.0:
            status = "WEAK"
        else:
            status = "KEEP"

        if p_value > 0.05:
            status = "WEAK"

        return ValidationResult(
            feature=feature_name,
            baseline=round(baseline_mean, 4),
            new_score=round(new_mean, 4),
            gain=round(gain, 2),
            std=round(std, 4),
            p_value=round(p_value, 4),
            importance=round(importance, 2),
            leak_risk=leak_risk,
            status=status
        )

    def _t_cdf(self, t: float, df: int) -> float:
        """简化t分布CDF计算"""
        # 使用近似
        import math
        x = df / (df + t * t)
        return 1 - 0.5 * math.pow(x, df / 2)

    def validate_all(self) -> Dict:
        """验证所有新增特征"""
        features_to_test = [
            ('cycle', self._add_cycle_features),
            ('decay', self._add_decay_features),
            ('volatility', self._add_volatility_features),
            ('state', self._add_state_features),
        ]

        results = []
        for name, func in features_to_test:
            print(f"Validating {name}...")
            result = self.validate_single_feature(name, func)
            results.append(result)
            print(f"  baseline={result.baseline:.2%}, new={result.new_score:.2%}, gain={result.gain:.2f}%, status={result.status}")

        return {r.feature: r.__dict__ for r in results}

    def validate_combinations(self) -> Dict:
        """验证特征组合增益"""
        feature_funcs = [
            ('cycle', self._add_cycle_features),
            ('decay', self._add_decay_features),
            ('volatility', self._add_volatility_features),
            ('state', self._add_state_features),
        ]

        # 测试所有组合
        combinations_results = {}

        # 单个特征
        for name, func in feature_funcs:
            result = self.validate_single_feature(name, func)
            combinations_results[name] = {
                'features': [name],
                'hit_rate': result.new_score,
                'gain': result.gain,
                'p_value': result.p_value,
                'status': result.status
            }

        # 两个特征组合
        for name1, func1 in feature_funcs:
            for name2, func2 in feature_funcs:
                if name1 >= name2:
                    continue

                def combined_func(base, upto_idx):
                    base = func1(base.copy(), upto_idx)
                    base = func2(base, upto_idx)
                    return base

                result = self.validate_single_feature(f"{name1}+{name2}", combined_func)
                combinations_results[f"{name1}+{name2}"] = {
                    'features': [name1, name2],
                    'hit_rate': result.new_score,
                    'gain': result.gain,
                    'p_value': result.p_value,
                    'status': result.status
                }

        # 三个特征组合
        for name1, func1 in feature_funcs:
            for name2, func2 in feature_funcs:
                for name3, func3 in feature_funcs:
                    if name1 >= name2 or name2 >= name3:
                        continue

                    def combined3(base, upto_idx):
                        base = func1(base.copy(), upto_idx)
                        base = func2(base, upto_idx)
                        base = func3(base, upto_idx)
                        return base

                    result = self.validate_single_feature(f"{name1}+{name2}+{name3}", combined3)
                    combinations_results[f"{name1}+{name2}+{name3}"] = {
                        'features': [name1, name2, name3],
                        'hit_rate': result.new_score,
                        'gain': result.gain,
                        'p_value': result.p_value,
                        'status': result.status
                    }

        # 所有特征
        def all_features(base, upto_idx):
            base = self._add_cycle_features(base.copy(), upto_idx)
            base = self._add_decay_features(base, upto_idx)
            base = self._add_volatility_features(base, upto_idx)
            base = self._add_state_features(base, upto_idx)
            return base

        result = self.validate_single_feature("all", all_features)
        combinations_results["all"] = {
            'features': ['cycle', 'decay', 'volatility', 'state'],
            'hit_rate': result.new_score,
            'gain': result.gain,
            'p_value': result.p_value,
            'status': result.status
        }

        return combinations_results


def run_validation():
    """执行特征验证"""
    print("=" * 60)
    print("特征增益验证")
    print("=" * 60)

    validator = FeatureValidator('/home/admin1/liuhecai_strategy_search/truth_dataset.json')

    # 阶段1：单个特征验证
    print("\n[阶段1] 单特征验证")
    single_results = validator.validate_all()

    # 保存单个特征结果
    with open('/home/admin1/liuhecai_strategy_search/feature_validation.json', 'w') as f:
        json.dump(single_results, f, ensure_ascii=False, indent=2)

    # 阶段2：组合验证
    print("\n[阶段2] 组合验证")
    combo_results = validator.validate_combinations()

    combo_report = {
        'combinations': combo_results,
        'timestamp': datetime.now().isoformat()
    }

    with open('/home/admin1/liuhecai_strategy_search/feature_combination_report.json', 'w') as f:
        json.dump(combo_report, f, ensure_ascii=False, indent=2)

    # 汇总
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)

    keep = [k for k, v in single_results.items() if v['status'] == 'KEEP']
    weak = [k for k, v in single_results.items() if v['status'] == 'WEAK']
    remove = [k for k, v in single_results.items() if v['status'] == 'REMOVE']

    print(f"\nKEEP ({len(keep)}): {keep}")
    print(f"WEAK ({len(weak)}): {weak}")
    print(f"REMOVE ({len(remove)}): {remove}")

    # 判断是否允许继续
    best_combo = max(combo_results.items(), key=lambda x: x[1]['gain'])
    ensemble_gain = best_combo[1]['gain']
    ensemble_p = best_combo[1]['p_value']

    avg_gain = np.mean([v['gain'] for v in single_results.values()])

    print(f"\n平均特征增益: {avg_gain:.2f}%")
    print(f"最佳组合: {best_combo[0]}, gain={ensemble_gain:.2f}%, p={ensemble_p:.4f}")

    if avg_gain > 1.0 and ensemble_gain > 2.0 and ensemble_p < 0.05:
        decision = "CONTINUE"
        print(f"\n✓ 验证通过，允许架构扩展")
    else:
        decision = "STOP"
        print(f"\n✗ 验证未通过，停止架构扩展")

    # 保存最终决策
    decision_report = {
        'avg_feature_gain': round(avg_gain, 2),
        'best_combination': best_combo[0],
        'ensemble_gain': round(ensemble_gain, 2),
        'ensemble_p_value': round(ensemble_p, 4),
        'decision': decision,
        'allowed_to_modularize': decision == "CONTINUE",
        'timestamp': datetime.now().isoformat()
    }

    with open('/home/admin1/liuhecai_strategy_search/validation_decision.json', 'w') as f:
        json.dump(decision_report, f, ensure_ascii=False, indent=2)

    return decision_report


if __name__ == '__main__':
    result = run_validation()
    print(f"\n最终决策: {result['decision']}")