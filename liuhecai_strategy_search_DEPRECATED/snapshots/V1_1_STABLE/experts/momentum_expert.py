"""MomentumExpert - 短期速度专家
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


def compute_momentum_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    """
    计算 MomentumExpert 评分
    纯短期速度：streak * 1.0
    """
    scores = {}

    for z in ZODIACS:
        # 计算连续出现次数
        streak = 0
        for i in range(upto_idx - 1, -1, -1):
            if z in df.iloc[i]['zodiacs']:
                streak += 1
            else:
                break
        scores[z] = float(streak)

    # Z-score 标准化
    score_values = _z_score_normalize([scores[z] for z in ZODIACS])
    for i, z in enumerate(ZODIACS):
        scores[z] = score_values[i]

    return scores


def get_expert_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    return compute_momentum_scores(df, upto_idx)
