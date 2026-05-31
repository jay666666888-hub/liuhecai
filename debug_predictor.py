#!/usr/bin/env python3
"""调试V26预测器"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.predictors.active.v26.predictor import V26Predictor

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)

predictor = V26Predictor()

# 测试几个特定的period
for i in [100, 200, 300, 400, 500]:
    result = predictor.predict(hist[:i])
    pred = result.prediction[0]
    actual = hist[i].get('开奖生肖', [])
    print(f"Period {i}: pred={pred}, actual={actual}, hit={pred in actual}")
    print(f"  Scores: {dict(sorted(result.scores.items(), key=lambda x: -x[1])[:3])}")
