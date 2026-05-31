# meta_v2/tests/test_weight_effectiveness.py
"""Weight Effectiveness Test - 动态权重 vs 固定权重对比验证"""
import pytest
import sys
import json
import numpy as np
import pandas as pd
from typing import Dict, List
sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')
from schema import load_standardized
from meta_v2.meta_strategy_v2 import MetaStrategyV2

EXPERTS = ['Gap', 'Trend', 'Momentum', 'Color']
ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
BASELINE = 0.50


def run_backtest_fixed_weights(df: pd.DataFrame, start_idx: int, end_idx: int,
                               fixed_weights: Dict[str, float]) -> List[Dict]:
    """固定权重回测 - 跳过StateRouter/ColorActivator/ChaosHandler/DiversityPenalty"""
    from collections import defaultdict

    entropy_history = []
    volatility_history = []
    prediction_history = []
    actual_history = []
    hit_history = []
    expert_histories = {name: [] for name in EXPERTS}

    for idx in range(start_idx, end_idx):
        # 计算特征
        window = min(20, idx)
        recent_data = df.iloc[:idx]
        zodiac_counts = recent_data['zodiac'].value_counts()
        probs = np.array([zodiac_counts.get(z, 0) / window for z in ZODIACS])
        probs = probs[probs > 0]
        entropy = -np.sum(probs * np.log(probs)) if len(probs) > 0 else 0
        expected = window / 12
        volatility = np.std([zodiac_counts.get(z, 0) for z in ZODIACS]) / expected if expected > 0 else 0
        entropy_history.append(entropy)
        volatility_history.append(volatility)

        # 获取专家预测
        preds = _get_expert_predictions(df, idx, EXPERTS, ZODIACS)
        prediction_history.append(preds)
        actual = df.iloc[idx + 1]['zodiac']
        actual_history.append(actual)

        # 更新命中
        for expert_name in EXPERTS:
            top6 = preds.get(expert_name, [])
            hit = 1 if actual in top6 else 0
            expert_histories[expert_name].append(hit)
            hit_history.append(hit)

        # 固定权重聚合
        zodiac_scores = defaultdict(float)
        for expert_name, top6 in preds.items():
            weight = fixed_weights.get(expert_name, 0.25)
            for i, zodiac in enumerate(top6):
                position_bonus = 1.0 / (1 + i * 0.1)
                zodiac_scores[zodiac] += weight * position_bonus

        sorted_zodiacs = sorted(zodiac_scores.items(), key=lambda x: x[1], reverse=True)
        top6 = [z for z, s in sorted_zodiacs[:6]]

        # 计算指标
        hit = 1 if actual in top6 else 0
        recent_30_hits = hit_history[-30:] if len(hit_history) >= 30 else hit_history
        rolling_30 = sum(recent_30_hits) / len(recent_30_hits) if recent_30_hits else 0
        mean_hit = sum(hit_history) / len(hit_history) if hit_history else 0

        cumulative = []
        running = 0
        for h in hit_history:
            running += h - BASELINE
            cumulative.append(running)
        max_drawdown = min(cumulative) if cumulative else 0

        stability_score = 1 - np.std(hit_history[-50:]) if len(hit_history) >= 50 else 0.5

    return {
        "mean_hit_rate": round(mean_hit, 4),
        "rolling_30_hit": round(rolling_30, 4),
        "max_drawdown": round(max_drawdown, 4),
        "stability_score": round(stability_score, 4),
        "total_predictions": len(hit_history)
    }


