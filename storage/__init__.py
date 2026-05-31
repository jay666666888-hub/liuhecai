#!/usr/bin/env python3
"""
storage - 存储层安全拦截

🚫 禁止直接 open storage 目录下的账本文件
必须通过 predictor.ledger_writer 接口写入
"""

import builtins
import os

_original_open = builtins.open

_DENIED_PATTERNS = [
    "prediction_ledger",
    "result_ledger",
    "aggregated_live",
    "live_ledger",
]


def _guarded_open(path, *args, **kwargs):
    """拦截对账本文件的直接写入"""
    path_str = str(path)

    if args and 'w' in args[0]:
        if any(pat in path_str for pat in _DENIED_PATTERNS):
            raise PermissionError(
                f"禁止直接写入账本文件: {path}\n"
                f"必须通过 predictor.ledger_writer.write_live_prediction() 写入"
            )

    if args and 'a' in args[0]:
        if any(pat in path_str for pat in _DENIED_PATTERNS):
            raise PermissionError(
                f"禁止直接追加账本文件: {path}\n"
                f"必须通过 predictor.ledger_writer 接口"
            )

    return _original_open(path, *args, **kwargs)


def _safe_open(path, *args, **kwargs):
    """LedgerWriter 专用安全通道（不走拦截）"""
    return _original_open(path, *args, **kwargs)


def write_batch_ledger(records: list, model_type: str = "single_prediction"):
    """
    Backtest 脚本批量写入接口

    绕过 storage 层拦截，直接写入 aggregated_live.jsonl
    用于 backtest_v27/v28.py 等脚本

    Args:
        records: [{version, issue, prediction, source, actual, hit}, ...]
        model_type: 模型类型 (single_prediction | pingte_yixiao | backtest)
                    必须在写入时确定，metrics 层禁止推断
    """
    import json
    from pathlib import Path

    AGGREGATED_LIVE = Path(__file__).parent / "aggregated_live.jsonl"

    with _safe_open(AGGREGATED_LIVE, 'a', encoding='utf-8') as f:
        for rec in records:
            rec["model_type"] = model_type
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


builtins.open = _guarded_open