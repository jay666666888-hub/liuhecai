#!/usr/bin/env python3
"""
澳门六合 - v21 Legacy Adapter

只做 wrapper，不改写旧逻辑。

旧逻辑来源: features/sunday_effect.SundayEffectFeature + v12 pattern_based
v21 = v12 + 周日效应调整
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.base_predictor import BasePredictor, PredictionResult
from predictor.six_zodiac_predictor import predict_top6
from features.sunday_effect import SundayEffectFeature

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

V12_PARAMS = {
    "lookback": 11,
    "pattern_weight": 1.45,
    "gap_weight": 0.098,
    "trend_weight": 0.267,
    "variance_weight": 0.177,
    "alt_mode": "trend"
}


class V21Predictor(BasePredictor):
    """v21预测器 - Legacy Adapter (v12 + 周日效应)"""

    def __init__(self, version: str = "v21"):
        super().__init__(version)
        self.params = V12_PARAMS
        self.sunday_feature = SundayEffectFeature()

    def predict(self, history, top_k=6):
        """
        包装 v21 旧逻辑

        v21 = v12 pattern_based + 周日效应调整

        Args:
            history: 历史记录列表
            top_k: 返回前k个预测

        Returns:
            PredictionResult 对象
        """
        n = len(history)

        # 获取周日调整系数
        sunday_adjustment = self.sunday_feature.compute(history)
        is_sunday = self.sunday_feature.get_weekday(history[-1]) == 6 if history else False

        # 调用 v12 旧逻辑
        prediction = predict_top6(history, self.params, "pattern_based")

        # 如果是周日，应用 sunday effect 调整
        if is_sunday and sunday_adjustment:
            # 取 gap 最高的作为调整后预测
            adjusted_scores = {
                z: sunday_adjustment.get(z, 0) * (top_k - i)
                for i, z in enumerate(prediction)
            }
            prediction = sorted(adjusted_scores.keys(), key=lambda z: adjusted_scores[z], reverse=True)[:top_k]

        # 计算得分
        scores = {z: sunday_adjustment.get(z, 0) for z in ZODIACS}

        return PredictionResult(
            prediction=prediction[:top_k],
            scores=scores,
            metadata={
                "type": "legacy_adapter",
                "version": "v21",
                "strategy": "sunday_effect",
                "is_sunday": is_sunday,
                "sunday_adjustment": sunday_adjustment
            }
        )
