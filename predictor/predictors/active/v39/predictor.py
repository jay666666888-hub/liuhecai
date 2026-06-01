#!/usr/bin/env python3
"""
澳门六合 - v39 30码预测器

策略：生肖分区综合得分
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from predictor.base_predictor import BasePredictor, PredictionResult
from predictor.constants import get_zodiac_map_for_date

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


class V39NumberPredictor(BasePredictor):
    """v39 30码预测器"""

    def __init__(self, version: str = "v39"):
        super().__init__(version)
        self.params = {"lookback": 50, "top_k": 30}

    def predict(self, history, top_k=30):
        if not history:
            return PredictionResult(
                prediction=[f"{i:02d}" for i in range(1, top_k + 1)],
                scores={},
                metadata={"error": "no history"}
            )

        n = len(history)
        lookback = min(self.params["lookback"], n)
        recent = history[-lookback:]

        zodiac_map = get_zodiac_map_for_date(history[-1]['开奖时间'])

        zodiac_to_nums = {z: [] for z in ZODIACS}
        for num in range(1, 50):
            num_str = f"{num:02d}"
            zodiac = zodiac_map.get(num_str)
            if zodiac:
                zodiac_to_nums[zodiac].append(num_str)

        zodiac_scores = {}
        for zodiac in ZODIACS:
            count = sum(1 for r in recent if r.get('特码生肖') == zodiac)
            zodiac_scores[zodiac] = count / lookback

        num_scores = {}
        for num in range(1, 50):
            num_str = f"{num:02d}"
            zodiac = zodiac_map.get(num_str, '未知')

            gap = 0
            for i in range(len(history) - 1, -1, -1):
                if any(n in history[i].get('开奖号码', []) for n in [num_str, num]):
                    break
                gap += 1

            freq_score = zodiac_scores.get(zodiac, 0)
            num_scores[num_str] = gap * 0.6 + freq_score * 100

        result = []
        nums_per_zodiac = max(1, 30 // 12)  # 30个码均匀分配

        for zodiac in ZODIACS:
            nums = zodiac_to_nums.get(zodiac, [])
            scored_nums = [(n, num_scores.get(n, 0)) for n in nums]
            scored_nums.sort(key=lambda x: x[1], reverse=True)
            result.extend([n for n, s in scored_nums[:nums_per_zodiac]])

        all_scored = [(n, num_scores.get(n, 0)) for n in result]
        all_scored.sort(key=lambda x: x[1], reverse=True)
        final_prediction = [n for n, s in all_scored[:30]]

        if len(final_prediction) < 30:
            all_nums = set(f"{i:02d}" for i in range(1, 50))
            remaining = list(all_nums - set(final_prediction))
            remaining.sort(key=lambda x: num_scores.get(x, 0), reverse=True)
            final_prediction.extend(remaining[:30 - len(final_prediction)])

        return PredictionResult(
            prediction=final_prediction[:30],
            scores={n: num_scores.get(n, 0) for n in final_prediction[:30]},
            metadata={"mode": "30ma", "top_k": 30}
        )