# meta_v2/expert_manager.py
"""专家状态管理器 - 冻结/恢复机制"""
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime

BASELINE = 0.50
FREEZE_THRESHOLD = 0.03  # recovery需要 > baseline + 0.03
MAX_FREEZE = 200
OBSERVE_PERIOD = 30

# All 7 experts - must match MetaStrategyV2.EXPERTS
EXPERTS = ['Gap', 'Trend', 'Momentum', 'Frequency', 'Color', 'AntiTrend', 'Cycle']


class ExpertStateManager:
    """专家冻结/恢复管理"""

    def __init__(self):
        self.expert_hit_sequences = defaultdict(list)
        self.expert_states = defaultdict(lambda: "ACTIVE")
        self.freeze_start_times = defaultdict(lambda: None)  # 冻结开始时的total_hits
        self.observe_count = defaultdict(int)
        self.consecutive_failures = defaultdict(int)
        self.consecutive_recoveries = defaultdict(int)
        self.freeze_reports = {}
        self.total_hits = defaultdict(int)  # 追踪总点击数（未截断）

    def record_hit(self, expert_name: str, hit: bool):
        """记录单次命中"""
        self.expert_hit_sequences[expert_name].append(1 if hit else 0)
        self.total_hits[expert_name] += 1
        if len(self.expert_hit_sequences[expert_name]) > 200:
            self.expert_hit_sequences[expert_name] = self.expert_hit_sequences[expert_name][-200:]
        self._update_state(expert_name)

    def _rolling_hit_rate(self, expert_name: str, window: int) -> float:
        """计算滑动命中率"""
        seq = self.expert_hit_sequences[expert_name]
        if len(seq) < window:
            window = len(seq)
        if window == 0:
            return 0.0
        return sum(seq[-window:]) / window

    def _zscore(self, expert_name: str, window: int = 50) -> float:
        """计算z-score"""
        seq = self.expert_hit_sequences[expert_name][-window:]
        if len(seq) < 10:
            return 0.0
        mean = sum(seq) / len(seq)
        std = (sum((x - mean) ** 2 for x in seq) / len(seq)) ** 0.5
        if std == 0:
            return 0.0
        return (mean - BASELINE) / std

    def _update_state(self, expert_name: str):
        """更新专家状态"""
        current_state = self.expert_states[expert_name]
        rolling_30 = self._rolling_hit_rate(expert_name, 30)
        rolling_50 = self._rolling_hit_rate(expert_name, 50)

        if current_state == "ACTIVE":
            if rolling_30 < BASELINE:
                self.consecutive_failures[expert_name] += 1
                self.consecutive_recoveries[expert_name] = 0
                if self.consecutive_failures[expert_name] >= 30:
                    self.expert_states[expert_name] = "FROZEN"
                    self.freeze_start_times[expert_name] = self.total_hits[expert_name]
                    self._create_freeze_report(expert_name, rolling_30, rolling_50)
            else:
                self.consecutive_failures[expert_name] = 0
                self.consecutive_recoveries[expert_name] += 1

        elif current_state == "FROZEN":
            freeze_duration = self.total_hits[expert_name] - (self.freeze_start_times[expert_name] or 0)
            if freeze_duration >= MAX_FREEZE:
                self.expert_states[expert_name] = "OBSERVE"
                self.observe_count[expert_name] = 0
                return

            if rolling_50 > BASELINE + FREEZE_THRESHOLD and self._zscore(expert_name, 50) > 1:
                self.consecutive_recoveries[expert_name] += 1
                self.consecutive_failures[expert_name] = 0
                if self.consecutive_recoveries[expert_name] >= 50:
                    self.expert_states[expert_name] = "ACTIVE"
                    self.freeze_start_times[expert_name] = None
                    self.consecutive_recoveries[expert_name] = 0
            else:
                self.consecutive_recoveries[expert_name] = 0

        elif current_state == "OBSERVE":
            self.observe_count[expert_name] += 1
            if self.observe_count[expert_name] >= OBSERVE_PERIOD:
                if rolling_30 > BASELINE:
                    self.expert_states[expert_name] = "ACTIVE"
                else:
                    self.expert_states[expert_name] = "FROZEN"
                self.observe_count[expert_name] = 0

    def _create_freeze_report(self, expert_name: str, rolling_30: float, rolling_50: float):
        """创建冻结报告"""
        freeze_start = self.freeze_start_times.get(expert_name)
        self.freeze_reports[expert_name] = {
            "expert": expert_name,
            "freeze_reason": f"rolling_hit_30={rolling_30:.4f} < baseline={BASELINE}",
            "freeze_start": freeze_start,
            "freeze_duration": 0,
            "rolling_hit_30": round(rolling_30, 4),
            "rolling_hit_50": round(rolling_50, 4),
            "zscore": round(self._zscore(expert_name, 50), 4),
            "status": "FROZEN",
            "timestamp": datetime.now().isoformat()
        }

    def get_expert_state(self, expert_name: str) -> str:
        """获取专家状态"""
        return self.expert_states[expert_name]

    def get_expert_weights(self) -> Dict[str, float]:
        """获取专家权重（冻结专家=0）"""
        weights = {}
        for expert in EXPERTS:
            state = self.expert_states[expert]
            if state == "FROZEN":
                weights[expert] = 0.0
            elif state == "OBSERVE":
                weights[expert] = 0.05
            else:
                weights[expert] = 1.0
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        return weights

    def get_recent_hit_rates(self) -> Dict[str, float]:
        """获取近期命中率"""
        return {
            expert: self._rolling_hit_rate(expert, 20)
            for expert in EXPERTS
        }

    def get_freeze_report(self, expert_name: str) -> Optional[Dict]:
        """获取冻结报告"""
        return self.freeze_reports.get(expert_name)

    def get_all_reports(self) -> Dict[str, Dict]:
        """获取所有冻结报告"""
        reports = {}
        for expert in EXPERTS:
            report = self.freeze_reports.get(expert)
            if report:
                report = dict(report)
                if self.freeze_start_times.get(expert):
                    report["freeze_duration"] = self.total_hits[expert] - self.freeze_start_times[expert]
                reports[expert] = report
        return reports

    def reset(self):
        """重置所有状态"""
        self.expert_hit_sequences = defaultdict(list)
        self.expert_states = defaultdict(lambda: "ACTIVE")
        self.freeze_start_times = defaultdict(lambda: None)
        self.observe_count = defaultdict(int)
        self.consecutive_failures = defaultdict(int)
        self.consecutive_recoveries = defaultdict(int)
        self.freeze_reports = {}
        self.total_hits = defaultdict(int)