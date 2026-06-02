#!/usr/bin/env python3
"""
澳门六合数据获取模块
- 使用官方 API: https://history.macaumarksix.com/history/macaujc2/y/${year}
- 特码生肖：zodiac[6]（官方直接给出，无需额外映射）
- 警告：extract_zodiac_mapping 基于错误假设，不再使用

RESILIENCE_MODE:
- Retry: 3 attempts with exponential backoff (1s, 2s, 4s)
- Timeout: connect=5s, read=10s
- Cache fallback: on API failure, use latest cached data (marked source=cache)
- Circuit breaker: after 3 consecutive failures, open for 30 minutes
"""

import json
import os
import time
import warnings
import requests
from datetime import datetime
from typing import List, Dict, Optional
from collections import Counter
from pathlib import Path

# API 配置
API_BASE = "https://history.macaumarksix.com/history/macaujc2/y"
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# RESILIENCE_MODE 配置
RETRY_CONFIG = {
    "attempts": 3,
    "backoff": [1, 2, 4],  # seconds
    "connect_timeout": 5,
    "read_timeout": 10,
}
CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 3,
    "recovery_timeout": 30 * 60,  # 30 minutes in seconds
}
CACHE_METADATA_FILE = os.path.join(CACHE_DIR, "_cache_metadata.json")

# Circuit breaker 持久化状态文件
_CIRCUIT_STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "runtime", "circuit_breaker.json"
)


# Circuit breaker state
_circuit_state = {
    "failures": 0,
    "opened_at": None,
    "last_error": None,
}


def _load_circuit_state():
    """从持久化文件加载 circuit breaker 状态"""
    global _circuit_state
    if os.path.exists(_CIRCUIT_STATE_FILE):
        try:
            with open(_CIRCUIT_STATE_FILE, 'r') as f:
                state = json.load(f)
                _circuit_state["failures"] = state.get("failures", 0)
                _circuit_state["opened_at"] = state.get("opened_at")
                _circuit_state["last_error"] = state.get("last_error")
        except:
            pass


def _save_circuit_state():
    """保存 circuit breaker 状态到持久化文件"""
    os.makedirs(os.path.dirname(_CIRCUIT_STATE_FILE), exist_ok=True)
    with open(_CIRCUIT_STATE_FILE, 'w') as f:
        json.dump(_circuit_state, f, ensure_ascii=False, indent=2)


# 启动时加载持久化状态
_load_circuit_state()


def _get_cache_metadata() -> Dict:
    """获取缓存元数据"""
    if os.path.exists(CACHE_METADATA_FILE):
        with open(CACHE_METADATA_FILE, "r") as f:
            return json.load(f)
    return {"last_api_success": None, "last_cache_read": None, "source": None}


def _save_cache_metadata(metadata: Dict):
    """保存缓存元数据"""
    with open(CACHE_METADATA_FILE, "w") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def _is_circuit_open() -> bool:
    """检查 circuit breaker 是否打开"""
    global _circuit_state

    if _circuit_state["opened_at"] is None:
        return False

    # 检查是否超过恢复时间
    elapsed = time.time() - _circuit_state["opened_at"]
    if elapsed > CIRCUIT_BREAKER_CONFIG["recovery_timeout"]:
        # 恢复时间已过，尝试半开，重置状态
        _circuit_state["opened_at"] = None
        _circuit_state["failures"] = 0
        _save_circuit_state()
        return False

    return True


def _record_failure(error: str):
    """记录失败，增加失败计数"""
    global _circuit_state

    _circuit_state["failures"] += 1
    _circuit_state["last_error"] = error

    if _circuit_state["failures"] >= CIRCUIT_BREAKER_CONFIG["failure_threshold"]:
        _circuit_state["opened_at"] = time.time()

    _save_circuit_state()


def _record_success():
    """记录成功，重置计数器"""
    global _circuit_state

    _circuit_state["failures"] = 0
    _circuit_state["opened_at"] = None
    _circuit_state["last_error"] = None

    _save_circuit_state()
    _circuit_state["opened_at"] = None
    _circuit_state["last_error"] = None


