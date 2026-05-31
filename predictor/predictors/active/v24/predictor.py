#!/usr/bin/env python3
"""
澳门六合 - v24 多策略组合预测器

策略：v23 + gap + decay(0.90) 加权投票
权重：v23(2.5) + gap(0.5) + decay(0.5)
2026年测试：86/142 = 60.56%
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.base_predictor import BasePredictor, PredictionResult

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


class V24IntervalPredictor(BasePredictor):
    """v24多策略组合预测器 - 继承BasePredictor"""

    def __init__(self, version: str = "v24"):
        super().__init__(version)
        self.params = {
            "v23_weight": 2.5,
            "gap_weight": 0.5,
            "decay_weight": 0.5,
            "decay": 0.90
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

        # v23 策略
        scores_v23 = {z: 0.0 for z in ZODIACS}
        for i, r in enumerate(recs):
            z = r.get('zodiac') or r.get('特码生肖')
            weight = 0.85 ** (n - i - 1)
            scores_v23[z] += weight
        last_appear = {}
        for i, r in enumerate(recs):
            zodiac = r.get('zodiac') or r.get('特码生肖')
            last_appear[zodiac] = i
        gaps = {z: n - last_appear.get(z, -1) - 1 for z in ZODIACS}
        max_gap = max(gaps.values()) if gaps else 1
        for z in ZODIACS:
            scores_v23[z] += (gaps[z] / max_gap) * 4.0
        recent = recs[-30:]
        freq = {}
        for r in recent:
            z = r.get('zodiac') or r.get('特码生肖')
            freq[z] = freq.get(z, 0) + 1
        max_freq = max(freq.values()) if freq else 1
        for z in ZODIACS:
            scores_v23[z] += (freq.get(z, 0) / max_freq) * 1.5
        pred_v23 = sorted(ZODIACS, key=lambda z: scores_v23[z], reverse=True)[:top_k]

        # gap 策略
        pred_gap = sorted(ZODIACS, key=lambda z: gaps[z], reverse=True)[:top_k]

        # decay 策略
        scores_decay = {z: 0.0 for z in ZODIACS}
        for i, r in enumerate(recs):
            z = r.get('zodiac') or r.get('特码生肖')
            weight = self.params["decay"] ** (n - i - 1)
            scores_decay[z] += weight
        pred_decay = sorted(ZODIACS, key=lambda z: scores_decay[z], reverse=True)[:top_k]

        # 加权投票
        vote_scores = {z: 0.0 for z in ZODIACS}
        weights = [
            (pred_v23, self.params["v23_weight"]),
            (pred_gap, self.params["gap_weight"]),
            (pred_decay, self.params["decay_weight"])
        ]
        for pred, weight in weights:
            for rank, z in enumerate(pred):
                vote_scores[z] += (top_k - rank) * weight

        prediction = sorted(ZODIACS, key=lambda z: vote_scores[z], reverse=True)[:top_k]

        return PredictionResult(
            prediction=prediction,
            scores=vote_scores,
            metadata={
                "strategy": "v24_multi_strategy_vote",
                "params": self.params,
                "history_len": n,
                "component_predictions": {
                    "v23": pred_v23,
                    "gap": pred_gap,
                    "decay": pred_decay
                }
            }
        )


def predict_v23(recs, top_k=6):
    """v23策略 - 衰减 + 间隔 + 频率"""
    n = len(recs)
    scores = {z: 0 for z in ZODIACS}

    # 衰减频率
    for i, r in enumerate(recs):
        z = r.get('zodiac') or r.get('特码生肖')
        weight = 0.85 ** (n - i - 1)
        scores[z] += weight

    # 间隔比率
    last_appear = {}
    for i, r in enumerate(recs):
        zodiac = r.get('zodiac') or r.get('特码生肖')
        last_appear[zodiac] = i
    gaps = {z: n - last_appear.get(z, -1) - 1 for z in ZODIACS}
    max_gap = max(gaps.values()) if gaps else 1
    for z in ZODIACS:
        scores[z] += (gaps[z] / max_gap) * 4.0

    # 近期频率
    recent = recs[-30:]
    freq = {}
    for r in recent:
        z = r.get('zodiac') or r.get('特码生肖')
        freq[z] = freq.get(z, 0) + 1
    max_freq = max(freq.values()) if freq else 1
    for z in ZODIACS:
        scores[z] += (freq.get(z, 0) / max_freq) * 1.5

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_gap(recs, top_k=6):
    """纯gap策略"""
    n = len(recs)
    last_appear = {}
    for i, r in enumerate(recs):
        last_appear[r.get('zodiac') or r.get('特码生肖')] = i
    gaps = {z: n - last_appear.get(z, -1) - 1 for z in ZODIACS}
    return [z for z, g in sorted(gaps.items(), key=lambda x: -x[1])][:top_k]


def predict_decay(recs, decay=0.90, top_k=6):
    """衰减频率策略"""
    n = len(recs)
    scores = {z: 0 for z in ZODIACS}
    for i, r in enumerate(recs):
        z = r.get('zodiac') or r.get('特码生肖')
        weight = decay ** (n - i - 1)
        scores[z] += weight
    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_v24(recs, top_k=6):
    """v24多策略组合 - 加权投票

    权重分配：
    - v23: 2.5 (最高权重，v23本身已达59.86%)
    - gap: 0.5
    - decay(0.90): 0.5
    """
    # 各策略预测
    pred_v23 = predict_v23(recs)
    pred_gap = predict_gap(recs)
    pred_decay = predict_decay(recs, 0.90)

    # 投票得分
    vote_scores = {z: 0 for z in ZODIACS}
    weights = [(pred_v23, 2.5), (pred_gap, 0.5), (pred_decay, 0.5)]

    for pred, weight in weights:
        for rank, z in enumerate(pred):
            vote_scores[z] += (top_k - rank) * weight

    return [z for z, s in sorted(vote_scores.items(), key=lambda x: -x[1])][:top_k]


def predict(records, idx, params=None):
    """预测接口"""
    history = records[:idx]
    return predict_v24(history, top_k=6)


if __name__ == '__main__':
    import json

    with open('/mnt/c/Users/Admin/liuhecai/liuhecai_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = [{'issue': item['期号'], 'zodiac': item['特码生肖']} for item in data]
    records = sorted(records, key=lambda x: x['issue'])

    # 2026年测试
    records_2026 = [r for r in records if str(r['issue']).startswith('2026')]
    records_2025 = [r for r in records if str(r['issue']).startswith('2025')]

    hits = 0
    total = 0
    for idx in range(len(records_2026)):
        train = records_2025 + records_2026[:idx] if idx > 0 else records_2025
        actual = records_2026[idx]['zodiac']
        pred = predict_v24(train)
        if actual in pred:
            hits += 1
        total += 1

    print(f"v24 2026年测试: {hits}/{total} = {hits/total*100:.2f}%")

    # 全量测试
    hits_all = 0
    total_all = 0
    for i in range(100, len(records)):
        pred = predict_v24(records[:i])
        if records[i]['zodiac'] in pred:
            hits_all += 1
        total_all += 1
    print(f"v24 全量: {hits_all}/{total_all} = {hits_all/total_all*100:.2f}%")