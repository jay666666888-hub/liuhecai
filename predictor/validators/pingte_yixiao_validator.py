#!/usr/bin/env python3
"""
澳门六合 - 平特一肖验证器
预测生肖出现在开奖7码中即命中（无论位置）
"""
from typing import List
from .base_validator import BaseValidator

class PingteYixiaoValidator(BaseValidator):
    """平特一肖验证器 - 预测生肖在开奖7码中即命中"""

    @property
    def name(self) -> str:
        return "pingte_yixiao"

    def evaluate(self, prediction: List[str], actual_list: List[str], actual: str = None) -> bool:
        """
        平特一肖命中规则：预测生肖出现在开奖7码中即命中

        Args:
            prediction: 预测的生肖列表（如 ["鼠"]）
            actual_list: 开奖的7个生肖列表
            actual: 特码（平特一肖不需要此参数）

        Returns:
            预测生肖在开奖7码中即命中
        """
        if not self.validate_prediction_format(prediction):
            return False
        if not self.validate_actual_format(actual_list):
            return False

        predicted = prediction[0]  # 取第一个预测
        return predicted in actual_list