def fetch_year_data(
    year: int,
    force_refresh: bool = False,
    _internal_call: bool = False
) -> List[Dict]:
    """
    获取指定年份数据（带 RESILIENCE_MODE）

    Args:
        year: 年份
        force_refresh: 强制从 API 重新获取
        _internal_call: 内部调用标志，用于避免递归 circuit breaker 检查

    Returns:
        records: 记录列表
        source: 数据来源 ("api" 或 "cache")
    """
    cache_path = os.path.join(CACHE_DIR, f"liuhecai_{year}.json")

    # 检查 circuit breaker
    if _is_circuit_open():
        print(f"[警告] Circuit breaker 打开，跳过 API 调用，使用缓存")
        return _load_cached_data_or_empty(cache_path)

    # 尝试从缓存加载
    if not force_refresh and os.path.exists(cache_path):
        cached = _load_cached_data_or_empty(cache_path)
        if cached:
            metadata = _get_cache_metadata()
            metadata["last_cache_read"] = datetime.now().isoformat()
            metadata["source"] = "cache"
            _save_cache_metadata(metadata)
            return cached

    # 尝试 API 调用（带 retry）
    for attempt in range(RETRY_CONFIG["attempts"]):
        try:
            url = f"{API_BASE}/{year}"
            resp = requests.get(
                url,
                timeout=(
                    RETRY_CONFIG["connect_timeout"],
                    RETRY_CONFIG["read_timeout"]
                )
            )
            resp.raise_for_status()
            data = resp.json()

            if not data.get("result"):
                raise ValueError(f"API返回失败: {data.get('message')}")

            records = data["data"]

            # 保存缓存
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)

            # 记录成功
            _record_success()
            metadata = _get_cache_metadata()
            metadata["last_api_success"] = datetime.now().isoformat()
            metadata["source"] = "api"
            _save_cache_metadata(metadata)

            return records

        except requests.exceptions.Timeout:
            error_msg = f"API 超时 (attempt {attempt + 1}/{RETRY_CONFIG['attempts']})"
            print(f"[警告] {error_msg}")
            _record_failure(error_msg)

        except requests.exceptions.ConnectionError as e:
            error_msg = f"API 连接失败 (attempt {attempt + 1}/{RETRY_CONFIG['attempts']}): {e}"
            print(f"[警告] {error_msg}")
            _record_failure(str(e))

        except requests.exceptions.HTTPError as e:
            error_msg = f"API HTTP 错误 (attempt {attempt + 1}/{RETRY_CONFIG['attempts']}): {e}"
            print(f"[警告] {error_msg}")
            _record_failure(str(e))

        except Exception as e:
            error_msg = f"API 未知错误 (attempt {attempt + 1}/{RETRY_CONFIG['attempts']}): {e}"
            print(f"[警告] {error_msg}")
            _record_failure(str(e))

        # 如果不是最后一次尝试，等待 backoff
        if attempt < RETRY_CONFIG["attempts"] - 1:
            backoff_time = RETRY_CONFIG["backoff"][attempt]
            print(f"[重试] 等待 {backoff_time}s 后重试...")
            _stats["retries"] += 1
            time.sleep(backoff_time)

    # 所有重试都失败了，使用缓存
    print(f"[回退] API 不可用，使用缓存数据")
    metadata = _get_cache_metadata()
    metadata["source"] = "cache"
    _save_cache_metadata(metadata)

    return _load_cached_data_or_empty(cache_path)


