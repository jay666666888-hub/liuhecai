"""FrequencyExpert - 频率专家
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


def compute_frequency_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    """
    计算 FrequencyExpert 评分
    纯频率：近期出现频率
    """
    scores = {}
    data = df.iloc[:upto_idx]

    freq_window = 10
    if upto_idx < freq_window:
        for z in ZODIACS:
            scores[z] = 0.0
        return scores

    recent = data.iloc[-freq_window:]

    for z in ZODIACS:
        # 统计近期出现次数
        freq = sum(1 for i in range(len(recent)) if z in recent.iloc[i]['zodiacs'])
        # 归一化到期望频率
        expected_freq = freq_window / 12
        score = freq / expected_freq if expected_freq > 0 else 0
        scores[z] = score

    # Z-score 标准化
    score_values = _z_score_normalize([scores[z] for z in ZODIACS])
    for i, z in enumerate(ZODIACS):
        scores[z] = score_values[i]

    return scores


def get_expert_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    return compute_frequency_scores(df, upto_idx)
