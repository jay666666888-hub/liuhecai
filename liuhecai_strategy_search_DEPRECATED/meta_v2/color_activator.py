# meta_v2/color_activator.py
"""COLOR动态注入器（可插拔组件）"""
from typing import Dict, Optional

BASELINE = 0.50


class ColorActivator:
    """动态COLOR权重注入（可插拔组件）"""

    def __init__(self):
        self.baseline = BASELINE
        self.last_activation = None
        self.last_color_weight = 0.0

    def get_weight(self, base_weights: Dict[str, float],
                   rolling_hit_20: float = 0.5) -> Dict[str, float]:
        """
        获取带COLOR注入的权重（接口方法）
        """
        color_weight = self.get_color_weight(rolling_hit_20)
        return self.inject_color(base_weights, rolling_hit_20)

    def update(self, rolling_hit_20: float = None):
        """
        更新状态（接口方法）
        """
        if rolling_hit_20 is not None:
            self.last_activation = rolling_hit_20

    def report(self) -> Dict:
        """
        生成报告（接口方法）
        """
        return {
            "color_weight": self.last_color_weight,
            "activated": self.last_color_weight > 0,
            "baseline": self.baseline
        }

    def get_color_confidence(self, rolling_hit_20: float) -> float:
        """color_confidence = rolling_hit_20 / baseline, cap at 1.5"""
        confidence = rolling_hit_20 / self.baseline
        return min(1.5, confidence)

    def get_color_weight(self, rolling_hit_20: float) -> float:
        """color_weight = min(0.15, 0.15 × color_confidence), if confidence < 1.05 → 0"""
        confidence = self.get_color_confidence(rolling_hit_20)
        if confidence < 1.05:
            return 0.0
        self.last_color_weight = min(0.15, 0.15 * confidence)
        return self.last_color_weight

    def inject_color(self, base_weights: dict, rolling_hit_20: float = 0.5) -> dict:
        """注入COLOR权重到基础权重"""
        color_weight = self.get_color_weight(rolling_hit_20)
        if color_weight <= 0:
            return base_weights

        others_total = sum(v for k, v in base_weights.items() if k != "Color")
        if others_total <= 0:
            return base_weights

        scale = (1 - color_weight) / others_total
        result = {}
        for expert, w in base_weights.items():
            if expert == "Color":
                result[expert] = color_weight
            else:
                result[expert] = w * scale

        total = sum(result.values())
        if total > 0:
            result = {k: v / total for k, v in result.items()}
        return result

    def reset(self):
        """重置"""
        self.last_activation = None
        self.last_color_weight = 0.0