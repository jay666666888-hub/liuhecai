#!/usr/bin/env python3
"""
澳门六合 - 预测协调器 (Orchestrator)

统一入口，多版本并行预测，标准化输出。

🚫 强制规则：
- 所有版本必须通过 orchestrator 运行
- 禁止 predictor 自己写 ledger
- 禁止 predictor 自己 fetch data
- 禁止直接写入 result_ledger.jsonl（已废弃）
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Any
from predictor.base_predictor import BasePredictor, PredictionResult
from predictor.predictor_registry import PredictorRegistry
from predictor.ledger_writer import write_live_prediction, verify_prediction, get_writer
from predictor.data_fetcher import get_all_records, build_standard_records


class PredictOrchestrator:
    """
    多版本预测协调器

    负责：
    1. 加载 active 版本
    2. 统一执行预测
    3. 统一写入 ledger
    """

    def __init__(self, active_versions: List[str] = None):
        """
        初始化 orchestrator

        Args:
            active_versions: 活跃版本列表，如 ["v23", "v24"]
        """
        if active_versions is None:
            from predictor.index_generator import generate_index
            index = generate_index()
            active_versions = index.get("active", ["v23", "v24"])

        self.active_versions = active_versions
        self.predictors: Dict[str, BasePredictor] = {}
        self._load_predictors()

    def _load_predictors(self):
        """通过 PredictorRegistry 加载所有预测器（插件式）"""
        # 先扫描插件目录
        PredictorRegistry.scan()

        for version in self.active_versions:
            try:
                self.predictors[version] = PredictorRegistry.get(version)
                print(f"  ✓ 加载 {version}")
            except ValueError as e:
                print(f"  ✗ 跳过 {version}: {e}")

    def predict(self, history: List[Dict], top_k: int = 6) -> Dict[str, PredictionResult]:
        """
        对所有活跃版本生成预测

        Args:
            history: 历史记录列表
            top_k: 默认返回前k个预测（会被 play_type 覆盖）

        Returns:
            {version: PredictionResult} 字典
        """
        results = {}
        for version, predictor in self.predictors.items():
            try:
                # 根据 play_type 决定 top_k
                from predictor.predictor_registry import PredictorRegistry
                metadata = PredictorRegistry.get_metadata(version)
                play_type = metadata.get('play_type', 'liuhe')
                if play_type == 'duoma':
                    actual_top_k = metadata.get('top_k', 24)
                else:
                    actual_top_k = top_k
                result = predictor.predict(history, top_k=actual_top_k)
                results[version] = result
            except Exception as e:
                print(f"  ✗ {version} 预测失败: {e}")
                results[version] = PredictionResult(
                    prediction=[],
                    scores={},
                    metadata={"error": str(e), "version": version}
                )
        return results

    def write_results(self, results: Dict[str, PredictionResult], issue: str, zodiac_list: List[str] = None):
        """
        将预测结果写入 ledger

        Args:
            results: predict() 返回的结果
            issue: 期号
            zodiac_list: 完整7个生肖列表（平特一肖用）
        """
        writer = get_writer()
        for version, result in results.items():
            if not result.prediction:
                continue
            try:
                from predictor.predictor_registry import PredictorRegistry
                metadata = PredictorRegistry.get_metadata(version)
                play_type = metadata.get('play_type', 'liuhe')
                write_live_prediction(
                    version=version,
                    issue=issue,
                    prediction=result.prediction,
                    model=f"{version}_predictor",
                    strategy=result.metadata.get("strategy", "unknown"),
                    play_type=play_type,
                    zodiac_list=zodiac_list
                )
            except Exception as e:
                print(f"  ✗ {version} 写入失败: {e}")

    def run_cycle(self, history: List[Dict], issue: str, top_k: int = 6, zodiac_list: List[str] = None) -> Dict[str, PredictionResult]:
        """
        执行完整预测周期

        Args:
            history: 历史记录列表
            issue: 当前期号
            top_k: 返回前k个预测
            zodiac_list: 完整7个生肖列表（平特一肖用）

        Returns:
            {version: PredictionResult} 字典
        """
        # 1. 生成预测
        results = self.predict(history, top_k=top_k)

        # 2. 写入 ledger
        self.write_results(results, issue, zodiac_list)

        return results


def sync_latest_results() -> Dict[str, Any]:
    """
    从 API 获取最新开奖结果（不再写入 result_ledger.jsonl）

    流程：
    1. 从 API 获取最新数据（force_refresh）
    2. 返回最新期号和开奖结果

    注意：result_ledger.jsonl 已废弃，开奖结果存储在 aggregated_live.jsonl
    """
    from datetime import datetime

    # 从 API 获取最新数据
    records = get_all_records([2024, 2025, 2026], force_refresh=True)
    standard = build_standard_records(records)

    if not standard:
        print("  [同步] 无法获取 API 数据")
        return {"synced": 0, "api_latest": None, "api_latest_zodiac": None}

    api_latest = standard[-1]
    api_latest_issue = api_latest["期号"]
    api_latest_zodiac = api_latest["特码生肖"]

    print(f"  [同步] API 最新: {api_latest_issue} ({api_latest_zodiac})")

    return {
        "synced": 1,
        "api_latest": api_latest_issue,
        "api_latest_zodiac": api_latest_zodiac
    }


def run_live_cycle(active_versions: List[str] = None) -> Dict[str, Any]:
    """
    运行实盘预测周期

    Args:
        active_versions: 活跃版本列表，默认从 index.json 自动读取

    Returns:
        预测结果字典
    """
    if active_versions is None:
        from predictor.index_generator import generate_index
        index = generate_index()
        active_versions = index.get("active", ["v23", "v24"])

    print("=" * 50)
    print("澳门六合 - 预测协调器")
    print("=" * 50)
    print(f"活跃版本: {', '.join(active_versions)}")

    # 0. 同步最新开奖结果
    print("\n[0] 同步开奖结果...")
    sync_result = sync_latest_results()
    print(f"  已同步: {sync_result['synced']} 条")

    # 1. 获取最新数据
    print("\n[1] 获取数据...")
    records = get_all_records([2024, 2025, 2026], force_refresh=True)
    standard = build_standard_records(records)

    if not standard:
        print("无法获取数据，退出")
        return {}

    n = len(standard)
    latest = standard[-1]
    latest_issue = latest["期号"]
    latest_actual = latest["特码生肖"]
    latest_special_number = latest.get("特码号码")  # 多码验证用
    # 获取完整7个生肖列表（用于平特一肖验证）
    latest_zodiac_list = latest.get("开奖生肖", []) if latest.get("开奖生肖") else []

    print(f"  最新开奖: {latest_issue} ({latest_actual})")
    print(f"  开奖生肖: {latest_zodiac_list}")
    print(f"  特码号码: {latest_special_number}")
    print(f"  历史数据: {n} 期")

    # 2. 验证上期预测
    print("\n[2] 验证上期...")
    writer = get_writer()
    for version in active_versions:
        try:
            # 检查该版本是否有上期预测记录
            existing = [r for r in writer.read_live_predictions(version, limit=1000) if r['issue'] == latest_issue]
            if not existing:
                print(f"  {version}: - (无预测记录，跳过)")
                continue

            hit, updated = verify_prediction(version, latest_issue, latest_actual, latest_zodiac_list, latest_special_number)
            if hit is not None:
                status = "✓ 命中" if hit else "✗ 未中"
                duoma_info = f" ({latest_special_number})" if updated.get('play_type') == 'duoma' else f" ({latest_actual})"
                print(f"  {version}: {status}{duoma_info}")
        except Exception as e:
            print(f"  {version}: 验证失败 - {e}")

    # 3. 生成下期预测
    next_issue = str(int(latest_issue) + 1)
    history = standard  # 用全部历史预测

    print(f"\n[3] 生成预测...")
    print(f"  预测期号: {next_issue}")

    orchestrator = PredictOrchestrator(active_versions)
    # 传入 zodiac_list 用于写入（平特一肖需要）
    results = orchestrator.run_cycle(history, next_issue, zodiac_list=latest_zodiac_list)

    # 4. 打印结果
    print("\n[4] 预测结果:")
    for version, result in results.items():
        print(f"  {version}: {result.prediction}")

    print("\n完成!")
    return {
        "issue": next_issue,
        "results": {v: r.to_dict() for v, r in results.items()}
    }
