#!/usr/bin/env python3
"""
澳门六合 - 24码验证器
预测24个号码，特码号码在预测中即命中
"""
from typing import List
from .liuhe_validator import LiuheValidator


class Special24maValidator(LiuheValidator):
    """24码验证器 - 特码号码在预测的24个号码中即命中"""

    @property
    def name(self) -> str:
        return "special_24ma"

    def evaluate(self, prediction: List[str], actual_list: List[str], actual: str = None) -> bool:
        """
        24码命中规则：特码号码在预测的24个号码中即命中

        Args:
            prediction: 预测的号码列表（如 ["01", "02", "06", ...]）
            actual_list: 开奖的7个号码列表
            actual: 特码号码（字符串，如 "06"）

        Returns:
            特码号码(actual)在预测24码中即命中
        """
        if not self.validate_prediction_format(prediction):
            return False
        if not self.validate_actual_format(actual_list):
            return False

        return actual in prediction if actual else False