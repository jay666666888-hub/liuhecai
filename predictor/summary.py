#!/usr/bin/env python3
"""
Dashboard Summary 计算模块

唯一数据源：storage/aggregated_live.jsonl
🚫 禁止扫描版本目录
🚫 禁止手写 summary

总命中率 = ALL data（backtest + live）
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


STORAGE_DIR = Path(__file__).parent.parent / "storage"
VERSION_BOOK_DIR = Path(__file__).parent.parent / "version_book"
AGGREGATED_LIVE_FILE = STORAGE_DIR / "aggregated_live.jsonl"


def _load_jsonl(file_path: Path) -> List[Dict]:
    """加载 JSONL 文件"""
    records = []
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def compute_summary(index: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    从 aggregated_live.jsonl 计算 summary（唯一数据源）

    总命中率 = ALL data（backtest + live）
    """
    if index is None:
        from predictor.index_generator import generate_index
        index = generate_index()

    active_versions = index.get("active", [])

    # 单一数据源
    all_records = _load_jsonl(AGGREGATED_LIVE_FILE)

    # 按 version 分组
    version_records: Dict[str, List[Dict]] = {}
    for rec in all_records:
        v = rec.get("version")
        if not v:
            continue
        if v not in version_records:
            version_records[v] = []
        version_records[v].append(rec)

    summary = []
    for version in active_versions:
        records = version_records.get(version, [])

        # 总命中率 = ALL data（backtest + live）
        verified = [r for r in records if r.get("actual") is not None]
        pending = [r for r in records if r.get("actual") is None]
        hits = [r for r in verified if r.get("hit") == True]

        total = len(verified)
        hits_count = len(hits)
        pending_count = len(pending)

        # 计算 max_streak（按期号升序，检测期号间隙）
        sorted_verified = sorted(verified, key=lambda x: x["issue"])
        max_streak = 0
        streak = 0
        prev_issue = None
        for r in sorted_verified:
            issue = int(r.get('issue', 0))
            if prev_issue is not None and issue != prev_issue - 1:
                streak = 0
            if not r.get('hit'):
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
            prev_issue = issue

        hit_rate = hits_count / total if total > 0 else 0

        # 从 metadata 获取额外信息
        metadata_path = VERSION_BOOK_DIR / version / "metadata.json"
        strategy_type = "unknown"
        frozen = False
        notes = ""

        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                strategy_type = metadata.get("strategy_type", "unknown")
                frozen = metadata.get("frozen", False)
                notes = metadata.get("notes", "")

        summary.append({
            "version": version,
            "frozen": frozen,
            "strategy_type": strategy_type,
            "hit_rate": hit_rate,
            "backtest_hit_rate": hit_rate,
            "live_hit_rate": hit_rate,
            "live_predictions": total + pending_count,
            "live_verified": total,
            "live_pending": pending_count,
            "live_hits": hits_count,
            "live_max_streak": max_streak,
            "notes": notes
        })

    active_list = index.get("active", [])
    current = active_list[0] if active_list else "v24"

    return {
        "versions": active_versions,
        "current": current,
        "updated_at": datetime.now().isoformat(),
        "summary": summary
    }