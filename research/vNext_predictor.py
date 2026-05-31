#!/usr/bin/env python3
"""
澳门六合 - vNext 跨周期结构预测器
Phase 2: 综合A+B+C策略

A: 跨周期结构特征
- 周期状态切换检测
- 长周期冷热分析
- 多窗口趋势融合
- 组合共振

B: 集成策略
- Regime Detection
- Dynamic Weighting
- Meta Learner

C: 非传统特征
- 信息熵
- 状态转移图
- 图嵌入
"""

import sys
sys.path.insert(0, '/mnt/c/Users/Admin/liuhecai')
from predictor.data_fetcher import get_all_records, build_standard_records
import numpy as np
from scipy import stats
from collections import Counter, defaultdict
from dataclasses import dataclass, field

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


@dataclass
class CrossCycleFeatures:
    """跨周期特征"""
    # 多窗口gap
    gap_5: dict  # 最近5期gap
    gap_11: dict
    gap_30: dict
    gap_60: dict
    gap_120: dict

    # 趋势变化
    trend_short: dict   # 5期趋势
    trend_medium: dict  # 21期趋势
    trend_long: dict    # 55期趋势

    # 熵
    entropy_30: float   # 30期分布熵
    entropy_change: float  # 熵变化

    # 状态
    regime: str  # 'hot', 'cold', 'neutral'
    regime_confidence: float


class RegimeDetector:
    """市场状态检测"""

    def __init__(self):
        self.windows = [11, 30, 60]
        self.hot_threshold = 0.7  # 频率>70%为热
        self.cold_threshold = 0.3  # 频率<30%为冷

    def detect(self, history):
        """检测当前市场状态"""
        n = len(history)
        if n < 30:
            return 'neutral', 0.5

        # 多窗口频率
        window_results = {}
        for w in self.windows:
            window = history[max(0, n-w):n]
            freq = Counter(r['特码生肖'] for r in window)
            total = sum(freq.values())
            max_freq = max(freq.values()) if freq else 0
            window_results[w] = {
                'entropy': self._calc_entropy(freq, total),
                'max_freq_ratio': max_freq / total if total > 0 else 0,
                'top_zodiac': freq.most_common(1)[0][0] if freq else None
            }

        # 判断状态
        recent_entropy = window_results[30]['entropy']
        recent_max_ratio = window_results[30]['max_freq_ratio']

        if recent_max_ratio > self.hot_threshold:
            return 'hot', recent_max_ratio
        elif recent_max_ratio < self.cold_threshold:
            return 'cold', 1 - recent_max_ratio
        else:
            return 'neutral', 0.5

    def _calc_entropy(self, freq, total):
        probs = [c / total for c in freq.values() if c > 0]
        if not probs:
            return 0
        return -sum(p * np.log2(p) for p in probs if p > 0)


