#!/usr/bin/env python3
"""
澳门六合 - 新特征预测器 v17
特征：五行 + 相冲 + 相合 + 原始pattern
"""

import random
import json
import os
from datetime import datetime
from typing import Dict, List
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, BASE_DIR)

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.animal_mapper import ZODIAC_WUXING, ZODIAC_SHENGKE, WUXING_XIANGSHENG, get_zodiac_wuxing, get_zodiac_shengke


def build_wuxing_cache(records: List[Dict], upto: int) -> Dict:
    """构建含五行特征的缓存"""
    zodiacs = sorted(set(r["特码生肖"] for r in records))
    cache = {}

    for z in zodiacs:
        positions = [i for i in range(upto) if records[i]["特码生肖"] == z]
        gaps = [positions[i+1] - positions[i] - 1 for i in range(len(positions) - 1)] if len(positions) > 1 else []
        last_gap = upto - positions[-1] - 1 if positions else 999

        cache[z] = {
            "gap": last_gap,
            "avg_gap": sum(gaps) / len(gaps) if gaps else 12,
            "recent10": sum(1 for i in range(max(0, upto-10), upto) if records[i]["特码生肖"] == z),
            "recent20": sum(1 for i in range(max(0, upto-20), upto) if records[i]["特码生肖"] == z),
            "streak": 0,
            "positions": positions,
            "wuxing": get_zodiac_wuxing(z),
        }

        # 计算连出现
        for i in range(upto - 1, -1, -1):
            if records[i]["特码生肖"] == z:
                cache[z]["streak"] += 1
            else:
                break

    return cache


def predict_wuxing_enhanced(records: List[Dict], params: Dict) -> List[str]:
    """五行增强预测"""
    n = len(records)
    cache = build_wuxing_cache(records, n)
    zodiacs = list(cache.keys())
    lookback = params.get("lookback", 11)

    scores = {}
    for z in zodiacs:
        c = cache[z]
        w = c["wuxing"]

        # ===== 基础特征（原始pattern）=====
        positions = [i for i in range(n) if records[i]["特码生肖"] == z]
        if len(positions) < 3:
            pattern_score = 0.5
        else:
            pos = positions[-lookback:] if len(positions) > lookback else positions
            intervals = [pos[i] - pos[i+1] for i in range(len(pos)-1)]

            alt_mode = params.get("alt_mode", "trend")
            if alt_mode == "strict":
                alt_score = sum(1 for i in range(len(intervals)-1) if intervals[i] > intervals[i+1])
                pattern_ratio = alt_score / max(len(intervals)-1, 1)
            else:
                if len(intervals) >= 3:
                    trend_count = sum(1 for i in range(len(intervals)-1) if intervals[i] > intervals[i+1])
                    pattern_ratio = trend_count / (len(intervals) - 1)
                else:
                    pattern_ratio = 0.5

            current_gap = n - positions[0] - 1
            trend = intervals[0] - intervals[1] if len(intervals) >= 2 else 0
            avg_int = sum(intervals) / len(intervals) if intervals else 12
            variance = sum((x - avg_int) ** 2 for x in intervals) / len(intervals) if intervals else 0

            pattern_score = (
                pattern_ratio * params.get("pattern_weight", 1.45) +
                min(current_gap, 50) * params.get("gap_weight", 0.098) +
                trend * params.get("trend_weight", 0.267) +
                (1 / (1 + variance)) * params.get("variance_weight", 0.177)
            )

        # ===== 五行特征 =====
        # 同五行近期出现多的倾向于少出现（均值回归）
        wuxing_count = sum(1 for zz in cache if cache[zz]["wuxing"] == w)
        wuxing_gap = 0
        for zz in cache:
            if cache[zz]["wuxing"] == w:
                wuxing_gap = max(wuxing_gap, cache[zz]["gap"])

        wuxing_score = min(wuxing_gap, 30) / 30 * params.get("wuxing_weight", 0.3)

        # ===== 相冲特征 =====
        # 相冲的生肖倾向于不同时出现
        shengke = get_zodiac_shengke(z)
        shengke_gap = cache.get(shengke, {}).get("gap", 0)
        shengke_score = min(shengke_gap, 20) / 20 * params.get("shengke_weight", 0.2)

        # ===== 综合评分 =====
        scores[z] = (
            pattern_score * params.get("base_weight", 0.6) +
            wuxing_score * params.get("wuxing_weight", 0.2) +
            shengke_score * params.get("shengke_weight", 0.2)
        )

    ranked = sorted(zodiacs, key=lambda z: scores[z], reverse=True)
    return ranked[:6]