def _load_cached_data_or_empty(cache_path: str) -> List[Dict]:
    """加载缓存数据，如果不存在返回空列表"""
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def get_api_health_status() -> Dict:
    """
    获取 API 健康状态（用于监控）

    Returns:
        {
            "circuit_breaker": "open" | "closed",
            "consecutive_failures": int,
            "last_error": str | None,
            "last_api_success": str | None,
            "cache_availability": "fresh" | "stale" | "none"
        }
    """
    metadata = _get_cache_metadata()
    cache_available = "none"

    # 检查缓存新鲜度
    for year in [datetime.now().year, datetime.now().year - 1]:
        cache_path = os.path.join(CACHE_DIR, f"liuhecai_{year}.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    data = json.load(f)
                    if data:
                        cache_available = "fresh" if metadata.get("last_api_success") else "stale"
                        break
            except:
                pass

    return {
        "circuit_breaker": "open" if _is_circuit_open() else "closed",
        "consecutive_failures": _circuit_state["failures"],
        "last_error": _circuit_state["last_error"],
        "last_api_success": metadata.get("last_api_success"),
        "cache_availability": cache_available,
        "source": metadata.get("source"),
    }


# ============================================================
# 以下为原有函数，接口不变
# ============================================================

# 生肖列表
ZODIACS = ["鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"]


# ============================================================
# 统计计数器（用于监控）
# ============================================================
_stats = {
    "api_calls": 0,
    "api_success": 0,
    "api_failure": 0,
    "cache_fallback": 0,
    "retries": 0,
}


def get_stats() -> Dict:
    """获取统计数据"""
    return dict(_stats)


def _reset_stats():
    """重置统计（用于测试）"""
    global _stats
    _stats = {
        "api_calls": 0,
        "api_success": 0,
        "api_failure": 0,
        "cache_fallback": 0,
        "retries": 0,
    }


# ============================================================
# 以下为原有函数，接口不变
# ============================================================

def get_special_zodiac(record: Dict) -> str:
    """获取特码生肖（官方直接给出）- 唯一合法来源"""
    return record["zodiac"].split(",")[6]


def get_special_number(record: Dict) -> int:
    """获取特码号码"""
    return int(record["openCode"].split(",")[6])


def get_all_records(years: List[int] = None, force_refresh: bool = False) -> List[Dict]:
    """获取多年数据，按时间正序排列"""
    global _stats

    if years is None:
        years = [datetime.now().year]

    all_records = []
    seen_periods = set()  # 去重
    for year in sorted(set(years)):
        # 新调用使用 resilience 模式的 fetch_year_data
        records = fetch_year_data(year, force_refresh=force_refresh, _internal_call=True)
        _stats["api_calls"] += 1
        if records:
            # 检查数据来源
            metadata = _get_cache_metadata()
            if metadata.get("source") == "api":
                _stats["api_success"] += 1
            else:
                _stats["cache_fallback"] += 1
        else:
            _stats["api_failure"] += 1

        for r in records:
            if r["expect"] not in seen_periods:
                seen_periods.add(r["expect"])
                all_records.append(r)

    # 按期号排序
    all_records.sort(key=lambda x: x["expect"])
    return all_records


def build_standard_records(records: List[Dict]) -> List[Dict]:
    """构建标准化记录（用于预测）

    Args:
        records: API返回的原始记录列表

    Returns:
        标准化记录列表，每条包含:
        - 期号: str
        - 特码生肖: str (直接来自API的zodiac[6])
        - 其他字段...
    """
    result = []
    for r in records:
        special_num = get_special_number(r)
        special_zodiac = get_special_zodiac(r)  # 直接使用API数据
        result.append({
            "期号": r["expect"],
            "开奖时间": r["openTime"],
            "特码号码": str(special_num),
            "特码生肖": special_zodiac,  # 直接来自API，无二次映射
            "波色": r["wave"].split(",")[6],
            "开奖号码": r["openCode"].split(","),
            "开奖生肖": r["zodiac"].split(","),
            "波色列表": r["wave"].split(","),
        })
    return result


# ============================================================
# 以下函数已废弃，不再使用
# ============================================================

def extract_zodiac_mapping(records: List[Dict]) -> Dict[int, str]:
    """
    DEPRECATED: 此函数基于错误假设（号码固定对应生肖）

    实际上生肖映射是按年动态变化的，每年的映射都不同。
    请使用 get_special_zodiac(record) 直接从API获取特码生肖。

    保留此函数仅用于向后兼容，将在后续版本中移除。
    """
    warnings.warn(
        "extract_zodiac_mapping is deprecated. "
        "Use get_special_zodiac(record) directly from API data. "
        "Zodiac mapping is per-year dynamic, not fixed.",
        DeprecationWarning,
        stacklevel=2
    )

    # 返回空映射，强制调用方使用正确的方法
    return {}


def validate_zodiac_mapping(mapping: Dict[int, str], records: List[Dict]) -> float:
    """
    DEPRECATED: 此函数不再使用
    """
    warnings.warn(
        "validate_zodiac_mapping is deprecated. "
        "API data is already validated.",
        DeprecationWarning,
        stacklevel=2
    )
    return 0.0


if __name__ == "__main__":
    # 测试
    records = get_all_records([2024, 2025])
    print(f"获取 {len(records)} 条记录")
    print(f"最新期号: {records[-1]['expect']}")
    print(f"特码生肖: {get_special_zodiac(records[-1])}")

    # 测试标准记录
    standard = build_standard_records(records)
    print(f"标准记录: {len(standard)} 条")
    print(f"最新: {standard[-1]['期号']} -> {standard[-1]['特码生肖']}")