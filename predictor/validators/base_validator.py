#!/usr/bin/env python3
"""
澳门六合 - 验证器基类
所有验证器必须继承此基类
"""
from abc import ABC, abstractmethod
from typing import List, Optional

class BaseValidator(ABC):
    """验证器基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """验证器名称"""
        pass

    @abstractmethod
    def evaluate(self, prediction: List[str], actual_list: List[str], actual: str = None) -> bool:
        """
        评估预测是否命中

        Args:
            prediction: 预测的生肖列表
            actual_list: 开奖的生肖列表（7个）
            actual: 特码（用于六肖验证）

        Returns:
            是否命中
        """
        pass

    def validate_prediction_format(self, prediction: List[str]) -> bool:
        """验证预测格式"""
        if not isinstance(prediction, list):
            return False
        if len(prediction) == 0:
            return False
        return True

    def validate_actual_format(self, actual_list: List[str]) -> bool:
        """验证开奖结果格式"""
        if not isinstance(actual_list, list):
            return False
        if len(actual_list) == 0:
            return False
        return True