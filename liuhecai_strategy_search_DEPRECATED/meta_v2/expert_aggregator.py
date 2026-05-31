# meta_v2/expert_aggregator.py
"""Decision Diversity Aggregator - 分数加权聚合 + 强制探索"""
from typing import Dict, List, Tuple
import random
from collections import defaultdict

from meta_v2.diversity_config import (
    EXPLORE_PROB_MIN, EXPLORE_PROB_MAX, ENTROPY_THRESHOLD,
    JACCARD_THRESHOLD, JACCARD_PENALTY
)

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
DIVERSITY_POOL = ZODIACS  # 探索替换池


class ExpertAggregator:
    """Decision Diversity Aggregator"""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.replace_prob_min = EXPLORE_PROB_MIN
        self.replace_prob_max = EXPLORE_PROB_MAX
        self.entropy_threshold = ENTROPY_THRESHOLD
        self.similarity_threshold = JACCARD_THRESHOLD
        self.penalty_factor = JACCARD_PENALTY
        self.last_report = {}

    def aggregate(
        self,
        expert_scores: Dict[str, Dict[str, float]],
        expert_weights: Dict[str, float],
        entropy: float,
        diversity_scores: Dict[str, float] = None
    ) -> Tuple[List[str], Dict]:
        """
        核心聚合: final[z] = Σ(expert_weight × expert_confidence × zodiac_score)
        关键：每专家分数归一化到[0,1]，避免量纲差异导致某专家主导
        """
        if diversity_scores is None:
            diversity_scores = {z: 1.0 for z in ZODIACS}

        # 0. 预归一化：将每专家的score映射归一化到[0,1]
        normalized_scores = self._normalize_expert_scores(expert_scores)

        # 1. 计算每个专家的置信度（score离散度）
        expert_confidences = self._calc_expert_confidences(normalized_scores)

        # 2. 加权聚合: final[z] = Σ(weight × conf × norm_score)
        zodiac_scores = defaultdict(float)
        for expert_name, zodiac_score_map in normalized_scores.items():
            weight = expert_weights.get(expert_name, 0.25)
            conf = expert_confidences.get(expert_name, 0.5)
            for zodiac, score in zodiac_score_map.items():
                zodiac_scores[zodiac] += weight * conf * score

        # 3. 应用多样性惩罚
        penalized_scores = self._apply_diversity_penalty(
            zodiac_scores, expert_scores, expert_weights
        )

        # 4. 强制探索（高熵时随机替换）
        final_scores = self._apply_forced_exploration(
            penalized_scores, entropy, diversity_scores
        )

        # 5. 排序输出TOP6
        sorted_zodiacs = sorted(
            final_scores.items(), key=lambda x: x[1], reverse=True
        )
        top6 = [z for z, s in sorted_zodiacs[:6]]

        # 6. 生成报告
        self.last_report = {
            "expert_weights": expert_weights,
            "expert_confidences": {k: round(v, 4) for k, v in expert_confidences.items()},
            "zodiac_scores": {k: round(v, 4) for k, v in final_scores.items()},
            "top6": top6,
        }

        return top6, self.last_report

    def _calc_expert_confidences(
        self, expert_scores: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """专家置信度：基于score离散度
        score越集中/conf越低 → 专家越不确定
        score越分散/conf越高 → 专家越确定
        """
        confidences = {}
        for expert_name, score_map in expert_scores.items():
            scores = list(score_map.values())
            if len(scores) < 2:
                confidences[expert_name] = 0.5
                continue
            mean_s = sum(scores) / len(scores)
            std_s = (sum((s - mean_s) ** 2 for s in scores) / len(scores)) ** 0.5
            # 归一化：std小→conf高，std大→conf低
            conf = 1.0 / (1.0 + std_s)
            confidences[expert_name] = max(0.1, min(1.0, conf))
        return confidences

    def _normalize_expert_scores(
        self, expert_scores: Dict[str, Dict[str, float]]
    ) -> Dict[str, Dict[str, float]]:
        """Percentile-rank归一化（处理负分问题）

        问题：Gap Expert对长期未出现的生肖给出负分（如-0.59）
        Min-Max归一化将负分→0，导致Gap权重乘以0后完全排除该生肖
        即使Trend/Momentum正确识别了该生肖，聚合后仍然遗漏

        解决：使用百分位排名归一化
        - 排名11/12 → norm=0.08（低但非零）
        - 排名1/12 → norm=0.92（高）
        这样负分生肖仍能从其他专家获得投票
        """
        normalized = {}
        for expert_name, score_map in expert_scores.items():
            # Sort zodiacs by score descending
            sorted_zodiacs = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
            n = len(sorted_zodiacs)

            normalized[expert_name] = {}
            for rank, (zodiac, score) in enumerate(sorted_zodiacs):
                # Percentile: rank 0 → 1.0, rank n-1 → 1/n
                percentile = 1.0 - (rank / n)
                normalized[expert_name][zodiac] = percentile

        return normalized

    def _apply_diversity_penalty(
        self,
        zodiac_scores: Dict[str, float],
        expert_scores: Dict[str, Dict[str, float]],
        expert_weights: Dict[str, float],
    ) -> Dict[str, float]:
        """Jaccard相似度惩罚：similarity>0.8时削弱重复专家的贡献"""
        result = zodiac_scores.copy()
        experts = list(expert_scores.keys())

        penalties_applied = []
        for i in range(len(experts)):
            for j in range(i + 1, len(experts)):
                exp_a, exp_b = experts[i], experts[j]
                top6_a = self._get_top6_from_scores(expert_scores[exp_a])
                top6_b = self._get_top6_from_scores(expert_scores[exp_b])
                sim = self._jaccard(top6_a, top6_b)

                if sim > self.similarity_threshold:
                    penalties_applied.append({
                        "pair": f"{exp_a}-{exp_b}",
                        "similarity": round(sim, 4),
                    })
                    # 削弱较弱的专家
                    if expert_weights.get(exp_a, 0) <= expert_weights.get(exp_b, 0):
                        weaker = exp_a
                    else:
                        weaker = exp_b
                    for zodiac in zodiac_scores:
                        if zodiac in expert_scores[weaker]:
                            result[zodiac] *= self.penalty_factor

        self.last_report["penalties"] = penalties_applied
        return result

    def _apply_forced_exploration(
        self,
        zodiac_scores: Dict[str, float],
        entropy: float,
        diversity_scores: Dict[str, float],
    ) -> Dict[str, float]:
        """高熵时强制探索：随机替换1个低分生肖"""
        # 动态探索概率
        replace_prob = min(
            self.replace_prob_max,
            self.replace_prob_min + entropy * 0.25
        )

        if entropy < 2.2:  # 不需要探索
            return zodiac_scores

        if self.rng.random() > replace_prob:
            return zodiac_scores

        # 找最低分且不在TOP3的生肖
        sorted_scores = sorted(
            zodiac_scores.items(), key=lambda x: x[1], reverse=True
        )
        non_top3 = [z for z, s in sorted_scores[3:] if z in DIVERSITY_POOL]
        if not non_top3:
            return zodiac_scores

        # 采样一个替换
        replaced = self.rng.choice(non_top3)
        candidates = [z for z in DIVERSITY_POOL if z != replaced]
        if candidates:
            replacement = self.rng.choice(candidates)
            # 用diversity_scores引导替换
            repl_scores = {
                z: diversity_scores.get(z, 1.0) for z in candidates
            }
            total = sum(repl_scores.values())
            if total > 0:
                probs = [repl_scores[z] / total for z in candidates]
                replacement = self.rng.choices(candidates, weights=probs, k=1)[0]

            result = zodiac_scores.copy()
            result[replaced] = result.get(replacement, 0.5)
            self.last_report["exploration"] = {
                "replaced": replaced,
                "replacement": replacement,
                "entropy": round(entropy, 4),
            }
            return result

        return zodiac_scores

    def _get_top6_from_scores(
        self, score_map: Dict[str, float]
    ) -> List[str]:
        return [z for z, s in sorted(
            score_map.items(), key=lambda x: x[1], reverse=True
        )[:6]]

    def _jaccard(self, list_a: List[str], list_b: List[str]) -> float:
        set_a, set_b = set(list_a), set(list_b)
        if not set_a and not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def calc_expert_correlation(
        self, expert_scores: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """计算专家两两相关性（用于诊断）"""
        experts = list(expert_scores.keys())
        correlations = {}
        for i in range(len(experts)):
            for j in range(i + 1, len(experts)):
                exp_a, exp_b = experts[i], experts[j]
                top6_a = self._get_top6_from_scores(expert_scores[exp_a])
                top6_b = self._get_top6_from_scores(expert_scores[exp_b])
                key = f"{exp_a}_{exp_b}"
                correlations[key] = round(self._jaccard(top6_a, top6_b), 4)
        return correlations

    def report(self) -> Dict:
        return self.last_report

    def reset(self):
        self.last_report = {}