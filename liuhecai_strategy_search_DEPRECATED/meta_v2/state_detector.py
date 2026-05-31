# meta_v2/state_detector.py
"""市场状态检测器 - 四维特征独立检测器 + 投票聚合"""
import numpy as np
from typing import Dict

DEFAULT_WINDOW = 20
MIN_HISTORY = 20

# Percentile-based thresholds (recalculated on first run via data_stats)
# Default fallbacks - will be overridden if data_stats is provided
ENTROPY_P20 = 1.86
ENTROPY_P80 = 2.12
VOL_P20 = 0.57
VOL_P80 = 0.79


class MarketStateDetector:
    def __init__(self, window: int = DEFAULT_WINDOW):
        self.window = window
        self.entropy_history = []
        self.volatility_history = []
        self.stability_history = []
        self.regime_history = []
        self.state_confirmation = {"HOT": 0, "COLD": 0, "TRANSITION": 0, "CHAOTIC": 0}
        self.current_state = "HOT"
        self.detection_signals = {}
        self.state_counts = {"HOT": 0, "COLD": 0, "TRANSITION": 0, "CHAOTIC": 0, "UNCERTAIN": 0}
        self.pending_state = None

    def _calc_entropy(self, probs: np.ndarray) -> float:
        probs = probs[probs > 0]
        if len(probs) == 0:
            return 0.0
        return -np.sum(probs * np.log(probs))

    def _get_percentile(self, history: list, percentile: float) -> float:
        if len(history) < MIN_HISTORY:
            return 0.0
        return np.percentile(history, percentile)

    def _vote_state(self, entropy: float, volatility: float,
                    stability: float, regime_shift: bool) -> Dict[str, int]:
        if len(self.entropy_history) < MIN_HISTORY:
            return {"HOT": 0, "COLD": 0, "TRANSITION": 0, "CHAOTIC": 0}

        scores = {"HOT": 0, "COLD": 0, "TRANSITION": 0, "CHAOTIC": 0}

        # Entropy: detect chaos with larger window (30 instead of 20)
        # Use rolling window of 30 for entropy calculation
        entropy_window = 30
        if len(self.entropy_history) >= entropy_window:
            recent_entropies = self.entropy_history[-entropy_window:]
            mean_entropy = sum(recent_entropies) / len(recent_entropies)
            # If recent average entropy is high, the market is chaotic
            # Using percentile-based thresholds instead of fixed values
            if mean_entropy > ENTROPY_P80:
                scores["CHAOTIC"] += 2
            elif mean_entropy < ENTROPY_P20:
                scores["HOT"] += 2
            # else: middle band, no vote

        # For current entropy reading, also contribute one vote if extreme
        if entropy > ENTROPY_P80:
            scores["CHAOTIC"] += 1
        elif entropy < ENTROPY_P20:
            scores["HOT"] += 1

        # Volatility: also use larger window
        vol_window = 30
        if len(self.volatility_history) >= vol_window:
            recent_vols = self.volatility_history[-vol_window:]
            mean_vol = sum(recent_vols) / len(recent_vols)
            if mean_vol > VOL_P80:
                scores["COLD"] += 2
            elif mean_vol < VOL_P20:
                scores["HOT"] += 2

        # Current volatility reading
        if volatility > VOL_P80:
            scores["COLD"] += 1
        elif volatility < VOL_P20:
            scores["HOT"] += 1

        # Stability: vote TRANSITION if stability is low (high variance in predictions)
        # stability < 0.6 indicates unstable prediction history
        if stability < 0.6:
            scores["TRANSITION"] += 1
        if stability < 0.4:
            scores["TRANSITION"] += 1  # extra vote for very unstable

        # Regime: vote TRANSITION if regime shift detected (even if condition is strict)
        if regime_shift:
            scores["TRANSITION"] += 2

        return scores

    def update(self, entropy: float, volatility: float, stability: float, regime_shift: bool):
        self.entropy_history.append(entropy)
        self.volatility_history.append(volatility)
        self.stability_history.append(stability)
        self.regime_history.append(regime_shift)
        if len(self.entropy_history) > 100:
            self.entropy_history = self.entropy_history[-100:]
            self.volatility_history = self.volatility_history[-100:]
            self.stability_history = self.stability_history[-100:]
            self.regime_history = self.regime_history[-100:]

    def detect_state(self) -> str:
        if len(self.entropy_history) < MIN_HISTORY:
            self.state_counts["UNCERTAIN"] += 1
            return "UNCERTAIN"

        current_entropy = self.entropy_history[-1]
        current_volatility = self.volatility_history[-1] if self.volatility_history else 0
        current_stability = self.stability_history[-1] if self.stability_history else 0.5
        current_regime = self.regime_history[-1] if self.regime_history else False

        scores = self._vote_state(current_entropy, current_volatility, current_stability, current_regime)

        self.detection_signals = {
            "entropy_signal": "CHAOTIC" if current_entropy > 2.35 else ("HOT" if current_entropy < 2.0 else "MID"),
            "volatility_signal": "COLD" if current_volatility > 0.85 else ("HOT" if current_volatility < 0.55 else "MID"),
            "stability_signal": "TRANSITION" if current_stability < self._get_percentile(self.stability_history, 20) else "HOT",
            "regime_signal": "TRANSITION" if current_regime else "NONE"
        }

        max_state = max(scores, key=scores.get)
        max_score = scores[max_state]
        sorted_scores = sorted(scores.values(), reverse=True)
        gap = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) >= 2 else 0
        confidence = gap / max_score if max_score > 0 else 0

        # Drop confidence gate - use direct assignment with hysteresis fallback
        if max_score == 0:
            # No votes at all → stay in current state
            self.state_counts[self.current_state] += 1
            return self.current_state

        # Tie-breaking: when tied, prefer the current_state to avoid thrashing
        # This ensures consistent voting when multiple states have same score
        if sorted_scores[0] == sorted_scores[1]:
            # Tied - stay with current_state if it's one of the tied states
            if self.current_state in [s for s in scores if scores[s] == sorted_scores[0]]:
                max_state = self.current_state

        if self.pending_state == max_state:
            self.state_confirmation[max_state] += 1
        else:
            self.pending_state = max_state
            self.state_confirmation[max_state] = 1
            for s in self.state_confirmation:
                if s != max_state:
                    self.state_confirmation[s] = 0

        if self.state_confirmation[max_state] >= 2:
            if self.current_state != max_state:
                self.current_state = max_state
            self.state_confirmation = {k: 0 for k in self.state_confirmation}
            self.pending_state = None

        self.state_counts[self.current_state] += 1
        return self.current_state

    def get_detection_signals(self) -> Dict[str, str]:
        return self.detection_signals

    def get_scores(self) -> Dict[str, int]:
        if len(self.entropy_history) < MIN_HISTORY:
            return {"HOT": 0, "COLD": 0, "TRANSITION": 0, "CHAOTIC": 0}
        return self._vote_state(
            self.entropy_history[-1],
            self.volatility_history[-1] if self.volatility_history else 0,
            self.stability_history[-1] if self.stability_history else 0.5,
            self.regime_history[-1] if self.regime_history else False
        )

    def get_state_distribution(self) -> Dict[str, int]:
        return self.state_counts.copy()

    def reset(self):
        self.entropy_history = []
        self.volatility_history = []
        self.stability_history = []
        self.regime_history = []
        self.state_confirmation = {"HOT": 0, "COLD": 0, "TRANSITION": 0, "CHAOTIC": 0}
        self.current_state = "HOT"
        self.detection_signals = {}
        self.state_counts = {"HOT": 0, "COLD": 0, "TRANSITION": 0, "CHAOTIC": 0, "UNCERTAIN": 0}
        self.pending_state = None