class CrossCycleFeatureExtractor:
    """跨周期特征提取"""

    def __init__(self):
        self.zodiacs = ZODIACS

    def extract(self, history):
        """提取所有跨周期特征"""
        n = len(history)
        if n < 30:
            return None

        # 1. 多窗口gap
        gaps = {}
        for w in [5, 11, 30, 60, 120]:
            window = history[max(0, n-w):n]
            gaps_w = {}
            for z in self.zodiacs:
                positions = [i for i, r in enumerate(window) if r.get('特码生肖') == z]
                if not positions:
                    gaps_w[z] = w  # 从未出现
                else:
                    gaps_w[z] = w - positions[-1] - 1
            gaps[f'gap_{w}'] = gaps_w

        # 2. 多窗口趋势
        trends = {}
        for w in [5, 21, 55]:
            window = history[max(0, n-w):n]
            trend_w = {}
            for z in self.zodiacs:
                positions = [i for i, r in enumerate(window) if r.get('特码生肖') == z]
                if len(positions) >= 2:
                    intervals = [positions[i] - positions[i-1] for i in range(1, len(positions))]
                    trend_w[z] = np.mean(intervals)  # 平均间隔
                else:
                    trend_w[z] = w / 2  # 默认
            trends[f'trend_{w}'] = trend_w

        # 3. 熵
        window_30 = history[max(0, n-30):n]
        freq_30 = Counter(r['特码生肖'] for r in window_30)
        total_30 = sum(freq_30.values())
        entropy_30 = self._calc_entropy(freq_30, total_30)

        window_60 = history[max(0, n-60):n]
        freq_60 = Counter(r['特码生肖'] for r in window_60)
        total_60 = sum(freq_60.values())
        entropy_60 = self._calc_entropy(freq_60, total_60)

        # 4. 组合共振：检查哪些生肖在多个窗口都处于"热"状态
        resonance = {}
        for z in self.zodiacs:
            score = 0
            # gap_11小于5?
            if gaps['gap_11'][z] < 5:
                score += 1
            # gap_30小于10?
            if gaps['gap_30'][z] < 10:
                score += 1
            # trend_21变小?(最近间隔减小)
            if trends['trend_21'][z] < 8:
                score += 1
            resonance[z] = score

        return {
            'gaps': gaps,
            'trends': trends,
            'entropy_30': entropy_30,
            'entropy_change': entropy_30 - entropy_60,
            'resonance': resonance,
            'n': n
        }

    def _calc_entropy(self, freq, total):
        if total == 0:
            return 0
        probs = [c / total for c in freq.values() if c > 0]
        if not probs:
            return 0
        return -sum(p * np.log2(p) for p in probs if p > 0)


class InformationEntropyScorer:
    """基于信息熵的评分"""

    def __init__(self):
        self.zodiacs = ZODIACS
        self.max_entropy = np.log2(12)

    def score(self, history):
        """计算基于熵的得分"""
        n = len(history)
        window_30 = history[max(0, n-30):n]

        # 频率分布
        freq = Counter(r['特码生肖'] for r in window_30)
        total = sum(freq.values())

        # 每个生肖的"稀有度"得分
        scores = {}
        for z in self.zodiacs:
            count = freq.get(z, 0)
            if count == 0:
                # 从未出现，极高稀有度
                scores[z] = 1.0
            else:
                # 出现频率越低，稀有度越高
                prob = count / total
                # 信息量：-log2(p)，越稀有信息量越大
                info = -np.log2(prob) if prob > 0 else 10
                scores[z] = min(info / self.max_entropy, 2.0)  # 归一化

        return scores


class GapRatioScorer:
    """间隔比率评分"""

    def __init__(self):
        self.zodiacs = ZODIACS

    def score(self, history):
        """计算间隔比率得分"""
        n = len(history)

        scores = {}
        for z in self.zodiacs:
            positions = [i for i, r in enumerate(history) if r.get('特码生肖') == z]
            if not positions:
                scores[z] = 0.0
                continue

            current_gap = n - positions[-1] - 1

            # 计算间隔比率：当前间隔/历史平均间隔
            if len(positions) >= 3:
                intervals = [positions[i] - positions[i-1] for i in range(1, len(positions))]
                avg_interval = np.mean(intervals)
                current_interval = current_gap

                # 比率>1表示冷却中，<1表示加热中
                ratio = current_interval / avg_interval if avg_interval > 0 else 1.0

                # 转换得分：比率越高分越低（冷号）
                scores[z] = 2.0 / (1 + ratio)  # 范围0-2
            else:
                scores[z] = min(current_gap / 20, 1.5)

        # 归一化到0-1
        max_score = max(scores.values()) if scores else 1
        if max_score > 0:
            scores = {z: s / max_score for z, s in scores.items()}

        return scores


