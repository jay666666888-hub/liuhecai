#!/usr/bin/env python3
"""
澳门六合预测面板 - Web服务

规则：
- Dashboard 只读 storage/aggregated_live.jsonl
- Dashboard 不扫描版本目录
- 统计从 ledger 实时计算，禁止手写 summary
"""

from flask import Flask, jsonify, render_template, request
import os
import sys
import json
import gzip
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(BASE_DIR))

app = Flask(__name__, template_folder='templates')
STORAGE_DIR = BASE_DIR / "storage"
VERSION_BOOK_DIR = BASE_DIR / "version_book"

# 数据源常量（用于统计计算隔离）
DATA_SOURCE_LIVE = "live"
DATA_SOURCE_BACKTEST = "backtest"
DATA_SOURCE_LIVE_UPDATE = "live_update"
DATA_SOURCE_SANDBOX = "sandbox"
DATA_SOURCE_REPLAY = "replay"

ALLOWED_LIVE_SOURCES = {DATA_SOURCE_LIVE, DATA_SOURCE_LIVE_UPDATE}

# Flask gzip 响应压缩
@app.after_request
def compress_response(response):
    if response.status_code != 200:
        return response
    # 仅压缩 JSON 响应且大小超过 1KB
    if response.content_type and 'application/json' in response.content_type:
        body = response.get_data()
        if len(body) > 1024:
            # 检查客户端是否接受 gzip
            if request.accept_encodings and 'gzip' in request.accept_encodings:
                try:
                    compressed = gzip.compress(body, compresslevel=6)
                    if len(compressed) < len(body):
                        response.set_data(compressed)
                        response.headers['Content-Encoding'] = 'gzip'
                        response.headers['Content-Length'] = str(len(compressed))
                        response.headers['Vary'] = 'Accept-Encoding'
                except Exception:
                    pass  # 压缩失败时返回原始响应
    return response

# Storage files
AGGREGATED_LIVE_FILE = STORAGE_DIR / "aggregated_live.jsonl"
PREDICTION_INDEX_FILE = STORAGE_DIR / "prediction_index.json"


# 统计计算优化：避免重复排序，缓存结果
# 缓存 TTL 30秒

_cache = {}
_cache_ttl = 30  # 秒

# 全量统计缓存（存储 /api/stats/all 的完整结果）
_stats_all_cache = None
_stats_all_timestamp = None


def _get_cached(key, loader, ttl=30):
    """带 TTL 的简单内存缓存"""
    now = datetime.now().timestamp()
    if key in _cache:
        data, timestamp = _cache[key]
        if now - timestamp < ttl:
            return data
    data = loader()
    _cache[key] = (data, now)
    return data


def _get_stats_all_cached(loader, ttl=30):
    """全量统计缓存 - 所有统计一次性计算和缓存"""
    global _stats_all_cache, _stats_all_timestamp
    now = datetime.now().timestamp()
    if _stats_all_cache and _stats_all_timestamp and (now - _stats_all_timestamp < ttl):
        return _stats_all_cache
    data = loader()
    _stats_all_cache = data
    _stats_all_timestamp = now
    return data


def _clear_cache():
    """清除缓存（数据更新时调用）"""
    _cache.clear()


# ========== Stats Engine 实时计算函数 ==========

def _get_stats_stats(category, stat_type):
    """调用 stats_engine 实时计算 stats（带缓存）"""
    # 延迟导入避免循环依赖
    from predictor.data_fetcher import get_all_records, build_standard_records
    from predictor.stats_engine import (
        compute_zodiac_miss,
        compute_wave_miss,
        compute_hot_stats,
        compute_special_number_miss,
    )

    # 构建 standard_records
    records = get_all_records([2024, 2025, 2026])
    standard_records = build_standard_records(records)

    # 计算 stats
    if category == "special_stats" and stat_type == "zodiac_miss":
        return compute_zodiac_miss(standard_records)
    elif category == "special_stats" and stat_type == "wave_miss":
        return compute_wave_miss(standard_records)
    elif category == "draw_stats" and stat_type == "hot_stats":
        return compute_hot_stats(standard_records)
    elif category == "number_stats" and stat_type == "special_number_miss":
        return compute_special_number_miss(standard_records)
    else:
        raise ValueError(f"Unknown stat: {category}/{stat_type}")


