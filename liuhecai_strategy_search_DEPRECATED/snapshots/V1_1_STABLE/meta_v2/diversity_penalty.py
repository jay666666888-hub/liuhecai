# meta_v2/diversity_penalty.py
"""专家多样性惩罚（可插拔组件）"""
from typing import Dict, List, Optional

SIMILARITY_THRESHOLD = 0.8
PENALTY_FACTOR = 0.7


class ExpertDiversityPenalty:
    """Jaccard相似度惩罚（可插拔组件）"""

    def __init__(self):
        self.similarity_threshold = SIMILARITY_THRESHOLD
        self.penalty_factor = PENALTY_FACTOR
        self.last_penalty_report = []

    def get_weight(self, base_weights: Dict[str, float],
                   predictions: Dict[str, List[str]]) -> Dict[str, float]:
        """
        应用相似度惩罚（接口方法）
        """
        return self.apply_penalty(base_weights, predictions)

    def update(self, predictions: Dict[str, List[str]] = None):
        """
        更新状态（接口方法）
        """
        if predictions:
            self.last_penalty_report = self.get_similarity_report(predictions)

    def report(self) -> Dict:
        """
        生成报告（接口方法）
        """
        return {
            "similarity_threshold": self.similarity_threshold,
            "penalty_factor": self.penalty_factor,
            "last_penalty_report": self.last_penalty_report
        }

    def _jaccard(self, set_a: List[str], set_b: List[str]) -> float:
        """计算Jaccard相似度"""
        set_a = set(set_a)
        set_b = set(set_b)
        if len(set_a) == 0 and len(set_b) == 0:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def apply_penalty(self, weights: Dict[str, float],
                     predictions: Dict[str, List[str]]) -> Dict[str, float]:
        """应用相似度惩罚"""
        result = weights.copy()
        experts = list(predictions.keys())

        penalties_applied = []
        for i in range(len(experts)):
            for j in range(i + 1, len(experts)):
                exp_a = experts[i]
                exp_b = experts[j]
                sim = self._jaccard(predictions.get(exp_a, []), predictions.get(exp_b, []))

                if sim > self.similarity_threshold:
                    penalties_applied.append({
                        "expert_a": exp_a,
                        "expert_b": exp_b,
                        "similarity": round(sim, 4),
                        "penalty": self.penalty_factor
                    })
                    if weights[exp_a] <= weights[exp_b]:
                        weaker = exp_a
                    else:
                        weaker = exp_b
                    result[weaker] = weights[weaker] * self.penalty_factor

        self.last_penalty_report = penalties_applied

        total = sum(result.values())
        if total > 0:
            result = {k: v / total for k, v in result.items()}
        return result

    def get_similarity_report(self, predictions: Dict[str, List[str]]) -> List[dict]:
        """生成相似度报告"""
        report = []
        experts = list(predictions.keys())

        for i in range(len(experts)):
            for j in range(i + 1, len(experts)):
                exp_a = experts[i]
                exp_b = experts[j]
                sim = self._jaccard(predictions.get(exp_a, []), predictions.get(exp_b, []))

                if sim > self.similarity_threshold:
                    report.append({
                        "expert_a": exp_a,
                        "expert_b": exp_b,
                        "similarity": round(sim, 4),
                        "penalty": self.penalty_factor
                    })

        return report

    def reset(self):
        """重置"""
        self.last_penalty_report = []