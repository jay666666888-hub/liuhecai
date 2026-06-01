#!/usr/bin/env python3
"""
澳门六合 - v36 24码预测器

策略：生肖分区综合得分
- 使用全局生肖年份映射系统
- 根据开奖时间自动选择对应农历年的生肖映射
- 计算每个号码的遗漏值 + 近17期出现频率
- 按生肖分区加权
- 综合取24个
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from predictor.base_predictor import BasePredictor, PredictionResult
from predictor.constants import get_zodiac_map_for_date, get_lunar_year_for_date

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


class V36NumberPredictor(BasePredictor):
    """v36 24码预测器 - 生肖分区综合得分策略"""

    def __init__(self, version: str = "v36"):
        super().__init__(version)
        self.params = {
            "lookback": 50,
            "top_k": 24
        }

    def predict(self, history, top_k=24):
        """
        生成24码预测 - 生肖分区综合得分策略

        Args:
            history: 历史记录列表
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

        # 获取生肖映射
        latest_record = history[-1]
        zodiac_map = get_zodiac_map_for_date(latest_record['开奖时间'])

        # 反向映射：生肖 -> 号码列表
        zodiac_to_nums = {z: [] for z in ZODIACS}
        for num in range(1, 50):
            num_str = f"{num:02d}"
            zodiac = zodiac_map.get(num_str)
            if zodiac:
                zodiac_to_nums[zodiac].append(num_str)

        # 计算每个生肖的权重（基于近期出现频率）
        zodiac_scores = {}
        for zodiac in ZODIACS:
            count = sum(1 for r in recent if r.get('特码生肖') == zodiac)
            zodiac_scores[zodiac] = count / lookback

        # 为每个号码打分
        num_scores = {}
        for num in range(1, 50):
            num_str = f"{num:02d}"
            zodiac = zodiac_map.get(num_str, '未知')

            # 遗漏值
            gap = 0
            for i in range(len(history) - 1, -1, -1):
                if any(n in history[i].get('开奖号码', []) for n in [num_str, num]):
                    break
                gap += 1

            # 频率得分
            freq_score = zodiac_scores.get(zodiac, 0)

            # 综合得分
            num_scores[num_str] = gap * 0.6 + freq_score * 100

        # 按生肖分区选取
        result = []
        nums_per_zodiac = max(1, top_k // 12)

        # 按得分排序每个生肖的号码
        for zodiac in ZODIACS:
            nums = zodiac_to_nums.get(zodiac, [])
            scored_nums = [(n, num_scores.get(n, 0)) for n in nums]
            scored_nums.sort(key=lambda x: x[1], reverse=True)
            result.extend([n for n, s in scored_nums[:nums_per_zodiac]])

        # 按得分排序取前 top_k
        all_scored = [(n, num_scores.get(n, 0)) for n in result]
        all_scored.sort(key=lambda x: x[1], reverse=True)
        final_prediction = [n for n, s in all_scored[:top_k]]

        # 如果不够24个，用得分最高的补齐
        if len(final_prediction) < top_k:
            all_nums = set(f"{i:02d}" for i in range(1, 50))
            remaining = list(all_nums - set(final_prediction))
            remaining.sort(key=lambda x: num_scores.get(x, 0), reverse=True)
            final_prediction.extend(remaining[:top_k - len(final_prediction)])

        return PredictionResult(
            prediction=final_prediction[:top_k],
            scores={n: num_scores.get(n, 0) for n in final_prediction[:top_k]},
            metadata={"mode": "24ma", "top_k": top_k}
        )