# ========== 数据加载 ==========

def _load_jsonl(file_path):
    """加载 JSONL 文件"""
    return _get_cached(f"jsonl:{file_path}", lambda: _load_jsonl_uncached(file_path), _cache_ttl)


def _load_jsonl_uncached(file_path):
    """加载 JSONL 文件（无缓存）"""
    records = []
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def _load_aggregated_live(version=None):
    """从 aggregated_live.jsonl 加载实盘数据（只读此文件，不扫描版本目录）"""
    cache_key = f"aggregated_live:{version or 'all'}"
    return _get_cached(cache_key, lambda: _load_aggregated_live_uncached(version), _cache_ttl)


def _load_aggregated_live_uncached(version=None):
    """从 aggregated_live.jsonl 加载实盘数据（无缓存）"""
    records = _load_jsonl_uncached(AGGREGATED_LIVE_FILE)

    if version:
        records = [r for r in records if r.get("version") == version]

    records.sort(key=lambda x: x['issue'], reverse=True)

    # 总命中率 = ALL data（backtest + live），不禁用过滤
    predictions = [r for r in records if r.get("prediction")]
    results = [r for r in records if r.get("actual") is not None]

    return predictions, results


def load_version_data(version):
    """从 aggregated_live.jsonl 加载实盘数据（只读此文件，不扫描版本目录）"""
    cache_key = f"version_data:{version}"
    return _get_cached(cache_key, lambda: _load_version_data_uncached(version), _cache_ttl)


def _load_version_data_uncached(version):
    """从 aggregated_live.jsonl 加载实盘数据（无缓存）"""
    records = _load_jsonl_uncached(AGGREGATED_LIVE_FILE)

    if version:
        records = [r for r in records if r.get("version") == version]

    records.sort(key=lambda x: x['issue'], reverse=True)

    if records:
        return {
            "records": records,
            "mode": "live",
            "source": str(AGGREGATED_LIVE_FILE)
        }

    return {"records": [], "mode": "none", "source": None}


def _load_index():
    """加载 version_book/index.json（兼容新旧结构）"""
    return _get_cached("index", _load_index_uncached, _cache_ttl)


def _load_index_uncached():
    """加载 version_book/index.json（无缓存）"""
    index_file = VERSION_BOOK_DIR / "index.json"
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)

        # 兼容新结构 {active, retired, experimental, active_by_play_type}
        if "active" in index or "retired" in index or "experimental" in index:
            return {
                "active": index.get("active", []),
                "active_by_play_type": index.get("active_by_play_type", {}),
                "retired": index.get("retired", []),
                "experimental": index.get("experimental", [])
            }
        # 旧结构 {versions, current, summary}
        return index
    return None


def _compute_summary():
    """
    从 aggregated_live.jsonl 计算 summary（委托给 summary.py）

    🚫 规则：
    - Dashboard 只读 storage/aggregated_live.jsonl
    - 禁止扫描版本目录
    - 禁止手写 summary
    """
    from predictor.summary import compute_summary
    index = _load_index()
    return compute_summary(index)


# ========== 统计计算 ==========

def _compute_cache_key(results, version):
    """
    计算缓存键：CACHE_FIX_MODE 策略

    规则：
    - stats:{version}:{latest_issue}:{latest_record_hash}
    - 若 record_hash 缺失，fallback 到 sha256(version+latest_issue+verified_count+total_hits)

    解决场景 B/C/D（status/hit/actual 修改但 count 不变）时的缓存过期问题
    """
    import hashlib

    if not results:
        return f"stats:{version or 'all'}:empty"

    # 最新记录（results 已按 issue 倒序排列）
    latest = results[0]
    latest_issue = latest.get('issue', 'unknown')
    latest_record_hash = latest.get('record_hash')

    if latest_record_hash:
        return f"stats:{version or 'all'}:{latest_issue}:{latest_record_hash}"
    else:
        # Fallback：使用数据内容哈希
        total = len(results)
        hits = sum(1 for r in results if r.get('hit', False))
        content = f"{version or 'all'}:{latest_issue}:{total}:{hits}"
        fallback_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"stats:{version or 'all'}:{latest_issue}:{fallback_hash}"