class TrendScorer:
    """趋势评分 - 多窗口融合"""

    def __init__(self):
        self.zodiacs = ZODIACS

    def score(self, history):
        """计算趋势得分"""
        n = len(history)

        scores = {}
        for z in self.zodiacs:
            positions = [i for i, r in enumerate(history) if r.get('特码生肖') == z]
            if not positions:
                scores[z] = 0.5
                continue

            current_gap = n - positions[-1] - 1

            # 多窗口分析
            trend_scores = []

            for w in [11, 30, 60]:
                window = history[max(0, n-w):n]
                w_positions = [i for i, r in enumerate(window) if r.get('特码生肖') == z]
                if len(w_positions) >= 2:
                    intervals = [w_positions[i] - w_positions[i-1] for i in range(1, len(w_positions))]
                    # 趋势：最近间隔 vs 平均间隔
                    recent = intervals[-1]
                    avg = np.mean(intervals)
                    if recent < avg * 0.7:  # 明显加快
                        trend_scores.append(1.0)
                    elif recent > avg * 1.3:  # 明显变慢
                        trend_scores.append(0.0)
                    else:
                        trend_scores.append(0.5)
                else:
                    trend_scores.append(0.5)

            # 加权平均：短期权重更高
            final_score = 0.5 * trend_scores[0] + 0.3 * trend_scores[1] + 0.2 * trend_scores[2]
            scores[z] = final_score

        return scores


class ResonanceScorer:
    """组合共振评分"""

    def __init__(self):
        self.zodiacs = ZODIACS

    def score(self, history):
        """计算组合共振得分"""
        n = len(history)
        scores = {z: 0.0 for z in self.zodiacs}

        for z in self.zodiacs:
            positions = [i for i, r in enumerate(history) if r.get('特码生肖') == z]
            if not positions:
                continue

            current_gap = n - positions[-1] - 1
            total_appearances = len(positions)

            # 冷却共振：gap大但最近有出现
            if 15 <= current_gap <= 30:
                scores[z] += 2.0
            elif current_gap > 30:
                scores[z] += 1.0

            # 频率共振：最近出现频率高于平均
            if n >= 60:
                recent_60 = len([p for p in positions if n - p <= 60])
                expected_60 = total_appearances * 60 / n
                if recent_60 > expected_60 * 1.2:
                    scores[z] += 2.0

            # 间隔缩小共振：最近间隔在减小
            if len(positions) >= 3:
                intervals = [positions[i] - positions[i-1] for i in range(1, len(positions))]
                if len(intervals) >= 2:
                    if intervals[-1] < intervals[-2] * 0.8:
                        scores[z] += 1.5

            # 短期回归共振：gap_11小于10
            if current_gap < 10:
                scores[z] += 1.0

        # 归一化
        max_score = max(scores.values()) if scores else 1
        if max_score > 0:
            scores = {z: s / max_score for z, s in scores.items()}

        return scores


class EnsemblePredictor:
    """集成预测器"""

    def __init__(self):
        self.zodiacs = ZODIACS
        self.feature_extractor = CrossCycleFeatureExtractor()
        self.regime_detector = RegimeDetector()
        self.entropy_scorer = InformationEntropyScorer()
        self.gap_scorer = GapRatioScorer()
        self.trend_scorer = TrendScorer()
        self.resonance_scorer = ResonanceScorer()

        # 动态权重 - 根据regime调整
        self.regime_weights = {
            'hot': {
                'entropy': 0.10,
                'gap': 0.35,
                'trend': 0.35,
                'resonance': 0.20
            },
            'cold': {
                'entropy': 0.15,
                'gap': 0.40,
                'trend': 0.25,
                'resonance': 0.20
            },
            'neutral': {
                'entropy': 0.15,
                'gap': 0.30,
                'trend': 0.30,
                'resonance': 0.25
            }
        }

    def predict(self, history, top_k=6):
        """生成预测"""
        n = len(history)
        if n < 50:
            # 数据不足，用简单频率模型
            freq = Counter(r['特码生肖'] for r in history)
            top6 = [z for z, c in freq.most_common(top_k)]
            return top6, {}

        # 检测regime
        regime, confidence = self.regime_detector.detect(history)
        weights = self.regime_weights[regime]

        # 提取特征
        features = self.feature_extractor.extract(history)

        # 计算各维度得分
        entropy_scores = self.entropy_scorer.score(history)
        gap_scores = self.gap_scorer.score(history)
        trend_scores = self.trend_scorer.score(history)
        resonance_scores = self.resonance_scorer.score(history)

        # 融合得分
        fused_scores = {z: 0.0 for z in self.zodiacs}
        for z in self.zodiacs:
            fused_scores[z] = (
                entropy_scores.get(z, 0) * weights['entropy'] +
                gap_scores.get(z, 0) * weights['gap'] +
                trend_scores.get(z, 0) * weights['trend'] +
                resonance_scores.get(z, 0) * weights['resonance']
            )

        # 排序取top_k
        ranked = sorted(self.zodiacs, key=lambda z: fused_scores[z], reverse=True)
        prediction = ranked[:top_k]

        metadata = {
            'regime': regime,
            'regime_confidence': confidence,
            'weights': weights,
            'entropy_scores': entropy_scores,
            'gap_scores': gap_scores,
            'trend_scores': trend_scores,
            'resonance_scores': resonance_scores
        }

        return prediction, metadata


