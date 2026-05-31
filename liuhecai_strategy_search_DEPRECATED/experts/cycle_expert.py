"""CycleExpert - 频域周期检测专家

允许特征:
- fft_peak_strength: FFT 峰值强度
- dominant_cycle_length: 主周期长度
- spectral_entropy: 归一化频谱熵
- cycle_phase: 当前相位

禁止特征:
- gap, trend, moving_average, streak

评分公式:
score = dominant_cycle_strength * (1 - entropy_norm)

核心原则:
CycleExpert 回答："这个序列是否存在稳定周期结构？"
而不是："这个周期有多好用于预测"
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


def _min_max_normalize(values: List[float]) -> List[float]:
    """Min-max 标准化到 [0, 1]"""
    arr = np.array(values)
    min_val = np.min(arr)
    max_val = np.max(arr)
    if max_val == min_val:
        return [0.5] * len(values)
    return ((arr - min_val) / (max_val - min_val)).tolist()


def compute_spectral_entropy(power_spectrum: np.ndarray) -> float:
    """
    计算频谱熵

    频谱熵衡量频谱的"平坦度"：
    - 高 entropy = 噪声-like（能量分散）= 无明显周期
    - 低 entropy = 强周期信号（能量集中在少数频率）
    """
    # 归一化频谱
    total = np.sum(power_spectrum)
    if total == 0:
        return 1.0  # 最大熵

    p = power_spectrum / total
    p = p[p > 0]  # 避免 log(0)

    entropy = -np.sum(p * np.log2(p))

    # 归一化到 [0, 1]（最大熵是 log2(n_freqs)）
    n = len(power_spectrum)
    max_entropy = np.log2(n) if n > 1 else 1.0
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

    return normalized_entropy


def compute_cycle_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    """
    计算 CycleExpert 评分

    评分公式:
    score = dominant_cycle_strength * (1 - entropy_norm)

    其中:
    - dominant_cycle_strength: FFT 峰值强度（归一化）
    - entropy_norm: 归一化频谱熵（归一化到 [0, 1]）
    """
    scores = {}

    for z in ZODIACS:
        # 获取该 zodiac 的出现位置（在 zodiacs 列表中）
        positions = []
        for row_idx in range(upto_idx):
            if z in df.iloc[row_idx]['zodiacs']:
                positions.append(row_idx)

        if len(positions) < 8:
            scores[z] = 0.0
            continue

        # 创建二进制信号
        max_idx = upto_idx
        signal = np.zeros(max_idx)
        for p in positions:
            if p < max_idx:
                signal[p] = 1.0

        # 计算 FFT
        fft = np.fft.fft(signal)
        power = np.abs(fft) ** 2
        freqs = np.fft.fftfreq(len(signal))

        # 只取正频率部分
        positive_freqs = freqs[:len(freqs) // 2]
        positive_power = power[:len(power) // 2]
        positive_power[0] = 0  # 移除 DC 分量

        if len(positive_power) == 0 or np.sum(positive_power) == 0:
            scores[z] = 0.0
            continue

        # 计算频谱熵
        entropy_norm = compute_spectral_entropy(positive_power)

        # 找主周期
        peak_idx = np.argmax(positive_power)
        dominant_freq = positive_freqs[peak_idx] if peak_idx < len(positive_freqs) else 0

        # dominant_cycle_strength: 峰值功率占总功率的比例
        peak_power = positive_power[peak_idx]
        total_power = np.sum(positive_power)
        dominant_cycle_strength = peak_power / total_power if total_power > 0 else 0

        # 计算 cycle_phase（当前位置在周期中的位置）
        if positions:
            last_pos = positions[-1]
            if dominant_freq > 0:
                # 周期长度
                period = 1.0 / dominant_freq
                # 相位：当前位置距离上一个周期起点的距离
                cycle_phase = (upto_idx - last_pos) / period if period > 0 else 0.5
                cycle_phase = cycle_phase % 1.0  # 归一化到 [0, 1]
            else:
                cycle_phase = 0.5
        else:
            cycle_phase = 0.5

        # 计算最终分数
        # score = peak_strength * (1 - entropy_norm)
        # entropy_norm 高（噪声信号）→ (1 - entropy_norm) 低 → 降权
        # entropy_norm 低（周期信号）→ (1 - entropy_norm) 高 → 保持权重
        raw_score = dominant_cycle_strength * (1 - entropy_norm)

        scores[z] = raw_score

    # Z-score 标准化所有分数
    score_values = [scores[z] for z in ZODIACS]
    score_values_norm = _z_score_normalize(score_values)

    # 重新赋值为标准化后的分数
    for i, z in enumerate(ZODIACS):
        scores[z] = score_values_norm[i]

    return scores


def get_expert_scores(df: pd.DataFrame, upto_idx: int) -> Dict[str, float]:
    """入口函数"""
    return compute_cycle_scores(df, upto_idx)
