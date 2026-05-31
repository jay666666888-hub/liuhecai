#!/usr/bin/env python3
"""
澳门六合 - 六肖验证器
预测生肖必须匹配特码生肖（开奖7码中的第1个）才算命中
"""
from typing import List
from .base_validator import BaseValidator

class LiuheValidator(BaseValidator):
    """六肖验证器 - 预测匹配特码生肖即命中"""

    @property
    def name(self) -> str:
        return "liuhe"

    def evaluate(self, prediction: List[str], actual_list: List[str], actual: str = None) -> bool:
        """
        六肖命中规则：特码出现在预测的6个生肖中即命中

        Args:
            prediction: 预测的生肖列表（如 ["鼠", "牛", "虎", "兔", "龍", "蛇"]）
            actual_list: 开奖的7个生肖列表
            actual: 特码（用于六肖验证）

        Returns:
            特码(actual)在预测6肖中即命中
        """
        if not self.validate_prediction_format(prediction):
            return False
        if not self.validate_actual_format(actual_list):
            return False

        # 六肖：特码是否在预测的6肖中
        return actual in prediction if actual else False