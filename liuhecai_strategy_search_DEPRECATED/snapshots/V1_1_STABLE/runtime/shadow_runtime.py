"""
Shadow Mode Runtime - 运行预测但不修改任何核心逻辑

冻结: /experts/, /meta_v2/, /tests/
状态: SYSTEM_RUNNING | DEVELOPMENT_FROZEN

故障触发条件（允许开发）:
- hit_rate 连续低于 0.45
- drawdown 持续恶化
- StateDetector 异常
- 某专家连续失效
"""
import json
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/home/admin1/liuhecai_strategy_search")
RUNTIME_DIR = BASE_DIR / "runtime"
PREDICTIONS_DIR = RUNTIME_DIR / "predictions"
ACTUAL_RESULTS_DIR = RUNTIME_DIR / "actual_results"
DAILY_METRICS_DIR = RUNTIME_DIR / "daily_metrics"
SHADOW_REPORTS_DIR = RUNTIME_DIR / "shadow_reports"
SNAPSHOTS_DIR = RUNTIME_DIR / "snapshots"

# 数据文件
DATA_FILE = BASE_DIR / "zodiac_validation.csv"

# 系统状态
STATE_FILE = RUNTIME_DIR / "system_state.json"
LAST_PREDICTION_FILE = PREDICTIONS_DIR / "latest_prediction.json"
LAST_METRICS_FILE = DAILY_METRICS_DIR / "latest_metrics.json"

# 故障阈值
HIT_RATE_THRESHOLD = 0.45
DRAWDOWN_TRIGGER = -0.15
CONSECUTIVE_FAILURES = 5

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


