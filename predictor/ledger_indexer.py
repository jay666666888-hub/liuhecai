#!/usr/bin/env python3
"""
澳门六合 - 版本账本索引器
按版本聚合统计，生成版本账本

职责：
- 按 version 分组聚合 ledger 数据
- 计算 hit_rate / max_streak 等统计
- 生成 version_book/vN/ 回测账本

注意：
- 不做数据写入（只读）
- 统计计算依赖 ledger.py 提供的基础数据
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
LEDGER_DIR = os.path.join(BASE_DIR, "storage")
VERSION_BOOK_DIR = os.path.join(BASE_DIR, "version_book")

os.makedirs(VERSION_BOOK_DIR, exist_ok=True)

# 版本配置 - 从 index_generator 动态读取，不再硬编码
# 唯一事实源：predictors/active/ 目录 + metadata.json
# 兼容旧版本：如果 active 目录不存在，退回 hardcoded VERSIONS（仅用于生成回测账本）

from predictor.index_generator import generate_index

def get_versions_from_index():
    """从 index_generator 获取版本列表"""
    try:
        index = generate_index()
        active = index.get("active", [])
        # 回测只需 v9-v12 的参数配置
        legacy_params = {
            "v9": {
                "strategy_type": "pattern_based",
                "params": {"lookback": 13, "pattern_weight": 2.0, "gap_weight": 0.04, "trend_weight": 0.08, "variance_weight": 0.25, "alt_mode": "strict"},
                "notes": "原始v9版本，二元特征"
            },
            "v10": {
                "strategy_type": "pattern_based",
                "params": {"lookback": 13, "pattern_weight": 3.5, "gap_weight": 0.07, "trend_weight": 0.15, "variance_weight": 0.4, "alt_mode": "strict"},
                "notes": "参数优化版本"
            },
            "v11": {
                "strategy_type": "pattern_based",
                "params": {"lookback": 8, "pattern_weight": 2.65, "gap_weight": 0.056, "trend_weight": 0.099, "variance_weight": 0.304, "alt_mode": "strict"},
                "notes": "随机搜索找到的最佳参数"
            },
            "v12": {
                "strategy_type": "pattern_based",
                "params": {"lookback": 11, "pattern_weight": 1.45, "gap_weight": 0.098, "trend_weight": 0.267, "variance_weight": 0.177, "alt_mode": "trend"},
                "notes": "大规模随机搜索找到的新最佳参数"
            }
        }
        # 对于 active 目录中的版本，尝试从 metadata.json 读取参数
        from pathlib import Path
        # base_dir = predictor/ 目录 (ledger_indexer.py 在 predictor/ 下)
        base_dir = Path(__file__).parent  # = .../liuhecai/predictor/
        active_dir = base_dir / "predictors" / "active"
        result = {}
        for v in active:
            metadata_path = active_dir / v / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    meta = json.load(f)
                    params = meta.get("params", legacy_params.get(v, {}).get("params", {}))
                    result[v] = {
                        "strategy_type": meta.get("strategy_type", "pattern_based"),
                        "params": params,
                        "notes": meta.get("notes", "")
                    }
            elif v in legacy_params:
                result[v] = legacy_params[v]
        return result if result else legacy_params
    except Exception as e:
        print(f"[ledger_indexer] 动态读取失败，退回legacy: {e}")
        return {
            "v9": {"strategy_type": "pattern_based", "params": {"lookback": 13, "pattern_weight": 2.0, "gap_weight": 0.04, "trend_weight": 0.08, "variance_weight": 0.25, "alt_mode": "strict"}, "notes": "原始v9版本"},
            "v10": {"strategy_type": "pattern_based", "params": {"lookback": 13, "pattern_weight": 3.5, "gap_weight": 0.07, "trend_weight": 0.15, "variance_weight": 0.4, "alt_mode": "strict"}, "notes": "参数优化版本"},
            "v11": {"strategy_type": "pattern_based", "params": {"lookback": 8, "pattern_weight": 2.65, "gap_weight": 0.056, "trend_weight": 0.099, "variance_weight": 0.304, "alt_mode": "strict"}, "notes": "随机搜索"},
            "v12": {"strategy_type": "pattern_based", "params": {"lookback": 11, "pattern_weight": 1.45, "gap_weight": 0.098, "trend_weight": 0.267, "variance_weight": 0.177, "alt_mode": "trend"}, "notes": "大规模随机搜索"}
        }

VERSIONS = get_versions_from_index()


def _read_jsonl(file_path: str) -> List[Dict]:
    """读取JSONL文件"""
    records = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def load_ledger():
    """加载账本数据"""
    predictions = _read_jsonl(os.path.join(LEDGER_DIR, "prediction_ledger.jsonl"))
    results = _read_jsonl(os.path.join(LEDGER_DIR, "result_ledger.jsonl"))
    return predictions, results


def run_backtest_for_version(version: str, params: Dict) -> Dict:
    """对指定版本运行回测"""
    import sys
    sys.path.insert(0, BASE_DIR)
    from predictor.data_fetcher import get_all_records, build_standard_records
    from predictor.six_zodiac_predictor import predict_top6

    records = get_all_records([2024, 2025, 2026])
    standard = build_standard_records(records)

    lookback = params.get("lookback", 13)
    feature_type = "pattern_based"

    hits = 0
    total = 0
    streak = 0
    max_streak = 0
    streak_list = []
    recent_results = []

    for i in range(lookback, len(standard)):
        history = standard[:i]
        top6 = predict_top6(history, params, feature_type)
        actual = standard[i]["特码生肖"]

        hit = actual in top6

        if hit:
            hits += 1
            streak = 0
        else:
            streak += 1
            max_streak = max(max_streak, streak)

        total += 1
        recent_results.append({"issue": standard[i]["期号"], "hit": hit, "actual": actual})

        if len(recent_results) <= 100:
            streak_list.append(streak)

    hit_rate = hits / total if total > 0 else 0

    # 最近100期
    recent_100 = recent_results[-100:] if len(recent_results) >= 100 else recent_results
    recent_100_hits = sum(1 for r in recent_100 if r["hit"])
    recent_100_rate = recent_100_hits / len(recent_100) if recent_100 else 0

    # 最近50期
    recent_50 = recent_results[-50:] if len(recent_results) >= 50 else recent_results
    recent_50_hits = sum(1 for r in recent_50 if r["hit"])
    recent_50_rate = recent_50_hits / len(recent_50) if recent_50 else 0

    # 平均连错
    avg_streak = sum(streak_list) / len(streak_list) if streak_list else 0

    return {
        "version": version,
        "backtest_hit_rate": hit_rate,
        "backtest_recent_100": recent_100_rate,
        "backtest_recent_50": recent_50_rate,
        "backtest_total": total,
        "backtest_hits": hits,
        "backtest_max_streak": max_streak,
        "backtest_avg_streak": avg_streak,
        "backtest_at": datetime.now().isoformat(),
        "params": params
    }


def get_backtest_ledger_path(version: str) -> str:
    """获取回测账本路径"""
    return os.path.join(VERSION_BOOK_DIR, version, "backtest_ledger.jsonl")


def compute_live_stats(version: str, predictions: List[Dict], results: List[Dict]) -> Dict:
    """计算实盘统计（基于回测账本）"""
    ledger_path = get_backtest_ledger_path(version)

    if not os.path.exists(ledger_path):
        return {
            "live_predictions": 0,
            "live_results": 0,
            "live_hits": 0,
            "live_hit_rate": 0,
            "live_max_streak": 0
        }

    # 从回测账本读取 - 每条记录自带 actual/hit
    backtest_records = _read_jsonl(ledger_path)

    if not backtest_records:
        return {
            "live_predictions": 0,
            "live_results": 0,
            "live_hits": 0,
            "live_hit_rate": 0,
            "live_max_streak": 0
        }

    # 计算统计 - 直接用 backtest_records 计算
    total = len(backtest_records)
    hits = sum(1 for r in backtest_records if r.get("hit", False))
    hit_rate = hits / total if total > 0 else 0

    # 计算连错
    sorted_records = sorted(backtest_records, key=lambda x: x["issue"])
    max_streak = 0
    streak = 0
    for r in sorted_records:
        if r.get("hit", False):
            streak = 0
        else:
            streak += 1
            max_streak = max(max_streak, streak)

    return {
        "live_predictions": total,
        "live_results": total,
        "live_hits": hits,
        "live_hit_rate": hit_rate,
        "live_max_streak": max_streak
    }


def generate_version_books():
    """生成所有版本账本"""
    predictions, results = load_ledger()

    version_books = {}

    for version, config in VERSIONS.items():
        print(f"处理 {version}...")

        # 生成回测账本
        generate_backtest_ledger(version)

        # 回测
        backtest = run_backtest_for_version(version, config["params"])

        # 实盘统计
        live = compute_live_stats(version, predictions, results)

        # 合并
        book = {
            "version": version,
            "strategy_type": config.get("strategy_type", "pattern_based"),
            "params": config["params"],
            "notes": config.get("notes", ""),
            "backtest": backtest,
            "live": live,
            "frozen": version != "v12",  # v12是当前版本，其他冻结
            "updated_at": datetime.now().isoformat()
        }

        # 保存
        book_path = os.path.join(VERSION_BOOK_DIR, f"{version}.json")
        with open(book_path, "w", encoding="utf-8") as f:
            json.dump(book, f, ensure_ascii=False, indent=2)

        version_books[version] = book
        print(f"  {version}: 回测{backtest['backtest_hit_rate']*100:.1f}%, 实盘{live['live_hit_rate']*100:.1f}%")

    # 生成索引
    index = {
        "versions": list(VERSIONS.keys()),
        "current": "v12",
        "updated_at": datetime.now().isoformat(),
        "summary": [
            {
                "version": vb["version"],
                "frozen": vb["frozen"],
                "backtest_hit_rate": vb["backtest"]["backtest_hit_rate"],
                "live_hit_rate": vb["live"]["live_hit_rate"],
                "live_predictions": vb["live"]["live_predictions"],
                "live_max_streak": vb["live"]["live_max_streak"]
            }
            for vb in version_books.values()
        ]
    }

    index_path = os.path.join(VERSION_BOOK_DIR, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\n版本账本已生成到 {VERSION_BOOK_DIR}")
    return version_books


if __name__ == "__main__":
    generate_version_books()