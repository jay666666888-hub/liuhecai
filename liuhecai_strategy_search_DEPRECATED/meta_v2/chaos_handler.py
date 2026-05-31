# meta_v2/chaos_handler.py
"""CHAOS处理器 - 混乱市场处理（可插拔组件）"""
import random
from typing import Dict, List, Tuple, Optional


class ChaosHandler:
    """CHAOTIC状态特殊处理（可插拔组件）"""

    def __init__(self, seed: int = 42):
        self.dominance_counter = {}
        self.rng = random.Random(seed)
        self.last_explore_result = None

    def get_weight(self, base_weights: Dict[str, float],
                   entropy_score: float) -> Dict[str, float]:
        """
        获取处理后的权重（接口方法）
        """
        # 应用噪声
        weights = self.apply_noise(base_weights)
        # 裁剪
        weights = self.clip_weights(weights)
        # 检查主导惩罚
        weights = self.check_dominance_penalty(weights)
        return weights

    def update(self, entropy_score: float = None, predictions: Dict[str, List[str]] = None):
        """
        更新状态（接口方法）
        """
        pass  # 无状态更新

    def report(self) -> Dict:
        """
        生成报告（接口方法）
        """
        return {
            "dominance_counter": self.dominance_counter.copy(),
            "last_explore_result": self.last_explore_result
        }

    def get_explore_probability(self, entropy_score: float) -> float:
        """动态探索概率: 0.05 + entropy_score × 0.25, clip [0.05, 0.30]"""
        prob = 0.05 + entropy_score * 0.25
        return max(0.05, min(0.30, prob))

    def apply_noise(self, base_weights: Dict[str, float]) -> Dict[str, float]:
        """应用N(0, 0.03)噪声"""
        result = {}
        for expert, weight in base_weights.items():
            noise = self.rng.gauss(0, 0.03)
            result[expert] = max(0, weight + noise)
        return result

    def clip_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """裁剪到[0.10, 0.40]"""
        result = {}
        for expert, weight in weights.items():
            result[expert] = max(0.10, min(0.40, weight))
        total = sum(result.values())
        if total > 0:
            result = {k: v / total for k, v in result.items()}
        return result

    def check_dominance_penalty(self, weights: Dict[str, float]) -> Dict[str, float]:
        """禁止连续10期主导：weight × 0.8"""
        result = weights.copy()
        max_weight = max(weights.values())
        for expert, weight in weights.items():
            if weight == max_weight:
                self.dominance_counter[expert] = self.dominance_counter.get(expert, 0) + 1
                if self.dominance_counter[expert] >= 10:
                    result[expert] = weight * 0.8
            else:
                self.dominance_counter[expert] = 0
        return result

    def should_explore(self, entropy_score: float) -> bool:
        """判断是否触发探索"""
        prob = self.get_explore_probability(entropy_score)
        return self.rng.random() < prob

    def get_replacement(self, current_top6: List[str], all_zodiacs: List[str],
                       recent_hit_rates: Dict[str, float],
                       diversity_scores: Dict[str, float]) -> Tuple[str, str, str]:
        """
        获取探索替换：非TOP6按 recent_hit_rate × diversity_score 采样
        返回: (replaced_zodiac, replacement_zodiac, reason)
        """
        non_top6 = [z for z in all_zodiacs if z not in current_top6]
        if not non_top6:
            return current_top6[-1], random.choice(all_zodiacs), "no_replacement_available"

        scores = {}
        for zodiac in non_top6:
            scores[zodiac] = recent_hit_rates.get(zodiac, 0.5) * diversity_scores.get(zodiac, 1.0)

        total = sum(scores.values())
        if total > 0:
            probs = {z: s / total for z, s in scores.items()}
            replacement = self.rng.choices(list(probs.keys()), weights=list(probs.values()), k=1)[0]
        else:
            replacement = self.rng.choice(non_top6)

        replaced = self.rng.choice(current_top6)

        self.last_explore_result = {
            "replaced": replaced,
            "replacement": replacement,
            "reason": "exploration_triggered"
        }

        return replaced, replacement, "exploration_triggered"

    def reset(self):
        """重置"""
        self.dominance_counter = {}
        self.last_explore_result = None