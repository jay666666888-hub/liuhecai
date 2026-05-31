#!/usr/bin/env python3
"""更新V26预测器参数"""
import json

# 新的最佳参数
new_params = {
    "lookback": 30,
    "gap_weight": 0.603,
    "freq_weight": 0.474,
    "streak_weight": 0.092,
    "trend_weight": 1.566,
    "variance_weight": 1.869
}

# 读取predictor.py
with open('predictor/predictors/active/v26/predictor.py', 'r') as f:
    content = f.read()

# 更新参数
old_params = '''self.params = {
            "lookback": 16,
            "gap_weight": 0.535,
            "freq_weight": 0.987,
            "streak_weight": 0.193,
            "trend_weight": 0.113,
            "variance_weight": 0.548
        }'''

new_params_str = '''self.params = {
            "lookback": 30,
            "gap_weight": 0.603,
            "freq_weight": 0.474,
            "streak_weight": 0.092,
            "trend_weight": 1.566,
            "variance_weight": 1.869
        }'''

content = content.replace(old_params, new_params_str)

with open('predictor/predictors/active/v26/predictor.py', 'w') as f:
    f.write(content)

print("Updated predictor.py with new params")

# 更新metadata.json
metadata = {
    "version": "v26",
    "strategy_type": "pingte_yixiao",
    "play_type": "pingte_yixiao",
    "params": new_params,
    "notes": "平特一肖 - 预测1个生肖，7码中包含即命中",
    "frozen": False,
    "created_at": "2026-05-25T16:10:00.000000",
    "updated_at": "2026-05-25T19:00:00.000000",
    "backtest": {"total": 861, "hits": 450, "hit_rate": 0.5230},
    "status": "active"
}

with open('predictor/predictors/active/v26/metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print("Updated metadata.json")
