#!/usr/bin/env python3
"""
澳门六合 - v7 Legacy Adapter

只做 wrapper，不改写旧逻辑。

旧逻辑来源: multi_strategy_predictor.predict_v7()
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.base_predictor import BasePredictor, PredictionResult
from predictor.multi_strategy_predictor import predict_v7

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


class V7Predictor(BasePredictor):
    """v7预测器 - Legacy Adapter"""

    def __init__(self, version: str = "v7"):
        super().__init__(version)

    def predict(self, history, top_k=6):
        """
        包装 v7 旧逻辑

        Args:
            history: 历史记录列表
            top_k: 返回前k个预测

        Returns:
            PredictionResult 对象
        """
        # 调用旧逻辑（不改写）
        prediction, scores = predict_v7(history)

        return PredictionResult(
            prediction=prediction[:top_k],
            scores=scores,
            metadata={
                "type": "legacy_adapter",
                "version": "v7",
                "strategy": "rank_based"
            }
        )