def ensure_dirs():
    """确保运行时目录结构存在"""
    for d in [PREDICTIONS_DIR, ACTUAL_RESULTS_DIR, DAILY_METRICS_DIR, SHADOW_REPORTS_DIR, SNAPSHOTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_data():
    """加载数据文件并适配格式

    CSV格式: period,date,zodiac_year,number,raw_zodiac,calc_zodiac,match
    - calc_zodiac: 实际开奖的生肖（当前期目标）
    - raw_zodiac: 简单期结果

    适配 MetaStrategyV2 期望的格式:
    - zodiac: 当前期 target (calc_zodiac)
    - zodiacs: 每行的生肖列表（7个，从历史数据计算）
    """
    import pandas as pd
    df = pd.read_csv(DATA_FILE)

    # 使用 calc_zodiac 作为 zodiac (target)
    # calc_zodiac 是当前期的 special_zodiac
    df['zodiac'] = df['calc_zodiac']

    # 创建 zodiacs 列 - 模拟每行7个生肖的列表
    # 由于真实数据是单行单生肖格式，我们需要创建模拟的 zodiacs
    # 这可以通过 sliding window 实现：用最近7期的 raw_zodiac 作为 zodiacs
    if 'zodiacs' not in df.columns:
        # 使用 rolling window 创建 zodiacs
        # 每行的 zodiacs = [prev6_raw, prev5_raw, ..., curr_raw]
        # 这样当前期的 special_zodiac (calc_zodiac) 可以与 zodiacs 中匹配

        # 由于数据结构限制，我们使用一个简化方法：
        # zodiacs = [raw_zodiac] * 7 (作为模拟)
        # 这意味着每行都预测所有生肖

        # 更好的方法：从 historical data 计算
        raw_list = df['raw_zodiac'].tolist() if 'raw_zodiac' in df.columns else ['鼠'] * len(df)

        zodiacs_list = []
        for i in range(len(df)):
            # 取最近7期（如果不足7期，用历史available的）
            start_idx = max(0, i - 6)
            window = raw_list[start_idx:i+1]

            # 如果不足7个，用 '鼠' 补齐
            while len(window) < 7:
                window = ['鼠'] + window

            # 刚好7个
            if len(window) == 7:
                zodiacs_list.append(window)
            else:
                # 取最后7个
                zodiacs_list.append(window[-7:])

        df['zodiacs'] = zodiacs_list

    return df


def load_system_state():
    """加载系统状态"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        "mode": "SHADOW_MODE_V1",
        "status": "INITIAL",
        "total_predictions": 0,
        "last_update": None,
        "fault_triggers": []
    }


def save_system_state(state):
    """保存系统状态"""
    state["last_update"] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def run_prediction(df, upto_idx):
    """
    运行预测 - 仅使用冻结的专家逻辑
    不修改任何核心文件
    """
    import sys
    sys.path.insert(0, str(BASE_DIR))

    from meta_v2.meta_strategy_v2 import MetaStrategyV2

    # 创建策略实例
    ms = MetaStrategyV2(df)

    # 获取市场状态
    entropy, volatility, stability, regime_shift = ms._calc_state_features(upto_idx)
    ms.state_detector.update(entropy, volatility, stability, regime_shift)
    current_state = ms.state_detector.detect_state()

    # 获取专家评分
    expert_scores = ms._get_expert_scores(upto_idx)
    ms._current_expert_scores = expert_scores

    # 执行预测（使用当前冻结的聚合逻辑）
    top6, report = ms.predict_top6()

    # 提取专家权重
    expert_weights = report.get("base_weights", {})
    aggregation = report.get("aggregation", {})

    # 计算置信度（基于expert_confidences的离散度）
    confidences = aggregation.get("expert_confidences", {})
    avg_confidence = sum(confidences.values()) / len(confidences) if confidences else 0.5

    return {
        "date": df.iloc[upto_idx]['date'] if 'date' in df.columns else str(upto_idx),
        "period": df.iloc[upto_idx]['period'] if 'period' in df.columns else str(upto_idx),
        "market_state": current_state,
        "top6": top6,
        "expert_weights": {k: round(v, 4) for k, v in expert_weights.items()},
        "expert_confidences": {k: round(v, 4) for k, v in confidences.items()},
        "confidence": round(avg_confidence, 4),
        "zodiac_scores": aggregation.get("zodiac_scores", {}),
        "raw_report": report
    }


def save_prediction(prediction):
    """保存预测结果"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Convert numpy types to Python native types for JSON serialization
    def convert_to_native(obj):
        import numpy as np
        if isinstance(obj, dict):
            return {k: convert_to_native(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_native(item) for item in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj

    pred_clean = convert_to_native(prediction)

    # 保存 latest
    with open(LAST_PREDICTION_FILE, 'w') as f:
        json.dump(pred_clean, f, indent=2, ensure_ascii=False)

    # 保存带时间戳的副本
    pred_file = PREDICTIONS_DIR / f"prediction_{timestamp}.json"
    with open(pred_file, 'w') as f:
        json.dump(pred_clean, f, indent=2, ensure_ascii=False)

    return pred_file


def save_actual_result(actual_zodiac, period=None, date=None):
    """保存实际结果（等待外部输入）"""
    result = {
        "actual_zodiac": actual_zodiac,
        "period": period,
        "date": date or datetime.now().isoformat(),
        "recorded_at": datetime.now().isoformat()
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = ACTUAL_RESULTS_DIR / f"actual_{timestamp}.json"

    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # 更新 latest
    with open(ACTUAL_RESULTS_DIR / "latest_actual.json", 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result_file


def calculate_metrics(prediction, actual_result):
    """计算每日指标"""
    hit = 1 if actual_result["actual_zodiac"] in prediction["top6"] else 0

    # 加载历史计算 rolling
    history_file = DAILY_METRICS_DIR / "history.json"
    if history_file.exists():
        with open(history_file, 'r') as f:
            history = json.load(f)
    else:
        history = {"hits": [], "rolling_30": [], "drawdown": []}

    history["hits"].append(hit)

    # 计算指标
    hits = history["hits"]
    n = len(hits)

    hit_rate = sum(hits) / n if n > 0 else 0
    recent_30 = hits[-30:] if len(hits) >= 30 else hits
    rolling_30 = sum(recent_30) / len(recent_30) if recent_30 else 0

    # 计算 drawdown
    cumulative = []
    running = 0
    for h in hits:
        running += h - 0.5  # baseline = 0.5
        cumulative.append(running)

    max_drawdown = min(cumulative) if cumulative else 0
    current_drawdown = cumulative[-1] if cumulative else 0

    # 计算 expert contribution
    expert_contribution = {}
    if "raw_report" in prediction:
        report = prediction["raw_report"]
        agg = report.get("aggregation", {})
        zodiac_scores = agg.get("zodiac_scores", {})

        for expert_name, expert_scores in prediction.get("expert_weights", {}).items():
            # 简化：使用 expert_weight 作为贡献代理
            expert_contribution[expert_name] = round(expert_scores, 4)

    metrics = {
        "hit": hit,
        "hit_rate": round(hit_rate, 4),
        "rolling_30_hit": round(rolling_30, 4),
        "max_drawdown": round(max_drawdown, 4),
        "current_drawdown": round(current_drawdown, 4),
        "total_predictions": n,
        "expert_contribution": expert_contribution,
        "prediction": prediction,
        "actual": actual_result,
        "calculated_at": datetime.now().isoformat()
    }

    # 保存历史
    history["rolling_30"].append(rolling_30)
    history["drawdown"].append(current_drawdown)
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)

    return metrics


def save_metrics(metrics):
    """保存指标"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with open(LAST_METRICS_FILE, 'w') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    metrics_file = DAILY_METRICS_DIR / f"metrics_{timestamp}.json"
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    return metrics_file


def check_fault_conditions(metrics, state):
    """检查故障触发条件"""
    triggers = []

    # hit_rate 连续低于阈值
    if metrics["rolling_30_hit"] < HIT_RATE_THRESHOLD:
        consecutive_low = state.get("consecutive_low_hit_rate", 0) + 1
        if consecutive_low >= CONSECUTIVE_FAILURES:
            triggers.append({
                "type": "HIT_RATE_LOW",
                "value": metrics["rolling_30_hit"],
                "threshold": HIT_RATE_THRESHOLD,
                "consecutive": consecutive_low
            })
        state["consecutive_low_hit_rate"] = consecutive_low
    else:
        state["consecutive_low_hit_rate"] = 0

    # drawdown 持续恶化
    history_file = DAILY_METRICS_DIR / "history.json"
    if history_file.exists():
        with open(history_file, 'r') as f:
            history = json.load(f)
        drawdowns = history.get("drawdown", [])
        if len(drawdowns) >= 10:
            recent = drawdowns[-10:]
            if all(d < drawdowns[i] for i, d in enumerate(recent[:-1])):
                triggers.append({
                    "type": "DRAWDOWN_WORSENING",
                    "current": drawdowns[-1],
                    "trend": "10 consecutive lower"
                })

    return triggers


def generate_shadow_summary():
    """生成 Shadow Summary 报告"""
    history_file = DAILY_METRICS_DIR / "history.json"

    summary = {
        "mode": "SHADOW_MODE_V1",
        "status": "SYSTEM_RUNNING",
        "generated_at": datetime.now().isoformat(),
        "development_frozen": True,
        "fault_triggers_enabled": True
    }

    if history_file.exists():
        with open(history_file, 'r') as f:
            history = json.load(f)

        hits = history.get("hits", [])
        n = len(hits)

        if n > 0:
            summary.update({
                "total_predictions": n,
                "hit_rate": round(sum(hits) / n, 4),
                "rolling_30_hit": round(history.get("rolling_30", [0])[-1], 4),
                "max_drawdown": round(min(history.get("drawdown", [0])), 4),
                "current_drawdown": round(history.get("drawdown", [0])[-1] if history.get("drawdown") else 0, 4)
            })
        else:
            summary.update({
                "total_predictions": 0,
                "hit_rate": 0,
                "rolling_30_hit": 0,
                "max_drawdown": 0,
                "current_drawdown": 0
            })
    else:
        summary.update({
            "total_predictions": 0,
            "hit_rate": 0,
            "rolling_30_hit": 0,
            "max_drawdown": 0,
            "current_drawdown": 0
        })

    # 读取最新状态
    state = load_system_state()
    summary["fault_triggers"] = state.get("fault_triggers", [])

    # 保存
    summary_file = SHADOW_REPORTS_DIR / "shadow_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    return summary


def create_snapshot():
    """创建系统快照"""
    import pandas as pd
    from meta_v2.meta_strategy_v2 import MetaStrategyV2

    snapshot = {
        "created_at": datetime.now().isoformat(),
        "data_range": {},
        "expert_states": {},
        "system_status": {}
    }

    try:
        df = load_data()
        n = len(df)

        # 数据范围
        snapshot["data_range"] = {
            "total_rows": n,
            "date_range": {
                "start": df['date'].iloc[0] if 'date' in df.columns else "unknown",
                "end": df['date'].iloc[-1] if 'date' in df.columns else "unknown"
            }
        }

        # 专家状态
        ms = MetaStrategyV2(df)
        for expert in ['Gap', 'Trend', 'Momentum', 'Frequency', 'Color', 'AntiTrend', 'Cycle']:
            state = ms.expert_manager.get_expert_state(expert)
            hit_rate = ms.expert_manager._rolling_hit_rate(expert, 30)
            snapshot["expert_states"][expert] = {
                "state": state,
                "rolling_hit_30": round(hit_rate, 4)
            }

        snapshot["system_status"] = "SNAPSHOT_COMPLETE"

    except Exception as e:
        snapshot["system_status"] = f"SNAPSHOT_ERROR: {str(e)}"

    # 保存快照
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_file = SNAPSHOTS_DIR / f"snapshot_{timestamp}.json"
    with open(snapshot_file, 'w') as f:
        json.dump(snapshot, f, indent=2)

    with open(SNAPSHOTS_DIR / "latest_snapshot.json", 'w') as f:
        json.dump(snapshot, f, indent=2)

    return snapshot


def run_full_cycle(predict_only=False):
    """
    运行完整周期

    Args:
        predict_only: 如果 True，只生成预测不等待实际结果
    """
    ensure_dirs()

    # 加载数据
    df = load_data()
    last_idx = len(df) - 1

    # 加载系统状态
    state = load_system_state()

    print(f"[Shadow Mode] Loading data: {len(df)} rows")

    # 运行预测
    print(f"[Shadow Mode] Running prediction at index {last_idx}...")
    prediction = run_prediction(df, last_idx)
    pred_file = save_prediction(prediction)

    print(f"[Shadow Mode] Prediction saved to: {pred_file}")
    print(f"  - Market State: {prediction['market_state']}")
    print(f"  - Top6: {prediction['top6']}")
    print(f"  - Confidence: {prediction['confidence']}")

    # 更新系统状态
    state["total_predictions"] += 1
    state["status"] = "PREDICTION_GENERATED"

    # 检查故障条件
    triggers = check_fault_conditions(
        {"rolling_30_hit": 0, "max_drawdown": 0},
        state
    )
    if triggers:
        state["fault_triggers"] = triggers

    save_system_state(state)

    # 如果只预测，生成 shadow summary 并返回
    summary = generate_shadow_summary()
    print(f"\n[Shadow Mode] Shadow Summary:")
    print(f"  - Total Predictions: {summary.get('total_predictions', 0)}")
    print(f"  - Mode: {summary.get('mode')}")
    print(f"  - Status: {summary.get('status')}")
    print(f"  - Development Frozen: {summary.get('development_frozen')}")

    return prediction, summary


def main():
    """主入口"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--predict-only":
        prediction, summary = run_full_cycle(predict_only=True)
    else:
        prediction, summary = run_full_cycle(predict_only=False)

    print("\n[Shadow Mode] System ready.")
    print("To record actual result: python shadow_runtime.py --record-actual <zodiac>")


if __name__ == "__main__":
    main()