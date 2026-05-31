"""TrendExpert - 趋势方向变化加速度专家

允许特征:
- EMA_slope: 双尺度 EMA 斜率 (span=12 vs span=50)
- direction_strength: 方向强度

禁止特征:
- cycle, gap, periodicity, rolling_mean

核心原则:
TrendExpert 捕捉 "方向变化的加速度"
不是：趋势水平、趋势周期、趋势强度
"""
import numpy as np
import pandas as pd
from typing import Dict, List

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


def _z_score_normalize(values: List[float]) -> List[float]:
    """Z-score 标准化"""
    arr = np.array(values)
    mean = np.mean(arr)
    std = np.std(arr)
    if std == 0:
        return [0.0] * len(values)
    return ((arr - mean) / std).tolist()


def _compute_ema(series: pd.Series, span: int) -> pd.Series:
    """计算 EMA"""
    return series.ewm(span=span, adjust=False).mean()


def compute_trend_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    """
    计算 TrendExpert 评分

    评分公式:
    score = EMA_slope + direction_strength

    其中:
    - EMA_slope = slope(EMA_12 - EMA_50)，捕捉短期 vs 长期趋势的偏离速度
    - direction_strength = |EMA_12 - EMA_50| 的大小
    """
    scores = {}
    data = df.iloc[:upto_idx]

    # 计算每个 zodiac 的出现频率时间序列
    # 使用滚动窗口计算频率
    window = min(30, upto_idx)

    if window < 12:
        # 数据不足
        for z in ZODIACS:
            scores[z] = 0.0
        return scores

    # 创建 zodiac 出现的时间序列 (1 if zodiac appears at position in zodiacs list)
    for z in ZODIACS:
        # Binary signal: 1 if zodiac z appears in the zodiacs list at that row
        signal = np.array([1 if z in data.iloc[i]['zodiacs'] else 0 for i in range(len(data))])

        if len(signal) < 50:
            scores[z] = 0.0
            continue

        signal_series = pd.Series(signal)

        # 计算双尺度 EMA
        ema_12 = _compute_ema(signal_series, span=12)
        ema_50 = _compute_ema(signal_series, span=50)

        # trend_signal = EMA_12 - EMA_50
        trend_signal = ema_12 - ema_50

        # 计算 EMA_slope: 最近的变化率
        # 使用最后几个点的线性回归斜率
        n_points = min(10, len(trend_signal))
        recent = trend_signal.iloc[-n_points:]
        if n_points >= 2:
            x = np.arange(n_points)
            # 线性回归斜率
            slope = np.polyfit(x, recent.values, 1)[0]
        else:
            slope = 0.0

        # 计算 direction_strength
        # |EMA_12 - EMA_50| 的均值表示趋势强度
        direction_strength = float(np.abs(trend_signal.iloc[-5:]).mean())

        # 最终分数
        # slope 捕捉变化速度（加速度）
        # direction_strength 捕捉趋势强度
        raw_score = slope + direction_strength * 0.5
        scores[z] = raw_score

    # Z-score 标准化
    score_values = _z_score_normalize([scores[z] for z in ZODIACS])
    for i, z in enumerate(ZODIACS):
        scores[z] = score_values[i]

    return scores


def get_expert_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    """入口函数"""
    return compute_trend_scores(df, upto_idx)
