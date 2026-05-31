# meta_v2/tests/test_state_detector.py
"""MarketStateDetector 单元测试"""
import pytest
import numpy as np
import sys
sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')
from meta_v2.state_detector import MarketStateDetector


def test_entropy_calculation():
    """测试信息熵计算"""
    detector = MarketStateDetector(window=20)
    uniform_probs = np.ones(12) / 12
    entropy = detector._calc_entropy(uniform_probs)
    assert entropy > 2.0


def test_vote_state_chaotic():
    """测试CHAOTIC状态投票"""
    detector = MarketStateDetector(window=20)
    # Need 30 entropy readings for rolling mean voting
    for _ in range(30):
        detector.update(entropy=2.45, volatility=0.5, stability=0.5, regime_shift=False)
    # High current entropy + high rolling mean → CHAOTIC
    scores = detector._vote_state(entropy=2.6, volatility=0.5, stability=0.5, regime_shift=False)
    # Rolling mean ~2.45 > 2.40 → CHAOTIC+2, current > 2.50 → CHAOTIC+1
    assert scores["CHAOTIC"] == 3, f"Expected 3, got {scores}"


def test_vote_state_cold():
    """测试COLD状态投票"""
    detector = MarketStateDetector(window=20)
    for _ in range(30):
        detector.update(entropy=2.0, volatility=0.9, stability=0.5, regime_shift=False)
    # High current volatility + high rolling mean → COLD
    scores = detector._vote_state(entropy=2.0, volatility=1.2, stability=0.5, regime_shift=False)
    # Rolling mean ~0.9 > 0.85 → COLD+2, current > 1.0 → COLD+1
    assert scores["COLD"] == 3, f"Expected 3, got {scores}"


def test_vote_state_transition():
    """测试TRANSITION状态投票"""
    detector = MarketStateDetector(window=20)
    for _ in range(20):
        detector.update(entropy=2.0, volatility=0.5, stability=0.5, regime_shift=False)
    # Low stability + regime_shift → TRANSITION
    # stability<0.6=+1, stability<0.4=+1, regime_shift=+2
    scores = detector._vote_state(entropy=2.0, volatility=0.5, stability=0.2, regime_shift=True)
    assert scores["TRANSITION"] == 4, f"Expected 4, got {scores}"


def test_vote_state_hot():
    """测试HOT状态投票"""
    detector = MarketStateDetector(window=20)
    for _ in range(30):
        detector.update(entropy=1.0, volatility=0.2, stability=0.5, regime_shift=False)
    # Low entropy + low volatility → HOT (mean_entropy<2.05=+2, current<1.95=+1, mean_vol<0.55=+2, current<0.40=+1)
    scores = detector._vote_state(entropy=1.0, volatility=0.2, stability=0.7, regime_shift=False)
    # Rolling mean gives: entropy mean ~1.0 < 2.05 → +2, current < 1.95 → +1
    # Volatility: mean ~0.2 < 0.55 → +2, current < 0.40 → +1
    assert scores["HOT"] == 6, f"Expected 6, got {scores}"


def test_detect_state_stable():
    """测试低波动稳定市场"""
    detector = MarketStateDetector(window=20)
    for _ in range(20):
        detector.update(entropy=1.0, volatility=0.2, stability=0.7, regime_shift=False)
    state = detector.detect_state()
    assert state == "HOT"


def test_detect_state_high_volatility():
    """测试高波动市场"""
    detector = MarketStateDetector(window=20)
    for _ in range(20):
        detector.update(entropy=2.0, volatility=1.5, stability=0.5, regime_shift=False)
    state = detector.detect_state()
    assert state in ["COLD", "HOT"]


def test_detect_state_transition():
    """测试转换状态"""
    detector = MarketStateDetector(window=20)
    for _ in range(20):
        detector.update(entropy=2.5, volatility=0.5, stability=0.2, regime_shift=True)
    state = detector.detect_state()
    assert state in ["TRANSITION", "HOT", "UNCERTAIN"]


def test_insufficient_history():
    """测试历史数据不足时返回UNCERTAIN"""
    detector = MarketStateDetector(window=20)
    detector.update(entropy=2.5, volatility=0.8, stability=0.3, regime_shift=False)
    state = detector.detect_state()
    assert state == "UNCERTAIN"


def test_reset():
    """测试重置功能"""
    detector = MarketStateDetector(window=20)
    for _ in range(20):
        detector.update(entropy=2.5, volatility=0.8, stability=0.3, regime_shift=False)
    detector.reset()
    assert len(detector.entropy_history) == 0
    assert detector.current_state == "HOT"
    assert sum(detector.state_counts.values()) == 0


def test_state_distribution():
    """测试状态分布统计"""
    detector = MarketStateDetector(window=20)
    for i in range(30):
        if i < 10:
            detector.update(entropy=1.0, volatility=0.2, stability=0.7, regime_shift=False)
        elif i < 20:
            detector.update(entropy=3.0, volatility=1.5, stability=0.2, regime_shift=True)
        else:
            detector.update(entropy=2.0, volatility=0.8, stability=0.5, regime_shift=False)
        detector.detect_state()

    dist = detector.get_state_distribution()
    assert sum(dist.values()) <= 30
    active_states = [k for k, v in dist.items() if v > 0]
    assert len(active_states) >= 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])