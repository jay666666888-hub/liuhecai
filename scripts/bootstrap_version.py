#!/usr/bin/env python3
"""
澳门六合 - 统一 Bootstrap 脚本

用法:
    python3 scripts/bootstrap_version.py --version v25 --rebuild

流程:
    1. data_fetcher 同步数据
    2. 创建版本目录
    3. 初始化 live_ledger
    4. 初始化 backtest_ledger (walk-forward)
    5. 自动生成 metadata.json
    6. 重建 index.json

禁止:
    python v23_bootstrap.py
    python v24_bootstrap.py
"""

import argparse
import json
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/mnt/c/Users/Admin/liuhecai")
PREDICTOR_DIR = BASE_DIR / "predictor"
VERSION_BOOK_DIR = BASE_DIR / "version_book"
SCRIPTS_DIR = BASE_DIR / "scripts"
STORAGE_DIR = BASE_DIR / "storage"

# 添加 base dir 到路径，用于导入 predictor 包
sys.path.insert(0, str(BASE_DIR))

# 直接导入（predictor 是包，用相对导入）
import importlib
data_fetcher = importlib.import_module("predictor.data_fetcher")
get_all_records = data_fetcher.get_all_records
build_standard_records = data_fetcher.build_standard_records

from predictor.ledger_writer import get_writer, aggregate_all_to_storage, init_live_ledger_from_history


# ========== 版本配置 ==========

def get_version_config(version: str) -> dict:
    """获取版本配置"""
    configs = {
        "v5": {
            "strategy_type": "gap_threshold",
            "params": {},
            "predict_fn": "v5",
            "notes": "gap阈值加权"
        },
        "v7": {
            "strategy_type": "rank_based",
            "params": {},
            "predict_fn": "v7",
            "notes": "排名法"
        },
        "v12": {
            "strategy_type": "pattern_based",
            "params": {
                "lookback": 11,
                "pattern_weight": 1.45,
                "gap_weight": 0.098,
                "trend_weight": 0.267,
                "variance_weight": 0.177,
                "alt_mode": "trend"
            },
            "predict_fn": "v12",
            "notes": "主力模型"
        },
        "v21": {
            "strategy_type": "sunday_effect",
            "params": {},
            "predict_fn": "v21",
            "notes": "周日调整版"
        },
        "v23": {
            "strategy_type": "2026_focused",
            "params": {"decay": 0.85, "gap_weight": 4.0, "freq_weight": 1.5},
            "predict_fn": "v23",
            "notes": "专注2026年"
        },
        "v24": {
            "strategy_type": "multi_strategy_vote",
            "params": {"weights": {"v23": 2.5, "gap": 0.5, "decay": 0.5}},
            "predict_fn": "v24",
            "notes": "多策略组合"
        }
    }
    return configs.get(version, {})


def step1_sync_data():
    """步骤1: 同步数据"""
    print("\n[步骤1] 同步数据...")
    print("  注意: 请先运行 scripts/sync_result_to_data.py 同步 result_ledger 到 liuhecai_data.json")
    records = get_all_records([2024, 2025, 2026], force_refresh=True)
    standard = build_standard_records(records)
    print(f"  API 数据: {len(records)} 条记录")
    print(f"  最新期号: {standard[-1]['期号']}")
    return standard


def step2_create_dirs(version: str, rebuild: bool = False):
    """步骤2: 创建版本目录"""
    print(f"\n[步骤2] 创建版本目录...")
    version_dir = VERSION_BOOK_DIR / version
    if version_dir.exists():
        if rebuild:
            print(f"  重建模式: 删除旧目录")
            shutil.rmtree(version_dir)
        else:
            print(f"  目录已存在: {version_dir}")
            print(f"  跳过（使用 --rebuild 强制重建）")
            return version_dir

    version_dir.mkdir(parents=True, exist_ok=True)
    print(f"  创建: {version_dir}")
    return version_dir


