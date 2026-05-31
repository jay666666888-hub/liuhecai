"""GapExpert - 时间间隔专家

允许特征:
- last_seen_distance: 上次出现至今的间隔
- missing_rank: 在 zodiac 列表中的排名
- gap_acceleration: gap(t) - gap(t-1)

禁止特征:
- 周期统计 (cycle_mean, cycle_std)
- 趋势特征
- 窗口统计
"""
import numpy as np
import pandas as pd
from typing import Dict, List

# Use the actual zodiac characters from the data
ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


def _z_score_normalize(values: List[float]) -> List[float]:
    """Z-score 标准化"""
    arr = np.array(values)
    mean = np.mean(arr)
    std = np.std(arr)
    if std == 0:
        return [0.0] * len(values)
    return ((arr - mean) / std).tolist()


def compute_gap_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    """
    计算 GapExpert 评分

    评分公式:
    score = missing_rank * 2.0 + gap_acceleration * 0.5

    其中:
    - missing_rank: gap 越大，排名越高 (z-score 标准化)
    - gap_acceleration: gap(t) - gap(t-1)，一阶差分 (z-score 标准化)
    """
    scores = {}

    # 计算每个 zodiac 的 gap (last_seen_distance)
    # zodiacs 列是每行7个生肖的列表，需要搜索所有行
    gaps = {}
    for z in ZODIACS:
        # 找到所有在 zodiacs 列表中包含 z 的行索引
        last_seen = -1
        for row_idx in range(upto_idx):
            zodiacs_list = df.iloc[row_idx]['zodiacs']
            if z in zodiacs_list:
                last_seen = row_idx

        if last_seen >= 0:
            gap = upto_idx - last_seen - 1
        else:
            gap = upto_idx  # 从未出现
        gaps[z] = gap

    # 计算 gap_acceleration: gap(t) - gap(t-1)
    gap_accels = {}
    for z in ZODIACS:
        # 找最后两次出现
        appearances = []
        for row_idx in range(upto_idx):
            zodiacs_list = df.iloc[row_idx]['zodiacs']
            if z in zodiacs_list:
                appearances.append(row_idx)

        if len(appearances) >= 2:
            # gap(t) = upto_idx - appearances[-1] - 1
            # gap(t-1) = appearances[-1] - appearances[-2] - 1
            gap_t = upto_idx - appearances[-1] - 1
            gap_t_minus_1 = appearances[-1] - appearances[-2] - 1
            gap_accel = gap_t - gap_t_minus_1
        else:
            gap_accel = 0.0
        gap_accels[z] = gap_accel

    # 计算 missing_rank: 基于 gap 的排名
    gap_values = [gaps[z] for z in ZODIACS]
    gap_ranks = np.argsort(np.argsort(gap_values))[::-1]  # 降序排名
    missing_ranks = {z: float(gap_ranks[i]) for i, z in enumerate(ZODIACS)}

    # 标准化
    gap_values_norm = _z_score_normalize([gaps[z] for z in ZODIACS])
    gap_accel_values_norm = _z_score_normalize([gap_accels[z] for z in ZODIACS])
    missing_rank_values_norm = _z_score_normalize([missing_ranks[z] for z in ZODIACS])

    # 组合评分
    for i, z in enumerate(ZODIACS):
        missing_rank_norm = missing_rank_values_norm[i]
        gap_accel_norm = gap_accel_values_norm[i]

        # 原始组合 (在标准化空间)
        raw_score = missing_rank_norm * 2.0 + gap_accel_norm * 0.5
        scores[z] = raw_score

    return scores


def get_expert_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    """入口函数"""
    return compute_gap_scores(df, upto_idx)
