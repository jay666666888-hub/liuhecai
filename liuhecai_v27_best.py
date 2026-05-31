#!/usr/bin/env python3
"""
V27 平特一肖 - Walk-Forward最优参数
命中率: 54.40%
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.predictors.active.v26.predictor import V26Predictor

# 最佳参数 (54.4% in Walk-Forward)
best_params = {
    "lookback": 75,
    "gap_weight": -0.238,
    "freq_weight": 0.925,
    "streak_weight": -0.205,
    "trend_weight": 1.564,
    "variance_weight": 1.792
}

# 1. 更新V26为退役
v26_metadata = {
    "version": "v26",
    "status": "retired",
    "retire_reason": "被v27替代，v27 Walk-Forward验证54.4%",
    "notes": "平特一肖 - 预测1个生肖，7码中包含即命中",
    "created_at": "2026-05-25T16:10:00.000000",
    "updated_at": "2026-05-26T00:00:00.000000"
}

# 2. 创建V27
v27_dir = Path('predictor/predictors/active/v27')
v27_dir.mkdir(exist_ok=True)

v27_metadata = {
    "version": "v27",
    "status": "active",
    "strategy_type": "pingte_yixiao",
    "play_type": "pingte_yixiao",
    "params": best_params,
    "notes": "平特一肖 - Walk-Forward验证54.4%，最优参数",
    "frozen": False,
    "created_at": "2026-05-26T00:00:00.000000",
    "updated_at": "2026-05-26T00:00:00.000000"
}

with open('predictor/predictors/active/v26/metadata.json', 'w') as f:
    json.dump(v26_metadata, f, ensure_ascii=False, indent=2)
print("V26 已标记为退役")

with open(v27_dir / 'metadata.json', 'w') as f:
    json.dump(v27_metadata, f, ensure_ascii=False, indent=2)
print("V27 metadata.json 已创建")

# 3. 创建V27 predictor.py
v27_predictor = '''#!/usr/bin/env python3
"""
澳门六合 - v27 平特一肖预测器
Walk-Forward验证: 54.40%
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from predictor.base_predictor import BasePredictor, PredictionResult

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

class V27Predictor(BasePredictor):
    """平特一肖预测器 - Walk-Forward最优参数"""
    def __init__(self, version: str = "v27"):
        super().__init__(version)
        self.params = ''' + json.dumps(best_params, indent=4) + '''

    def _compute_features(self, window, z):
        positions = [idx for idx, r in enumerate(window) if r["特码生肖"] == z]
        if not positions:
            return {"gap": 999, "frequency": 0, "streak": 0, "trend": 0, "variance": 0}
        gap = len(window) - positions[-1] - 1
        frequency = len(positions)
        streak = 0
        for idx in range(len(window)-1, -1, -1):
            if window[idx]["特码生肖"] == z:
                streak += 1
            else:
                break
        if len(positions) >= 2:
            intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]
            trend = intervals[0] - intervals[1] if len(intervals) >= 2 else 0
        else:
            trend = 0
        if len(positions) >= 3:
            intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]
            avg_int = sum(intervals) / len(intervals)
            variance = sum((x - avg_int) ** 2 for x in intervals) / len(intervals)
        else:
            variance = 0
        return {"gap": gap, "frequency": frequency, "streak": streak, "trend": trend, "variance": variance}

    def predict(self, history, top_k=1):
        n = len(history)
        lookback = self.params["lookback"]
        window = history[max(0, n-lookback):n]
        scores = {}
        for z in ZODIACS:
            f = self._compute_features(window, z)
            gap_score = min(f["gap"], 50) / 50
            freq_score = f["frequency"] / lookback
            streak_score = min(f["streak"], 5) / 5
            trend_score = max(0, min(f["trend"], 10)) / 10
            variance_score = 1 / (1 + f["variance"] / 10)
            scores[z] = (
                gap_score * self.params["gap_weight"] +
                freq_score * self.params["freq_weight"] +
                streak_score * self.params["streak_weight"] +
                trend_score * self.params["trend_weight"] +
                variance_score * self.params["variance_weight"]
            )
        ranked = sorted(ZODIACS, key=lambda z: scores[z], reverse=True)
        prediction = [ranked[0]]
        return PredictionResult(
            prediction=prediction,
            scores=scores,
            metadata={"type": "pingte_yixiao", "version": "v27", "strategy": "walk_forward_optimal", "params": self.params, "play_type": "pingte_yixiao"}
        )
'''

with open(v27_dir / 'predictor.py', 'w') as f:
    f.write(v27_predictor)
print("V27 predictor.py 已创建")

# 4. 移动V26 predictor到retired
import shutil
retired_dir = Path('predictor/predictors/retired')
retired_dir.mkdir(exist_ok=True)
shutil.move('predictor/predictors/active/v26/predictor.py', retired_dir / 'v26_predictor.py')
print("V26 predictor.py 已移动到 retired")

# 5. 重新生成index
import predictor.index_generator as ig
ig.write_index()
print("\\nIndex已更新")
