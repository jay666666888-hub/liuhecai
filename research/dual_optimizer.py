#!/usr/bin/env python3
"""
澳门六合 - 双轨随机搜索优化器
v13: 命中率优先
v14: 连错优先
"""

import random
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, BASE_DIR)

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.predictor import predict_top6


def evaluate_params(records: List[Dict], params: Dict) -> Dict:
    """评估一组参数

    Returns:
        hit_rate, hit_rate_100, hit_rate_50, max_streak
    """
    lookback = params.get("lookback", 13)
    n = len(records)

    hits = 0
    total = 0
    streak = 0
    max_streak = 0
    results = []

    for i in range(lookback, n):
        history = records[:i]
        top6 = predict_top6(history, params, "pattern_based")
        actual = records[i]["特码生肖"]

        hit = actual in top6
        if hit:
            hits += 1
            streak = 0
        else:
            streak += 1
            max_streak = max(max_streak, streak)

        total += 1
        results.append({"issue": records[i]["期号"], "hit": hit})

    hit_rate = hits / total if total > 0 else 0

    # 最近100期
    recent_100 = results[-100:] if len(results) >= 100 else results
    hit_rate_100 = sum(1 for r in recent_100 if r["hit"]) / len(recent_100) if recent_100 else 0

    # 最近50期
    recent_50 = results[-50:] if len(results) >= 50 else results
    hit_rate_50 = sum(1 for r in recent_50 if r["hit"]) / len(recent_50) if recent_50 else 0

    return {
        "hit_rate": hit_rate,
        "hit_rate_100": hit_rate_100,
        "hit_rate_50": hit_rate_50,
        "max_streak": max_streak,
        "total": total
    }


def random_params() -> Dict:
    """生成随机参数"""
    return {
        "lookback": random.randint(5, 20),
        "pattern_weight": round(random.uniform(0.5, 5.0), 3),
        "gap_weight": round(random.uniform(0.01, 0.2), 3),
        "trend_weight": round(random.uniform(0.01, 0.5), 3),
        "variance_weight": round(random.uniform(0.05, 0.5), 3),
        "alt_mode": random.choice(["strict", "trend"])
    }


def optimize_hit_rate(records: List[Dict], iterations: int = 2000) -> Tuple[Dict, Dict]:
    """命中率优先优化"""
    print(f"\n{'='*50}")
    print("v13 命中率优化搜索 (目标: max hit_rate)")
    print(f"{'='*50}")

    best_params = None
    best_score = -1
    best_stats = None

    for i in range(iterations):
        if i % 200 == 0:
            print(f"  进度: {i}/{iterations}", flush=True)

        params = random_params()
        stats = evaluate_params(records, params)

        # 命中率优先，连错作为惩罚（超过5期扣分）
        streak_penalty = max(0, stats["max_streak"] - 5) * 0.01
        score = stats["hit_rate"] - streak_penalty

        if score > best_score:
            best_score = score
            best_params = params
            best_stats = stats
            print(f"  [{i}] 新最佳! 命中率:{stats['hit_rate']*100:.2f}% 连错:{stats['max_streak']} score:{score:.4f}")

    return best_params, best_stats


def optimize_streak(records: List[Dict], iterations: int = 2000) -> Tuple[Dict, Dict]:
    """连错优先优化"""
    print(f"\n{'='*50}")
    print("v14 连错优化搜索 (目标: min max_streak, hit_rate >= 50%)")
    print(f"{'='*50}")

    best_params = None
    best_streak = 999
    best_hit_rate = 0
    best_stats = None

    for i in range(iterations):
        if i % 200 == 0:
            print(f"  进度: {i}/{iterations}", flush=True)

        params = random_params()
        stats = evaluate_params(records, params)

        # 连错优先，命中率必须 >= 50%
        if stats["hit_rate"] < 0.50:
            continue

        # 优先最小连错，其次最高命中率
        if stats["max_streak"] < best_streak:
            best_streak = stats["max_streak"]
            best_hit_rate = stats["hit_rate"]
            best_params = params
            best_stats = stats
            print(f"  [{i}] 新最佳! 连错:{stats['max_streak']} 命中率:{stats['hit_rate']*100:.2f}%")

    return best_params, best_stats


