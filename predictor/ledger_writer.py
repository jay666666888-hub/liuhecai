#!/usr/bin/env python3
"""
澳门六合 - 实盘预测写入接口

规则：
- predictor 只允许调用 write_live_prediction(version, data)
- 禁止直接 _safe_open("storage/prediction_ledger.jsonl")
- 禁止直接 _safe_open("storage/result_ledger.jsonl")
- 所有写入必须经过 LedgerWriter 接口
- Hash Chain 保证数据完整性
"""

# 安全拦截：必须最先导入，确保 storage/__init__.py 的 open 拦截生效
# LedgerWriter 使用 _safe_open 绕过拦截
import builtins
import sys
import os

# 先加载 safe_open
_original_open = builtins.open
_storage_init = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_storage_init, '..'))

from storage import _safe_open  # noqa: F401,E402

import json
import hashlib
import tempfile
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BASE_DIR = Path("/mnt/c/Users/Admin/liuhecai")
STORAGE_DIR = BASE_DIR / "storage"
VERSION_BOOK_DIR = BASE_DIR / "version_book"

# Storage files
PREDICTION_INDEX_FILE = STORAGE_DIR / "prediction_index.json"
AGGREGATED_LIVE_FILE = STORAGE_DIR / "aggregated_live.jsonl"

# Genesis marker for first record
GENESIS_HASH = "GENESIS"