def compute_stats(predictions, results, version=None):
    """从 ledger 数据计算统计数据"""
    # 总命中率 = ALL data（backtest + live），不禁用过滤

    # 使用新缓存键策略：CACHE_FIX_MODE
    cache_key = _compute_cache_key(results, version)
    if cache_key in _cache:
        cached = _cache[cache_key]
        return cached[0] if isinstance(cached, tuple) else cached

    total = len(results)
    hits = sum(1 for r in results if r.get('hit', False))
    hit_rate = hits / total if total > 0 else 0

    # 计算最高连错（检测期号间隙，两个连续miss之间如果有gap应断链）
    max_streak = 0
    current_streak = 0
    prev_issue = None
    for r in results:
        issue = int(r.get('issue', 0))
        if prev_issue is not None and issue != prev_issue - 1:
            # Gap detected - reset streak chain
            current_streak = 0
        if not r.get('hit', False):
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0
        prev_issue = issue

    # 最近100期/50期（假设 results 已按 issue 排序）
    recent_100 = results[:100] if len(results) >= 100 else results
    recent_50 = results[:50] if len(results) >= 50 else results

    hits_100 = sum(1 for r in recent_100 if r.get('hit', False))
    hits_50 = sum(1 for r in recent_50 if r.get('hit', False))

    result = {
        'total_predictions': len(predictions),
        'total_results': total,
        'total_hits': hits,
        'hit_rate': hit_rate,
        'hit_rate_100': hits_100 / len(recent_100) if recent_100 else 0,
        'hit_rate_50': hits_50 / len(recent_50) if recent_50 else 0,
        'pending': len(predictions) - total,
        'max_streak': max_streak
    }

    _cache[cache_key] = (result, time.time())
    return result


# ========== API 路由 ==========

@app.route('/')
def index():
    """仪表盘主页"""
    return render_template('design_v3.html')


@app.route('/api/data')
def api_data():
    """API: 获取所有数据"""
    version = request.args.get('version')

    if version:
        predictions, results = _load_aggregated_live(version)
    else:
        index = _load_index()
        active = index.get("active", []) if index else []
        current_version = active[0] if active else "v24"
        predictions, results = _load_aggregated_live(current_version)

    stats = compute_stats(predictions, results, version or current_version)

    merged = []
    for p in predictions[:500]:
        merged.append({
            'id': p['id'],
            'issue': p['issue'],
            'prediction': p['prediction'],
            'created_at': p.get('created_at'),
            'actual': p.get('actual'),
            'hit': p.get('hit'),
        })

    return jsonify({
        'stats': stats,
        'version': version or current_version,
        'records': merged
    })


@app.route('/api/latest')
def api_latest():
    """API: 获取最新待验证预测（从聚合层）"""
    predictions, _ = _load_aggregated_live()

    for p in predictions:
        if p.get("status") == "pending":
            return jsonify({
                'pending': True,
                'prediction': p
            })

    return jsonify({'pending': False})


@app.route('/api/versions')
def api_versions():
    """API: 获取所有版本信息（新结构）"""
    index = _load_index()

    if index and "active" in index:
        # 新结构
        # retired 可能是 dict 列表或字符串列表，提取 version 字段
        retired_list = index.get("retired", [])
        if retired_list and isinstance(retired_list[0], dict):
            retired_list = [v['version'] for v in retired_list]
        return jsonify({
            "active": index["active"],
            "active_by_play_type": index.get("active_by_play_type", {}),
            "retired": retired_list,
            "experimental": index["experimental"],
            "all_versions": index["active"] + retired_list + index["experimental"]
        })

    # 旧格式兼容
    version_book = _compute_summary()
    return jsonify(version_book)


