#!/usr/bin/env python3
"""
区间加权策略测试
在现有得分基础上，对后区(20-49)给予加权
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.predictors.active.number_selection_v1.predictor import NumberSelectionPredictorV1

records = get_all_records([2024, 2025, 2026])
standard = build_standard_records(records)
print(f"总期数: {len(standard)}")

lookback = 50

# 测试不同 zone_weight
for zone_boost in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]:
    hits = 0
    total = 0
    max_streak = 0
    streak = 0

    for i in range(lookback, len(standard)):
        history = standard[:i]
        predictor = NumberSelectionPredictorV1("test")

        # 获取基础得分
        weights = {"freq_weight": 0.5, "gap_weight": 0.5, "zodiac_weight": 0.0}
        latest_record = history[-1]
        from predictor.constants import get_zodiac_map_for_date
        zodiac_map = get_zodiac_map_for_date(latest_record['开奖时间'])

        # 计算频率得分
        recent = history[-lookback:]
        freq_scores = {}
        for num in range(1, 50):
            num_str = f"{num:02d}"
            count = sum(1 for r in recent if r.get('特码号码') == num_str or r.get('特码号码') == str(num) or r.get('特码号码') == num)
            freq_scores[num_str] = count / lookback

        # 计算遗漏得分
        gap_scores = {}
        for num in range(1, 50):
            num_str = f"{num:02d}"
            gap = 0
            for j in range(len(history) - 1, -1, -1):
                if history[j].get('特码号码') == num_str or history[j].get('特码号码') == str(num) or history[j].get('特码号码') == num:
                    break
                gap += 1
            gap_scores[num_str] = gap

        # 综合打分 + 区间加权
        num_scores = {}
        max_gap = max(gap_scores.values()) if gap_scores else 1

        for num in range(1, 50):
            num_str = f"{num:02d}"
            freq = freq_scores.get(num_str, 0)
            gap = gap_scores.get(num_str, 0) / max_gap if max_gap > 0 else 0

            score = freq * 0.5 + gap * 0.5

            # 后区加权
            if num >= 20:
                score *= (1 + zone_boost)

            num_scores[num_str] = score

        # 排序取前30
        sorted_nums = sorted(num_scores.items(), key=lambda x: x[1], reverse=True)
        prediction = [n for n, s in sorted_nums[:30]]

        actual = standard[i].get("特码号码")
        hit = actual in prediction if actual else False

        if hit:
            hits += 1
            streak = 0
        else:
            streak += 1
            max_streak = max(max_streak, streak)
        total += 1

    hit_rate = hits / total * 100 if total > 0 else 0
    print(f"zone_boost={zone_boost:.1f}: 命中率 {hit_rate:.2f}%, 最大连错 {max_streak}")

print("\n基准: 固定选20-49 = 61.75%")