#!/usr/bin/env python3
"""
澳门六合 - v5 Legacy Adapter

只做 wrapper，不改写旧逻辑。

旧逻辑来源: multi_strategy_predictor.predict_v5_next()
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.base_predictor import BasePredictor, PredictionResult
from predictor.multi_strategy_predictor import build_cache_v5, predict_v5_next

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


class V5Predictor(BasePredictor):
    """v5预测器 - Legacy Adapter"""

    def __init__(self, version: str = "v5"):
        super().__init__(version)
        self._cache = None
        self._zodiacs = ZODIACS

    def _ensure_cache(self, history):
        """延迟构建缓存（只构建一次）"""
        if self._cache is None:
            self._cache = build_cache_v5(history, self._zodiacs)
        return self._cache

    def predict(self, history, top_k=6):
        """
        包装 v5 旧逻辑

        Args:
            history: 历史记录列表
            top_k: 返回前k个预测

        Returns:
            PredictionResult 对象
        """
        cache = self._ensure_cache(history)

        # 调用旧逻辑（不改写）
        prediction = predict_v5_next(cache, self._zodiacs)[:top_k]

        # 计算得分（从旧逻辑提取）
        scores = {}
        last_interval = cache[-1]['interval_raw']
        for z in self._zodiacs:
            # 简化得分 = interval_raw 作为一种分数
            scores[z] = float(last_interval.get(z, 0))

        return PredictionResult(
            prediction=prediction,
            scores=scores,
            metadata={
                "type": "legacy_adapter",
                "version": "v5",
                "strategy": "gap_threshold"
            }
        )
