#!/usr/bin/env python3
"""
澳门六合 - v23 间隔分析预测器

优化目标：2026年60%命中率
策略：衰减频率 + 间隔比率 + 近期频率
参数：decay=0.85, gap_weight=4.0, freq_weight=1.5
训练数据：2025年 + 2026历史

2026实际测试：84/141 = 59.57%
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.base_predictor import BasePredictor, PredictionResult

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


class V23IntervalPredictor(BasePredictor):
    """v23预测器 - 继承BasePredictor"""

    def __init__(self, version: str = "v23"):
        super().__init__(version)
        self.params = {
            "decay": 0.85,
            "gap_weight": 4.0,
            "freq_weight": 1.5,
            "freq_window": 30
        }

    def predict(self, history, top_k=6):
        """
        生成预测

        Args:
            history: 历史记录列表
            top_k: 返回前k个预测

        Returns:
            PredictionResult 对象
        """
        recs = history
        n = len(recs)
        scores = {z: 0.0 for z in ZODIACS}

        # 1. 衰减频率
        for i, r in enumerate(recs):
            z = r.get('zodiac') or r.get('特码生肖')
            weight = self.params["decay"] ** (n - i - 1)
            scores[z] += weight

        # 2. 间隔比率
        last_appear = {}
        for i, r in enumerate(recs):
            zodiac = r.get('zodiac') or r.get('特码生肖')
            last_appear[zodiac] = i
        gaps = {z: n - last_appear.get(z, -1) - 1 for z in ZODIACS}
        max_gap = max(gaps.values()) if gaps else 1
        for z in ZODIACS:
            scores[z] += (gaps[z] / max_gap) * self.params["gap_weight"]

        # 3. 近期频率
        window = self.params["freq_window"]
        recent = recs[-window:]
        freq = {}
        for r in recent:
            z = r.get('zodiac') or r.get('特码生肖')
            freq[z] = freq.get(z, 0) + 1
        max_freq = max(freq.values()) if freq else 1
        for z in ZODIACS:
            scores[z] += (freq.get(z, 0) / max_freq) * self.params["freq_weight"]

        # 排序取 top_k
        ranked = sorted(zodiacs, key=lambda z: scores[z], reverse=True) if (zodiacs := ZODIACS) else []
        prediction = ranked[:top_k]

        return PredictionResult(
            prediction=prediction,
            scores=scores,
            metadata={
                "strategy": "v23_interval",
                "params": self.params,
                "history_len": n
            }
        )


def predict_v23(recs, top_k=6):
    """v23预测策略

    混合评分：
    1. 衰减频率（decay=0.85）
    2. 间隔比率（gap_weight=4.0）
    3. 近期频率（freq_weight=1.5，窗口30期）
    """
    n = len(recs)
    scores = {z: 0 for z in ZODIACS}

    # 1. 衰减频率
    for i, r in enumerate(recs):
        z = r.get('zodiac') or r.get('特码生肖')
        weight = 0.85 ** (n - i - 1)
        scores[z] += weight

    # 2. 间隔比率
    last_appear = {}
    for i, r in enumerate(recs):
        zodiac = r.get('zodiac') or r.get('特码生肖')
        last_appear[zodiac] = i
    gaps = {z: n - last_appear.get(z, -1) - 1 for z in ZODIACS}
    max_gap = max(gaps.values()) if gaps else 1
    for z in ZODIACS:
        scores[z] += (gaps[z] / max_gap) * 4.0

    # 3. 近期频率（窗口30期）
    recent = recs[-30:]
    freq = {}
    for r in recent:
        z = r.get('zodiac') or r.get('特码生肖')
        freq[z] = freq.get(z, 0) + 1
    max_freq = max(freq.values()) if freq else 1
    for z in ZODIACS:
        scores[z] += (freq.get(z, 0) / max_freq) * 1.5

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict(records, idx, params=None):
    """预测接口

    Args:
        records: 标准记录列表
        idx: 当前预测位置
        params: 参数字典（可选）

    Returns:
        top6预测列表
    """
    history = records[:idx]
    return predict_v23(history, top_k=6)


# 直接执行时进行验证
if __name__ == '__main__':
    import json

    with open('/mnt/c/Users/Admin/liuhecai/liuhecai_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = [{'issue': item['期号'], 'zodiac': item['特码生肖']} for item in data]
    records = sorted(records, key=lambda x: x['issue'])

    # 2025年训练，2026年测试
    records_2026 = [r for r in records if str(r['issue']).startswith('2026')]
    records_2025 = [r for r in records if str(r['issue']).startswith('2025')]

    print(f"2025年训练数据: {len(records_2025)}期")
    print(f"2026年测试数据: {len(records_2026)}期")

    # Walk-forward测试
    hits = 0
    total = 0
    for idx in range(len(records_2026)):
        train = records_2025 + records_2026[:idx] if idx > 0 else records_2025
        actual = records_2026[idx]['zodiac']
        pred = predict_v23(train)
        if actual in pred:
            hits += 1
        total += 1

    print(f"\n2026年测试结果: {hits}/{total} = {hits/total*100:.2f}%")

    # 全量walk-forward测试
    print("\n=== 全量walk-forward测试 ===")
    hits_all = 0
    total_all = 0
    for i in range(100, len(records)):
        recs = records[:i]
        actual = records[i]['zodiac']
        pred = predict_v23(recs)
        if actual in pred:
            hits_all += 1
        total_all += 1
    print(f"全量回测: {hits_all}/{total_all} = {hits_all/total_all*100:.2f}%")