#!/usr/bin/env python3
"""
澳门六合 - 号码选择验证器
验证特码号码是否在预测的号码列表中（24码/12码/6码/30码）
"""
from typing import List
from .base_validator import BaseValidator


class NumberSelectionValidator(BaseValidator):
    """号码选择验证器 - 验证特码号码是否在预测的号码列表中"""

    @property
    def name(self) -> str:
        return "number_selection"

    def evaluate(self, prediction: List[str], actual_list: List[str], actual: str = None) -> bool:
        """
        号码选择命中规则：特码号码出现在预测的号码列表中即命中

        Args:
            prediction: 预测的号码列表（如 ["01", "05", "12", "23", "34", "45"]）
            actual_list: 开奖的号码列表（当前实现中未使用）
            actual: 特码号码（如 "45"）

        Returns:
            特码(actual)在预测号码列表中即命中
        """
        if not self.validate_prediction_format(prediction):
            return False
        if not actual:
            return False

        return actual in prediction