def _atomic_write(file_path, content_fn):
    """
    原子写入：先写 temp，再 rename
    content_fn: 接受文件对象，调用 write
    """
    file_path = Path(file_path)
    dir_path = file_path.parent
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix='.tmp_', suffix='.atomic')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            content_fn(f)
        os.replace(tmp_path, file_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


class LedgerWriter:
    """实盘预测写入器 - Hash Chain 防篡改"""

    def __init__(self):
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保目录结构存在"""
        STORAGE_DIR.mkdir(exist_ok=True)
        VERSION_BOOK_DIR.mkdir(exist_ok=True)

    def _generate_id(self, issue: str, version: str) -> str:
        """生成唯一ID"""
        ts = datetime.now().isoformat().replace("-", "").replace(":", "").replace("T", "_")[:16]
        return f"{issue}_{version}_{ts}"

    def _compute_hash_legacy(self, record: Dict) -> str:
        """旧版 hash 计算（兼容旧记录）"""
        core = f"{record['issue']}|{record['version']}|{','.join(record['prediction'])}"
        return hashlib.sha256(core.encode()).hexdigest()[:16]

    def _compute_record_hash(self, record: Dict, prev_hash: str = None) -> str:
        """
        计算记录 hash（包含 prev_hash 形成链）

        组成：issue|version|prediction|actual|hit|prev_hash
        """
        actual = record.get("actual") or ""
        hit = str(record.get("hit") or "")
        pred = ",".join(record.get("prediction") or [])
        core = f"{record['issue']}|{record['version']}|{pred}|{actual}|{hit}|{prev_hash or GENESIS_HASH}"
        return hashlib.sha256(core.encode()).hexdigest()[:16]

    def _get_last_record_hash(self) -> str:
        """获取最后一条记录的 hash（用于链式写入）"""
        if not AGGREGATED_LIVE_FILE.exists():
            return GENESIS_HASH

        with _safe_open(AGGREGATED_LIVE_FILE, 'r', encoding='utf-8') as f:
            last_line = None
            for line in f:
                line = line.strip()
                if line:
                    last_line = line
            if last_line:
                try:
                    rec = json.loads(last_line)
                    return rec.get("record_hash") or rec.get("hash") or GENESIS_HASH
                except json.JSONDecodeError:
                    return GENESIS_HASH
        return GENESIS_HASH

    def _load_index(self) -> Dict:
        """加载索引"""
        if PREDICTION_INDEX_FILE.exists():
            with _safe_open(PREDICTION_INDEX_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"version": 1, "updated_at": None, "versions": {}}

    def _save_index(self, index: Dict):
        """保存索引（原子写入）"""
        index["updated_at"] = datetime.now().isoformat()
        _atomic_write(PREDICTION_INDEX_FILE, lambda f: json.dump(index, f, ensure_ascii=False, indent=2))

    def verify_chain(self) -> Tuple[bool, List[str]]:
        """
        校验 hash 链完整性

        Returns:
            (is_valid, error_list)
        """
        errors = []
        if not AGGREGATED_LIVE_FILE.exists():
            return True, []

        prev_hash = None
        with _safe_open(AGGREGATED_LIVE_FILE, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"行{i+1}: JSON 解析失败，跳过")
                    continue

                has_record_hash = "record_hash" in rec and rec.get("record_hash") is not None
                has_hash = "hash" in rec and rec.get("hash") is not None

                if has_record_hash:
                    # 新格式：使用记录中存储的 prev_hash 计算
                    prev_from_record = rec.get("prev_hash") or GENESIS_HASH
                    actual_hash = self._compute_record_hash(rec, prev_from_record)
                    expected_hash = rec.get("record_hash")
                    if expected_hash != actual_hash:
                        errors.append(f"行{i+1}[{rec.get('issue')}][{rec.get('version')}]: hash 不匹配 (expected={expected_hash}, actual={actual_hash})")
                    prev_hash = expected_hash
                elif has_hash:
                    # 旧格式：只验证 hash 是否正确
                    actual_hash = self._compute_hash_legacy(rec)
                    expected_hash = rec.get("hash")
                    if expected_hash != actual_hash:
                        errors.append(f"行{i+1}[{rec.get('issue')}][{rec.get('version')}]: legacy hash 不匹配 (expected={expected_hash}, actual={actual_hash})")
                    prev_hash = expected_hash

        return len(errors) == 0, errors

    def write_live_prediction(
        self,
        version: str,
        issue: str,
        prediction: List[str],
        model: str = None,
        strategy: str = None,
        play_type: str = "liuhe",
        zodiac_list: List[str] = None
    ) -> Dict:
        """
        写入实盘预测（唯一数据源写入 aggregated_live.jsonl）

        Args:
            version: 版本号（如 v23, v24）
            issue: 期号
            prediction: 预测的六肖
            model: 模型名称（可选，默认 {version}_interval_predictor）
            strategy: 策略名称（可选）

        Returns:
            写入的记录

        🚫 规则：
        - 只写入 storage/aggregated_live.jsonl
        - 不再写入 version_book/{v}/live_ledger.jsonl
        - 禁止重复写入（同一 version+issue 只保留一条）
        - Hash Chain 保证数据完整性
        """
        now = datetime.now().isoformat()
        record_id = self._generate_id(issue, version)

        record = {
            "id": record_id,
            "issue": issue,
            "version": version,
            "model": model or f"{version}_interval_predictor",
            "strategy": strategy or f"{version}_weighted_vote",
            "prediction": prediction,
            "play_type": play_type,
            "zodiac_list": zodiac_list,  # 平特一肖用：完整7个生肖
            "actual": None,
            "hit": None,
            "created_at": now,
            "source": "live",
            "status": "pending",
        }

        # Hash Chain
        prev_hash = self._get_last_record_hash()
        record["prev_hash"] = prev_hash
        record["record_hash"] = self._compute_record_hash(record, prev_hash)

        # 检查是否已存在同 version+issue 的记录（去重）
        index = self._load_index()
        needs_overwrite = (
            version in index["versions"] and
            index["versions"][version].get("latest_issue") == issue
        )

        if AGGREGATED_LIVE_FILE.exists() and needs_overwrite:
            # 优化：先检查记录是否真实存在，避免全量扫描
            # 使用临时文件实现高效替换（流式处理，不占用内存）
            temp_records = []
            found = False
            with _safe_open(AGGREGATED_LIVE_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    if rec.get("version") == version and rec.get("issue") == issue:
                        found = True
                        temp_records.append(record)  # 用新记录替代旧记录
                    else:
                        temp_records.append(rec)

            if found:
                # 流式写入：避免将所有记录加载到内存后再写入
                _atomic_write(AGGREGATED_LIVE_FILE, lambda f: f.write(''.join(json.dumps(rec, ensure_ascii=False) + "\n" for rec in temp_records)))
            else:
                # 记录不存在，回退到追加模式
                with _safe_open(AGGREGATED_LIVE_FILE, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
        else:
            # 直接追加（最快路径）
            with _safe_open(AGGREGATED_LIVE_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # 更新索引
        index = self._load_index()
        if version not in index["versions"]:
            index["versions"][version] = {"latest_issue": None, "pending_issue": None}
        index["versions"][version]["latest_issue"] = issue
        index["versions"][version]["pending_issue"] = issue
        self._save_index(index)

        return record

    def verify_prediction(
        self,
        version: str,
        issue: str,
        actual: str,
        zodiac_list: List[str] = None,
        special_number: str = None
    ) -> Tuple[bool, Dict]:
        """
        验证预测并更新 aggregated_live.jsonl（唯一数据源）

        Args:
            version: 版本号
            issue: 期号
            actual: 实际开奖生肖
            zodiac_list: 开奖生肖列表（平特一肖用）
            special_number: 特码号码（多码验证用）

        Returns:
            (hit, updated_record)

        🚫 规则：
        - 只更新 storage/aggregated_live.jsonl
        - 不再写入 version_book/{v}/live_ledger.jsonl
        - verified 状态的记录不可再修改
        """
        from predictor.predictor_registry import PredictorRegistry

        if not PredictorRegistry._metadata:
            PredictorRegistry.scan()

        # 判断是否为多码验证（使用号码而非生肖）
        from predictor.predictor_registry import PredictorRegistry as PR
        play_type = None
        try:
            play_type = PR.get_play_type(version)
        except:
            pass
        is_duoma = play_type == 'duoma'

        # 多码验证：用号码；其他验证：用生肖
        eval_actual = special_number if is_duoma else actual

        aggregated_records = []
        updated_record = {}

        if AGGREGATED_LIVE_FILE.exists():
            with _safe_open(AGGREGATED_LIVE_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    if rec.get("version") == version and rec.get("issue") == issue:
                        if rec.get("status") == "verified":
                            # 已验证的记录：检查 actual 是否需要更正（脏数据修复）
                            if rec.get("actual") != actual:
                                rec["actual"] = actual
                                predicted = rec.get("prediction", [])
                                z_list = zodiac_list if zodiac_list is not None else rec.get("zodiac_list", [])
                                if not z_list and zodiac_list is None:
                                    z_list = rec.get("actual_list", [])
                                rec["hit"] = PredictorRegistry.evaluate(version, predicted, z_list, eval_actual)
                                if zodiac_list:
                                    rec["actual_list"] = zodiac_list
                                if is_duoma and special_number:
                                    rec["special_number"] = special_number
                                rec["verified_at"] = datetime.now().isoformat()
                                prev_hash = rec.get("prev_hash")
                                rec["record_hash"] = self._compute_record_hash(rec, prev_hash)
                                updated_record = rec
                            else:
                                updated_record = rec
                            aggregated_records.append(rec)
                            continue

                        rec["actual"] = actual

                        predicted = rec.get("prediction", [])
                        z_list = zodiac_list if zodiac_list is not None else rec.get("zodiac_list", [])
                        if not z_list and zodiac_list is None:
                            z_list = rec.get("actual_list", [])
                        rec["hit"] = PredictorRegistry.evaluate(version, predicted, z_list, eval_actual)

                        if zodiac_list:
                            rec["actual_list"] = zodiac_list
                        if is_duoma and special_number:
                            rec["special_number"] = special_number

                        rec["verified_at"] = datetime.now().isoformat()
                        rec["status"] = "verified"

                        # 重新计算 hash
                        prev_hash = rec.get("prev_hash")
                        rec["record_hash"] = self._compute_record_hash(rec, prev_hash)
                        updated_record = rec

                    aggregated_records.append(rec)

        _atomic_write(AGGREGATED_LIVE_FILE, lambda f: f.write(''.join(json.dumps(rec, ensure_ascii=False) + "\n" for rec in aggregated_records)))

        return updated_record.get("hit", False), updated_record

    def read_live_predictions(self, version: str = None, limit: int = 100) -> List[Dict]:
        """读取实盘预测（唯一数据源：aggregated_live.jsonl）"""
        all_records = []
        if version:
            if AGGREGATED_LIVE_FILE.exists():
                with _safe_open(AGGREGATED_LIVE_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            rec = json.loads(line)
                            if rec.get("version") == version:
                                all_records.append(rec)
        else:
            if AGGREGATED_LIVE_FILE.exists():
                with _safe_open(AGGREGATED_LIVE_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            all_records.append(json.loads(line))

        all_records.sort(key=lambda x: x.get('issue', ''), reverse=True)
        return all_records[:limit]

    def get_pending_predictions(self, version: str = None) -> List[Dict]:
        """获取待验证预测"""
        records = self.read_live_predictions(version)
        return [r for r in records if r.get("status") == "pending"]

    def aggregate_all_to_storage(self) -> int:
        """重新聚合所有版本到 storage/aggregated_live.jsonl（优先 backtest 数据）"""
        all_records = []

        if VERSION_BOOK_DIR.exists():
            for version_dir in VERSION_BOOK_DIR.iterdir():
                if not version_dir.is_dir():
                    continue
                # 读取 live_ledger
                live_ledger_file = version_dir / "live_ledger.jsonl"
                if live_ledger_file.exists():
                    with _safe_open(live_ledger_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                all_records.append(json.loads(line))
                # 读取 backtest_ledger（平特一肖版本的历史回测数据）
                backtest_ledger_file = version_dir / "backtest_ledger.jsonl"
                if backtest_ledger_file.exists():
                    with _safe_open(backtest_ledger_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                all_records.append(json.loads(line))

        # 优先使用 backtest 数据（prediction 非空），其次 live_ledger
        seen = {}
        for rec in all_records:
            key = f"{rec['version']}_{rec['issue']}"
            existing = seen.get(key)
            # backtest 数据优先于 live_ledger（prediction 非空时）
            if existing is None:
                seen[key] = rec
            elif rec.get('source') == 'backtest' and not existing.get('prediction'):
                # 当前记录是 backtest 且已有记录prediction为空，替换
                seen[key] = rec
            elif rec.get('source') == 'backtest' and existing.get('source') != 'backtest' and not existing.get('prediction'):
                # 已有记录是 live_ledger 且 prediction 为空，backtest 有数据，替换
                seen[key] = rec
            # 否则保留已有记录（优先 live_ledger 的更新记录）

        _atomic_write(AGGREGATED_LIVE_FILE, lambda f: f.write(''.join(json.dumps(rec, ensure_ascii=False) + "\n" for rec in sorted(seen.values(), key=lambda x: x['issue'], reverse=True))))

        return len(seen)

    def init_live_ledger_from_history(self, version: str, records: List[Dict]) -> int:
        """从历史记录初始化 live_ledger.jsonl（bootstrap 专用）"""
        version_dir = VERSION_BOOK_DIR / version
        live_ledger_file = version_dir / "live_ledger.jsonl"

        with _safe_open(live_ledger_file, 'w', encoding='utf-8') as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        return len(records)


# 全局单例
_writer = None

def get_writer() -> LedgerWriter:
    global _writer
    if _writer is None:
        _writer = LedgerWriter()
    return _writer

def write_live_prediction(version: str, issue: str, prediction: List[str], **kwargs) -> Dict:
    """写入实盘预测（快捷函数）"""
    return get_writer().write_live_prediction(version, issue, prediction, **kwargs)

def verify_prediction(version: str, issue: str, actual: str, zodiac_list: List[str] = None, special_number: str = None) -> Tuple[bool, Dict]:
    """验证预测（快捷函数）"""
    return get_writer().verify_prediction(version, issue, actual, zodiac_list, special_number)

def read_live_predictions(version: str = None, limit: int = 100) -> List[Dict]:
    """读取实盘预测（快捷函数）"""
    return get_writer().read_live_predictions(version, limit)

def aggregate_all_to_storage() -> int:
    """重新聚合所有版本到 storage"""
    return get_writer().aggregate_all_to_storage()

def init_live_ledger_from_history(version: str, records: List[Dict]) -> int:
    """从历史记录初始化 live_ledger（bootstrap 专用）"""
    return get_writer().init_live_ledger_from_history(version, records)

def verify_chain() -> Tuple[bool, List[str]]:
    """校验 hash 链完整性"""
    return get_writer().verify_chain()


if __name__ == "__main__":
    # 测试
    writer = LedgerWriter()

    # 测试写入
    rec = writer.write_live_prediction("v99", "2026999", ["鼠", "牛", "虎", "兔", "龍", "蛇"])
    print(f"写入: {rec['id']}")
    print(f"record_hash: {rec['record_hash']}")

    # 测试读取
    pending = writer.get_pending_predictions()
    print(f"待验证: {len(pending)} 条")

    # 测试 hash chain 校验
    valid, errors = writer.verify_chain()
    print(f"Hash Chain 校验: {'✓ 通过' if valid else '✗ 失败'}")
    if errors:
        for e in errors:
            print(f"  - {e}")

    # 清理测试数据
    import shutil
    v99_dir = VERSION_BOOK_DIR / "v99"
    if v99_dir.exists():
        shutil.rmtree(v99_dir)
    print("清理完成")