#!/usr/bin/env python3
"""
澳门六合 - v30 动态权重融合预测器 v2
只融合适合六肖的策略：v12, v21, v23

P1: 权重动态化 - 根据最近30期各策略有效性动态调整
P4: 版本投票 - 多策略融合
P2: 冷热反转层
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from predictor.base_predictor import BasePredictor, PredictionResult
from features.sunday_effect import SundayEffectFeature

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


class V30FusionPredictor(BasePredictor):
    """动态权重融合预测器 - v30"""

    def __init__(self, version: str = "v30"):
        super().__init__(version)
        self.sunday_feature = SundayEffectFeature()
        self._dynamic_weights = None
        self._last_weight_update = 0
        self._weight_window = 30

    def _compute_v12_scores(self, history):
        """计算v12策略得分"""
        n = len(history)
        lookback = min(11, n)
        window = history[n-lookback:n]
        scores = {z: 0.0 for z in ZODIACS}

        for z in ZODIACS:
            positions = [i for i, r in enumerate(window) if r.get('特码生肖') == z]
            if not positions:
                current_gap, pattern_ratio = 999, 0.0
            else:
                current_gap = lookback - positions[-1] - 1
                pattern_count = len([p for p in positions if p < 3])
                pattern_ratio = pattern_count / lookback

            positions_full = [i for i, r in enumerate(history) if r.get('特码生肖') == z]
            if len(positions_full) >= 2:
                intervals = [positions_full[i] - positions_full[i-1] for i in range(1, len(positions_full))]
                trend = intervals[-1] - intervals[-2] if len(intervals) >= 2 else 0
            else:
                trend = 0

            if len(positions_full) >= 3:
                recent_intervals = intervals[-3:]
                avg_int = sum(recent_intervals) / len(recent_intervals)
                variance = sum((x - avg_int) ** 2 for x in recent_intervals) / len(recent_intervals)
            else:
                variance = 0

            scores[z] = (
                pattern_ratio * 1.45 +
                min(current_gap, 50) * 0.098 +
                trend * 0.267 +
                (1 / (1 + variance)) * 0.177
            )
        return scores

    def _compute_v21_scores(self, history):
        """计算v21策略得分 - v12 + 周日效应"""
        scores = self._compute_v12_scores(history)
        sunday_adj = self.sunday_feature.compute(history)
        is_sunday = self.sunday_feature.get_weekday(history[-1]) == 6 if history else False

        if is_sunday and sunday_adj:
            for i, z in enumerate(sorted(ZODIACS, key=lambda z: scores[z], reverse=True)):
                scores[z] += sunday_adj.get(z, 0) * (6 - i)
        return scores

    def _compute_v23_scores(self, history):
        """计算v23策略得分 - 衰减频率+间隔比率+近期频率"""
        n = len(history)
        scores = {z: 0.0 for z in ZODIACS}

        # 衰减频率
        for i, r in enumerate(history):
            z = r.get('特码生肖')
            if z:
                weight = 0.85 ** (n - i - 1)
                scores[z] = scores.get(z, 0) + weight

        # 间隔比率
        last_appear = {}
        for i, r in enumerate(history):
            zodiac = r.get('特码生肖')
            if zodiac:
                last_appear[zodiac] = i
        gaps = {z: n - last_appear.get(z, -1) - 1 for z in ZODIACS}
        max_gap = max(gaps.values()) if gaps else 1
        for z in ZODIACS:
            scores[z] = scores.get(z, 0) + (gaps[z] / max_gap) * 4.0

        # 近期频率（窗口30期）
        recent = history[-30:]
        freq = {}
        for r in recent:
            z = r.get('特码生肖')
            if z:
                freq[z] = freq.get(z, 0) + 1
        max_freq = max(freq.values()) if freq else 1
        for z in ZODIACS:
            scores[z] = scores.get(z, 0) + (freq.get(z, 0) / max_freq) * 1.5

        return scores

    def _normalize_scores(self, scores):
        """归一化得分到0-1范围"""
        values = list(scores.values())
        min_val, max_val = min(values), max(values)
        if max_val - min_val < 1e-9:
            return {z: 0.5 for z in scores}
        return {z: (v - min_val) / (max_val - min_val) for z, v in scores.items()}

    def _compute_gap(self, history, zodiac):
        """计算某个生肖的current gap"""
        positions = [i for i, r in enumerate(history) if r.get('特码生肖') == zodiac]
        if not positions:
            return 999
        return len(history) - positions[-1] - 1

    def _apply_cold_hot_adjustment(self, scores, gaps):
        """P2: 冷热反转层"""
        adjusted = {}
        for z, score in scores.items():
            gap = gaps.get(z, 999)
            if gap < 3:
                score *= 0.85
            elif 3 <= gap <= 12:
                score *= 1.15
            elif gap > 25:
                score *= 0.92
            adjusted[z] = score
        return adjusted

    def _compute_dynamic_weights(self, history):
        """计算最近各策略的准确性作为动态权重"""
        if len(history) < 80:
            return None

        # 用最近60期评估前面60期
        eval_start = len(history) - 60
        train_end = eval_start
        if train_end < 60:
            return None

        strategies = ['v12', 'v21', 'v23']
        hit_counts = {s: 0 for s in strategies}
        total_counts = {s: 0 for s in strategies}

        for idx in range(60, len(history) - 30):
            hist = history[idx-60:idx]
            actual = history[idx].get('特码生肖')
            if not actual:
                continue

            # v12
            pred = sorted(ZODIACS, key=lambda z: self._compute_v12_scores(hist)[z], reverse=True)[:6]
            if actual in pred:
                hit_counts['v12'] += 1
            total_counts['v12'] += 1

            # v21
            pred = sorted(ZODIACS, key=lambda z: self._compute_v21_scores(hist)[z], reverse=True)[:6]
            if actual in pred:
                hit_counts['v21'] += 1
            total_counts['v21'] += 1

            # v23
            pred = sorted(ZODIACS, key=lambda z: self._compute_v23_scores(hist)[z], reverse=True)[:6]
            if actual in pred:
                hit_counts['v23'] += 1
            total_counts['v23'] += 1

        accuracy = {}
        for s in strategies:
            accuracy[s] = hit_counts[s] / max(total_counts[s], 1)

        total = sum(accuracy.values())
        if total > 0:
            return {s: accuracy[s] / total for s in strategies}
        return None

    def predict(self, history, top_k=6):
        n = len(history)

        # 更新动态权重
        if n - self._last_weight_update >= 20:
            self._dynamic_weights = self._compute_dynamic_weights(history)
            self._last_weight_update = n

        # 计算各策略得分
        v12_scores = self._compute_v12_scores(history)
        v21_scores = self._compute_v21_scores(history)
        v23_scores = self._compute_v23_scores(history)

        # 归一化
        v12_norm = self._normalize_scores(v12_scores)
        v21_norm = self._normalize_scores(v21_scores)
        v23_norm = self._normalize_scores(v23_scores)

        # 动态或默认权重
        if self._dynamic_weights:
            w = self._dynamic_weights
        else:
            w = {'v12': 0.40, 'v21': 0.35, 'v23': 0.25}

        # 加权融合
        fused = {z: 0.0 for z in ZODIACS}
        for z in ZODIACS:
            fused[z] = (
                v12_norm[z] * w.get('v12', 0.33) +
                v21_norm[z] * w.get('v21', 0.33) +
                v23_norm[z] * w.get('v23', 0.33)
            )

        # 计算gaps用于冷热反转
        gaps = {z: self._compute_gap(history, z) for z in ZODIACS}

        # 应用冷热反转
        adjusted = self._apply_cold_hot_adjustment(fused, gaps)

        # 排序
        ranked = sorted(ZODIACS, key=lambda z: adjusted[z], reverse=True)
        prediction = ranked[:top_k]

        return PredictionResult(
            prediction=prediction,
            scores=adjusted,
            metadata={
                "type": "dynamic_fusion",
                "version": "v30",
                "strategy": "P1+P2+P4 (v12+v21+v23)",
                "weights": w if self._dynamic_weights else "default"
            }
        )


if __name__ == '__main__':
    from predictor.data_fetcher import get_all_records, build_standard_records

    print("=== v30 动态权重融合预测器 v2 ===")

    records = get_all_records([2024, 2025, 2026])
    standard = build_standard_records(records)
    print(f"数据: {len(standard)}期")

    print("\n=== Walk-Forward回测 ===")
    hits = 0
    total = 0
    results = []

    for i in range(100, len(standard)):
        history = standard[:i]
        actual = standard[i]['特码生肖']
        predictor = V30FusionPredictor()
        pred = predictor.predict(history, top_k=6).prediction
        hit = actual in pred
        if hit:
            hits += 1
        total += 1
        results.append(hit)
        if i % 100 == 0:
            print(f"进度: {i}/{len(standard)}, 当前命中率: {hits/total*100:.2f}%")

    print(f"\n全量回测结果: {hits}/{total} = {hits/total*100:.2f}%")
    l50_hits = sum(results[-50:])
    print(f"L50: {l50_hits}/50 = {l50_hits/50*100:.2f}%")