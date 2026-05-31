#!/usr/bin/env python3
"""比较预测器输出和ledger记录"""
import json

# 加载ledger记录
with open('version_book/v26/backtest_ledger.jsonl', 'r') as f:
    ledger = {}
    for line in f:
        r = json.loads(line)
        ledger[r['issue']] = r

# 运行预测器
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.predictors.active.v26.predictor import V26Predictor

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)

predictor = V26Predictor()

# 检查前20期
print("前20期预测对比:")
for i in range(16, 36):
    issue = hist[i]['期号']
    result = predictor.predict(hist[:i])
    pred = result.prediction[0]
    
    ledger_pred = ledger.get(issue, {}).get('prediction', ['N/A'])
    ledger_hit = ledger.get(issue, {}).get('hit', 'N/A')
    
    actual = hist[i].get('开奖生肖', [])
    match = "✓" if pred == ledger_pred[0] else "✗"
    print(f"{issue}: predictor={pred}, ledger={ledger_pred}, match={match}, hit={ledger_hit}, actual={actual[0] if actual else 'N/A'}")