@app.route('/api/records')
def api_records():
    """API: 按 source 和 version 获取预测记录（只支持 live）

    Query params:
        source: 'live' (required, only live is supported)
        version: 可选，如 'v12'
    """
    source = request.args.get('source')
    version = request.args.get('version')

    if not source:
        return jsonify({"error": "source 参数必填"}), 400

    if source != "live":
        return jsonify({"error": "source 必须是 'live'（Dashboard 只读 aggregated_live.jsonl）"}), 400

    predictions, results = _load_aggregated_live(version)
    stats = compute_stats(predictions, results, version)

    merged = []
    for p in predictions[:500]:
        play_type = p.get('play_type')
        merged.append({
            'id': p['id'],
            'issue': p['issue'],
            'version': p.get('version'),
            'play_type': play_type,
            'prediction': p['prediction'],
            'created_at': p.get('created_at'),
            'source': source,
            'actual': p.get('actual'),
            'actual_list': p.get('actual_list') if play_type == 'pingte_yixiao' else None,
            'hit': p.get('hit'),
            'status': p.get('status', 'verified')
        })

    return jsonify({
        'source': source,
        'version': version,
        'stats': stats,
        'records': merged
    })


@app.route('/api/records/<version>')
def api_records_by_version(version):
    """API: 获取指定版本的预测记录（从 aggregated_live.jsonl）"""
    version_data = load_version_data(version)
    records = version_data.get("records", [])

    stats = compute_stats(records, [r for r in records if r.get("actual") is not None], version)

    merged = []
    for p in records[:500]:
        # 只对平特一肖版本返回 actual_list（完整7码用于验证）
        play_type = p.get('play_type')
        merged.append({
            'id': p.get('id'),
            'issue': p.get('issue'),
            'version': p.get('version', version),
            'play_type': play_type,
            'prediction': p.get('prediction', []),
            'created_at': p.get('created_at'),
            'actual': p.get('actual'),
            'actual_list': p.get('actual_list') if play_type == 'pingte_yixiao' else None,
            'hit': p.get('hit'),
            'status': p.get('status'),
        })

    return jsonify({
        'version': version,
        "mode": version_data.get("mode", "unknown"),
        "source": version_data.get("source"),
        'count': len(records),
        'stats': stats,
        'records': merged
    })


@app.route('/api/summary')
def api_summary():
    """API: 获取汇总统计（实时计算）"""
    index = _load_index()
    version_book = _compute_summary()

    # 额外统计
    total_versions = len(version_book.get("versions", []))
    active_versions = sum(1 for v in version_book.get("summary", []) if not v.get("frozen"))

    # 从聚合层统计总实盘预测数
    live_records = _load_jsonl(AGGREGATED_LIVE_FILE)
    verified = [r for r in live_records if r.get("actual") is not None]
    total_live = len(verified)
    live_hits = sum(1 for r in verified if r.get("hit"))
    live_hit_rate = live_hits / total_live if total_live > 0 else 0

    # 按版本统计命中率，找出最高者
    version_stats = {}
    for r in verified:
        v = r.get("version")
        if v not in version_stats:
            version_stats[v] = {"total": 0, "hits": 0}
        version_stats[v]["total"] += 1
        if r.get("hit"):
            version_stats[v]["hits"] += 1

    best_version = None
    best_hit_rate = 0
    for v, s in version_stats.items():
        if s["total"] >= 10:  # 至少10条记录才参与比较
            rate = s["hits"] / s["total"]
            if rate > best_hit_rate:
                best_hit_rate = rate
                best_version = v

    return jsonify({
        "versions": total_versions,
        "active_versions": active_versions,
        "live_predictions": total_live,
        "hit_rate": live_hit_rate,
        "best_version": best_version,
        "best_hit_rate": best_hit_rate,
        "best_version_stats": version_stats.get(best_version) if best_version else None,
        "summary": version_book.get("summary", []),
        "index": index  # 包含新结构信息
    })


# ========== 可观测性端点 ==========

