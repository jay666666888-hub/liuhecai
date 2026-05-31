#!/usr/bin/env python3
"""
澳门六合 - v21 周日效应 (已迁移到 features/sunday_effect.py)

此文件为保持旧 import 兼容而保留，实际逻辑已移至 features/sunday_effect.py

⚠️ 已废弃，请使用 V21Predictor (v21_adapter.py)
"""

from features.sunday_effect import SundayEffectFeature, compute_sunday_adjustment


def get_weekday(record):
    """获取开奖日期的星期几"""
    feature = SundayEffectFeature()
    return feature.get_weekday(record)


def predict_v21(records, upto, params, use_sunday_adjustment=True):
    """
    v21 预测（已废弃，使用 V21Predictor）

    兼容旧接口，调用 features/sunday_effect.py
    """
    from predictor.predictor import predict_top6

    history = records[:upto]
    prediction = predict_top6(history, params, "pattern_based")

    if use_sunday_adjustment:
        feature = SundayEffectFeature()
        is_sunday = feature.get_weekday(history[-1]) == 6 if history else False

        if is_sunday:
            # 周日调整
            sunday_scores = feature.compute(history)
            adjusted = {z: sunday_scores.get(z, 0) for z in prediction}
            prediction = sorted(adjusted.keys(), key=lambda z: adjusted[z], reverse=True)

    return prediction
