#!/usr/bin/env python3
"""
澳门六合 - v29 平特一肖预测器
平特一肖验证规则：预测1个生肖，开奖7个生肖中包含即命中
特征计算：基于开奖生肖（7个）分布，非特码生肖（1个）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from predictor.base_predictor import BasePredictor, PredictionResult

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

class V29Predictor(BasePredictor):
    """平特一肖预测器 - 基于开奖7码特征"""
    def __init__(self, version: str = "v29"):
        super().__init__(version)
        self.params = {
    "lookback": 75,
    "gap_weight": -0.3,
    "freq_weight": 1.0,
    "streak_weight": -0.2,
    "trend_weight": 1.5,
    "variance_weight": 1.5
}

    def _compute_features(self, window, z):
        """计算生肖z在window中开奖7码的特征"""
        # 统计z在每期开奖7码中出现的次数
        appearances = []  # 每期出现几次z
        for rec in window:
            zodiac_list = rec.get("开奖生肖", [])
            count = zodiac_list.count(z)
            appearances.append(count)

        total_appearances = sum(appearances)
        freq = total_appearances / len(window)  # 平均每期出现次数

        # gap: 最近一次出现距今多少期
        gap = 999
        for i in range(len(window)-1, -1, -1):
            if appearances[i] > 0:
                gap = len(window) - 1 - i
                break

        # streak: 连续出现的期数
        streak = 0
        for i in range(len(window)-1, -1, -1):
            if appearances[i] > 0:
                streak += 1
            else:
                break

        # trend: 最近间隔 vs 前一个间隔的变化
        last_gap = gap
        trend = 0
        if len(appearances) >= 2:
            prev_gap = 999
            for i in range(len(window)-2, -1, -1):
                if appearances[i] > 0:
                    prev_gap = len(window) - 1 - i
                    break
            trend = last_gap - prev_gap  # 正数=间隔变大（变稀疏），负数=变频繁

        # variance: 出现次数的方差（波动性）
        variance = 0
        if len(appearances) > 1:
            mean = total_appearances / len(window)
            variance = sum((x - mean) ** 2 for x in appearances) / len(appearances)

        return {
            "gap": gap,
            "freq": freq,
            "streak": streak,
            "trend": trend,
            "variance": variance
        }

    def predict(self, history, top_k=1):
        n = len(history)
        lookback = self.params["lookback"]
        window = history[max(0, n-lookback):n]
        scores = {}
        for z in ZODIACS:
            f = self._compute_features(window, z)
            gap_score = min(f["gap"], 50) / 50
            freq_score = f["freq"] * 10  # 放大因为是小数
            streak_score = min(f["streak"], 5) / 5
            trend_score = max(0, min(f["trend"], 10)) / 10
            variance_score = 1 / (1 + f["variance"])
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
            metadata={"type": "pingte_yixiao", "version": "v29", "strategy": "开奖7码特征", "params": self.params, "play_type": "pingte_yixiao"}
        )