# confidence_filter.py
"""Confidence Filter Layer - 不修改现有预测系统，只在外层增加决策过滤器"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


@dataclass
class DecisionResult:
    """决策结果"""
    top_predictions: List[str]          # 过滤后的 TOP1-3
    confidence: float                    # 置信度分数
    decision: str                         # 'SELECT' or 'SKIP'
    top1_score: float                     # TOP1 原始分数
    top2_score: float                     # TOP2 原始分数
    score_gap: float                      # TOP1 - TOP2
    state_stability_weight: float
    entropy_penalty: float
    expert_agreement: float


def confidence_score(
    zodiac_scores: Dict[str, float],
    market_state: str,
    entropy: float,
    expert_weights: Dict[str, float],
    expert_confidences: Dict[str, float],
    threshold: float = 0.55
) -> DecisionResult:
    """
    计算置信度分数并做出决策

    Formula:
    confidence = (Top1 - Top2) / Top1 * state_stability_weight - entropy_penalty * expert_agreement_score

    Where:
    - (Top1 - Top2) / Top1: normalized score gap
    - state_stability_weight: HOT=0.7, COLD=0.8, CHAOTIC=0.5, TRANSITION=0.9, UNCERTAIN=1.0
    - entropy_penalty: entropy > 2.2 ? 0.2 : 0.0 (高熵降低信心)
    - expert_agreement_score: weighted avg of expert confidences
    """

    # 1. 排序获取 TOP1/TOP2
    sorted_zodiacs = sorted(zodiac_scores.items(), key=lambda x: x[1], reverse=True)

    if len(sorted_zodiacs) < 2:
        top1 = sorted_zodiacs[0] if sorted_zodiacs else ('鼠', 0.0)
        top2 = ('鼠', 0.0)
    else:
        top1 = sorted_zodiacs[0]
        top2 = sorted_zodiacs[1]

    top1_z, top1_score = top1
    top2_z, top2_score = top2

    # 2. 计算分数差距（归一化）
    if top1_score > 0:
        score_gap_normalized = (top1_score - top2_score) / top1_score
    else:
        score_gap_normalized = 0.0

    # 3. State stability weight (how confident we are in this state)
    state_weights = {
        'HOT': 0.7,
        'COLD': 0.8,
        'CHAOTIC': 0.5,
        'TRANSITION': 0.9,
        'UNCERTAIN': 1.0
    }
    state_stability_weight = state_weights.get(market_state, 0.8)

    # 4. Entropy penalty
    entropy_penalty = 0.2 if entropy > 2.2 else 0.0

    # 5. Expert agreement score
    # Weighted average of expert confidences
    if expert_confidences:
        total_weight = sum(expert_confidences.values())
        if total_weight > 0:
            expert_agreement = sum(conf for conf in expert_confidences.values()) / len(expert_confidences)
        else:
            expert_agreement = 0.5
    else:
        expert_agreement = 0.5

    # 6. Final confidence calculation
    confidence = score_gap_normalized * state_stability_weight - entropy_penalty * (1 - expert_agreement)

    # Clamp to [0, 1]
    confidence = max(0.0, min(1.0, confidence))

    # 7. Decision
    if confidence < threshold:
        decision = 'SKIP'
        top_predictions = []  # 不预测
    else:
        decision = 'SELECT'
        # 输出 TOP1-3（不是 TOP6）
        top_predictions = [z for z, s in sorted_zodiacs[:3]]

    return DecisionResult(
        top_predictions=top_predictions,
        confidence=round(confidence, 4),
        decision=decision,
        top1_score=round(top1_score, 4),
        top2_score=round(top2_score, 4),
        score_gap=round(score_gap_normalized, 4),
        state_stability_weight=round(state_stability_weight, 2),
        entropy_penalty=round(entropy_penalty, 2),
        expert_agreement=round(expert_agreement, 2)
    )


def run_confidence_filter_evaluation(
    meta_strategy_results: List[Dict],
    threshold: float = 0.55
) -> Dict:
    """
    运行置信度过滤评估

    Args:
        meta_strategy_results: MetaStrategyV2.run_backtest() 的结果列表
        threshold: 置信度阈值

    Returns:
        evaluation metrics
    """

    decisions = []
    selected_results = []
    skipped_results = []

    for result in meta_strategy_results:
        # 提取必要数据
        zodiac_scores = result.get('zodiac_scores', {})
        market_state = result.get('market_state', 'UNCERTAIN')
        # 从 raw report 获取 entropy（如果可用）
        raw_report = result.get('raw_report', {}) if isinstance(result.get('raw_report'), dict) else {}
        entropy = raw_report.get('entropy', 2.0) if 'entropy' in raw_report else 2.0

        # Expert weights and confidences
        expert_weights = result.get('expert_weights', {})
        expert_confidences = raw_report.get('aggregation', {}).get('expert_confidences', {})

        # Calculate confidence
        decision = confidence_score(
            zodiac_scores, market_state, entropy,
            expert_weights, expert_confidences, threshold
        )

        decisions.append(decision)

        if decision.decision == 'SELECT':
            selected_results.append((result, decision))
            skipped_results.append(None)
        else:
            selected_results.append(None)
            skipped_results.append((result, decision))

    # 计算指标
    n_total = len(meta_strategy_results)
    n_selected = sum(1 for d in decisions if d.decision == 'SELECT')
    n_skipped = n_total - n_selected

    # Hit rate when selected
    hits_when_selected = 0
    for i, (result, decision) in enumerate(selected_results):
        if result is None:
            continue
        actual = meta_strategy_results[i]['actual']
        if actual in decision.top_predictions:
            hits_when_selected += 1

    hit_rate_when_selected = hits_when_selected / n_selected if n_selected > 0 else 0

    # Coverage rate
    coverage_rate = n_selected / n_total if n_total > 0 else 0

    # Skipped ratio
    skipped_ratio = n_skipped / n_total if n_total > 0 else 0

    # Precision vs baseline (compare hit rate of selected to overall)
    overall_hits = sum(1 for r in meta_strategy_results if r['actual'] in r.get('prediction', []))
    overall_hit_rate = overall_hits / n_total if n_total > 0 else 0

    precision_vs_baseline = hit_rate_when_selected - overall_hit_rate

    # Top1 hit rate specifically
    top1_hits = 0
    for i, (result, decision) in enumerate(selected_results):
        if result is None:
            continue
        actual = meta_strategy_results[i]['actual']
        if decision.top_predictions and decision.top_predictions[0] == actual:
            top1_hits += 1

    top1_hit_rate = top1_hits / n_selected if n_selected > 0 else 0

    return {
        'n_total': n_total,
        'n_selected': n_selected,
        'n_skipped': n_skipped,
        'hit_rate_when_selected': round(hit_rate_when_selected, 4),
        'top1_hit_rate': round(top1_hit_rate, 4),
        'coverage_rate': round(coverage_rate, 4),
        'skipped_ratio': round(skipped_ratio, 4),
        'overall_hit_rate': round(overall_hit_rate, 4),
        'precision_vs_baseline': round(precision_vs_baseline, 4),
        'threshold_used': threshold,
        'decisions': decisions
    }


# Quick test function
def quick_test(df, ms, start_idx=200, end_idx=300, threshold=0.55):
    """快速测试置信度过滤"""

    results = []
    for idx in range(start_idx, end_idx):
        if idx >= len(df) - 1:
            break

        entropy, volatility, stability, regime_shift = ms._calc_state_features(idx)
        ms.state_detector.update(entropy, volatility, stability, regime_shift)
        state = ms.state_detector.detect_state()

        expert_scores = ms._get_expert_scores(idx)
        ms._current_expert_scores = expert_scores
        top6, report = ms.predict_top6()

        actual = df.iloc[idx + 1]['zodiac']

        # Get zodiac_scores from aggregation
        zodiac_scores = report.get('aggregation', {}).get('zodiac_scores', {})
        if not zodiac_scores:
            # Fallback: compute from expert scores
            zodiac_scores = {}
            for expert, scores in expert_scores.items():
                for z, s in scores.items():
                    zodiac_scores[z] = zodiac_scores.get(z, 0) + s

        expert_weights = report.get('base_weights', {})
        expert_confidences = report.get('aggregation', {}).get('expert_confidences', {})

        decision = confidence_score(
            zodiac_scores, state, entropy,
            expert_weights, expert_confidences, threshold
        )

        results.append({
            'idx': idx,
            'actual': actual,
            'prediction': top6,
            'decision': decision,
            'zodiac_scores': zodiac_scores,
            'market_state': state,
            'entropy': entropy,
            'hit': 1 if actual in top6 else 0,
            'top1_match': 1 if decision.top_predictions and decision.top_predictions[0] == actual else 0
        })

        preds = {e: [z for z, s in sorted(expert_scores[e].items(), key=lambda x: x[1], reverse=True)[:6]] for e in expert_scores}
        ms.update(preds, actual)

    # Compute metrics
    decisions = [r['decision'] for r in results]
    n_total = len(results)
    n_selected = sum(1 for d in decisions if d.decision == 'SELECT')
    n_skipped = n_total - n_selected

    hits_when_selected = sum(1 for r in results if r['hit'] and r['decision'].decision == 'SELECT')
    hit_rate_when_selected = hits_when_selected / n_selected if n_selected > 0 else 0

    top1_hits = sum(1 for r in results if r['top1_match'] and r['decision'].decision == 'SELECT')
    top1_hit_rate = top1_hits / n_selected if n_selected > 0 else 0

    overall_hit = sum(1 for r in results if r['hit'])
    overall_hit_rate = overall_hit / n_total if n_total > 0 else 0

    coverage = n_selected / n_total if n_total > 0 else 0
    skipped = n_skipped / n_total if n_total > 0 else 0

    return {
        'n_total': n_total,
        'n_selected': n_selected,
        'n_skipped': n_skipped,
        'hit_rate_when_selected': round(hit_rate_when_selected, 4),
        'top1_hit_rate': round(top1_hit_rate, 4),
        'coverage_rate': round(coverage, 4),
        'skipped_ratio': round(skipped, 4),
        'overall_hit_rate': round(overall_hit_rate, 4),
        'precision_vs_baseline': round(hit_rate_when_selected - overall_hit_rate, 4),
        'threshold_used': threshold,
        'results': results
    }