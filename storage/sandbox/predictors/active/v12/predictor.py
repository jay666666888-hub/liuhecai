#!/usr/bin/env python3
"""
澳门六合 - v12 Legacy Adapter

只做 wrapper，不改写旧逻辑。

旧逻辑来源: predictor.predict_top6() with pattern_based
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.base_predictor import BasePredictor, PredictionResult
from predictor.six_zodiac_predictor import predict_top6

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

V12_PARAMS = {
    "lookback": 11,
    "pattern_weight": 1.45,
    "gap_weight": 0.098,
    "trend_weight": 0.267,
    "variance_weight": 0.177,
    "alt_mode": "trend"
}


class V12Predictor(BasePredictor):
    """v12预测器 - Legacy Adapter"""

    def __init__(self, version: str = "v12"):
        super().__init__(version)
        self.params = V12_PARAMS

    def predict(self, history, top_k=6):
        """
        包装 v12 旧逻辑

        Args:
            history: 历史记录列表
            top_k: 返回前k个预测

        Returns:
            PredictionResult 对象
        """
        n = len(history)

        # 调用旧逻辑（不改写）
        prediction = predict_top6(history, self.params, "pattern_based")

        # 计算得分（简化版）
        scores = {z: 0.0 for z in ZODIACS}
        for i, z in enumerate(prediction):
            scores[z] = float(top_k - i)

        return PredictionResult(
            prediction=prediction[:top_k],
            scores=scores,
            metadata={
                "type": "legacy_adapter",
                "version": "v12",
                "strategy": "pattern_based",
                "params": self.params
            }
        )