def _get_expert_predictions(df: pd.DataFrame, upto_idx: int,
                            experts: list, zodiacs: list) -> Dict[str, List[str]]:
    """获取各专家预测（复制自MetaStrategyV2）"""
    predictions = {}
    data = df.iloc[:upto_idx]

    for expert_name in experts:
        scores = {}
        for z in zodiacs:
            score = 0
            if expert_name == 'Gap':
                positions = data[data['zodiac'] == z].index.tolist()
                gap = upto_idx - positions[-1] - 1 if positions else upto_idx
                score = gap * 2.0
                if len(positions) >= 3:
                    intervals = np.diff(positions)
                    cycle_mean = np.mean(intervals)
                    cycle_std = np.std(intervals)
                    if cycle_std > 0:
                        residual = (gap - cycle_mean) / cycle_std
                        score += residual * 0.5
            elif expert_name == 'Trend':
                hits = (data['zodiac'] == z).astype(float).values
                n = len(hits)
                ages = np.arange(n)[::-1]
                weights = np.exp(-0.1 * ages)
                score = np.sum(hits * weights)
            elif expert_name == 'Momentum':
                streak = 0
                for i in range(upto_idx - 1, -1, -1):
                    if df.iloc[i]['zodiac'] == z:
                        streak += 1
                    else:
                        break
                freq_10 = (data.iloc[-10:]['zodiac'] == z).sum() if upto_idx >= 10 else 0
                freq_20 = (data.iloc[-20:]['zodiac'] == z).sum() if upto_idx >= 20 else 0
                score = streak * 0.5 + freq_10 * 0.3 + (freq_10 - freq_20) * 0.2
            elif expert_name == 'Color':
                zodiac_colors = {
                    '红': ['马', '羊', '兔', '猴'],
                    '蓝': ['鼠', '牛', '蛇', '狗'],
                    '绿': ['虎', '龍', '雞', '豬']
                }
                color = None
                for c, zs in zodiac_colors.items():
                    if z in zs:
                        color = c
                        break
                if color:
                    freq_10 = (data.iloc[-10:]['color'] == color).sum() if upto_idx >= 10 else 0
                    expected = 10 / 3
                    score = freq_10 / expected if expected > 0 else 0
            scores[z] = score
        sorted_z = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        predictions[expert_name] = [z for z, s in sorted_z[:6]]
    return predictions


def test_weight_effectiveness():
    """对比动态权重 vs 固定权重（多起点验证）"""
    df = load_standardized('/home/admin1/liuhecai_strategy_search/truth_dataset.json')

    # 固定权重配置（使用HOT状态的基础权重）
    FIXED_WEIGHTS = {'Gap': 0.1, 'Trend': 0.7, 'Momentum': 0.2, 'Color': 0.0}

    results = []
    for start in [200, 300, 400, 450]:
        end = start + 200

        # A: 动态权重
        meta_a = MetaStrategyV2(df)
        r_a = meta_a.run_backtest(start_idx=start, end_idx=end)
        hits_a = [x['hit'] for x in r_a]
        mean_a = sum(hits_a) / len(hits_a)
        r30_a = sum(hits_a[-30:]) / 30 if len(hits_a) >= 30 else mean_a

        # B: 固定权重
        r_b = run_backtest_fixed_weights(df, start, end, FIXED_WEIGHTS)
        mean_b = r_b['mean_hit_rate']
        r30_b = r_b['rolling_30_hit']

        results.append({
            'start': start,
            'dynamic_hit': mean_a,
            'static_hit': mean_b,
            'dynamic_r30': r30_a,
            'static_r30': r30_b,
            'delta_hit': mean_a - mean_b
        })

    # 汇总
    avg_delta = sum(r['delta_hit'] for r in results) / len(results)
    dynamic_wins = sum(1 for r in results if r['delta_hit'] > 0.01)

    # 输出
    for r in results:
        print(f"start={r['start']}: dyn_hit={r['dynamic_hit']:.4f} sta_hit={r['static_hit']:.4f} delta={r['delta_hit']:+.4f}")

    print(f"\navg_delta={avg_delta:+.4f}, dynamic_wins={dynamic_wins}/{len(results)}")

    # 门控：至少3/4起点动态更优且平均增益>0
    winner = "DYNAMIC_HIT" if dynamic_wins >= 3 and avg_delta > 0 else "INCONCLUSIVE"
    gate = "EDGE_CONFIRMED" if winner == "DYNAMIC_HIT" else "SYSTEM_WORKING"

    report = {
        "dynamic_hit": round(sum(r['dynamic_hit'] for r in results) / len(results), 4),
        "static_hit": round(sum(r['static_hit'] for r in results) / len(results), 4),
        "avg_delta_hit": round(avg_delta, 4),
        "per_start": results,
        "winner": winner,
        "gate": gate
    }

    report_path = '/home/admin1/liuhecai_strategy_search/weight_effectiveness_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n赢家: {winner} [{gate}]")

    assert gate == 'EDGE_CONFIRMED', f"Dynamic weight not proven effective: {report}"


if __name__ == '__main__':
    test_weight_effectiveness()