def evaluate_params(records: List[Dict], params: Dict) -> Dict:
    """评估参数"""
    lookback = params.get("lookback", 11)
    n = len(records)

    hits = 0
    streak = 0
    max_streak = 0
    results = []

    for i in range(lookback, n):
        history = records[:i]
        top6 = predict_wuxing_enhanced(history, params)
        actual = records[i]["特码生肖"]
        hit = actual in top6

        if hit:
            hits += 1
            streak = 0
        else:
            streak += 1
            max_streak = max(max_streak, streak)
        results.append({"issue": records[i]["期号"], "hit": hit})

    hit_rate = hits / (n - lookback) if n > lookback else 0

    recent_100 = results[-100:] if len(results) >= 100 else results
    hit_rate_100 = sum(1 for r in recent_100 if r["hit"]) / len(recent_100) if recent_100 else 0
    recent_50 = results[-50:] if len(results) >= 50 else results
    hit_rate_50 = sum(1 for r in recent_50 if r["hit"]) / len(recent_50) if recent_50 else 0

    return {
        "hit_rate": hit_rate,
        "hit_rate_100": hit_rate_100,
        "hit_rate_50": hit_rate_50,
        "max_streak": max_streak,
        "total": n - lookback
    }


def random_params() -> Dict:
    """生成随机参数"""
    return {
        "lookback": random.randint(5, 20),
        "pattern_weight": round(random.uniform(0.5, 5.0), 3),
        "gap_weight": round(random.uniform(0.01, 0.25), 3),
        "trend_weight": round(random.uniform(0.01, 0.6), 3),
        "variance_weight": round(random.uniform(0.05, 0.6), 3),
        "alt_mode": random.choice(["strict", "trend"]),
        "base_weight": round(random.uniform(0.3, 0.8), 2),
        "wuxing_weight": round(random.uniform(0.1, 0.4), 2),
        "shengke_weight": round(random.uniform(0.1, 0.4), 2),
    }


def save_ledger(version: str, records: List[Dict], params: Dict):
    """保存回测账本"""
    version_dir = os.path.join(BASE_DIR, "version_book", version)
    os.makedirs(version_dir, exist_ok=True)
    ledger_path = os.path.join(version_dir, "backtest_ledger.jsonl")

    lookback = params.get("lookback", 11)
    n = len(records)

    with open(ledger_path, 'w', encoding='utf-8') as f:
        for i in range(lookback, n):
            history = records[:i]
            top6 = predict_wuxing_enhanced(history, params)
            actual = records[i]["特码生肖"]
            hit = actual in top6
            record = {
                "id": f"{records[i]['期号']}_{version}",
                "issue": records[i]["期号"],
                "version": version,
                "model": f"{version}_wuxing",
                "prediction": top6,
                "actual": actual,
                "hit": hit,
                "created_at": datetime.now().isoformat(),
                "source": "backtest"
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  账本已保存: {ledger_path}")


def update_version_book(version: str, params: Dict, stats: Dict, notes: str):
    """更新版本账本"""
    version_file = os.path.join(BASE_DIR, "version_book", f"{version}.json")
    book = {
        "version": version,
        "strategy_type": "wuxing_enhanced",
        "params": params,
        "notes": notes,
        "backtest": {
            "backtest_hit_rate": stats["hit_rate"],
            "backtest_recent_100": stats["hit_rate_100"],
            "backtest_recent_50": stats["hit_rate_50"],
            "backtest_total": stats["total"],
            "backtest_hits": int(stats["hit_rate"] * stats["total"]),
            "backtest_max_streak": stats["max_streak"],
            "backtest_at": datetime.now().isoformat()
        },
        "live": {"live_predictions": 0, "live_results": 0, "live_hits": 0, "live_hit_rate": 0, "live_max_streak": 0},
        "frozen": False,
        "updated_at": datetime.now().isoformat()
    }
    with open(version_file, 'w', encoding='utf-8') as f:
        json.dump(book, f, ensure_ascii=False, indent=2)
    print(f"  版本账本已更新: {version_file}")


def main():
    print("=" * 60)
    print("澳门六合 - 五行增强预测器 v17")
    print("新特征：五行 + 相冲")
    print("=" * 60)

    print("\n加载数据...")
    records = get_all_records([2024, 2025, 2026])
    standard = build_standard_records(records)
    print(f"数据加载完成: {len(standard)} 期")

    print("\n开始优化 (10000次迭代)...")

    best_params = None
    best_score = -1
    best_stats = None
    iterations = 10000

    for i in range(iterations):
        if i % 1000 == 0:
            print(f"  进度: {i}/{iterations}", flush=True)

        params = random_params()
        stats = evaluate_params(standard, params)

        streak_penalty = max(0, stats["max_streak"] - 5) * 0.02
        score = stats["hit_rate"] - streak_penalty

        if score > best_score:
            best_score = score
            best_params = params
            best_stats = stats
            print(f"  [{i}] 新最佳! 命中率:{stats['hit_rate']*100:.2f}% 连错:{stats['max_streak']}")

    print(f"\n最佳参数:")
    print(json.dumps(best_params, indent=2))
    print(f"\n统计:")
    print(f"  命中率: {best_stats['hit_rate']*100:.2f}%")
    print(f"  近100期: {best_stats['hit_rate_100']*100:.2f}%")
    print(f"  近50期: {best_stats['hit_rate_50']*100:.2f}%")
    print(f"  最高连错: {best_stats['max_streak']}")

    print("\n生成 v17 回测账本...")
    save_ledger("v17", standard, best_params)
    update_version_book("v17", best_params, best_stats, "五行增强策略: 五行相生相克 + 相冲 + pattern")

    print("\n" + "="*60)
    print("优化完成!")
    print("="*60)


if __name__ == "__main__":
    main()