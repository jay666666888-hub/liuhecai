"""ColorExpert - 颜色多样性信号专家
"""
import numpy as np
import pandas as pd
from typing import Dict, List

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

# 生肖对应的颜色分组
ZODIAC_COLORS = {
    'red': ['馬', '羊', '兔', '猴'],
    'blue': ['鼠', '牛', '蛇', '狗'],
    'green': ['虎', '龍', '雞', '豬']
}

COLOR_GROUPS = {
    'red': ['馬', '羊', '兔', '猴'],
    'blue': ['鼠', '牛', '蛇', '狗'],
    'green': ['虎', '龍', '雞', '豬']
}


def _z_score_normalize(values: List[float]) -> List[float]:
    arr = np.array(values)
    mean = np.mean(arr)
    std = np.std(arr)
    if std == 0:
        return [0.0] * len(values)
    return ((arr - mean) / std).tolist()


def compute_color_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    """
    计算 ColorExpert 评分
    颜色多样性信号：当某个生肖的颜色倾向于出现在颜色边界时给出高分
    """
    scores = {}
    data = df.iloc[:upto_idx]

    for z in ZODIACS:
        # 找到 zodiac 的颜色组
        color = None
        for c, zs in COLOR_GROUPS.items():
            if z in zs:
                color = c
                break

        if not color:
            scores[z] = 0.0
            continue

        # 测量：当这个生肖出现时，是否倾向于在颜色边界（下一个颜色不同）
        color_window = min(50, upto_idx)
        if color_window < 10:
            scores[z] = 0.0
            continue

        recent = data.iloc[-color_window:]

        boundary_count = 0
        total_count = 0

        for i in range(len(recent) - 1):
            # 检查当前行是否包含 zodiac z
            if z in recent.iloc[i]['zodiacs']:
                total_count += 1
                # 检查下一个颜色是否不同
                curr_color = None
                next_color = None
                for c, zs in COLOR_GROUPS.items():
                    if z in zs:
                        curr_color = c
                    if any(z2 in recent.iloc[i + 1]['zodiacs'] for z2 in zs):
                        next_color = c
                        break
                if curr_color and next_color and curr_color != next_color:
                    boundary_count += 1

        if total_count > 0:
            boundary_prob = boundary_count / total_count
            score = boundary_prob * 10
        else:
            score = 0.0

        scores[z] = score

    # Z-score 标准化
    score_values = _z_score_normalize([scores[z] for z in ZODIACS])
    for i, z in enumerate(ZODIACS):
        scores[z] = score_values[i]

    return scores


def get_expert_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    return compute_color_scores(df, upto_idx)
