# meta_v2/state_router.py
"""状态路由器 - 状态依赖权重 (可插拔组件)"""
from typing import Dict, Optional

# 重新平衡的BASE_WEIGHTS：减少Trend dominance，实现更均衡的专家贡献
# 问题诊断：Trend在HOT状态占0.7权重，导致贡献度偏斜72%
# 目标：每个状态下专家权重更均衡，让分数差异主要由expert_confidence反映
BASE_WEIGHTS = {
    "HOT": {"Gap": 0.25, "Trend": 0.25, "Momentum": 0.15, "Frequency": 0.10, "Color": 0.10, "AntiTrend": 0.10, "Cycle": 0.05},
    "COLD": {"Gap": 0.30, "Trend": 0.20, "Momentum": 0.20, "Frequency": 0.10, "Color": 0.10, "AntiTrend": 0.05, "Cycle": 0.05},
    "TRANSITION": {"Gap": 0.10, "Trend": 0.15, "Momentum": 0.20, "Frequency": 0.15, "Color": 0.10, "AntiTrend": 0.20, "Cycle": 0.10},
    "CHAOTIC": {"Gap": 0.15, "Trend": 0.15, "Momentum": 0.15, "Frequency": 0.15, "Color": 0.15, "AntiTrend": 0.15, "Cycle": 0.10},
    "UNCERTAIN": None  # 动态计算
}


class StateRouter:
    """状态依赖权重路由（可插拔组件）"""

    def __init__(self):
        self.current_state = "HOT"
        self.current_weights = {}

    def get_weight(self, state: Optional[str] = None) -> Dict[str, float]:
        """
        获取权重（接口方法）
        state: 市场状态
        returns: 专家权重字典
        """
        state = state or self.current_state

        if state == "UNCERTAIN":
            return self.current_weights  # 动态权重由外部设置

        return BASE_WEIGHTS.get(state, BASE_WEIGHTS["HOT"]).copy()

    def update(self, state: str, recent_hits: Dict[str, float] = None, stability: Dict[str, float] = None):
        """
        更新状态和权重（接口方法）
        """
        self.current_state = state

        if state == "UNCERTAIN" and recent_hits and stability:
            self.current_weights = self._calc_uncertain_weights(recent_hits, stability)
        else:
            self.current_weights = self.get_weight(state)

    def report(self) -> Dict:
        """
        生成报告（接口方法）
        """
        return {
            "state": self.current_state,
            "weights": self.current_weights,
            "base_weights": BASE_WEIGHTS.get(self.current_state, BASE_WEIGHTS["HOT"]).copy()
        }

    def _calc_uncertain_weights(self, recent_hits: Dict[str, float],
                                stability: Dict[str, float]) -> Dict[str, float]:
        """UNCERTAIN状态：weight = recent_hit × stability，normalize"""
        weights = {}
        for expert in ["Gap", "Trend", "Momentum", "Frequency", "Color", "AntiTrend", "Cycle"]:
            weights[expert] = recent_hits.get(expert, 0.0) * stability.get(expert, 0.5)

        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        return weights

    def apply_color_weight(self, base_weights: Dict[str, float],
                           color_weight: float) -> Dict[str, float]:
        """应用COLOR动态权重"""
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
        self.current_state = "HOT"
        self.current_weights = {}