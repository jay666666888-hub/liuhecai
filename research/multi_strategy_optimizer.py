#!/usr/bin/env python3
"""
澳门六合 - 多策略优化器
v15: 新特征 + Ensemble + 多模型
"""

import random
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, BASE_DIR)

from predictor.data_fetcher import get_all_records, build_standard_records


def build_enhanced_cache(records: List[Dict], upto: int) -> Dict:
    """增强特征缓存 - 包含新特征"""
    zodiacs = sorted(set(r["特码生肖"] for r in records))
    cache = {}

    n = upto
    for z in zodiacs:
        positions = [i for i in range(upto) if records[i]["特码生肖"] == z]
        gaps = [positions[i+1] - positions[i] - 1 for i in range(len(positions) - 1)] if len(positions) > 1 else []
        last_gap = upto - positions[-1] - 1 if positions else 999

        # 基本特征
        cache[z] = {
            "gap": last_gap,
            "avg_gap": sum(gaps) / len(gaps) if gaps else 12,
            "recent3": sum(1 for i in range(max(0, upto-3), upto) if records[i]["特码生肖"] == z),
            "recent5": sum(1 for i in range(max(0, upto-5), upto) if records[i]["特码生肖"] == z),
            "recent10": sum(1 for i in range(max(0, upto-10), upto) if records[i]["特码生肖"] == z),
            "recent20": sum(1 for i in range(max(0, upto-20), upto) if records[i]["特码生肖"] == z),
            "recent30": sum(1 for i in range(max(0, upto-30), upto) if records[i]["特码生肖"] == z),
            "streak": 0,
            "positions": positions,
        }

        # 计算连出现
        for i in range(upto - 1, -1, -1):
            if records[i]["特码生肖"] == z:
                cache[z]["streak"] += 1
            else:
                break

        # 新特征：冷热指数 (近期出现频率)
        cache[z]["hot_score"] = cache[z]["recent10"] / 10

        # 新特征：遗漏率 (当前遗漏/平均遗漏)
        cache[z]["gap_ratio"] = last_gap / cache[z]["avg_gap"] if cache[z]["avg_gap"] > 0 else 1

        # 新特征：周期位置 (在周期中的位置)
        if len(positions) >= 2:
            cycle = positions[0] - positions[1] if len(positions) > 1 else 12
            cache[z]["cycle_position"] = (n - positions[0]) % max(cycle, 1)
        else:
            cache[z]["cycle_position"] = 0

        # 新特征：阴阳指数 (基于生肖阴阳)
        zodiac_yinyang = {'鼠': '阳', '牛': '阴', '虎': '阳', '兔': '阴', '龙': '阳', '蛇': '阴',
                         '马': '阳', '羊': '阴', '猴': '阳', '鸡': '阴', '狗': '阳', '猪': '阴'}
        cache[z]["yinyang"] = zodiac_yinyang.get(z, '阳')

    return cache


def predict_with_ensemble(records: List[Dict], params: Dict) -> List[str]:
    """Ensemble预测 - 多策略融合"""
    n = len(records)
    cache = build_enhanced_cache(records, n)
    zodiacs = list(cache.keys())
    lookback = params.get("lookback", 11)

    # 策略1: Pattern-based (原始)
    scores1 = {}
    for z in zodiacs:
        c = cache[z]
        positions = [i for i in range(n) if records[i]["特码生肖"] == z]
        if len(positions) < 3:
            scores1[z] = 0.5
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
            scores1[z] = (
                pattern_ratio * params.get("pattern_weight", 1.45) +
                min(current_gap, 50) * params.get("gap_weight", 0.098) +
                trend * params.get("trend_weight", 0.267) +
                (1 / (1 + variance)) * params.get("variance_weight", 0.177)
            )

    # 策略2: Hot-cold weighted (新特征)
    scores2 = {}
    for z in zodiacs:
        c = cache[z]
        # 遗漏高 + 近期热 = 高分
        scores2[z] = (
            min(c["gap"], 50) / 50 * params.get("gap_weight", 0.098) * 2 +
            c["hot_score"] * params.get("hot_weight", 0.5) +
            min(c["gap_ratio"], 3) / 3 * params.get("gap_ratio_weight", 0.3)
        )

    # 策略3: Bayesian-like (基于出现概率)
    scores3 = {}
    total = len(records)
    for z in zodiacs:
        c = cache[z]
        # 先验概率 + 似然
        prior = len(c["positions"]) / total if total > 0 else 1/12
        # 后验估计：结合遗漏和频率
        posterior = prior * (1 + c["hot_score"]) * min(c["gap_ratio"], 2)
        scores3[z] = posterior * params.get("bayesian_weight", 1.0)

    # Ensemble融合
    w1 = params.get("w1", 0.5)  # pattern权重
    w2 = params.get("w2", 0.25)  # hot-cold权重
    w3 = params.get("w3", 0.25)  # bayesian权重

    final_scores = {}
    for z in zodiacs:
        # 归一化各策略得分
        max1 = max(scores1.values()) if scores1 else 1
        max2 = max(scores2.values()) if scores2 else 1
        max3 = max(scores3.values()) if scores3 else 1
        final_scores[z] = (
            (scores1.get(z, 0) / max1) * w1 +
            (scores2.get(z, 0) / max2) * w2 +
            (scores3.get(z, 0) / max3) * w3
        )

    ranked = sorted(zodiacs, key=lambda z: final_scores[z], reverse=True)
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
        top6 = predict_with_ensemble(history, params)
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

    # 最近100/50期
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


