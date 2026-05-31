#!/usr/bin/env python3
"""
澳门六合 - Score Normalization Layer

让所有版本的 score 变成可比较的。

🚫 强制规则：
- 禁止直接用 raw score 排序
- 禁止不同版本 score 直接比较
- 必须通过 normalization layer 控制评分语义
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List
import math
from dataclasses import dataclass, field
from predictor.base_predictor import PredictionResult


@dataclass
class NormalizedPrediction:
    """标准化后的预测结果"""
    version: str
    prediction: List[str]
    raw_scores: Dict[str, float] = field(default_factory=dict)
    normalized_scores: Dict[str, float] = field(default_factory=dict)
    ranking_scores: Dict[str, float] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "prediction": self.prediction,
            "raw_scores": self.raw_scores,
            "normalized_scores": self.normalized_scores,
            "ranking_scores": self.ranking_scores,
            "metadata": self.metadata
        }


class ScoreNormalizer:
    """
    Score 标准化器

    将不同版本的 score 转换成统一的 [0, 1] 区间
    """

    def __init__(self):
        self.version_configs = {
            "v5": {"type": "minmax", "scale": 1.0},
            "v7": {"type": "rank", "scale": 1.0},
            "v12": {"type": "rank", "scale": 1.0},
            "v21": {"type": "rank", "scale": 1.0},
            "v23": {"type": "minmax", "scale": 1.0},
            "v24": {"type": "minmax", "scale": 1.0},
        }

    def normalize(self, version: str, result: PredictionResult) -> NormalizedPrediction:
        """
        标准化单个版本的预测结果

        Args:
            version: 版本号
            result: 原始 PredictionResult

        Returns:
            NormalizedPrediction
        """
        raw_scores = result.scores.copy()
        config = self.version_configs.get(version, {"type": "minmax"})

        if config["type"] == "minmax":
            normalized = self._minmax_normalize(raw_scores)
        elif config["type"] == "rank":
            normalized = self._rank_normalize(raw_scores)
        else:
            normalized = raw_scores

        # 计算 ranking scores（基于 normalized）
        ranking = self._compute_ranking(normalized)

        return NormalizedPrediction(
            version=version,
            prediction=result.prediction,
            raw_scores=raw_scores,
            normalized_scores=normalized,
            ranking_scores=ranking,
            metadata=result.metadata
        )

    def _minmax_normalize(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Min-Max 标准化到 [0, 1]"""
        if not scores:
            return {}

        vals = list(scores.values())
        min_v, max_v = min(vals), max(vals)
        range_v = max_v - min_v if max_v != min_v else 1

        return {k: (v - min_v) / range_v for k, v in scores.items()}

    def _rank_normalize(self, scores: Dict[str, float]) -> Dict[str, float]:
        """基于排名的标准化"""
        if not scores:
            return {}

        # 按分数排序
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        n = len(sorted_items)

        # rank 0 = 最高分
        return {
            item[0]: (n - rank) / n
            for rank, item in enumerate(sorted_items)
        }

    def _compute_ranking(self, normalized_scores: Dict[str, float]) -> Dict[str, float]:
        """计算 ranking score（所有分数归一化为概率分布）"""
        if not normalized_scores:
            return {}

        vals = list(normalized_scores.values())
        total = sum(vals) if sum(vals) > 0 else 1

        return {k: v / total for k, v in normalized_scores.items()}

    def normalize_batch(self, results: Dict[str, PredictionResult]) -> Dict[str, NormalizedPrediction]:
        """
        批量标准化所有版本的预测结果

        Args:
            results: {version: PredictionResult}

        Returns:
            {version: NormalizedPrediction}
        """
        normalized = {}
        for version, result in results.items():
            normalized[version] = self.normalize(version, result)
        return normalized


class CrossVersionComparator:
    """
    跨版本比较器

    用于比较和排序不同版本的预测结果
    """

    def __init__(self):
        self.normalizer = ScoreNormalizer()

    def compare(self, normalized_results: Dict[str, NormalizedPrediction]) -> List[NormalizedPrediction]:
        """
        比较所有版本的预测结果，按综合得分排序

        Args:
            normalized_results: 标准化后的结果

        Returns:
            按 ranking score 排序的列表
        """
        # 计算每个版本的综合得分（取 top-1 预测的 ranking score）
        version_scores = []
        for version, result in normalized_results.items():
            if not result.prediction:
                continue
            top1 = result.prediction[0]
            top1_ranking = result.ranking_scores.get(top1, 0)
            version_scores.append((version, top1_ranking, result))

        # 按得分排序
        version_scores.sort(key=lambda x: x[1], reverse=True)

        return [item[2] for item in version_scores]

    def get_top_predictions(self, normalized_results: Dict[str, NormalizedPrediction], top_k: int = 3) -> List[Dict]:
        """
        获取跨版本投票最高的预测

        Args:
            normalized_results: 标准化后的结果
            top_k: 返回前 k 个预测

        Returns:
            跨版本投票结果
        """
        # 统计每个生肖被推荐的版本数
        zodiac_votes = {}
        for version, result in normalized_results.items():
            for rank, zodiac in enumerate(result.prediction):
                if zodiac not in zodiac_votes:
                    zodiac_votes[zodiac] = {"votes": 0, "total_score": 0}
                zodiac_votes[zodiac]["votes"] += 1
                zodiac_votes[zodiac]["total_score"] += result.ranking_scores.get(zodiac, 0)

        # 按票数和得分排序
        sorted_zodiacs = sorted(
            zodiac_votes.items(),
            key=lambda x: (x[1]["votes"], x[1]["total_score"]),
            reverse=True
        )

        return [
            {"zodiac": z, "votes": v["votes"], "score": v["total_score"]}
            for z, v in sorted_zodiacs[:top_k]
        ]


def run_normalized_cycle(active_versions: List[str] = None):
    """
    运行标准化预测周期

    Args:
        active_versions: 活跃版本列表

    Returns:
        标准化后的结果
    """
    from predictor.orchestrator import PredictOrchestrator
    from predictor.data_fetcher import get_all_records, build_standard_records

    if active_versions is None:
        active_versions = ["v23", "v24"]

    print("=" * 50)
    print("澳门六合 - 标准化预测")
    print("=" * 50)

    # 1. 获取数据
    records = get_all_records([2024, 2025, 2026], force_refresh=True)
    standard = build_standard_records(records)

    if not standard:
        print("无法获取数据，退出")
        return {}

    # 2. 生成预测
    orch = PredictOrchestrator(active_versions)
    results = orch.predict(standard)

    # 3. 标准化
    normalizer = ScoreNormalizer()
    normalized = normalizer.normalize_batch(results)

    # 4. 比较
    comparator = CrossVersionComparator()
    ranked = comparator.compare(normalized)

    # 5. 打印结果
    print(f"\n版本排名（按综合得分）:")
    for result in ranked:
        top1 = result.prediction[0] if result.prediction else "-"
        top1_score = result.ranking_scores.get(top1, 0) if result.prediction else 0
        print(f"  {result.version}: top1={top1}({top1_score:.3f}) | prediction={result.prediction[:3]}")

    # 6. 跨版本投票
    top_votes = comparator.get_top_predictions(normalized)
    print(f"\n跨版本投票:")
    for vote in top_votes:
        print(f"  {vote['zodiac']}: {vote['votes']}票 ({vote['score']:.3f})")

    return {
        "normalized": {v: r.to_dict() for v, r in normalized.items()},
        "ranked": [r.version for r in ranked],
        "top_votes": top_votes
    }
