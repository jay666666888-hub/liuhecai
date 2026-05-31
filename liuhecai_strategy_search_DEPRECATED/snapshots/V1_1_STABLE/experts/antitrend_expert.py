"""AntiTrendExpert - 反转机会专家
"""
import numpy as np
import pandas as pd
from typing import Dict, List

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


def _z_score_normalize(values: List[float]) -> List[float]:
    arr = np.array(values)
    mean = np.mean(arr)
    std = np.std(arr)
    if std == 0:
        return [0.0] * len(values)
    return ((arr - mean) / std).tolist()


def compute_antitrend_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    """
    计算 AntiTrendExpert 评分
    5个特征：trend_acceleration, sign_change_rate, reversal_strength,
           local_peak_distance, overshoot_score
    """
    scores = {}
    data = df.iloc[:upto_idx]

    window = min(30, upto_idx)
    if window < 15:
        for z in ZODIACS:
            scores[z] = 0.0
        return scores

    recent = data.iloc[-window:]

    for z in ZODIACS:
        # Feature 1: trend_acceleration
        w1 = len(recent) // 3
        w2 = len(recent) // 3
        w3 = len(recent) - w1 - w2

        count1 = sum(1 for i in range(w1) if z in recent.iloc[i]['zodiacs'])
        count2 = sum(1 for i in range(w1, w1+w2) if z in recent.iloc[i]['zodiacs'])
        count3 = sum(1 for i in range(len(recent) - w3, len(recent)) if z in recent.iloc[i]['zodiacs'])

        v1 = count2 - count1
        v2 = count3 - count2
        acceleration = v2 - v1
        trend_accel = max(0, -acceleration) * 2

        # Feature 2: sign_change_rate
        positions = [i for i in range(len(recent)) if z in recent.iloc[i]['zodiacs']]
        if len(positions) >= 4:
            signs = [1 if i % 2 == 0 else -1 for i in range(len(positions))]
            sign_changes = sum(1 for i in range(1, len(signs)) if signs[i] != signs[i-1])
            sign_change_rate = sign_changes / (len(positions) - 1) if len(positions) > 1 else 0
        else:
            sign_change_rate = 0
        sign_change_score = sign_change_rate * 5

        # Feature 3: reversal_strength
        if len(positions) >= 3:
            start_idx = max(0, positions[-1] - 4)
            end_idx = positions[-1] + 1
            last_run = [z in recent.iloc[i]['zodiacs'] for i in range(start_idx, end_idx)]
            alt_count = sum(1 for i in range(1, len(last_run)) if last_run[i] != last_run[i-1])
            reversal_strength = alt_count / (len(last_run) - 1) if len(last_run) > 1 else 0
        else:
            reversal_strength = 0
        reversal_score = reversal_strength * 5

        # Feature 4: local_peak_distance
        if len(positions) >= 2:
            recent_3 = positions[-3:] if len(positions) >= 3 else positions
            if len(recent_3) >= 2:
                local_peak_dist = recent_3[-1] - recent_3[-2]
                peak_distance_score = max(0, 10 - local_peak_dist) / 5
            else:
                peak_distance_score = 0
        else:
            peak_distance_score = 0

        # Feature 5: overshoot_score
        appearances = [i for i in range(upto_idx) if z in df.iloc[i]['zodiacs']]
        if len(appearances) >= 3:
            intervals = np.diff(appearances[-4:])
            expected_cycle = np.mean(intervals) if len(intervals) > 0 else 12
            current_gap = upto_idx - appearances[-1] - 1 if appearances else window
            overshoot = max(0, current_gap - expected_cycle)
            overshoot_score = min(overshoot / 5, 5)
        else:
            overshoot_score = 0

        # 合并所有特征
        raw_score = trend_accel + sign_change_score + reversal_score + peak_distance_score + overshoot_score
        scores[z] = raw_score

    # Z-score 标准化
    score_values = _z_score_normalize([scores[z] for z in ZODIACS])
    for i, z in enumerate(ZODIACS):
        scores[z] = score_values[i]

    return scores


def get_expert_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    return compute_antitrend_scores(df, upto_idx)
