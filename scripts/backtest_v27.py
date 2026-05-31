#!/usr/bin/env python3
"""
V27 平特一肖 - 回测写入账本（直接写入Dashboard数据源）
"""
import sys, os, json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/mnt/c/Users/Admin/liuhecai")
sys.path.insert(0, str(BASE_DIR))

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.predictors.active.v27.predictor import V27Predictor

STORAGE_DIR = BASE_DIR / "storage"
AGGREGATED_LIVE = STORAGE_DIR / "aggregated_live.jsonl"

def backtest_v27():
    records = get_all_records([2024, 2025, 2026])
    hist = build_standard_records(records)
    print(f'总数据: {len(hist)}期')

    pred = V27Predictor()
    version = "v27"
    params = pred.params
    lookback = params.get('lookback', 75)

    results = []
    now = datetime.now().isoformat()

    for i in range(lookback, len(hist)):
        history = hist[:i]
        cur = hist[i]
        actual_zodiac_list = cur.get("开奖生肖", [])
        actual = actual_zodiac_list[0] if actual_zodiac_list else None
        issue = cur.get("期号")

        result = pred.predict(history)
        predicted = result.prediction[0] if result.prediction else None
        hit = predicted in actual_zodiac_list if predicted and actual_zodiac_list else False

        record = {
            "id": f"{issue}_{version}_backtest",
            "issue": issue,
            "version": version,
            "model": "v27_walk_forward_optimal",
            "strategy": "walk_forward_optimal",
            "prediction": [predicted],
            "actual": actual,
            "actual_list": actual_zodiac_list,
            "hit": hit,
            "created_at": now,
            "source": "backtest",
            "status": "resolved",
            "play_type": "pingte_yixiao",
            "scores": result.scores
        }
        results.append(record)

    # 写入 Dashboard 数据源（通过 storage 层安全接口）
    from storage import write_batch_ledger
    write_batch_ledger(results, model_type="pingte_yixiao")

    # 统计
    hits = sum(1 for r in results if r.get("hit"))
    total = len(results)
    hit_rate = hits / total if total > 0 else 0

    print(f'回测写入: {total}期 -> {AGGREGATED_LIVE}')
    print(f'命中: {hits}/{total} = {hit_rate*100:.2f}%')

    # 更新 version_book/v27/metadata.json
    version_dir = BASE_DIR / "version_book" / version
    version_dir.mkdir(parents=True, exist_ok=True)
    
    metadata = {
        "version": version,
        "strategy_type": "pingte_yixiao",
        "play_type": "pingte_yixiao",
        "params": params,
        "notes": f"平特一肖 - Walk-Forward验证{hit_rate*100:.2f}%，最优参数",
        "frozen": False,
        "created_at": "2026-05-26T00:00:00.000000",
        "updated_at": now,
        "status": "active",
        "backtest": {
            "total": total,
            "hits": hits,
            "hit_rate": hit_rate
        }
    }
    with open(version_dir / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f'Metadata更新: {version_dir / "metadata.json"}')
    return total, hits, hit_rate

if __name__ == '__main__':
    backtest_v27()