def step3_init_live_ledger(version: str, standard: list):
    """步骤3: 初始化 live_ledger（从历史数据重建）"""
    print(f"\n[步骤3] 初始化 live_ledger...")
    version_dir = VERSION_BOOK_DIR / version
    live_ledger_file = version_dir / "live_ledger.jsonl"

    # 检查是否已有数据
    existing_issues = set()
    if live_ledger_file.exists():
        with open(live_ledger_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    rec = json.loads(line)
                    existing_issues.add(rec["issue"])
        print(f"  已有记录: {len(existing_issues)} 条")

    # 生成 live ledger 记录（从 storage/result_ledger 重建）
    result_ledger_file = STORAGE_DIR / "result_ledger.jsonl"
    predictions_file = STORAGE_DIR / "prediction_ledger.jsonl"

    records_to_write = []
    now = datetime.now().isoformat()

    # 读取已有预测（从 prediction_ledger）
    prediction_map = {}
    if predictions_file.exists():
        with open(predictions_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                v = rec.get("version") or rec.get("model", "").split("_")[0]
                if v == version:
                    prediction_map[rec["issue"]] = rec

    # 读取开奖结果
    result_map = {}
    if result_ledger_file.exists():
        with open(result_ledger_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                result_map[rec["issue"]] = rec

    # 为每期生成记录
    writer = get_writer()
    count = 0
    for item in standard:
        issue = item["期号"]
        if issue in existing_issues:
            continue

        # 尝试找到对应的预测和结果
        pred = prediction_map.get(issue, {})
        result = result_map.get(issue, {})

        prediction = pred.get("prediction", [])
        actual = result.get("actual") or item.get("特码生肖")
        hit = None
        status = "pending"

        if actual:
            if result:
                hit = actual in prediction if prediction else None
                status = "verified" if hit is not None else "verified"
            else:
                status = "pending"

        record = {
            "id": f"{issue}_{version}_bootstrap",
            "issue": issue,
            "version": version,
            "model": pred.get("model", f"{version}_interval_predictor"),
            "strategy": pred.get("strategy", f"{version}_weighted_vote"),
            "prediction": prediction if prediction else [],
            "actual": actual,
            "hit": hit,
            "created_at": now,
            "source": "live",
            "status": status
        }

        records_to_write.append(record)
        count += 1

    # 使用 ledger_writer 的安全方法写入 live_ledger
    init_live_ledger_from_history(version, records_to_write)

    print(f"  写入: {len(records_to_write)} 条记录")
    return live_ledger_file


def step4_init_backtest_ledger(version: str, standard: list):
    """步骤4: 初始化 backtest_ledger（walk-forward 回测）"""
    print(f"\n[步骤4] 初始化 backtest_ledger...")

    config = get_version_config(version)
    predict_fn_name = config.get("predict_fn", version)

    # 加载预测器
    if predict_fn_name == "v12":
        from predictor.predictor import predict_top6
        predict_fn = lambda recs: predict_top6(recs, config["params"], "pattern_based")
    elif predict_fn_name == "v21":
        from predictor.predictor import predict_top6
        def predict_v21_fn(recs):
            # 简化版 v21
            return predict_top6(recs, config["params"], "pattern_based")
        predict_fn = predict_v21_fn
    elif predict_fn_name == "v23":
        from predictor.v23_interval_predictor import predict_v23
        predict_fn = lambda recs: predict_v23(recs, top_k=6)
    elif predict_fn_name == "v24":
        from predictor.v24_interval_predictor import predict_v24
        predict_fn = lambda recs: predict_v24(recs, top_k=6)
    else:
        print(f"  警告: 未知预测函数 {predict_fn_name}，跳过 backtest")
        return None

    version_dir = VERSION_BOOK_DIR / version
    backtest_file = version_dir / "backtest_ledger.jsonl"

    # Walk-forward 回测
    lookback = 30  # 最小回测起点
    records_to_write = []
    now = datetime.now().isoformat()

    for i in range(lookback, len(standard)):
        history = standard[:i]
        actual = standard[i]["特码生肖"]
        issue = standard[i]["期号"]

        # 生成预测
        try:
            prediction = predict_fn(history)
            hit = actual in prediction
        except Exception as e:
            print(f"  回测失败 {issue}: {e}")
            continue

        record = {
            "id": f"{issue}_{version}_backtest",
            "issue": issue,
            "version": version,
            "model": f"{version}_interval_predictor",
            "strategy": config.get("strategy_type", "unknown"),
            "prediction": prediction,
            "actual": actual,
            "hit": hit,
            "created_at": now,
            "source": "backtest",
            "status": "resolved"
        }
        records_to_write.append(record)

        if (i - lookback + 1) % 100 == 0:
            print(f"  回测进度: {i - lookback + 1}/{len(standard) - lookback}")

    # 写入 backtest_ledger
    with open(backtest_file, 'w', encoding='utf-8') as f:
        for rec in records_to_write:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"  写入: {len(records_to_write)} 条记录")

    # 计算回测统计
    hits = sum(1 for r in records_to_write if r.get("hit"))
    total = len(records_to_write)
    hit_rate = hits / total if total > 0 else 0
    print(f"  回测命中率: {hits}/{total} = {hit_rate*100:.2f}%")

    return backtest_file


def step5_generate_metadata(version: str, standard: list):
    """步骤5: 生成 metadata.json

    从 aggregated_live.jsonl 读取数据，按 source 过滤计算统计
    """
    print(f"\n[步骤5] 生成 metadata.json...")

    version_dir = VERSION_BOOK_DIR / version

    def calc_stats_from_records(records):
        """从记录列表计算统计数据"""
        if not records:
            return {"total": 0, "hits": 0, "hit_rate": 0, "hit_rate_100": 0, "hit_rate_50": 0, "max_streak": 0}

        verified = [r for r in records if r.get("actual") is not None]
        total = len(verified)
        hits = sum(1 for r in verified if r.get("hit"))
        hit_rate = hits / total if total > 0 else 0

        # 计算连错（检测期号间隙）
        sorted_recs = sorted(verified, key=lambda x: x["issue"])
        max_streak = 0
        streak = 0
        prev_issue = None
        for r in sorted_recs:
            issue = int(r.get('issue', 0))
            if prev_issue is not None and issue != prev_issue - 1:
                # Gap detected - reset streak chain
                streak = 0
            if not r.get("hit"):
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
            prev_issue = issue

        # 最近100/50期
        recent_100 = sorted_recs[-100:] if len(sorted_recs) > 100 else sorted_recs
        recent_50 = sorted_recs[-50:] if len(sorted_recs) > 50 else sorted_recs

        hits_100 = sum(1 for r in recent_100 if r.get("hit"))
        hits_50 = sum(1 for r in recent_50 if r.get("hit"))

        return {
            "total": total,
            "hits": hits,
            "hit_rate": hit_rate,
            "hit_rate_100": hits_100 / len(recent_100) if recent_100 else 0,
            "hit_rate_50": hits_50 / len(recent_50) if recent_50 else 0,
            "max_streak": max_streak
        }

    # 从 aggregated_live.jsonl 读取（按 version + source 过滤）
    aggregated_file = STORAGE_DIR / "aggregated_live.jsonl"
    all_records = []
    if aggregated_file.exists():
        with open(aggregated_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    all_records.append(json.loads(line))

    # 按 source 分离
    version_records = [r for r in all_records if r.get("version") == version]
    live_records = [r for r in version_records if r.get("source") in ("live", "live_update")]
    backtest_records = [r for r in version_records if r.get("source") == "backtest"]

    live_stats = calc_stats_from_records(live_records)
    backtest_stats = calc_stats_from_records(backtest_records)

    config = get_version_config(version)

    metadata = {
        "version": version,
        "strategy_type": config.get("strategy_type", "unknown"),
        "params": config.get("params", {}),
        "notes": config.get("notes", ""),
        "frozen": False,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "backtest": backtest_stats,
        "live": live_stats
    }

    metadata_file = version_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"  生成: {metadata_file}")
    print(f"    回测: {backtest_stats['total']} 期, 命中率 {backtest_stats['hit_rate']*100:.2f}%")
    print(f"    实盘: {live_stats['total']} 期, 命中率 {live_stats['hit_rate']*100:.2f}%")

    return metadata_file


def step6_rebuild_index():
    """步骤6: 重建 index.json"""
    print("\n[步骤6] 重建 index.json...")

    # 收集所有版本
    versions = []
    summary = []

    for version_dir in VERSION_BOOK_DIR.iterdir():
        if not version_dir.is_dir() or version_dir.name.startswith('.'):
            continue

        metadata_file = version_dir / "metadata.json"
        if not metadata_file.exists():
            continue

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        version_name = version_dir.name
        versions.append(version_name)

        # 计算 live_predictions 从聚合层
        aggregated_file = STORAGE_DIR / "aggregated_live.jsonl"
        live_predictions = 0
        if aggregated_file.exists():
            with open(aggregated_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    if rec.get("version") == version_name and rec.get("source") == "live":
                        live_predictions += 1

        summary.append({
            "version": version_name,
            "frozen": metadata.get("frozen", False),
            "strategy_type": metadata.get("strategy_type", "unknown"),
            "hit_rate": metadata.get("backtest", {}).get("hit_rate", 0),
            "backtest_hit_rate": metadata.get("backtest", {}).get("hit_rate", 0),
            "live_hit_rate": metadata.get("live", {}).get("hit_rate", 0),
            "live_predictions": live_predictions,
            "live_max_streak": metadata.get("live", {}).get("max_streak", 0),
            "notes": metadata.get("notes", "")
        })

    versions.sort()

    # 确定 current 版本（最新的非冻结版本）
    current = "v24"  # 默认
    for v in sorted(versions, reverse=True):
        metadata_file = VERSION_BOOK_DIR / v / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                m = json.load(f)
            if not m.get("frozen", False):
                current = v
                break

    index = {
        "versions": versions,
        "current": current,
        "updated_at": datetime.now().isoformat(),
        "summary": summary
    }

    index_file = VERSION_BOOK_DIR / "index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"  生成: {index_file}")
    print(f"  版本: {versions}")
    print(f"  当前: {current}")

    # 聚合所有 live ledger 到 storage
    print("\n[聚合] 聚合所有版本到 storage/aggregated_live.jsonl...")
    count = aggregate_all_to_storage()
    print(f"  聚合: {count} 条记录")

    return index_file


# ========== 主流程 ==========

def main():
    parser = argparse.ArgumentParser(description="统一 Bootstrap 脚本")
    parser.add_argument("--version", required=True, help="版本号 (如 v24)")
    parser.add_argument("--rebuild", action="store_true", help="重建模式（删除旧数据）")
    parser.add_argument("--skip-backtest", action="store_true", help="跳过回测（只初始化 live ledger）")
    args = parser.parse_args()

    version = args.version

    print("=" * 60)
    print(f"澳门六合 - Bootstrap {version}")
    print("=" * 60)

    # 步骤1: 同步数据
    standard = step1_sync_data()

    # 步骤2: 创建目录
    version_dir = step2_create_dirs(version, rebuild=args.rebuild)

    if args.rebuild and version_dir.exists():
        # 删除旧账本
        for f in ["live_ledger.jsonl", "backtest_ledger.jsonl", "metadata.json"]:
            old_file = version_dir / f
            if old_file.exists():
                old_file.unlink()
                print(f"  删除: {old_file}")

    # 步骤3: 初始化 live_ledger
    step3_init_live_ledger(version, standard)

    # 步骤4: 初始化 backtest_ledger
    if not args.skip_backtest:
        step4_init_backtest_ledger(version, standard)
    else:
        print(f"\n[跳过] backtest_ledger 初始化")

    # 步骤5: 生成 metadata
    step5_generate_metadata(version, standard)

    # 步骤6: 重建 index
    step6_rebuild_index()

    print("\n" + "=" * 60)
    print(f"Bootstrap {version} 完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()