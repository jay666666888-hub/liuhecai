#!/usr/bin/env python3
"""
澳门六合 - 预测器基类接口

所有预测器必须继承 BasePredictor 并实现 predict() 方法。
禁止直接访问 data_fetcher 以外的数据源。

🚫 强制规则：
- 所有预测器必须继承 BasePredictor
- Step 3 完成前，禁止任何版本加入 active
- 所有数据访问必须通过 data_fetcher
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class PredictionResult:
    """统一预测结果格式"""
    prediction: List[str] = field(default_factory=list)  # 预测的6个生肖
    scores: Dict[str, float] = field(default_factory=dict)  # 各生肖得分
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据

    def to_dict(self) -> Dict:
        return {
            "prediction": self.prediction,
            "scores": self.scores,
            "metadata": self.metadata
        }


class BasePredictor(ABC):
    """预测器基类 - 所有版本必须继承"""

    def __init__(self, version: str):
        self.version = version
        self.name = self.__class__.__name__

    @abstractmethod
    def predict(self, history: List[Dict], top_k: int = 6) -> PredictionResult:
        """
        生成预测

        Args:
            history: 历史记录列表，每条记录包含 '特码生肖', '期号', '开奖时间' 等字段
            top_k: 返回前k个预测（默认6个）

        Returns:
            PredictionResult 对象

        Raises:
            NotImplementedError: 子类必须实现
        """
        raise NotImplementedError(f"{self.name} must implement predict()")

    def validate_history(self, history: List[Dict]) -> bool:
        """验证历史数据格式"""
        if not history:
            return False
        required_fields = ['特码生肖', '期号']
        return all(all(f in r for f in required_fields) for r in history)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} version={self.version}>"
