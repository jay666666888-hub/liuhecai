#!/usr/bin/env python3
"""
澳门六合预测账本 - 不可变预测记录系统
遵循: Prediction Ledger Immutable Specification v1

目录结构:
  storage/
    prediction_ledger.jsonl    # 预测记录（append-only）
    result_ledger.jsonl       # 开奖结果（append-only）
    ledger_snapshot/          # 压缩归档
"""

import json
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
PREDICTION_LEDGER_FILE = os.path.join(STORAGE_DIR, "prediction_ledger.jsonl")
RESULT_LEDGER_FILE = os.path.join(STORAGE_DIR, "result_ledger.jsonl")
SNAPSHOT_DIR = os.path.join(STORAGE_DIR, "ledger_snapshot")

os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


class PredictionLedgerError(Exception):
    """账本错误"""
    pass


class PredictionIDExistsError(PredictionLedgerError):
    """预测ID已存在"""
    pass


class LedgerIntegrityError(PredictionLedgerError):
    """账本完整性错误"""
    pass


def generate_prediction_id(issue: str, version: str, created_at: str = None) -> str:
    """生成唯一预测ID: {issue}_{version}_{timestamp}"""
    if created_at is None:
        created_at = datetime.now().isoformat()
    # 从 created_at 提取时间戳部分作为ID
    ts = created_at.replace("-", "").replace(":", "").replace("T", "_")[:16]
    return f"{issue}_{version}_{ts}"


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


def _append_jsonl(file_path: str, record: Dict) -> None:
    """追加记录到JSONL文件（append-only）"""
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


