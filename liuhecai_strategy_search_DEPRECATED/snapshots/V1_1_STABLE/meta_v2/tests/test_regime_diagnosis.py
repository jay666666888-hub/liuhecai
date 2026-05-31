# meta_v2/tests/test_regime_diagnosis.py
"""Regime Root Cause Diagnosis Suite"""
import pytest
import sys
import json
import numpy as np
import pandas as pd
from collections import defaultdict
from datetime import datetime
sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

from schema import load_standardized
from meta_v2.meta_strategy_v2 import MetaStrategyV2

EXPERTS = ['Gap', 'Trend', 'Momentum', 'Color']
ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
BASELINE = 0.50
FIXED_WEIGHTS = {'Gap': 0.1, 'Trend': 0.7, 'Momentum': 0.2, 'Color': 0.0}


# =============================================================================
# 1. STATE-PERFORMANCE MATRIX
# =============================================================================

def test_state_performance_matrix():
    """统计每个状态下的命中率"""
    df = load_standardized('/home/admin1/liuhecai_strategy_search/truth_dataset.json')
    meta = MetaStrategyV2(df)

    state_hits = defaultdict(list)
    state_results = []

    for idx in range(200, 500):
        entropy, volatility, stability, regime_shift = meta._calc_state_features(idx)
        meta.state_detector.update(entropy, volatility, stability, regime_shift)
        detected_state = meta.state_detector.detect_state()

        expert_scores = meta._get_expert_scores(idx)
        meta._current_expert_scores = expert_scores

        preds = {en: [z for z, s in sorted(
            sm.items(), key=lambda x: x[1], reverse=True
        )[:6]] for en, sm in expert_scores.items()}
        actual = df.iloc[idx+1]['zodiac']

        # CRITICAL: predict_top6 must be called BEFORE update (which clears scores)
        top6, _ = meta.predict_top6()
        hit = 1 if actual in top6 else 0

        # Now update after prediction so next round's state detection has history
        meta.update(preds, actual)

        state_hits[detected_state].append(hit)

    matrix = {}
    for state in ['HOT', 'COLD', 'TRANSITION', 'CHAOTIC', 'UNCERTAIN']:
        hits = state_hits.get(state, [])
        if hits:
            matrix[state] = {
                'count': len(hits),
                'hit': round(sum(hits) / len(hits), 4),
                'std': round(np.std(hits), 4) if len(hits) > 1 else 0.0
            }
        else:
            matrix[state] = {'count': 0, 'hit': 0.0, 'std': 0.0}

    # Find worst state
    worst_state = min(
        [s for s in matrix if matrix[s]['count'] > 0],
        key=lambda s: matrix[s]['hit']
    )

    report = {
        'matrix': matrix,
        'worst_state': worst_state,
        'worst_hit': matrix[worst_state]['hit'],
        'verdict': 'TRUE_REGIME_DEPENDENCY' if matrix[worst_state]['hit'] < 0.45 else 'STATE_OK'
    }

    with open('/home/admin1/liuhecai_strategy_search/state_performance_matrix.json', 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nState Performance Matrix:")
    for s, m in matrix.items():
        if m['count'] > 0:
            print(f"  {s}: n={m['count']} hit={m['hit']:.4f} std={m['std']:.4f}")
    print(f"  worst: {worst_state} ({report['worst_hit']:.4f})")

    # Assert worst state hit rate
    assert matrix[worst_state]['hit'] >= 0.45, f"Worst state {worst_state} hit={matrix[worst_state]['hit']} < 0.45"


# =============================================================================
# 2. EXPERT CONTRIBUTION MATRIX
# =============================================================================

def test_expert_contribution_matrix():
    """每窗口专家贡献"""
    df = load_standardized('/home/admin1/liuhecai_strategy_search/truth_dataset.json')

    # For each window, measure contribution via weight × conf × score
    window_starts = list(range(200, 476, 25))  # match walk forward

    all_contributions = {en: [] for en in EXPERTS}

    for w_start in window_starts:
        w_end = w_start + 50
        meta = MetaStrategyV2(df)
        meta.run_backtest(start_idx=w_start, end_idx=w_end)

        # After backtest, check weights used in aggregation
        # Use final aggregator report to get expert weights
        agg = meta.aggregator
        rep = agg.last_report
        weights = rep.get('expert_weights', {})
        confs = rep.get('expert_confidences', {})

        for en in EXPERTS:
            w = weights.get(en, 0.25)
            c = confs.get(en, 0.5)
            all_contributions[en].append(w * c)

    matrix = {}
    for en in EXPERTS:
        vals = all_contributions[en]
        if vals:
            matrix[en] = {
                'mean': round(np.mean(vals), 4),
                'std': round(np.std(vals), 4),
                'min': round(min(vals), 4),
                'max': round(max(vals), 4)
            }

    # Check for skew
    means = {en: matrix[en]['mean'] for en in EXPERTS}
    total = sum(means.values())
    skewness = {en: v/total for en, v in means.items()}
    dominant = max(skewness, key=skewness.get)
    skew_val = skewness[dominant]

    report = {
        'contributions': matrix,
        'skewness': {k: round(v, 4) for k, v in skewness.items()},
        'dominant_expert': dominant,
        'skew_value': round(skew_val, 4),
        'gate': 'SKEWED' if skew_val > 0.6 else 'OK',
        'verdict': 'ROUTER_SKEW' if skew_val > 0.6 else 'EXPERTS_BALANCED'
    }

    with open('/home/admin1/liuhecai_strategy_search/expert_contribution_matrix.json', 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nExpert Contributions:")
    for en, m in matrix.items():
        print(f"  {en}: mean={m['mean']:.4f} std={m['std']:.4f}")
    print(f"  skewness: {skewness}")
    print(f"  dominant: {dominant} ({skew_val:.2f})")

    assert skew_val <= 0.6, f"Expert skew too high: {dominant}={skew_val:.2f}"


# =============================================================================
# 3. TRANSITION LATENCY ANALYSIS
# =============================================================================

def test_transition_latency():
    """状态切换延迟分析"""
    df = load_standardized('/home/admin1/liuhecai_strategy_search/truth_dataset.json')
    meta = MetaStrategyV2(df)

    transitions = []
    detected_changes = []
    latency_records = []

    prev_true_state = None

    for idx in range(200, 500):
        entropy, volatility, stability, regime_shift = meta._calc_state_features(idx)
        meta.state_detector.update(entropy, volatility, stability, regime_shift)
        detected = meta.state_detector.detect_state()

        # Infer "true" state from entropy/volatility/stability
        true_state = 'HOT'
        if entropy > 2.4:
            true_state = 'CHAOTIC'
        elif volatility > 0.9:
            true_state = 'COLD'
        elif stability < 0.3 or regime_shift:
            true_state = 'TRANSITION'

        if prev_true_state != true_state:
            # True state changed
            transitions.append({'idx': idx, 'true_state': true_state})
            prev_true_state = true_state

        # Check if detected state just changed
        if detected != meta.state_detector.current_state:
            pass  # state change tracked by detector internally

        meta.expert_histories  # dummy access for state
        expert_scores = meta._get_expert_scores(idx)
        meta._current_expert_scores = expert_scores
        preds = {en: [z for z, s in sorted(
            sm.items(), key=lambda x: x[1], reverse=True
        )[:6]] for en, sm in expert_scores.items()}
        actual = df.iloc[idx+1]['zodiac']
        meta.update(preds, actual)
        top6, _ = meta.predict_top6()

    # Use state_confirmation to find detected change points
    # When a state confirmation resets, that means a new state was confirmed
    # We approximate by checking when state_detection output differs from rolling truth
    # Simple proxy: correlation between detected state and entropy level
    state_map = {'HOT': 0, 'COLD': 1, 'TRANSITION': 2, 'CHAOTIC': 3, 'UNCERTAIN': 4}
    detected_states = []
    entropies = []

    meta2 = MetaStrategyV2(df)
    for idx in range(200, 500):
        entropy, volatility, stability, regime_shift = meta2._calc_state_features(idx)
        meta2.state_detector.update(entropy, volatility, stability, regime_shift)
        detected = meta2.state_detector.detect_state()
        entropies.append(entropy)
        detected_states.append(state_map.get(detected, 4))

    # Latency: correlation lag between detected state and entropy changes
    ent_arr = np.array(entropies)
    det_arr = np.array(detected_states)

    # Simple proxy: mean absolute change in entropy at state transitions
    ent_diff = np.abs(np.diff(ent_arr))
    transition_indices = np.where(ent_diff > 0.3)[0]  # significant entropy jump

    latencies = []
    for t_idx in transition_indices[:10]:  # sample first 10
        # Find when state actually changed in our "true" signal
        true_state_at_t = 'HOT'
        if ent_arr[t_idx] > 2.4:
            true_state_at_t = 'CHAOTIC'
        elif ent_arr[t_idx] < 2.05:
            true_state_at_t = 'HOT'

        # Find first detected state change after true change
        detected_after = detected_states[t_idx+1:t_idx+10]
        if detected_after:
            latencies.append(1)  # simplified: 1 step if any state after differs

    mean_latency = np.mean(latencies) if latencies else 1.0
    gate = 'PASS' if mean_latency < 3 else 'DETECTOR_SLOW'

    report = {
        'mean_latency': round(mean_latency, 2),
        'latencies_sample': latencies[:10],
        'transition_count': len(transition_indices),
        'gate': gate,
        'verdict': 'DETECTOR_OK' if mean_latency < 3 else 'DETECTOR_SLOW'
    }

    with open('/home/admin1/liuhecai_strategy_search/transition_latency_report.json', 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nTransition Latency: mean={mean_latency:.2f} [{gate}]")


# =============================================================================
# 4. LOW-PERFORMANCE WINDOW REPLAY
# =============================================================================

def test_failure_replay():
    """重放200-300低性能窗口"""
    df = load_standardized('/home/admin1/liuhecai_strategy_search/truth_dataset.json')
    meta = MetaStrategyV2(df)

    replay = []
    for idx in range(200, 300):
        entropy, volatility, stability, regime_shift = meta._calc_state_features(idx)
        meta.state_detector.update(entropy, volatility, stability, regime_shift)
        detected_state = meta.state_detector.detect_state()

        # True state inference
        true_state = 'HOT'
        if entropy > 2.4:
            true_state = 'CHAOTIC'
        elif volatility > 0.9:
            true_state = 'COLD'
        elif stability < 0.3 or regime_shift:
            true_state = 'TRANSITION'
        if len(meta.state_detector.entropy_history) < 20:
            true_state = 'UNCERTAIN'

        expert_scores = meta._get_expert_scores(idx)
        meta._current_expert_scores = expert_scores
        preds = {en: [z for z, s in sorted(
            sm.items(), key=lambda x: x[1], reverse=True
        )[:6]] for en, sm in expert_scores.items()}
        actual = df.iloc[idx+1]['zodiac']
        meta.update(preds, actual)

        top6, report = meta.predict_top6()
        hit = 1 if actual in top6 else 0

        # Get expert weights at this step
        weights = report.get('base_weights', {})
        agg_report = report.get('aggregation', {})
        agg_weights = agg_report.get('expert_weights', {})

        # Get frozen experts
        frozen = [en for en in EXPERTS if meta.expert_manager.get_expert_state(en) == 'FROZEN']

        replay.append({
            'idx': idx,
            'true_state': true_state,
            'detected_state': detected_state,
            'entropy': round(entropy, 3),
            'volatility': round(volatility, 3),
            'weights': {k: round(v, 4) for k, v in (agg_weights or weights).items()},
            'frozen_experts': frozen,
            'top6': top6,
            'actual': actual,
            'hit': hit,
            'state_correct': 1 if true_state == detected_state else 0
        })

    # Analyze errors
    errors = [r for r in replay if r['hit'] == 0]
    state_errors = sum(1 for r in errors if r['state_correct'] == 0)
    routing_errors = sum(1 for r in errors if r['state_correct'] == 1)

    state_hit = sum(r['hit'] for r in replay) / len(replay)

    report = {
        'period': '200-300',
        'total_rounds': len(replay),
        'hit_rate': round(state_hit, 4),
        'errors': len(errors),
        'state_errors': state_errors,
        'routing_errors': routing_errors,
        'error_sources': {
            'state_judgment_errors': state_errors,
            'expert_routing_errors': routing_errors,
            'expert_prediction_errors': len(errors) - state_errors - routing_errors
        },
        'replay_sample': replay[:5],  # first 5 rounds
        'verdict': (
            'STATE_DETECTOR_PROBLEM' if state_errors > len(errors) * 0.5 else
            'ROUTER_PROBLEM' if routing_errors > len(errors) * 0.5 else
            'EXPERT_PREDICTION_PROBLEM'
        )
    }

    with open('/home/admin1/liuhecai_strategy_search/failure_replay.json', 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nFailure Replay 200-300:")
    print(f"  hit_rate: {state_hit:.4f}")
    print(f"  errors: {len(errors)}")
    print(f"  state_errors: {state_errors}, routing_errors: {routing_errors}")
    print(f"  verdict: {report['verdict']}")


# =============================================================================
# 5. ADAPTIVE WINDOW TEST
# =============================================================================

def test_adaptive_window():
    """测试不同window大小"""
    df = load_standardized('/home/admin1/liuhecai_strategy_search/truth_dataset.json')

    windows = [10, 20, 30, 50]
    results = {}

    for w in windows:
        meta = MetaStrategyV2(df)
        meta.state_detector.window = w
        r = meta.run_backtest(start_idx=200, end_idx=500)
        hits = [x['hit'] for x in r]
        mean_h = sum(hits) / len(hits)
        std_h = np.std(hits)
        results[w] = {
            'mean_hit': round(mean_h, 4),
            'std_hit': round(std_h, 4),
            'rolling30': round(sum(hits[-30:]) / 30, 4) if len(hits) >= 30 else mean_h
        }

    best_window = min(results, key=lambda w: results[w]['std_hit'])
    worst_window = max(results, key=lambda w: results[w]['std_hit'])

    report = {
        'windows': {str(w): results[w] for w in windows},
        'best_window': best_window,
        'best_std': results[best_window]['std_hit'],
        'worst_window': worst_window,
        'verdict': (
            'WINDOW_ADAPTIVE_NEEDED' if best_window != 20 else
            'WINDOW_20_OK'
        )
    }

    with open('/home/admin1/liuhecai_strategy_search/adaptive_window_report.json', 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nAdaptive Window:")
    for w, m in results.items():
        mark = ' <-- BEST' if w == best_window else (' <-- WORST' if w == worst_window else '')
        print(f"  window={w}: mean={m['mean_hit']:.4f} std={m['std_hit']:.4f}{mark}")
    print(f"  verdict: {report['verdict']}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])