def random_ensemble_params() -> Dict:
    """生成随机Ensemble参数"""
    return {
        # 基本参数
        "lookback": random.randint(5, 20),
        "pattern_weight": round(random.uniform(0.5, 5.0), 3),
        "gap_weight": round(random.uniform(0.01, 0.25), 3),
        "trend_weight": round(random.uniform(0.01, 0.6), 3),
        "variance_weight": round(random.uniform(0.05, 0.5), 3),
        "alt_mode": random.choice(["strict", "trend"]),
        # 新特征权重
        "hot_weight": round(random.uniform(0.1, 1.0), 3),
        "gap_ratio_weight": round(random.uniform(0.1, 0.8), 3),
        "bayesian_weight": round(random.uniform(0.1, 1.0), 3),
        # Ensemble权重
        "w1": round(random.uniform(0.2, 0.7), 2),
        "w2": round(random.uniform(0.1, 0.4), 2),
        "w3": round(random.uniform(0.1, 0.4), 2),
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
            top6 = predict_with_ensemble(history, params)
            actual = records[i]["特码生肖"]
            hit = actual in top6
            record = {
                "id": f"{records[i]['期号']}_{version}",
                "issue": records[i]["期号"],
                "version": version,
                "model": f"{version}_ensemble",
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
        "strategy_type": "ensemble",
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


def update_index():
    """更新版本索引"""
    index_path = os.path.join(BASE_DIR, "version_book", "index.json")
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)

    index["updated_at"] = datetime.now().isoformat()
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
    print(f"  索引已更新: {index_path}")


def main():
    print("=" * 60)
    print("澳门六合多策略优化器")
    print("策略: 新特征 + Ensemble + Bayesian")
    print("=" * 60)

    print("\n加载数据...")
    records = get_all_records([2024, 2025, 2026])
    standard = build_standard_records(records)
    print(f"数据加载完成: {len(standard)} 期")

    print("\n" + "="*60)
    print("开始 v15 Ensemble 优化 (5000次迭代)")
    print("="*60)

    best_params = None
    best_score = -1
    best_stats = None
    iterations = 10000

    for i in range(iterations):
        if i % 500 == 0:
            print(f"  进度: {i}/{iterations}", flush=True)

        params = random_ensemble_params()
        stats = evaluate_params(standard, params)

        # 综合评分: 命中率优先，连错惩罚
        streak_penalty = max(0, stats["max_streak"] - 4) * 0.02
        score = stats["hit_rate"] - streak_penalty

        if score > best_score:
            best_score = score
            best_params = params
            best_stats = stats
            print(f"  [{i}] 新最佳! 命中率:{stats['hit_rate']*100:.2f}% 连错:{stats['max_streak']} score:{score:.4f}")

    print(f"\n最佳参数:")
    print(json.dumps(best_params, indent=2))
    print(f"\n统计:")
    print(f"  命中率: {best_stats['hit_rate']*100:.2f}%")
    print(f"  近100期: {best_stats['hit_rate_100']*100:.2f}%")
    print(f"  近50期: {best_stats['hit_rate_50']*100:.2f}%")
    print(f"  最高连错: {best_stats['max_streak']}")

    # 保存v15
    print("\n生成 v15 回测账本...")
    save_ledger("v15", standard, best_params)
    update_version_book("v15", best_params, best_stats, "Ensemble策略: 新特征+热冷权重+贝叶斯融合")
    update_index()

    print("\n" + "="*60)
    print("优化完成!")
    print("="*60)


if __name__ == "__main__":
    main()