class PredictionLedger:
    """
    预测账本 - 不可变记录系统

    规则:
    1. 预测记录只能新增，不能修改或删除
    2. 每条预测有唯一ID
    3. 预测和结果分离
    """

    def __init__(self):
        self.predictions = _read_jsonl(PREDICTION_LEDGER_FILE)
        self.results = _read_jsonl(RESULT_LEDGER_FILE)
        self._build_indices()

    def _build_indices(self):
        """构建索引加速查询"""
        self.pred_id_index = {p["id"]: p for p in self.predictions}
        self.pred_issue_index = {}
        for p in self.predictions:
            issue = p["issue"]
            if issue not in self.pred_issue_index:
                self.pred_issue_index[issue] = []
            self.pred_issue_index[issue].append(p)

        # issue + version 联合唯一索引
        self.pred_issue_version_index = {}
        for p in self.predictions:
            key = (p["issue"], p.get("version", ""))
            if key not in self.pred_issue_version_index:
                self.pred_issue_version_index[key] = []
            self.pred_issue_version_index[key].append(p)

        self.result_pred_id_index = {r.get("prediction_id"): r for r in self.results}

    def add_prediction(
        self,
        issue: str,
        top6: List[str],
        version: str,
        strategy: str,
        source: str = "live",  # 新增：backtest 或 live
        created_at: str = None
    ) -> Dict:
        """
        添加预测记录

        Args:
            issue: 期号
            top6: 推荐六肖
            version: 版本号（如 v9, v10, v11, v12）
            strategy: 策略版本
            source: 数据来源（backtest 或 live）
            created_at: 创建时间

        Returns:
            预测记录

        Raises:
            PredictionIDExistsError: 如果预测ID已存在
        """
        if created_at is None:
            created_at = datetime.now().isoformat()

        pred_id = generate_prediction_id(issue, version, created_at)

        # 检查是否已存在
        if pred_id in self.pred_id_index:
            raise PredictionIDExistsError(
                f"FATAL ERROR: Prediction ID already exists: {pred_id}"
            )

        # 创建预测记录
        record = {
            "id": pred_id,
            "issue": issue,
            "version": version,
            "model": f"{version}_zigzag",  # 兼容旧格式
            "prediction": top6,
            "source": source,  # 新增
            "created_at": created_at,
            "strategy": strategy,
        }

        # 追加到账本
        _append_jsonl(PREDICTION_LEDGER_FILE, record)
        self.predictions.append(record)
        self.pred_id_index[pred_id] = record

        if issue not in self.pred_issue_index:
            self.pred_issue_index[issue] = []
        self.pred_issue_index[issue].append(record)

        # issue+version 索引
        key = (issue, version)
        if key not in self.pred_issue_version_index:
            self.pred_issue_version_index[key] = []
        self.pred_issue_version_index[key].append(record)

        return record

    def add_result(
        self,
        issue: str,
        actual: str,
        hit: bool,
        prediction_id: str = None,
        resolved_at: str = None
    ) -> Dict:
        """
        添加开奖结果记录（与预测记录分离）

        Args:
            issue: 期号
            actual: 实际生肖
            hit: 是否命中
            prediction_id: 关联的预测ID（如果已知）
            resolved_at: 开奖时间

        Returns:
            结果记录
        """
        if resolved_at is None:
            resolved_at = datetime.now().isoformat()

        # 如果没有提供prediction_id，尝试找到对应的预测
        if prediction_id is None:
            predictions = self.pred_issue_index.get(issue, [])
            if predictions:
                prediction_id = predictions[-1]["id"]

        result_id = f"result_{issue}"

        record = {
            "id": result_id,
            "prediction_id": prediction_id,
            "issue": issue,
            "actual": actual,
            "hit": hit,
            "resolved_at": resolved_at,
        }

        _append_jsonl(RESULT_LEDGER_FILE, record)
        self.results.append(record)
        self.result_pred_id_index[prediction_id] = record

        return record

    def get_prediction(self, issue: str) -> Optional[Dict]:
        """获取某期最新的预测"""
        predictions = self.pred_issue_index.get(issue, [])
        return predictions[-1] if predictions else None

    def get_prediction_by_version(self, issue: str, version: str) -> Optional[Dict]:
        """获取某期指定版本的预测"""
        key = (issue, version)
        predictions = self.pred_issue_version_index.get(key, [])
        return predictions[-1] if predictions else None

    def get_predictions_by_version(self, version: str) -> List[Dict]:
        """获取指定版本的所有预测"""
        return [
            p for p in self.predictions
            if p.get("version") == version
        ]

    def get_result(self, issue: str) -> Optional[Dict]:
        """获取某期的开奖结果"""
        predictions = self.pred_issue_index.get(issue, [])
        if not predictions:
            return None
        prediction_id = predictions[-1]["id"]
        return self.result_pred_id_index.get(prediction_id)

    def get_pending_predictions(self) -> List[Dict]:
        """获取待验证的预测列表"""
        pending = []
        for p in self.predictions:
            pred_id = p["id"]
            if pred_id not in self.result_pred_id_index:
                pending.append(p)
        return pending

    def get_stats(self) -> Dict:
        """获取账本统计"""
        total_predictions = len(self.predictions)
        total_results = len(self.results)

        hits = sum(1 for r in self.results if r.get("hit", False))
        hit_rate = hits / total_results if total_results > 0 else 0

        return {
            "total_predictions": total_predictions,
            "total_results": total_results,
            "total_hits": hits,
            "hit_rate": hit_rate,
        }


def startup_verification():
    """启动时验证账本完整性"""
    ledger = PredictionLedger()
    # 基本验证：确保文件可读
    return ledger


if __name__ == "__main__":
    # 测试账本
    print("=== 预测账本系统测试 ===")

    ledger = startup_verification()
    print(f"✅ 账本加载成功")
    print(f"   预测记录: {len(ledger.predictions)} 条")
    print(f"   结果记录: {len(ledger.results)} 条")

    stats = ledger.get_stats()
    print(f"   命中率: {stats['hit_rate']:.2%}")

    # 显示待验证预测
    pending = ledger.get_pending_predictions()
    if pending:
        print(f"   待验证: {len(pending)} 期")
        latest = pending[-1]
        print(f"   最新待验证: {latest['issue']} -> {latest['prediction']}")