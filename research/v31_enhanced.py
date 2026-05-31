#!/usr/bin/env python3
"""
澳门六合 - v31 增强型预测器
基于v12核心逻辑 + 多项增强

增强策略：
1. 多尺度gap分析
2. 动态权重调整
3. 冷热自适应
4. 多模型融合
"""

import sys
sys.path.insert(0, '/mnt/c/Users/Admin/liuhecai')
from predictor.data_fetcher import get_all_records, build_standard_records
import numpy as np
from scipy import stats
from collections import Counter

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


class V31EnhancedPredictor:
    """增强型预测器"""

    def __init__(self):
        self.zodiacs = ZODIACS
        self.lookback = 11

    def _compute_features(self, history):
        """计算所有特征"""
        n = len(history)

        features = {}
        for z in self.zodiacs:
            # 历史出现位置
            positions = [i for i, r in enumerate(history) if r.get('特码生肖') == z]

            if not positions:
                features[z] = {
                    'gap': n,  # 从未出现
                    'gap_5': n,
                    'gap_11': n,
                    'gap_30': n,
                    'gap_60': n,
                    'pattern_ratio': 0.0,
                    'pattern_ratio_5': 0.0,
                    'pattern_ratio_11': 0.0,
                    'freq_5': 0.0,
                    'freq_11': 0.0,
                    'freq_30': 0.0,
                    'freq_60': 0.0,
                    'trend': 0.0,
                    'variance': 0.0,
                    'streak': 0.0,
                    'last_position': -1
                }
                continue

            last_pos = positions[-1]
            current_gap = n - last_pos - 1

            # 多尺度gap
            gap_5 = n - last_pos - 1 if last_pos >= n - 5 else n - (n - 5) - 1
            gap_11 = current_gap
            gap_30 = current_gap if n - last_pos <= 30 else n - (n - 30) - 1
            gap_60 = current_gap if n - last_pos <= 60 else n - (n - 60) - 1

            # pattern_ratio (最近几期出现占比)
            window_5 = history[max(0, n-5):n]
            window_11 = history[max(0, n-11):n]

            pattern_count_5 = sum(1 for r in window_5 if r.get('特码生肖') == z)
            pattern_count_11 = sum(1 for r in window_11 if r.get('特码生肖') == z)

            # 频率
            freq_5 = pattern_count_5 / min(5, n)
            freq_11 = pattern_count_11 / min(11, n)

            window_30 = history[max(0, n-30):n]
            window_60 = history[max(0, n-60):n]
            freq_30 = sum(1 for r in window_30 if r.get('特码生肖') == z) / min(30, n)
            freq_60 = sum(1 for r in window_60 if r.get('特码生肖') == z) / min(60, n)

            # trend: 间隔变化
            if len(positions) >= 2:
                intervals = [positions[i] - positions[i-1] for i in range(1, len(positions))]
                trend = intervals[-1] - np.mean(intervals) if len(intervals) >= 2 else 0
                variance = np.var(intervals) if len(intervals) >= 2 else 0
            else:
                trend = 0
                variance = 0

            # streak
            streak = 0
            for i in range(n - 1, -1, -1):
                if history[i].get('特码生肖') == z:
                    streak += 1
                else:
                    break

            features[z] = {
                'gap': current_gap,
                'gap_5': gap_5,
                'gap_11': gap_11,
                'gap_30': gap_30,
                'gap_60': gap_60,
                'pattern_ratio': pattern_count_11 / min(11, n),
                'pattern_ratio_5': pattern_count_5 / min(5, n),
                'freq_5': freq_5,
                'freq_11': freq_11,
                'freq_30': freq_30,
                'freq_60': freq_60,
                'trend': trend,
                'variance': variance,
                'streak': streak,
                'last_position': last_pos
            }

        return features

    def _compute_scores_v1(self, features):
        """v12核心逻辑 - 作为基准"""
        scores = {}
        for z, f in features.items():
            scores[z] = (
                f['pattern_ratio'] * 1.45 +
                min(f['gap'], 50) * 0.098 +
                f['trend'] * 0.267 +
                (1 / (1 + f['variance'])) * 0.177
            )
        return scores

    def _compute_scores_v2(self, features):
        """增强v1: 多尺度gap"""
        scores = {}
        for z, f in features.items():
            # gap加权：短期gap更重要
            gap_score = (
                min(f['gap_5'], 20) / 20 * 0.4 +
                min(f['gap_11'], 50) / 50 * 0.35 +
                min(f['gap_30'], 100) / 100 * 0.25
            )

            # 频率加权
            freq_score = (
                f['freq_5'] * 0.4 +
                f['freq_11'] * 0.3 +
                f['freq_30'] * 0.2 +
                f['freq_60'] * 0.1
            )

            # 趋势
            trend_score = max(0, min(f['trend'] / 10, 1)) if f['trend'] < 0 else 0  # 负趋势=加速出现

            scores[z] = (
                freq_score * 2.0 +
                gap_score * 1.5 +
                trend_score * 1.0 +
                (1 / (1 + f['variance'])) * 0.3
            )
        return scores

    def _compute_scores_v3(self, features):
        """增强v2: 冷热自适应"""
        scores = {}
        for z, f in features.items():
            # 基于gap的冷热判断
            if f['gap'] < 3:
                # 太热了，可能要回调
                gap_mult = 0.7
            elif f['gap'] < 10:
                # 正常偏热
                gap_mult = 1.1
            elif f['gap'] > 25:
                # 太冷了，可能要回归
                gap_mult = 0.85
            else:
                gap_mult = 1.0

            base_score = (
                f['pattern_ratio'] * 1.5 +
                min(f['gap'], 50) * 0.1 +
                f['trend'] * 0.3 +
                (1 / (1 + f['variance'])) * 0.2
            )

            scores[z] = base_score * gap_mult
        return scores

    def _compute_scores_v4(self, features):
        """增强v3: 组合共振"""
        # 计算每个zodiac的共振分数
        resonance = {}
        for z, f in features.items():
            r = 0
            # gap共振：最近有出现但间隔不小
            if 8 <= f['gap'] <= 20:
                r += 2.0
            elif f['gap'] > 30:
                r += 1.0

            # 频率共振
            if f['freq_30'] > 0.15 and f['freq_30'] < 0.25:
                r += 1.5

            # 趋势共振
            if f['trend'] < -2:  # 间隔在缩短
                r += 1.0

            resonance[z] = r

        max_res = max(resonance.values()) if resonance else 1
        resonance = {z: r / max_res for z, r in resonance.items()}

        scores = {}
        for z, f in features.items():
            base_score = (
                f['pattern_ratio'] * 1.45 +
                min(f['gap'], 50) * 0.098 +
                f['trend'] * 0.267 +
                (1 / (1 + f['variance'])) * 0.177
            )

            scores[z] = base_score + resonance[z] * 0.5

        return scores

    def _normalize_scores(self, scores):
        """归一化得分"""
        values = list(scores.values())
        min_val, max_val = min(values), max(values)
        if max_val - min_val < 1e-9:
            return {z: 0.5 for z in scores}
        return {z: (v - min_val) / (max_val - min_val) for z, v in scores.items()}

    def _rank_vote(self, score_dicts, weights):
        """排名投票融合"""
        rank_votes = {z: 0.0 for z in self.zodiacs}

        for model_name, scores in score_dicts.items():
            norm_scores = self._normalize_scores(scores)
            ranked = sorted(self.zodiacs, key=lambda z: norm_scores[z], reverse=True)
            weight = weights.get(model_name, 1.0)

            for rank, z in enumerate(ranked):
                # 第1名得6分，第2名得5分...
                rank_votes[z] += (6 - rank) * weight

        return rank_votes

    def predict(self, history, top_k=6, method='fused'):
        """生成预测"""
        if len(history) < 50:
            freq = Counter(r['特码生肖'] for r in history)
            return [z for z, c in freq.most_common(top_k)], {}

        features = self._compute_features(history)

        if method == 'v1':
            scores = self._compute_scores_v1(features)
        elif method == 'v2':
            scores = self._compute_scores_v2(features)
        elif method == 'v3':
            scores = self._compute_scores_v3(features)
        elif method == 'v4':
            scores = self._compute_scores_v4(features)
        elif method == 'fused':
            # 融合多个模型
            score_dicts = {
                'v1': self._compute_scores_v1(features),
                'v2': self._compute_scores_v2(features),
                'v3': self._compute_scores_v3(features),
                'v4': self._compute_scores_v4(features)
            }
            weights = {'v1': 0.30, 'v2': 0.25, 'v3': 0.25, 'v4': 0.20}
            rank_votes = self._rank_vote(score_dicts, weights)
            scores = rank_votes
        else:
            scores = self._compute_scores_v1(features)

        ranked = sorted(self.zodiacs, key=lambda z: scores[z], reverse=True)
        return ranked[:top_k], scores


