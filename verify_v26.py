#!/usr/bin/env python3
"""验证V26当前性能"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.predictors.active.v26.predictor import V26Predictor

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f"数据: {len(hist)}期")

predictor = V26Predictor()
print(f"参数: {predictor.params}")

# 计算回测
hits = 0
total = 0
for i in range(16, len(hist)):
    result = predictor.predict(hist[:i])
    pred = result.prediction[0]
    actual_list = hist[i].get('开奖生肖', [])
    hit = pred in actual_list
    if hit:
        hits += 1
    total += 1

rate = hits / total if total > 0 else 0
print(f"回测: {hits}/{total} = {rate:.4f}")