def _check_data_health():
    """检查数据源健康状态"""
    import os
    from datetime import datetime

    AGGREGATED_LIVE_FILE = STORAGE_DIR / "aggregated_live.jsonl"

    check = {
        "exists": AGGREGATED_LIVE_FILE.exists(),
        "size_bytes": 0,
        "last_modified": None,
        "record_count": 0,
        "parse_ok": True,
        "error": None
    }

    if check["exists"]:
        try:
            stat = AGGREGATED_LIVE_FILE.stat()
            check["size_bytes"] = stat.st_size
            check["last_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

            # 统计记录数
            count = 0
            parse_ok = True
            with open(AGGREGATED_LIVE_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            json.loads(line)
                            count += 1
                        except:
                            parse_ok = False
                            break
            check["record_count"] = count
            check["parse_ok"] = parse_ok
        except Exception as e:
            check["error"] = str(e)
    else:
        check["error"] = "file not found"

    return check


def _check_cache_health():
    """检查缓存健康状态"""
    now = datetime.now().timestamp()

    entries = len(_cache)
    expired = 0
    timestamps = []
    for key, val in _cache.items():
        if isinstance(val, tuple) and len(val) >= 2:
            _, ts = val
            if now - ts >= _cache_ttl:
                expired += 1
            timestamps.append(ts)
        elif isinstance(val, dict):
            # Legacy format without timestamp
            expired += 1

    oldest = min(timestamps) if timestamps else None
    newest = max(timestamps) if timestamps else None

    hit_rate = 0.0
    return {
        "entries": entries,
        "hit_rate": hit_rate,
        "expired": expired,
        "oldest_entry": datetime.fromtimestamp(oldest).isoformat() if oldest else None,
        "newest_entry": datetime.fromtimestamp(newest).isoformat() if newest else None
    }


def _check_hashchain_health():
    """检查哈希链健康状态"""
    records = _load_jsonl_uncached(AGGREGATED_LIVE_FILE)

    total_records = len(records)
    chain_breaks = 0
    missing_hash = 0
    latest_hash = None

    prev_hash = None
    for r in records:
        current_hash = r.get('record_hash')
        if current_hash is None:
            missing_hash += 1
        else:
            if prev_hash is not None and r.get('prev_hash') != prev_hash:
                chain_breaks += 1
            prev_hash = current_hash

    if records:
        latest_hash = records[-1].get('record_hash')

    return {
        "total_records": total_records,
        "chain_breaks": chain_breaks,
        "missing_hash": missing_hash,
        "latest_hash": latest_hash
    }


def _check_pipeline_health():
    """检查 Pipeline 健康状态"""
    import os

    PIPELINE_LOCK_FILE = STORAGE_DIR / ".pipeline.lock"
    PIPELINE_STATUS_FILE = STORAGE_DIR / ".pipeline_status.json"

    last_run = None
    last_success = None
    runtime_seconds = None
    lock_status = "unlocked"
    circuit_breaker = "closed"

    # 检查锁文件
    if PIPELINE_LOCK_FILE.exists():
        try:
            with open(PIPELINE_LOCK_FILE, 'r') as f:
                lock_data = json.load(f)
                lock_status = f"locked (pid={lock_data.get('pid', 'unknown')})"
        except:
            lock_status = "locked (unknown)"

    # 检查状态文件
    if PIPELINE_STATUS_FILE.exists():
        try:
            with open(PIPELINE_STATUS_FILE, 'r') as f:
                status = json.load(f)
                last_run = status.get('last_run')
                last_success = status.get('last_success')
                runtime_seconds = status.get('runtime_seconds')
        except:
            pass

    # 检查 circuit breaker（来自 data_fetcher）
    try:
        from predictor.data_fetcher import get_api_health_status
        api_health = get_api_health_status()
        circuit_breaker = api_health.get('circuit_breaker', 'unknown')
    except:
        pass

    return {
        "last_run": last_run,
        "last_success": last_success,
        "runtime_seconds": runtime_seconds,
        "lock_status": lock_status,
        "circuit_breaker": circuit_breaker
    }


def _write_health_log(status, checks):
    """写健康检查日志"""
    import os
    from datetime import datetime

    LOG_DIR = BASE_DIR / "logs"
    LOG_DIR.mkdir(exist_ok=True)
    LOG_FILE = LOG_DIR / "health.log"

    failed = [c for c in checks if c.get('status') != 'ok']
    log_line = f"{datetime.now().isoformat()} status={status} failed_checks={len(failed)}\n"

    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_line)


@app.route('/health')
def api_health():
    """API: 总体健康状态"""
    checks = []

    # 数据源检查
    data_check = _check_data_health()
    if data_check["exists"] and data_check["parse_ok"]:
        data_status = "ok"
    elif not data_check["exists"]:
        data_status = "critical"
    else:
        data_status = "degraded"
    checks.append({"name": "data", "status": data_status, "details": data_check})

    # 缓存检查
    cache_check = _check_cache_health()
    cache_status = "ok" if cache_check["expired"] == 0 else "degraded"
    checks.append({"name": "cache", "status": cache_status, "details": cache_check})

    # 哈希链检查
    hashchain_check = _check_hashchain_health()
    if hashchain_check["chain_breaks"] > 0 or hashchain_check["missing_hash"] > 0:
        hashchain_status = "degraded"
    else:
        hashchain_status = "ok"
    checks.append({"name": "hashchain", "status": hashchain_status, "details": hashchain_check})

    # Pipeline 检查
    pipeline_check = _check_pipeline_health()
    if "locked" in pipeline_check.get("lock_status", ""):
        pipeline_status = "degraded"
    else:
        pipeline_status = "ok"
    checks.append({"name": "pipeline", "status": pipeline_status, "details": pipeline_check})

    # 确定总体状态
    critical_count = sum(1 for c in checks if c['status'] == 'critical')
    degraded_count = sum(1 for c in checks if c['status'] == 'degraded')

    if critical_count > 0:
        overall_status = "critical"
    elif degraded_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    # 写日志
    _write_health_log(overall_status, checks)

    return jsonify({
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "checks": checks
    })


@app.route('/health/data')
def api_health_data():
    """API: 数据源健康检查"""
    check = _check_data_health()
    return jsonify(check)


@app.route('/health/cache')
def api_health_cache():
    """API: 缓存健康检查"""
    check = _check_cache_health()
    return jsonify(check)


@app.route('/health/hashchain')
def api_health_hashchain():
    """API: 哈希链健康检查"""
    check = _check_hashchain_health()
    return jsonify(check)


@app.route('/health/pipeline')
def api_health_pipeline():
    """API: Pipeline 健康检查"""
    check = _check_pipeline_health()
    return jsonify(check)


# ========== Foundation Stats API (实时计算) ==========

@app.route('/api/stats/<category>/<stat_type>')
def api_stats(category, stat_type):
    """
    Foundation Stats 动态 API
    实时计算 stats（不再读取预生成文件）

    示例：
    /api/stats/special_stats/zodiac_miss
    /api/stats/draw_stats/hot_stats
    /api/stats/number_stats/special_number_miss
    """
    # 安全检查
    if category not in ("special_stats", "draw_stats", "number_stats"):
        return jsonify({"error": "unknown category", "type": stat_type}), 404

    # 使用缓存的实时计算
    cache_key = f"stats:{category}:{stat_type}"

    def compute_stat():
        return _get_stats_stats(category, stat_type)

    try:
        data = _get_cached(cache_key, compute_stat, 30)
        return jsonify({
            "success": True,
            "data": data,
            "cached_at": data.get("computed_at"),
            "ttl": 30
        })
    except ValueError as e:
        return jsonify({"error": str(e), "type": stat_type}), 404
    except Exception as e:
        return jsonify({"error": str(e), "type": stat_type}), 500


@app.route('/api/stats/categories')
def api_stats_categories():
    """
    获取所有 stats 类别和计算状态
    用于 Dashboard 动态发现
    """
    categories = {
        "special_stats": {
            "available_stats": ["zodiac_miss", "wave_miss"],
            "description": "生肖/波色遗漏统计"
        },
        "draw_stats": {
            "available_stats": ["hot_stats"],
            "description": "开奖热度统计"
        },
        "number_stats": {
            "available_stats": ["special_number_miss"],
            "description": "特码号码遗漏统计"
        }
    }

    return jsonify(categories)


@app.route('/api/stats/all')
def api_stats_all():
    """
    合并统计 API - 一次返回所有统计类型

    Query params:
        - precomputed=true: 使用方案C预计算数据（预留接口）
        - force_refresh=true: 强制重新计算（绕过缓存）

    返回结构:
    {
        "success": true,
        "stats": {
            "hot_stats": { ... },
            "zodiac_miss": { ... },
            "wave_miss": { ... },
            "special_number_miss": { ... }
        },
        "meta": {
            "computed_at": "...",
            "record_count": N,
            "latest_issue": "2026150",
            "cache_hit": true
        }
    }

    方案C预留: 当 precomputed=true 时，
    服务端优先从预计算文件读取（storage/stats_precomputed/）
    """
    use_precomputed = request.args.get('precomputed', 'false').lower() == 'true'
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'

    # 强制刷新时清除总缓存
    if force_refresh:
        global _stats_all_cache, _stats_all_timestamp
        _stats_all_cache = None
        _stats_all_timestamp = None

    stat_types = [
        ('hot_stats', 'draw_stats'),
        ('zodiac_miss', 'special_stats'),
        ('wave_miss', 'special_stats'),
        ('special_number_miss', 'number_stats')
    ]

    def compute_all_stats():
        """一次性计算所有统计（供缓存使用）"""
        results = {}
        computed_at = None
        record_count = 0
        latest_issue = None

        for stat_type, category in stat_types:
            try:
                data = _get_stats_stats(category, stat_type)
                results[stat_type] = data

                if not latest_issue and data.get('latest_issue'):
                    latest_issue = data['latest_issue']
                if not record_count and data.get('record_count'):
                    record_count = data['record_count']
                if not computed_at and data.get('computed_at'):
                    computed_at = data['computed_at']
            except Exception as e:
                results[stat_type] = {"error": str(e)}

        return {
            "stats": results,
            "meta": {
                "computed_at": computed_at,
                "record_count": record_count,
                "latest_issue": latest_issue
            }
        }

    # 使用全量缓存（一次性计算所有统计）
    cached_data = _get_stats_all_cached(compute_all_stats, ttl=30)

    # 检查是否来自缓存
    all_cached = _stats_all_timestamp is not None

    return jsonify({
        "success": True,
        "stats": cached_data["stats"],
        "meta": {
            "computed_at": cached_data["meta"]["computed_at"],
            "record_count": cached_data["meta"]["record_count"],
            "latest_issue": cached_data["meta"]["latest_issue"],
            "cache_hit": all_cached,
            "precomputed_mode": use_precomputed,
            "version": "2.0"
        }
    })


@app.route('/api/stats/zodiac_number_map')
def api_zodiac_number_map():
    """
    获取最新的生肖→号码动态映射
    从 build_standard_records() 实时计算
    """
    from predictor.constants import ZODIACS
    from predictor.data_fetcher import get_all_records, build_standard_records

    records = get_all_records([2024, 2025, 2026])
    standard_records = build_standard_records(records)
    if not standard_records:
        return jsonify({"error": "no data"}), 404

    # 从后往前扫，记录每个号码第一次出现时对应的生肖
    num_to_zodiac = {}
    for r in reversed(standard_records):
        special = r.get('特码号码')
        if special and special not in num_to_zodiac:
            zodiacs = r.get('开奖生肖', [])
            opencodes = r.get('开奖号码', [])
            try:
                idx = opencodes.index(int(special))
                num_to_zodiac[special] = zodiacs[idx]
            except (ValueError, IndexError):
                continue

    # 按生肖分组
    from collections import defaultdict
    zodiac_numbers = defaultdict(list)
    for num, z in num_to_zodiac.items():
        zodiac_numbers[z].append(num)

    # 构建结果 - 返回有序数组
    zodiac_order = ZODIACS
    map_list = []
    for z in zodiac_order:
        map_list.append({
            "zodiac": z,
            "numbers": sorted(zodiac_numbers.get(z, []), key=lambda x: int(x))
        })

    return jsonify({
        "success": True,
        "latest_issue": standard_records[-1].get('期号'),
        "computed_at": datetime.now().isoformat(),
        "map": map_list
    })


if __name__ == '__main__':
    print("=" * 50)
    print("澳门六合预测面板启动")
    print("访问: http://localhost:5188")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5188, debug=False)