def run_backtest(predictor, standard, method='fused', start=100):
    """回测"""
    n = len(standard)
    hits = 0
    total = 0
    results = []

    for i in range(start, n):
        history = standard[:i]
        actual = standard[i]['特码生肖']
        pred, _ = predictor.predict(history, top_k=6, method=method)
        hit = actual in pred
        if hit:
            hits += 1
        total += 1
        results.append(hit)

    return {'total': total, 'hits': hits, 'hit_rate': hits / total if total > 0 else 0, 'results': results}


print("=" * 60)
print("v31 增强型预测器 - 多方法对比")
print("=" * 60)

records = get_all_records([2024, 2025, 2026])
standard = build_standard_records(records)
print(f"数据: {len(standard)}期")

predictor = V31EnhancedPredictor()

# 测试各方法
methods = ['v1', 'v2', 'v3', 'v4', 'fused']
results = {}

print("\n--- 全量回测 ---")
for method in methods:
    result = run_backtest(predictor, standard, method=method)
    results[method] = result
    print(f"{method}: {result['hits']}/{result['total']} = {result['hit_rate']*100:.2f}%")

# 分窗口回测 - 最好的方法
best_method = max(results.keys(), key=lambda m: results[m]['hit_rate'])
print(f"\n最佳方法: {best_method}")

print(f"\n--- {best_method} 分窗口回测 ---")
for w in [50, 100, 200, 500, len(standard) - 100]:
    n = len(standard)
    if w >= n - 100:
        start, end = 100, n
    else:
        start, end = n - w, n

    hits = 0
    total = 0
    for i in range(start, end):
        history = standard[:i]
        actual = standard[i]['特码生肖']
        pred, _ = predictor.predict(history, top_k=6, method=best_method)
        if actual in pred:
            hits += 1
        total += 1

    print(f"窗口{w}: {hits}/{total} = {hits/total*100:.2f}%")

# 稳定性
print(f"\n--- {best_method} 稳定性分析 ---")
r = results[best_method]
res = r['results']
window_size = 50
sliding = []
for i in range(len(res)):
    start = max(0, i - window_size + 1)
    sliding.append(np.mean(res[start:i+1]))

print(f"滑动50期: min={min(sliding)*100:.2f}%, max={max(sliding)*100:.2f}%, std={np.std(sliding)*100:.2f}%")

for w in [30, 50, 100]:
    if len(res) >= w:
        recent = res[-w:]
        print(f"最近{w}: {sum(recent)}/{w} = {sum(recent)/w*100:.2f}%")

print("\n" + "=" * 60)