def run_backtest(predictor, standard, start=100):
    """完整回测"""
    n = len(standard)
    hits = 0
    total = 0
    results = []

    for i in range(start, n):
        history = standard[:i]
        actual = standard[i]['特码生肖']
        pred, _ = predictor.predict(history, top_k=6)
        hit = actual in pred
        if hit:
            hits += 1
        total += 1
        results.append(hit)

    return {
        'total': total,
        'hits': hits,
        'hit_rate': hits / total if total > 0 else 0,
        'results': results
    }


def run_window_backtests(predictor, standard):
    """分窗口回测"""
    n = len(standard)
    windows = [50, 100, 200, 500, n - 100]
    results = {}

    for w in windows:
        if w >= n - 100:
            start = 100
            end = n
        else:
            start = n - w
            end = n

        hits = 0
        total = 0

        for i in range(start, end):
            history = standard[:i]
            actual = standard[i]['特码生肖']
            pred, _ = predictor.predict(history, top_k=6)
            if actual in pred:
                hits += 1
            total += 1

        results[w] = {
            'hits': hits,
            'total': total,
            'hit_rate': hits / total if total > 0 else 0
        }

    return results


print("=" * 60)
print("vNext 跨周期结构预测器 - 回测")
print("=" * 60)

records = get_all_records([2024, 2025, 2026])
standard = build_standard_records(records)
print(f"数据: {len(standard)}期")

# 创建预测器
predictor = EnsemblePredictor()

# 全量回测
print("\n--- 全量回测 ---")
full_result = run_backtest(predictor, standard)
print(f"全量({full_result['total']}期): {full_result['hits']}/{full_result['total']} = {full_result['hit_rate']*100:.2f}%")

# 分窗口回测
print("\n--- 分窗口回测 ---")
window_results = run_window_backtests(predictor, standard)
for w, r in window_results.items():
    print(f"窗口{w}: {r['hits']}/{r['total']} = {r['hit_rate']*100:.2f}%")

# 稳定性分析
print("\n--- 稳定性分析 ---")
results = full_result['results']
# 滑动平均
window_size = 50
sliding_avg = []
for i in range(len(results)):
    start = max(0, i - window_size + 1)
    window = results[start:i+1]
    sliding_avg.append(np.mean(window))

print(f"滑动{window_size}期平均命中率:")
print(f"  最小: {min(sliding_avg)*100:.2f}%")
print(f"  最大: {max(sliding_avg)*100:.2f}%")
print(f"  标准差: {np.std(sliding_avg)*100:.2f}%")

# 最近各窗口
for w in [30, 50, 100]:
    if len(results) >= w:
        recent = results[-w:]
        print(f"最近{w}: {sum(recent)}/{w} = {sum(recent)/w*100:.2f}%")

print("\n" + "=" * 60)