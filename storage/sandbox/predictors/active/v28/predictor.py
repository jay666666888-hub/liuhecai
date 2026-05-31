#!/usr/bin/env python3
"""
澳门六合 - v28 平特一肖预测器
Walk-Forward验证: 55.72%
最优参数：lookback=137, gap=-1.0077, freq=0.9211, streak=-0.1236, trend=1.6992, variance=1.6857
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from predictor.base_predictor import BasePredictor, PredictionResult

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

class V28Predictor(BasePredictor):
    """平特一肖预测器 - Walk-Forward最优参数v2"""
    def __init__(self, version: str = "v28"):
        super().__init__(version)
        self.params = {
    "lookback": 137,
    "gap_weight": -1.0077,
    "freq_weight": 0.9211,
    "streak_weight": -0.1236,
    "trend_weight": 1.6992,
    "variance_weight": 1.6857
}

    def _compute_features(self, window, z):
        positions = [idx for idx, r in enumerate(window) if r["特码生肖"] == z]
        if not positions:
            return {"gap": 999, "frequency": 0, "streak": 0, "trend": 0, "variance": 0}
        gap = len(window) - positions[-1] - 1
        frequency = len(positions)
        streak = 0
        for idx in range(len(window)-1, -1, -1):
            if window[idx]["特码生肖"] == z:
                streak += 1
            else:
                break
        if len(positions) >= 2:
            intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]
            trend = intervals[0] - intervals[1] if len(intervals) >= 2 else 0
        else:
            trend = 0
        if len(positions) >= 3:
            intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]
            avg_int = sum(intervals) / len(intervals)
            variance = sum((x - avg_int) ** 2 for x in intervals) / len(intervals)
        else:
            variance = 0
        return {"gap": gap, "frequency": frequency, "streak": streak, "trend": trend, "variance": variance}

    def predict(self, history, top_k=1):
        n = len(history)
        lookback = self.params["lookback"]
        window = history[max(0, n-lookback):n]
        scores = {}
        for z in ZODIACS:
            f = self._compute_features(window, z)
            gap_score = min(f["gap"], 50) / 50
            freq_score = f["frequency"] / lookback
            streak_score = min(f["streak"], 5) / 5
            trend_score = max(0, min(f["trend"], 10)) / 10
            variance_score = 1 / (1 + f["variance"] / 10)
            scores[z] = (
                gap_score * self.params["gap_weight"] +
                freq_score * self.params["freq_weight"] +
                streak_score * self.params["streak_weight"] +
                trend_score * self.params["trend_weight"] +
                variance_score * self.params["variance_weight"]
            )
        ranked = sorted(ZODIACS, key=lambda z: scores[z], reverse=True)
        prediction = [ranked[0]]
        return PredictionResult(
            prediction=prediction,
            scores=scores,
            metadata={"type": "pingte_yixiao", "version": "v28", "strategy": "walk_forward_optimal", "params": self.params, "play_type": "pingte_yixiao"}
        )