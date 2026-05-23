#!/usr/bin/env python3
"""
澳门六合预测面板 - Web服务
"""

from flask import Flask, jsonify, render_template, request
import os

app = Flask(__name__, template_folder='templates')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_DIR = os.path.join(BASE_DIR, "storage")
VERSION_BOOK_DIR = os.path.join(BASE_DIR, "version_book")

import json


def load_version_book():
    """加载版本账本"""
    index_file = os.path.join(VERSION_BOOK_DIR, "index.json")
    if not os.path.exists(index_file):
        return None
    with open(index_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_live_ledger():
    """加载实盘账本数据（predictions + results joined）"""
    predictions = []
    results = []

    pred_file = os.path.join(LEDGER_DIR, "prediction_ledger.jsonl")
    result_file = os.path.join(LEDGER_DIR, "result_ledger.jsonl")

    if os.path.exists(pred_file):
        with open(pred_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    predictions.append(json.loads(line))

    if os.path.exists(result_file):
        with open(result_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(json.loads(line))

    return predictions, results


def load_ledger_by_filter(source, version=None):
    """按 source 和 version 过滤加载账本数据

    Args:
        source: 'backtest' | 'live'
        version: 可选，如 'v12'，None 表示所有版本

    Returns:
        (predictions, results) 元组
    """
    if source == "backtest":
        return _load_backtest_ledger(version)
    elif source == "live":
        return _load_live_ledger(version)
    else:
        return [], []


def _load_backtest_ledger(version=None):
    """加载回测账本

    Args:
        version: 可选，如 'v12'，None 表示所有版本
    """
    predictions = []
    results = []

    if version:
        # 特定版本
        ledger_file = os.path.join(VERSION_BOOK_DIR, version, "backtest_ledger.jsonl")
        if os.path.exists(ledger_file):
            with open(ledger_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        predictions.append(json.loads(line))
    else:
        # 所有版本
        for v in ["v9", "v10", "v11", "v12"]:
            ledger_file = os.path.join(VERSION_BOOK_DIR, v, "backtest_ledger.jsonl")
            if os.path.exists(ledger_file):
                with open(ledger_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            predictions.append(json.loads(line))

    # 回测账本每条记录自带 actual/hit，结果直接用 predictions 中的
    # predictions 中的每条记录就是完整的（包含 actual 和 hit）
    results = [p for p in predictions if p.get("actual") is not None]

    return predictions, results


def _load_live_ledger(version=None):
    """加载实盘账本（predictions + results join）

    Args:
        version: 可选，如 'v12'，None 表示所有版本
    """
    predictions, results = load_live_ledger()

    # 按版本过滤（从 model 字段提取，如 'v12_zigzag' -> 'v12'）
    if version:
        predictions = [p for p in predictions if _extract_version(p.get("model", "")) == version]

    # 按期号排序（降序）
    predictions.sort(key=lambda x: x['issue'], reverse=True)

    # 结果按期号排序（降序）
    results.sort(key=lambda x: x['issue'], reverse=True)

    return predictions, results


def _extract_version(model_str):
    """从 model 字符串提取版本号，如 'v12_zigzag' -> 'v12'"""
    if not model_str:
        return ""
    # 提取第一个 '_' 之前的部分作为版本
    return model_str.split("_")[0] if "_" in model_str else model_str


def load_ledger():
    """加载账本数据（仅用于 /api/data，保留兼容性）"""
    predictions = []
    results = []

    pred_file = os.path.join(LEDGER_DIR, "prediction_ledger.jsonl")
    result_file = os.path.join(LEDGER_DIR, "result_ledger.jsonl")

    if os.path.exists(pred_file):
        with open(pred_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    predictions.append(json.loads(line))

    if os.path.exists(result_file):
        with open(result_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(json.loads(line))

    return predictions, results


def load_ledger_by_version(version):
    """按版本加载账本数据（唯一键 = issue+version）"""
    predictions, results = load_ledger()

    # 按版本过滤
    version_predictions = [p for p in predictions if p.get("version") == version]

    # 按期号排序（降序）
    version_predictions.sort(key=lambda x: x['issue'], reverse=True)

    # 获取该版本预测的期号集合
    pred_issues = {p["issue"] for p in version_predictions}
    version_results = [r for r in results if r["issue"] in pred_issues]

    # 结果按期号排序
    version_results.sort(key=lambda x: x['issue'], reverse=True)

    return version_predictions, version_results


def compute_stats(predictions, results):
    """计算统计数据"""
    total = len(results)
    hits = sum(1 for r in results if r.get('hit', False))
    hit_rate = hits / total if total > 0 else 0

    # 计算最高连错
    max_streak = 0
    current_streak = 0
    for r in sorted(results, key=lambda x: x['issue']):
        if not r.get('hit', False):
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    # 最近100期命中率
    recent_100 = sorted(results, key=lambda x: x['issue'], reverse=True)[:100]
    hits_100 = sum(1 for r in recent_100 if r.get('hit', False))
    hit_rate_100 = hits_100 / len(recent_100) if recent_100 else 0

    # 最近50期命中率
    recent_50 = sorted(results, key=lambda x: x['issue'], reverse=True)[:50]
    hits_50 = sum(1 for r in recent_50 if r.get('hit', False))
    hit_rate_50 = hits_50 / len(recent_50) if recent_50 else 0

    return {
        'total_predictions': len(predictions),
        'total_results': total,
        'total_hits': hits,
        'hit_rate': hit_rate,
        'hit_rate_100': hit_rate_100,
        'hit_rate_50': hit_rate_50,
        'pending': len(predictions) - total,
        'max_streak': max_streak
    }


def compute_stats_from_version_book(version_book):
    """从版本账本计算统计数据"""
    current = version_book.get("current", "v12")
    versions = version_book.get("summary", [])

    current_version = None
    for v in versions:
        if v["version"] == current:
            current_version = v
            break

    if not current_version:
        return {
            "hit_rate": 0,
            "hit_rate_100": 0,
            "hit_rate_50": 0,
            "max_streak": 0,
            "total_predictions": 0
        }

    # 从完整版本账本读取更多统计
    version_file = os.path.join(VERSION_BOOK_DIR, f"{current}.json")
    full_stats = {}
    if os.path.exists(version_file):
        with open(version_file, 'r', encoding='utf-8') as f:
            full_stats = json.load(f)

    live = full_stats.get("live", {})
    backtest = full_stats.get("backtest", {})

    return {
        "hit_rate": current_version.get("backtest_hit_rate", 0),
        "hit_rate_100": current_version.get("live_hit_rate", 0),
        "hit_rate_50": backtest.get("backtest_recent_50", 0),
        "max_streak": live.get("live_max_streak", 0),
        "total_predictions": current_version.get("live_predictions", 0)
    }


@app.route('/')
def index():
    """仪表盘主页"""
    return render_template('dashboard.html')


@app.route('/api/data')
def api_data():
    """API: 获取所有数据"""
    version_book = load_version_book()

    if version_book is None:
        return jsonify({"error": "版本账本未生成"}), 500

    predictions, results = load_ledger()

    # 去重：每个期号只保留最新的一条预测
    seen_issues = set()
    unique_predictions = []
    for p in reversed(predictions):
        if p['issue'] not in seen_issues:
            seen_issues.add(p['issue'])
            unique_predictions.append(p)
    unique_predictions.reverse()

    # 按期号排序（降序）
    unique_predictions.sort(key=lambda x: x['issue'], reverse=True)

    stats = compute_stats_from_version_book(version_book)

    result_map = {r['issue']: r for r in results}

    merged = []
    for p in unique_predictions:
        issue = p['issue']
        result = result_map.get(issue, {})
        merged.append({
            'id': p['id'],
            'issue': issue,
            'prediction': p['prediction'],
            'created_at': p['created_at'],
            'result': result.get('actual') if result else None,
            'hit': result.get('hit') if result else None,
            'resolved_at': result.get('resolved_at') if result else None
        })

    return jsonify({
        'stats': stats,
        'records': merged[:500]
    })


@app.route('/api/latest')
def api_latest():
    """API: 获取最新待验证预测"""
    predictions, results = load_ledger()
    result_map = {r['issue']: r for r in results}

    for p in reversed(predictions):
        issue = p['issue']
        if issue not in result_map:
            return jsonify({
                'pending': True,
                'prediction': p
            })

    return jsonify({'pending': False})


@app.route('/api/versions')
def api_versions():
    """API: 获取所有版本信息"""
    version_book = load_version_book()
    if version_book is None:
        return jsonify({"error": "版本账本未生成"}), 500
    return jsonify(version_book)


@app.route('/api/records')
def api_records():
    """API: 按 source 和 version 获取预测记录

    Query params:
        source: 'backtest' | 'live' (required)
        version: 可选，如 'v12'
    """
    source = request.args.get('source')
    version = request.args.get('version')

    if not source:
        return jsonify({"error": "source 参数必填"}), 400

    if source not in ("backtest", "live"):
        return jsonify({"error": "source 必须是 'backtest' 或 'live'"}), 400

    predictions, results = load_ledger_by_filter(source, version)

    stats = compute_stats(predictions, results)

    result_map = {r['issue']: r for r in results}

    merged = []
    for p in predictions:
        issue = p['issue']
        result = result_map.get(issue, {})
        merged.append({
            'id': p['id'],
            'issue': issue,
            'version': p.get('version') or _extract_version(p.get('model', '')),
            'prediction': p['prediction'],
            'created_at': p['created_at'],
            'source': source,
            'actual': result.get('actual') if result else p.get('actual'),
            'hit': result.get('hit') if result else p.get('hit'),
            'resolved_at': result.get('resolved_at') if result else None
        })

    return jsonify({
        'source': source,
        'version': version,
        'stats': stats,
        'records': merged[:500]
    })


@app.route('/api/records/<version>')
def api_records_by_version(version):
    """API: 获取指定版本的预测记录（兼容旧版路径）

    兼容处理：旧数据用 model 字段，新数据用 version 字段
    """
    predictions, results = load_ledger()

    # 直接按版本字段过滤（禁止通过时间推断版本）
    # 兼容：model 或 version 字段都支持
    def get_version(p):
        return p.get("version") or p.get("model", "").split("_")[0]

    version_predictions = [p for p in predictions if get_version(p) == version]

    # 按期号排序（降序）
    version_predictions.sort(key=lambda x: x['issue'], reverse=True)

    # 获取该版本预测的期号集合
    pred_issues = {p["issue"] for p in version_predictions}
    version_results = [r for r in results if r["issue"] in pred_issues]
    version_results.sort(key=lambda x: x['issue'], reverse=True)

    stats = compute_stats(version_predictions, version_results)

    result_map = {r['issue']: r for r in results}

    merged = []
    for p in version_predictions:
        issue = p['issue']
        result = result_map.get(issue, {})
        merged.append({
            'id': p['id'],
            'issue': issue,
            'version': get_version(p),
            'prediction': p['prediction'],
            'created_at': p['created_at'],
            'result': result.get('actual') if result else None,
            'hit': result.get('hit') if result else None,
            'resolved_at': result.get('resolved_at') if result else None
        })

    return jsonify({
        'version': version,
        'stats': stats,
        'records': merged[:500]
    })


if __name__ == '__main__':
    print("=" * 50)
    print("澳门六合预测面板启动")
    print("访问: http://localhost:5188")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5188, debug=False)