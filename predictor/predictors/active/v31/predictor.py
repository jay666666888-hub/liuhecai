#!/usr/bin/env python3
"""
澳门六合 - v31 24码预测器

策略：生肖分区综合得分
- 使用全局生肖年份映射系统（zodiac_year_map）
- 根据开奖时间自动选择对应农历年的生肖映射
- 计算每个号码的遗漏值 + 近17期出现频率
- 按生肖分区加权
- 综合取24个

使用全局映射系统：
  from predictor.constants import get_zodiac_map_for_date, get_lunar_year_for_date

  zodiac_map = get_zodiac_map_for_date(record['开奖时间'])
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from predictor.base_predictor import BasePredictor, PredictionResult
from predictor.data_fetcher import build_standard_records, get_all_records
from predictor.constants import get_zodiac_map_for_date, get_lunar_year_for_date

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


class V31Special24maPredictor(BasePredictor):
    """v31 24码预测器 - 生肖分区综合得分策略"""

    def __init__(self, version: str = "v31"):
        super().__init__(version)
        self.params = {
            "lookback": 17,
            "top_k": 24
        }

    def predict(self, history, top_k=24):
        """
        生成24码预测 - 生肖分区综合得分策略

        Args:
            history: 历史记录列表（build_standard_records格式）
            top_k: 返回前k个预测（默认24个）

        Returns:
            PredictionResult 对象
        """
        if not history:
            return PredictionResult(
                prediction=[f"{i:02d}" for i in range(1, top_k + 1)],
                scores={},
                metadata={"error": "no history"}
            )

        n = len(history)
        lookback = min(self.params["lookback"], n)
        recent = history[-lookback:]

        # 1. 计算每个号码的遗漏值
        num_last = {}
        for idx, r in enumerate(history):
            z = r.get('特码生肖')
            num = r.get('特码号码')
            if z and num:
                num_str = f"{int(num):02d}"
                num_last[num_str] = idx

        # 2. 计算近lookback期各号码出现频率
        num_freq = {}
        for r in recent:
            num = r.get('特码号码')
            if num:
                num_str = f"{int(num):02d}"
                num_freq[num_str] = num_freq.get(num_str, 0) + 1

        # 3. 获取当前使用的生肖映射（根据最近一期的时间）
        # 每次预测使用最新的生肖映射
        latest_record_time = history[-1].get('开奖时间', '') if history else ''
        zodiac_map = get_zodiac_map_for_date(latest_record_time)
        lunar_year = get_lunar_year_for_date(latest_record_time)

        # 4. 计算各生肖在近lookback期的出现频率
        zodiac_appearances = {z: 0 for z in ZODIACS}
        for r in recent:
            z = r.get('特码生肖')
            if z in zodiac_appearances:
                zodiac_appearances[z] += 1

        avg_appearances = sum(zodiac_appearances.values()) / 12

        # 5. 计算综合得分：(遗漏 + 频率) × 生肖频率比
        num_scores = {}
        for zodiac, nums in zodiac_map.items():
            z_freq_ratio = zodiac_appearances[zodiac] / avg_appearances if avg_appearances > 0 else 1
            for num_str in nums:
                miss = n - num_last.get(num_str, -1) if num_str in num_last else n
                freq = num_freq.get(num_str, 0)
                num_scores[num_str] = (miss + freq) * z_freq_ratio

        # 6. 按得分排序取top_k
        ranked = sorted(num_scores.keys(), key=lambda x: num_scores[x], reverse=True)
        prediction = ranked[:top_k]

        return PredictionResult(
            prediction=prediction,
            scores=num_scores,
            metadata={
                "lookback": lookback,
                "strategy": "zodiac_partition_combined_score",
                "lunar_year": lunar_year,
                "zodiac_map_version": f"lunar_{lunar_year}"
            }
        )