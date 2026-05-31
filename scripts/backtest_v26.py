#!/usr/bin/env python3
"""
V26 平特一肖 - 全量回测并写入账本
"""
import sys, os, json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/mnt/c/Users/Admin/liuhecai")
sys.path.insert(0, str(BASE_DIR))

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.predictors.active.v26.predictor import V26Predictor

VERSION_BOOK_DIR = BASE_DIR / "version_book"

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

def backtest_v26():
    records = get_all_records([2024, 2025, 2026])
    hist = build_standard_records(records)
    print(f'总数据: {len(hist)}期')

    pred = V26Predictor()
    version = "v26"
    version_dir = VERSION_BOOK_DIR / version
    version_dir.mkdir(parents=True, exist_ok=True)
    backtest_file = version_dir / "backtest_ledger.jsonl"

    results = []
    now = datetime.now().isoformat()

    for i in range(16, len(hist)):  # lookback=16
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
            "model": "v26_gap_freq_trend_variance",
            "strategy": "gap_freq_trend_variance",
            "prediction": [predicted],
            "actual": actual,
            "actual_list": actual_zodiac_list,
            "hit": hit,
            "created_at": now,
            "source": "backtest",
            "status": "resolved",
            "scores": result.scores
        }
        results.append(record)

    # 写入账本
    with open(backtest_file, 'w', encoding='utf-8') as f:
        for rec in results:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 统计
    hits = sum(1 for r in results if r.get("hit"))
    total = len(results)
    hit_rate = hits / total if total > 0 else 0

    print(f'回测写入: {total}期')
    print(f'命中: {hits}/{total} = {hit_rate*100:.2f}%')

    # 更新 metadata
    metadata_file = version_dir / "metadata.json"
    metadata = {
        "version": version,
        "strategy_type": "pingte_yixiao",
        "play_type": "pingte_yixiao",
        "params": pred.params,
        "notes": "平特一肖 - 预测1个生肖，7码中包含即命中",
        "frozen": False,
        "created_at": "2026-05-25T16:10:00.000000",
        "updated_at": now,
        "backtest": {
            "total": total,
            "hits": hits,
            "hit_rate": hit_rate
        }
    }
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f'Metadata更新: {metadata_file}')

    return total, hits, hit_rate

if __name__ == '__main__':
    backtest_v26()