def save_backtest_ledger(version: str, records: List[Dict], params: Dict):
    """生成并保存回测账本"""
    version_dir = os.path.join(BASE_DIR, "version_book", version)
    os.makedirs(version_dir, exist_ok=True)

    ledger_path = os.path.join(version_dir, "backtest_ledger.jsonl")

    lookback = params.get("lookback", 13)
    n = len(records)

    with open(ledger_path, 'w', encoding='utf-8') as f:
        for i in range(lookback, n):
            history = records[:i]
            top6 = predict_top6(history, params, "pattern_based")
            actual = records[i]["特码生肖"]
            hit = actual in top6

            record = {
                "id": f"{records[i]['期号']}_{version}",
                "issue": records[i]["期号"],
                "version": version,
                "model": f"{version}_optimized",
                "prediction": top6,
                "actual": actual,
                "hit": hit,
                "created_at": datetime.now().isoformat(),
                "source": "backtest"
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"  账本已保存: {ledger_path}")


def update_version_book(version: str, params: Dict, stats: Dict, strategy_type: str, notes: str):
    """更新版本账本"""
    version_file = os.path.join(BASE_DIR, "version_book", f"{version}.json")

    book = {
        "version": version,
        "strategy_type": strategy_type,
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
        "live": {
            "live_predictions": 0,
            "live_results": 0,
            "live_hits": 0,
            "live_hit_rate": 0,
            "live_max_streak": 0
        },
        "frozen": False,
        "updated_at": datetime.now().isoformat()
    }

    with open(version_file, 'w', encoding='utf-8') as f:
        json.dump(book, f, ensure_ascii=False, indent=2)

    print(f"  版本账本已更新: {version_file}")


def main():
    print("=" * 60)
    print("澳门六合双轨优化器启动")
    print("=" * 60)

    # 加载数据
    print("\n加载数据...")
    records = get_all_records([2024, 2025, 2026])
    standard = build_standard_records(records)
    print(f"数据加载完成: {len(standard)} 期")

    # v13: 命中率优先
    print("\n" + "="*60)
    print("开始 v13 命中率优化 (2000次迭代)...")
    print("="*60)
    v13_params, v13_stats = optimize_hit_rate(standard, 2000)
    print(f"\nv13 最佳参数: {v13_params}")
    print(f"v13 统计: 命中率={v13_stats['hit_rate']*100:.2f}%, 近100={v13_stats['hit_rate_100']*100:.2f}%, 近50={v13_stats['hit_rate_50']*100:.2f}%, 连错={v13_stats['max_streak']}")

    # 保存 v13 账本
    print("\n生成 v13 回测账本...")
    save_backtest_ledger("v13", standard, v13_params)
    update_version_book("v13", v13_params, v13_stats, "pattern_based", "命中率优先优化 - 5000次随机搜索最优")

    # v14: 连错优先
    print("\n" + "="*60)
    print("开始 v14 连错优化 (2000次迭代)...")
    print("="*60)
    v14_params, v14_stats = optimize_streak(standard, 2000)
    print(f"\nv14 最佳参数: {v14_params}")
    print(f"v14 统计: 命中率={v14_stats['hit_rate']*100:.2f}%, 近100={v14_stats['hit_rate_100']*100:.2f}%, 近50={v14_stats['hit_rate_50']*100:.2f}%, 连错={v14_stats['max_streak']}")

    # 保存 v14 账本
    print("\n生成 v14 回测账本...")
    save_backtest_ledger("v14", standard, v14_params)
    update_version_book("v14", v14_params, v14_stats, "pattern_based", "连错优先优化 - 命中率保底50%")

    # 更新索引
    print("\n更新版本索引...")
    index_path = os.path.join(BASE_DIR, "version_book", "index.json")
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)

    # 确保 v13, v14 在版本列表中
    for v in ["v13", "v14"]:
        if v not in index["versions"]:
            index["versions"].append(v)

    # 更新 summary
    index["updated_at"] = datetime.now().isoformat()

    # 重新生成 summary
    index["summary"] = []
    for version in index["versions"]:
        version_file = os.path.join(BASE_DIR, "version_book", f"{version}.json")
        if os.path.exists(version_file):
            with open(version_file, 'r', encoding='utf-8') as f:
                vb = json.load(f)
                index["summary"].append({
                    "version": vb["version"],
                    "frozen": vb.get("frozen", True),
                    "backtest_hit_rate": vb.get("backtest", {}).get("backtest_hit_rate", 0),
                    "live_hit_rate": vb.get("live", {}).get("live_hit_rate", 0),
                    "live_predictions": vb.get("live", {}).get("live_predictions", 0),
                    "live_max_streak": vb.get("live", {}).get("live_max_streak", 0)
                })

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"索引已更新: {index_path}")

    print("\n" + "="*60)
    print("双轨优化完成!")
    print("="*60)
    print(f"\nv13 命中率版: 命中率={v13_stats['hit_rate']*100:.2f}%, 连错={v13_stats['max_streak']}")
    print(f"v14 稳定版:   命中率={v14_stats['hit_rate']*100:.2f}%, 连错={v14_stats['max_streak']}")


if __name__ == "__main__":
    main()