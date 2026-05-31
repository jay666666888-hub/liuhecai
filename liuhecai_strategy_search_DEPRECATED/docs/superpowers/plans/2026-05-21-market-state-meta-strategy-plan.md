# 状态切换型元策略实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 重构 meta_strategy.py，从静态投票改为 MarketStateDetector + ExpertRouter 架构，实现状态切换型元策略

**架构：** 市场状态检测（4维特征）→ 状态确认（三期）→ 专家权重路由（HOT/COLD/TRANSITION/CHAOTIC/UNCERTAIN）→ 动态COLOR注入 → 多样性惩罚 → 平滑过渡

**技术栈：** Python 3, numpy, pandas

---

## 文件结构

```
meta_v2/
├── __init__.py
├── state_detector.py      # MarketStateDetector - 四维特征检测器
├── expert_manager.py      # ExpertStateManager - 冻结/恢复机制
├── state_router.py        # StateRouter - 状态依赖权重
├── transition.py          # TransitionController - 平滑过渡
├── chaos_handler.py       # ChaosHandler - CHAOTIC处理
├── color_activator.py     # ColorActivator - 动态COLOR注入
├── diversity_penalty.py   # ExpertDiversityPenalty - 相似度惩罚
├── meta_strategy_v2.py    # MetaStrategyV2 - 整合所有组件
└── tests/
    ├── __init__.py
    ├── test_state_detector.py
    ├── test_expert_manager.py
    ├── test_state_router.py
    └── test_meta_strategy_v2.py
```

---

## 任务 1：MarketStateDetector

**文件：**
- 创建：`meta_v2/state_detector.py`
- 测试：`meta_v2/tests/test_state_detector.py`

- [ ] **步骤 1：编写失败的测试**

```python
# meta_v2/tests/test_state_detector.py
import pytest
import numpy as np
import sys
sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')
from meta_v2.state_detector import MarketStateDetector

def test_entropy_calculation():
    """测试信息熵计算"""
    detector = MarketStateDetector(window=20)
    # 均匀分布 = 最大熵
    uniform_probs = np.ones(12) / 12
    entropy = detector._calc_entropy(uniform_probs)
    assert entropy > 2.0  # 均匀分布熵约 2.48

def test_state_voting():
    """测试状态投票聚合"""
    detector = MarketStateDetector(window=20)
    scores = detector._vote_state(
        entropy_signal="CHAOTIC",
        volatility_signal="COLD",
        stability_signal="TRANSITION",
        regime_signal="TRANSITION"
    )
    assert scores["TRANSITION"] == 4
    assert scores["CHAOTIC"] == 2

def test_state_classification():
    """测试最终状态分类"""
    detector = MarketStateDetector(window=20)
    detector.entropy_history = [3.0] * 20  # 高熵
    detector.volatility_history = [0.5] * 20  # 高波动
    state = detector.detect_state()
    assert state in ["CHAOTIC", "COLD", "TRANSITION", "HOT", "UNCERTAIN"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_state_detector.py -v`
预期：FAIL，报错 "No module named 'meta_v2'"

- [ ] **步骤 3：编写最少实现代码**

```python
# meta_v2/state_detector.py
"""市场状态检测器"""
import numpy as np
from typing import Dict, Tuple

class MarketStateDetector:
    """四维特征检测器 + 投票聚合"""

    def __init__(self, window: int = 20):
        self.window = window
        self.entropy_history = []
        self.volatility_history = []
        self.stability_history = []
        self.regime_history = []
        self.state_confirmation = {"HOT": 0, "COLD": 0, "TRANSITION": 0, "CHAOTIC": 0}
        self.current_state = "HOT"

    def _calc_entropy(self, probs: np.ndarray) -> float:
        """计算信息熵 H = -∑p·log(p)"""
        probs = probs[probs > 0]
        return -np.sum(probs * np.log(probs))

    def _calc_volatility(self, zodiac_counts: np.ndarray) -> float:
        """计算波动率（标准差）"""
        expected = np.mean(zodiac_counts)
        if expected == 0:
            return 0.0
        return np.std(zodiac_counts) / expected

    def _detect_entropy_state(self, entropy: float) -> Tuple[str, int]:
        """熵检测器"""
        p80 = np.percentile(self.entropy_history, 80) if len(self.entropy_history) >= 10 else 2.5
        p20 = np.percentile(self.entropy_history, 20) if len(self.entropy_history) >= 10 else 1.5
        if entropy > p80:
            return "CHAOTIC", 2
        elif entropy < p20:
            return "HOT", 1
        return "HOT", 0

    def _detect_volatility_state(self, volatility: float) -> Tuple[str, int]:
        """波动率检测器"""
        p80 = np.percentile(self.volatility_history, 80) if len(self.volatility_history) >= 10 else 0.8
        p20 = np.percentile(self.volatility_history, 20) if len(self.volatility_history) >= 10 else 0.3
        if volatility > p80:
            return "COLD", 2
        elif volatility < p20:
            return "HOT", 1
        return "HOT", 0

    def _detect_stability_state(self, stability: float) -> Tuple[str, int]:
        """稳定性检测器"""
        p80 = np.percentile(self.stability_history, 80) if len(self.stability_history) >= 10 else 0.8
        p20 = np.percentile(self.stability_history, 20) if len(self.stability_history) >= 10 else 0.4
        if stability < p20:
            return "TRANSITION", 2
        elif stability > p80:
            return "HOT", 1
        return "HOT", 0

    def _detect_regime_state(self, regime_shift: bool) -> Tuple[str, int]:
        """状态切换检测器"""
        if regime_shift:
            return "TRANSITION", 2
        return "HOT", 0

    def _vote_state(self, entropy_signal: str, volatility_signal: str,
                    stability_signal: str, regime_signal: str) -> Dict[str, int]:
        """投票聚合"""
        scores = {"HOT": 0, "COLD": 0, "TRANSITION": 0, "CHAOTIC": 0}
        signal_map = {
            "HOT": ("HOT", 1), "COLD": ("COLD", 1), "TRANSITION": ("TRANSITION", 1), "CHAOTIC": ("CHAOTIC", 1)
        }
        for signal in [entropy_signal, volatility_signal, stability_signal, regime_signal]:
            if signal in signal_map:
                state, weight = signal_map[signal]
                scores[state] += weight
        return scores

    def update(self, entropy: float, volatility: float, stability: float, regime_shift: bool):
        """更新状态历史"""
        self.entropy_history.append(entropy)
        self.volatility_history.append(volatility)
        self.stability_history.append(stability)
        self.regime_history.append(regime_shift)
        # 保持窗口大小
        if len(self.entropy_history) > 100:
            self.entropy_history = self.entropy_history[-100:]

    def detect_state(self) -> str:
        """检测当前市场状态"""
        if len(self.entropy_history) < 10:
            return "UNCERTAIN"

        current_entropy = self.entropy_history[-1]
        current_volatility = self.volatility_history[-1] if self.volatility_history else 0
        current_stability = self.stability_history[-1] if self.stability_history else 0.5
        current_regime = self.regime_history[-1] if self.regime_history else False

        # 独立检测
        entropy_state, _ = self._detect_entropy_state(current_entropy)
        volatility_state, _ = self._detect_volatility_state(current_volatility)
        stability_state, _ = self._detect_stability_state(current_stability)
        regime_state, _ = self._detect_regime_state(current_regime)

        # 投票
        scores = self._vote_state(entropy_state, volatility_state, stability_state, regime_state)

        # 三期确认
        max_state = max(scores, key=scores.get)
        if self.state_confirmation.get(max_state, 0) >= 3:
            if self.current_state != max_state:
                self.current_state = max_state
            self.state_confirmation = {k: 0 for k in self.state_confirmation}
            self.state_confirmation[max_state] = 1
        else:
            self.state_confirmation[max_state] = self.state_confirmation.get(max_state, 0) + 1

        # 冲突处理
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) >= 2 and sorted_scores[0] - sorted_scores[1] < 2:
            return "UNCERTAIN"

        return self.current_state

    def get_detection_signals(self) -> Dict[str, str]:
        """获取各检测器信号"""
        if len(self.entropy_history) < 10:
            return {"entropy_signal": "UNKNOWN", "volatility_signal": "UNKNOWN",
                    "stability_signal": "UNKNOWN", "regime_signal": "UNKNOWN"}
        entropy_state, _ = self._detect_entropy_state(self.entropy_history[-1])
        volatility_state, _ = self._detect_volatility_state(self.volatility_history[-1])
        stability_state, _ = self._detect_stability_state(self.stability_history[-1])
        regime_state, _ = self._detect_regime_state(self.regime_history[-1])
        return {
            "entropy_signal": entropy_state,
            "volatility_signal": volatility_state,
            "stability_signal": stability_state,
            "regime_signal": regime_state
        }
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_state_detector.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
cd /home/admin1/liuhecai_strategy_search
git init meta_v2
git add meta_v2/state_detector.py meta_v2/tests/test_state_detector.py meta_v2/__init__.py meta_v2/tests/__init__.py
git commit -m "feat: add MarketStateDetector with 4-dimension feature detection"
```

---

## 任务 2：ExpertStateManager

**文件：**
- 创建：`meta_v2/expert_manager.py`
- 测试：`meta_v2/tests/test_expert_manager.py`

- [ ] **步骤 1：编写失败的测试**

```python
# meta_v2/tests/test_expert_manager.py
import pytest
import sys
sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')
from meta_v2.expert_manager import ExpertStateManager

def test_freeze_condition():
    """测试冻结条件：连续30期低于基准"""
    manager = ExpertStateManager()
    # 模拟30期低于基准
    for i in range(30):
        manager.record_hit("Gap", hit=False)
    assert manager.get_expert_state("Gap") == "FROZEN"

def test_recovery_condition():
    """测试恢复条件：连续50期高于基准+0.03且zscore>1"""
    manager = ExpertStateManager()
    # 先冻结
    for i in range(30):
        manager.record_hit("Gap", hit=False)
    # 模拟50期高于基准+0.03
    for i in range(50):
        manager.record_hit("Gap", hit=True)
    # zscore需要>1，这里简化处理
    assert manager.get_expert_state("Gap") in ["ACTIVE", "OBSERVE"]

def test_max_freeze_duration():
    """测试最大冻结期限：200期"""
    manager = ExpertStateManager()
    # 冻结超过200期
    for i in range(250):
        manager.record_hit("Gap", hit=False)
    # 应该进入OBSERVE状态
    assert manager.get_expert_state("Gap") in ["OBSERVE", "ACTIVE"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_expert_manager.py -v`
预期：FAIL

- [ ] **步骤 3：编写最少实现代码**

```python
# meta_v2/expert_manager.py
"""专家状态管理器 - 冻结/恢复机制"""
from typing import Dict, List
from collections import defaultdict

BASELINE = 0.50
FREEZE_THRESHOLD = 0.03  # recovery需要 > baseline + 0.03
MAX_FREEZE = 200

class ExpertStateManager:
    """专家冻结/恢复管理"""

    def __init__(self):
        self.expert_hit_sequences = defaultdict(list)  # expert -> [hit/not]
        self.expert_states = defaultdict(lambda: "ACTIVE")
        self.freeze_start_times = defaultdict(lambda: None)
        self.observe_count = defaultdict(int)
        self.consecutive_failures = defaultdict(int)
        self.consecutive_recoveries = defaultdict(int)

    def record_hit(self, expert_name: str, hit: bool):
        """记录单次命中"""
        self.expert_hit_sequences[expert_name].append(1 if hit else 0)
        # 保持最大长度
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
            # 检查冻结条件：连续30期 < baseline
            if rolling_30 < BASELINE:
                self.consecutive_failures[expert_name] += 1
                self.consecutive_recoveries[expert_name] = 0
                if self.consecutive_failures[expert_name] >= 30:
                    self.expert_states[expert_name] = "FROZEN"
                    self.freeze_start_times[expert_name] = len(self.expert_hit_sequences[expert_name])
            else:
                self.consecutive_failures[expert_name] = 0
                self.consecutive_recoveries[expert_name] += 1
        elif current_state == "FROZEN":
            freeze_duration = len(self.expert_hit_sequences[expert_name]) - (self.freeze_start_times[expert_name] or 0)
            # 检查安全机制
            if freeze_duration > MAX_FREEZE:
                self.expert_states[expert_name] = "OBSERVE"
                self.observe_count[expert_name] = 0
                return
            # 检查恢复条件：连续50期 > baseline + 0.03 且 zscore > 1
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
            # 观察30期
            self.observe_count[expert_name] += 1
            if self.observe_count[expert_name] >= 30:
                if rolling_30 > BASELINE:
                    self.expert_states[expert_name] = "ACTIVE"
                else:
                    self.expert_states[expert_name] = "FROZEN"
                self.observe_count[expert_name] = 0

    def get_expert_state(self, expert_name: str) -> str:
        """获取专家状态"""
        return self.expert_states[expert_name]

    def get_expert_weights(self) -> Dict[str, float]:
        """获取专家权重（冻结专家=0）"""
        weights = {}
        for expert in ["Gap", "Trend", "Momentum", "Color"]:
            if self.expert_states[expert] == "FROZEN":
                weights[expert] = 0.0
            elif self.expert_states[expert] == "OBSERVE":
                weights[expert] = 0.05
            else:
                weights[expert] = 1.0
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        return weights

    def get_recent_hit_rates(self) -> Dict[str, float]:
        """获取近期命中率"""
        return {expert: self._rolling_hit_rate(expert, 20) for expert in ["Gap", "Trend", "Momentum", "Color"]}
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_expert_manager.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
cd /home/admin1/liuhecai_strategy_search
git add meta_v2/expert_manager.py meta_v2/tests/test_expert_manager.py
git commit -m "feat: add ExpertStateManager with freeze/recovery mechanism"
```

---

## 任务 3：StateRouter

**文件：**
- 创建：`meta_v2/state_router.py`
- 测试：`meta_v2/tests/test_state_router.py`

- [ ] **步骤 1：编写失败的测试**

```python
# meta_v2/tests/test_state_router.py
import pytest
import sys
sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')
from meta_v2.state_router import StateRouter

def test_hot_weights():
    """测试HOT状态权重"""
    router = StateRouter()
    weights = router.get_base_weights("HOT")
    assert weights["Trend"] == pytest.approx(0.7, rel=0.01)
    assert weights["Momentum"] == pytest.approx(0.2, rel=0.01)
    assert weights["Gap"] == pytest.approx(0.1, rel=0.01)

def test_cold_weights():
    """测试COLD状态权重"""
    router = StateRouter()
    weights = router.get_base_weights("COLD")
    assert weights["Gap"] == pytest.approx(0.6, rel=0.01)

def test_uncertain_weights():
    """测试UNCERTAIN动态权重"""
    router = StateRouter()
    recent_hits = {"Gap": 0.4, "Trend": 0.6, "Momentum": 0.5, "Color": 0.3}
    stability = {"Gap": 0.3, "Trend": 0.6, "Momentum": 0.4, "Color": 0.2}
    weights = router.get_uncertain_weights(recent_hits, stability)
    # Trend应该权重最高（0.6*0.6=0.36）
    assert weights["Trend"] > weights["Gap"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_state_router.py -v`
预期：FAIL

- [ ] **步骤 3：编写最少实现代码**

```python
# meta_v2/state_router.py
"""状态路由器 - 状态依赖权重"""
from typing import Dict

BASE_WEIGHTS = {
    "HOT": {"Gap": 0.1, "Trend": 0.7, "Momentum": 0.2, "Color": 0.0},
    "COLD": {"Gap": 0.6, "Trend": 0.2, "Momentum": 0.2, "Color": 0.0},
    "TRANSITION": {"Gap": 0.25, "Trend": 0.25, "Momentum": 0.5, "Color": 0.0},
    "CHAOTIC": {"Gap": 0.25, "Trend": 0.25, "Momentum": 0.25, "Color": 0.25},
}

class StateRouter:
    """状态依赖权重路由"""

    def get_base_weights(self, state: str) -> Dict[str, float]:
        """获取基础权重"""
        return BASE_WEIGHTS.get(state, BASE_WEIGHTS["HOT"]).copy()

    def get_uncertain_weights(self, recent_hits: Dict[str, float],
                             stability: Dict[str, float]) -> Dict[str, float]:
        """UNCERTAIN状态：weight = recent_hit × stability，normalize"""
        weights = {}
        for expert in ["Gap", "Trend", "Momentum", "Color"]:
            weights[expert] = recent_hits.get(expert, 0.0) * stability.get(expert, 0.5)
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        return weights

    def apply_color_weight(self, base_weights: Dict[str, float],
                           color_weight: float) -> Dict[str, float]:
        """应用COLOR动态权重"""
        if color_weight <= 0:
            return base_weights
        others = sum(v for k, v in base_weights.items() if k != "Color")
        if others <= 0:
            return base_weights
        scale = (1 - color_weight) / others
        result = {}
        for expert, w in base_weights.items():
            if expert == "Color":
                result[expert] = color_weight
            else:
                result[expert] = w * scale
        total = sum(result.values())
        if total > 0:
            result = {k: v / total for k, v in result.items()}
        return result
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_state_router.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
cd /home/admin1/liuhecai_strategy_search
git add meta_v2/state_router.py meta_v2/tests/test_state_router.py
git commit -m "feat: add StateRouter with state-dependent weights"
```

---

## 任务 4：TransitionController

**文件：**
- 创建：`meta_v2/transition.py`
- 测试：`meta_v2/tests/test_transition.py`

- [ ] **步骤 1：编写失败的测试**

```python
# meta_v2/tests/test_transition.py
import pytest
import sys
sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')
from meta_v2.transition import TransitionController

def test_transition_initialization():
    """测试过渡初始化"""
    controller = TransitionController()
    assert controller.current_state == "HOT"
    assert controller.transition_active is False

def test_transition_calculation():
    """测试过渡期alpha计算"""
    controller = TransitionController()
    controller.start_transition("HOT", "COLD", confidence=0.6)
    # confidence 0.6 > 0.5 → 3期
    assert controller.transition_period == 3
    # step 1: alpha = 1/3
    alpha = controller.get_current_alpha()
    assert alpha == pytest.approx(0.333, rel=0.01)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_transition.py -v`
预期：FAIL

- [ ] **步骤 3：编写最少实现代码**

```python
# meta_v2/transition.py
"""过渡控制器 - 平滑状态切换"""
from typing import Dict, Optional, Tuple

class TransitionController:
    """自适应混合过渡"""

    def __init__(self):
        self.current_state = "HOT"
        self.transition_active = False
        self.transition_period = 0
        self.current_step = 0
        self.old_state = "HOT"
        self.new_state = "HOT"
        self.blend_weights = {}

    def start_transition(self, old_state: str, new_state: str, confidence: float) -> int:
        """启动过渡，返回过渡期长度"""
        if old_state == new_state:
            self.transition_active = False
            self.current_state = new_state
            return 0

        self.old_state = old_state
        self.new_state = new_state
        self.transition_active = True
        self.current_step = 0

        if confidence > 0.5:
            self.transition_period = 3
        elif confidence > 0.3:
            self.transition_period = 5
        else:
            self.transition_period = 8

        return self.transition_period

    def get_current_alpha(self) -> float:
        """获取当前混合因子"""
        if not self.transition_active:
            return 1.0 if self.current_state == self.new_state else 0.0
        if self.transition_period == 0:
            return 1.0
        return (self.current_step + 1) / self.transition_period

    def step(self) -> bool:
        """执行一步过渡，返回是否完成"""
        if not self.transition_active:
            return True

        self.current_step += 1
        if self.current_step >= self.transition_period:
            self.transition_active = False
            self.current_state = self.new_state
            return True
        return False

    def check_abort(self, third_state_scores: Dict[str, int]) -> bool:
        """检查是否需要中止过渡（第三状态成为第一）"""
        if not self.transition_active or len(third_state_scores) < 3:
            return False
        sorted_states = sorted(third_state_scores.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_states) >= 3 and sorted_states[0][0] not in [self.old_state, self.new_state]:
            return True
        return False

    def get_blended_weights(self, old_weights: Dict[str, float],
                            new_weights: Dict[str, float]) -> Dict[str, float]:
        """获取混合权重"""
        alpha = self.get_current_alpha()
        result = {}
        for expert in old_weights.keys():
            ow = old_weights.get(expert, 0)
            nw = new_weights.get(expert, 0)
            result[expert] = (1 - alpha) * ow + alpha * nw
        total = sum(result.values())
        if total > 0:
            result = {k: v / total for k, v in result.items()}
        return result

    def force_transition(self, new_state: str):
        """强制切换到新状态"""
        self.old_state = self.current_state
        self.new_state = new_state
        self.transition_active = True
        self.current_step = 0
        self.transition_period = 3
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_transition.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
cd /home/admin1/liuhecai_strategy_search
git add meta_v2/transition.py meta_v2/tests/test_transition.py
git commit -m "feat: add TransitionController with adaptive blend"
```

---

## 任务 5：ChaosHandler

**文件：**
- 创建：`meta_v2/chaos_handler.py`
- 测试：`meta_v2/tests/test_chaos_handler.py`

- [ ] **步骤 1：编写失败的测试**

```python
# meta_v2/tests/test_chaos_handler.py
import pytest
import numpy as np
import sys
sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')
from meta_v2.chaos_handler import ChaosHandler

def test_explore_probability():
    """测试动态探索概率"""
    handler = ChaosHandler()
    # 低熵: 0.05 + 1.5*0.25 = 0.425 → clip to 0.30
    prob = handler.get_explore_probability(1.5)
    assert prob == 0.30
    # 高熵: 0.05 + 3.0*0.25 = 0.80 → clip to 0.30
    prob = handler.get_explore_probability(3.0)
    assert prob == 0.30
    # 正常: 0.05 + 2.0*0.25 = 0.55
    prob = handler.get_explore_probability(2.0)
    assert prob == 0.55

def test_weight_clipping():
    """测试权重裁剪"""
    handler = ChaosHandler()
    weights = {"Gap": 0.5, "Trend": 0.5, "Momentum": 0.0, "Color": 0.0}
    clipped = handler.clip_weights(weights)
    assert clipped["Gap"] <= 0.40
    assert clipped["Trend"] <= 0.40
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_chaos_handler.py -v`
预期：FAIL

- [ ] **步骤 3：编写最少实现代码**

```python
# meta_v2/chaos_handler.py
"""CHAOS处理器 - 混乱市场处理"""
import numpy as np
from typing import Dict, List, Tuple, Optional
import random

class ChaosHandler:
    """CHAOTIC状态特殊处理"""

    def __init__(self):
        self.dominance_counter = {}  # expert -> consecutive dominant periods
        self.rng = np.random.default_rng(42)

    def get_explore_probability(self, entropy_score: float) -> float:
        """动态探索概率: 0.05 + entropy_score × 0.25, clip [0.05, 0.30]"""
        prob = 0.05 + entropy_score * 0.25
        return max(0.05, min(0.30, prob))

    def apply_noise(self, base_weights: Dict[str, float]) -> Dict[str, float]:
        """应用N(0, 0.03)噪声"""
        result = {}
        for expert, weight in base_weights.items():
            noise = self.rng.normal(0, 0.03)
            result[expert] = max(0, weight + noise)
        return result

    def clip_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """裁剪到[0.10, 0.40]"""
        result = {}
        for expert, weight in weights.items():
            result[expert] = max(0.10, min(0.40, weight))
        total = sum(result.values())
        if total > 0:
            result = {k: v / total for k, v in result.items()}
        return result

    def check_dominance_penalty(self, weights: Dict[str, float]) -> Dict[str, float]:
        """禁止连续10期主导：weight × 0.8"""
        result = weights.copy()
        for expert, weight in weights.items():
            if self.dominance_counter.get(expert, 0) >= 10:
                result[expert] = weight * 0.8
            if weight == max(weights.values()):
                self.dominance_counter[expert] = self.dominance_counter.get(expert, 0) + 1
            else:
                self.dominance_counter[expert] = 0
        return result

    def should_explore(self, entropy_score: float) -> bool:
        """判断是否触发探索"""
        prob = self.get_explore_probability(entropy_score)
        return random.random() < prob

    def get_replacement(self, current_top6: List[str], all_zodiacs: List[str],
                       recent_hit_rates: Dict[str, float], diversity_scores: Dict[str, float]) -> Tuple[str, str]:
        """
        获取探索替换：非TOP6按 recent_hit_rate × diversity_score 采样
        返回: (replaced_zodiac, replacement_zodiac, reason)
        """
        non_top6 = [z for z in all_zodiacs if z not in current_top6]
        if not non_top6:
            return current_top6[-1], random.choice(all_zodiacs), "no_replacement_available"

        scores = {}
        for zodiac in non_top6:
            scores[zodiac] = recent_hit_rates.get(zodiac, 0.5) * diversity_scores.get(zodiac, 1.0)

        total = sum(scores.values())
        if total > 0:
            probs = {z: s / total for z, s in scores.items()}
            replacement = random.choices(list(probs.keys()), weights=list(probs.values()), k=1)[0]
        else:
            replacement = random.choice(non_top6)

        replaced = random.choice(current_top6)
        return replaced, replacement, "exploration_triggered"
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_chaos_handler.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
cd /home/admin1/liuhecai_strategy_search
git add meta_v2/chaos_handler.py meta_v2/tests/test_chaos_handler.py
git commit -m "feat: add ChaosHandler with dynamic exploration"
```

---

## 任务 6：ColorActivator

**文件：**
- 创建：`meta_v2/color_activator.py`
- 测试：`meta_v2/tests/test_color_activator.py`

- [ ] **步骤 1：编写失败的测试**

```python
# meta_v2/tests/test_color_activator.py
import pytest
import sys
sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')
from meta_v2.color_activator import ColorActivator

def test_color_confidence():
    """测试COLOR置信度计算"""
    activator = ColorActivator()
    # rolling_hit_20 = 0.6, baseline = 0.5 → confidence = 1.2
    color_conf = activator.get_color_confidence(rolling_hit_20=0.6)
    assert color_conf == pytest.approx(1.2, rel=0.01)

def test_color_weight():
    """测试COLOR权重注入"""
    activator = ColorActivator()
    # confidence 1.2 → color_weight = min(0.15, 0.15*1.2) = 0.15
    weight = activator.get_color_weight(rolling_hit_20=0.6)
    assert weight == pytest.approx(0.15, rel=0.01)

def test_low_confidence_no_color():
    """测试低置信度时无COLOR"""
    activator = ColorActivator()
    # rolling_hit_20 = 0.45, baseline = 0.5 → confidence = 0.9 < 1.05 → weight = 0
    weight = activator.get_color_weight(rolling_hit_20=0.45)
    assert weight == 0.0
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_color_activator.py -v`
预期：FAIL

- [ ] **步骤 3：编写最少实现代码**

```python
# meta_v2/color_activator.py
"""COLOR动态注入器"""
BASELINE = 0.50

class ColorActivator:
    """动态COLOR权重注入"""

    def __init__(self):
        self.baseline = BASELINE

    def get_color_confidence(self, rolling_hit_20: float) -> float:
        """color_confidence = rolling_hit_20 / baseline, cap at 1.5"""
        confidence = rolling_hit_20 / self.baseline
        return min(1.5, confidence)

    def get_color_weight(self, rolling_hit_20: float) -> float:
        """color_weight = min(0.15, 0.15 × color_confidence), if confidence < 1.05 → 0"""
        confidence = self.get_color_confidence(rolling_hit_20)
        if confidence < 1.05:
            return 0.0
        return min(0.15, 0.15 * confidence)

    def inject_color(self, base_weights: dict, rolling_hit_20: float) -> dict:
        """注入COLOR权重到基础权重"""
        color_weight = self.get_color_weight(rolling_hit_20)
        if color_weight <= 0:
            return base_weights

        others_total = sum(v for k, v in base_weights.items() if k != "Color")
        if others_total <= 0:
            return base_weights

        scale = (1 - color_weight) / others_total
        result = {}
        for expert, w in base_weights.items():
            if expert == "Color":
                result[expert] = color_weight
            else:
                result[expert] = w * scale

        total = sum(result.values())
        if total > 0:
            result = {k: v / total for k, v in result.items()}
        return result
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_color_activator.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
cd /home/admin1/liuhecai_strategy_search
git add meta_v2/color_activator.py meta_v2/tests/test_color_activator.py
git commit -m "feat: add ColorActivator with dynamic weight injection"
```

---

## 任务 7：ExpertDiversityPenalty

**文件：**
- 创建：`meta_v2/diversity_penalty.py`
- 测试：`meta_v2/tests/test_diversity_penalty.py`

- [ ] **步骤 1：编写失败的测试**

```python
# meta_v2/tests/test_diversity_penalty.py
import pytest
import sys
sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')
from meta_v2.diversity_penalty import ExpertDiversityPenalty

def test_jaccard_similarity():
    """测试Jaccard相似度"""
    penalty = ExpertDiversityPenalty()
    top6_a = ["鼠", "牛", "虎", "兔", "龍", "蛇"]
    top6_b = ["鼠", "牛", "虎", "兔", "龍", "蛇"]  # 完全相同
    sim = penalty._jaccard(top6_a, top6_b)
    assert sim == 1.0

def test_penalty_application():
    """测试惩罚应用"""
    penalty = ExpertDiversityPenalty()
    weights = {"Gap": 0.3, "Trend": 0.4, "Momentum": 0.2, "Color": 0.1}
    predictions = {
        "Gap": ["鼠", "牛", "虎", "兔", "龍", "蛇"],
        "Trend": ["鼠", "牛", "虎", "兔", "龍", "蛇"],  # 完全相同
        "Momentum": ["马", "羊", "猴", "雞", "狗", "豬"],
        "Color": ["马", "羊", "猴", "雞", "狗", "豬"]
    }
    # Gap和Trend相似度=1.0 > 0.8，应触发惩罚
    new_weights = penalty.apply_penalty(weights, predictions)
    # Trend权重应该被降低
    assert new_weights["Trend"] < weights["Trend"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_diversity_penalty.py -v`
预期：FAIL

- [ ] **步骤 3：编写最少实现代码**

```python
# meta_v2/diversity_penalty.py
"""专家多样性惩罚"""
from typing import Dict, List, Tuple

class ExpertDiversityPenalty:
    """Jaccard相似度惩罚，避免专家输出高度重叠"""

    SIMILARITY_THRESHOLD = 0.8
    PENALTY_FACTOR = 0.7

    def _jaccard(self, set_a: List[str], set_b: List[str]) -> float:
        """计算Jaccard相似度"""
        set_a = set(set_a)
        set_b = set(set_b)
        if len(set_a) == 0 and len(set_b) == 0:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def apply_penalty(self, weights: Dict[str, float],
                     predictions: Dict[str, List[str]]) -> Dict[str, float]:
        """应用相似度惩罚"""
        result = weights.copy()
        experts = list(predictions.keys())

        for i in range(len(experts)):
            for j in range(i + 1, len(experts)):
                exp_a = experts[i]
                exp_b = experts[j]
                sim = self._jaccard(predictions.get(exp_a, []), predictions.get(exp_b, []))

                if sim > self.SIMILARITY_THRESHOLD:
                    # 降低较弱者的权重
                    if weights[exp_a] <= weights[exp_b]:
                        weaker = exp_a
                    else:
                        weaker = exp_b

                    result[weaker] = weights[weaker] * self.PENALTY_FACTOR

        # 重新归一化
        total = sum(result.values())
        if total > 0:
            result = {k: v / total for k, v in result.items()}
        return result

    def get_similarity_report(self, predictions: Dict[str, List[str]]) -> List[dict]:
        """生成相似度报告"""
        report = []
        experts = list(predictions.keys())

        for i in range(len(experts)):
            for j in range(i + 1, len(experts)):
                exp_a = experts[i]
                exp_b = experts[j]
                sim = self._jaccard(predictions.get(exp_a, []), predictions.get(exp_b, []))

                if sim > self.SIMILARITY_THRESHOLD:
                    report.append({
                        "expert_a": exp_a,
                        "expert_b": exp_b,
                        "similarity": round(sim, 4),
                        "penalty": self.PENALTY_FACTOR
                    })

        return report
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_diversity_penalty.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
cd /home/admin1/liuhecai_strategy_search
git add meta_v2/diversity_penalty.py meta_v2/tests/test_diversity_penalty.py
git commit -m "feat: add ExpertDiversityPenalty with Jaccard similarity"
```

---

## 任务 8：MetaStrategyV2（集成）

**文件：**
- 创建：`meta_v2/meta_strategy_v2.py`
- 测试：`meta_v2/tests/test_meta_strategy_v2.py`

- [ ] **步骤 1：编写失败的测试**

```python
# meta_v2/tests/test_meta_strategy_v2.py
import pytest
import sys
sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')
from schema import load_standardized
from meta_v2.meta_strategy_v2 import MetaStrategyV2

def test_full_pipeline():
    """测试完整流程"""
    df = load_standardized('/home/admin1/liuhecai_strategy_search/truth_dataset.json')
    meta = MetaStrategyV2(df)
    # 执行10期回测
    results = meta.run_backtest(start_idx=200, end_idx=210)
    assert len(results) == 10
    assert "mean_hit_rate" in results[0]
    assert "rolling_30_hit" in results[0]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_meta_strategy_v2.py -v`
预期：FAIL

- [ ] **步骤 3：编写完整实现代码**

```python
# meta_v2/meta_strategy_v2.py
"""状态切换型元策略V2"""
import numpy as np
import pandas as pd
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict

from meta_v2.state_detector import MarketStateDetector
from meta_v2.expert_manager import ExpertStateManager
from meta_v2.state_router import StateRouter
from meta_v2.transition import TransitionController
from meta_v2.chaos_handler import ChaosHandler
from meta_v2.color_activator import ColorActivator
from meta_v2.diversity_penalty import ExpertDiversityPenalty

EXPERTS = ['Gap', 'Trend', 'Momentum', 'Color']
ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
BASELINE = 0.50


class MetaStrategyV2:
    """状态切换型元策略"""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.state_detector = MarketStateDetector(window=20)
        self.expert_manager = ExpertStateManager()
        self.state_router = StateRouter()
        self.transition_controller = TransitionController()
        self.chaos_handler = ChaosHandler()
        self.color_activator = ColorActivator()
        self.diversity_penalty = ExpertDiversityPenalty()

        self.expert_histories = {name: [] for name in EXPERTS}
        self.prediction_history = []
        self.actual_history = []

    def _get_expert_predictions(self, upto_idx: int) -> Dict[str, List[str]]:
        """获取各专家预测"""
        predictions = {}
        data = self.df.iloc[:upto_idx]

        for expert_name in EXPERTS:
            scores = {}

            for z in ZODIACS:
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
                        if self.df.iloc[i]['zodiac'] == z:
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

    def _calc_state_features(self, upto_idx: int) -> Tuple[float, float, float, bool]:
        """计算市场状态特征"""
        data = self.df.iloc[:upto_idx]
        window = min(20, upto_idx)
        recent_data = data.iloc[-window:]

        # 1. 信息熵
        zodiac_counts = recent_data['zodiac'].value_counts()
        probs = np.array([zodiac_counts.get(z, 0) / window for z in ZODIACS])
        probs = probs[probs > 0]
        entropy = -np.sum(probs * np.log(probs)) if len(probs) > 0 else 0

        # 2. 波动率
        expected = window / 12
        volatility = np.std([zodiac_counts.get(z, 0) for z in ZODIACS]) / expected if expected > 0 else 0

        # 3. 稳定性（专家预测一致性）
        if len(self.prediction_history) >= 10:
            recent_preds = self.prediction_history[-10:]
            hit_counts = []
            for i, pred in enumerate(recent_preds):
                if i < len(self.actual_history):
                    actual = self.actual_history[i]
                    hit_counts.append(1 if actual in pred.get(list(EXPERTS)[0], []) else 0)
            hit_stability = np.std(hit_counts) if len(hit_counts) > 1 else 0
            hit_stability = 1 - hit_stability
        else:
            hit_stability = 0.5

        # 4. 状态切换
        regime_shift = False
        if len(self.prediction_history) >= 20:
            first_half = self.prediction_history[-20:-10]
            second_half = self.prediction_history[-10:]
            first_hits = sum(1 for p in first_half if self.actual_history[len(self.prediction_history)-20+first_half.index(p)] in p.get(list(EXPERTS)[0], []))
            second_hits = sum(1 for p in second_half if self.actual_history[len(self.prediction_history)-10+second_half.index(p)] in p.get(list(EXPERTS)[0], []))
            regime_shift = abs(first_hits - second_hits) > 3

        return entropy, volatility, hit_stability, regime_shift

    def update(self, predictions: Dict[str, List[str]], actual_zodiac: str):
        """更新所有组件"""
        self.actual_history.append(actual_zodiac)

        for expert_name in EXPERTS:
            top6 = predictions.get(expert_name, [])
            hit = 1 if actual_zodiac in top6 else 0
            self.expert_histories[expert_name].append(hit)
            self.expert_manager.record_hit(expert_name, hit > 0)

        self.prediction_history.append(predictions)

    def predict_top6(self) -> Tuple[List[str], Dict]:
        """预测TOP6"""
        current_state = self.state_detector.current_state
        detection_signals = self.state_detector.get_detection_signals()

        # 获取专家预测
        if len(self.prediction_history) > 0:
            predictions = self.prediction_history[-1]
        else:
            predictions = {name: ZODIACS[:6] for name in EXPERTS}

        # 基础权重
        if current_state == "UNCERTAIN":
            recent_hits = self.expert_manager.get_recent_hit_rates()
            stability = {name: 1 - np.std(self.expert_histories[name][-20:]) if len(self.expert_histories[name]) >= 20 else 0.5 for name in EXPERTS}
            base_weights = self.state_router.get_uncertain_weights(recent_hits, stability)
        else:
            base_weights = self.state_router.get_base_weights(current_state)

        # 应用COLOR
        recent_hits = self.expert_manager.get_recent_hit_rates()
        color_weight = self.color_activator.get_color_weight(recent_hits.get("Color", 0.5))
        if color_weight > 0:
            base_weights = self.color_activator.inject_color(base_weights, recent_hits.get("Color", 0.5))

        # CHAOTIC特殊处理
        if current_state == "CHAOTIC":
            entropy = self.state_detector.entropy_history[-1] if self.state_detector.entropy_history else 2.0
            base_weights = self.chaos_handler.apply_noise(base_weights)
            base_weights = self.chaos_handler.clip_weights(base_weights)
            base_weights = self.chaos_handler.check_dominance_penalty(base_weights)

            if self.chaos_handler.should_explore(entropy):
                replaced, replacement, reason = self.chaos_handler.get_replacement(
                    predictions.get("Trend", ZODIACS[:6]), ZODIACS,
                    {z: 0.5 for z in ZODIACS},
                    {z: 1.0 for z in ZODIACS}
                )
                for exp_preds in predictions.values():
                    if replaced in exp_preds:
                        idx = exp_preds.index(replaced)
                        exp_preds[idx] = replacement

        # 多样性惩罚
        base_weights = self.diversity_penalty.apply_penalty(base_weights, predictions)

        # 聚合TOP6
        zodiac_scores = defaultdict(float)
        for expert_name, top6 in predictions.items():
            weight = base_weights.get(expert_name, 0.25)
            for i, zodiac in enumerate(top6):
                position_bonus = 1.0 / (1 + i * 0.1)
                zodiac_scores[zodiac] += weight * position_bonus

        sorted_zodiacs = sorted(zodiac_scores.items(), key=lambda x: x[1], reverse=True)
        top6 = [z for z, s in sorted_zodiacs[:6]]

        report = {
            "market_state": current_state,
            "detection_signals": detection_signals,
            "base_weights": base_weights,
            "color_weight": color_weight
        }

        return top6, report

    def run_backtest(self, start_idx: int = 200, end_idx: Optional[int] = None) -> List[Dict]:
        """运行回测"""
        if end_idx is None:
            end_idx = len(self.df) - 1

        results = []
        for idx in range(start_idx, end_idx):
            # 计算状态特征
            entropy, volatility, stability, regime_shift = self._calc_state_features(idx)
            self.state_detector.update(entropy, volatility, stability, regime_shift)
            new_state = self.state_detector.detect_state()

            # 检测状态切换
            if new_state != self.state_detector.current_state and len(self.state_detector.entropy_history) >= 3:
                scores = self.state_detector._vote_state(
                    self.state_detector.get_detection_signals()["entropy_signal"],
                    self.state_detector.get_detection_signals()["volatility_signal"],
                    self.state_detector.get_detection_signals()["stability_signal"],
                    self.state_detector.get_detection_signals()["regime_signal"]
                )
                confidence = (max(scores.values()) - sorted(scores.values())[1]) / max(scores.values()) if max(scores.values()) > 0 else 0
                self.transition_controller.start_transition(
                    self.state_detector.current_state, new_state, confidence
                )

            # 获取专家预测
            preds = self._get_expert_predictions(idx)
            actual = self.df.iloc[idx + 1]['zodiac']

            # 更新
            self.update(preds, actual)

            # 过渡
            if self.transition_controller.transition_active:
                self.transition_controller.step()

            # 预测
            top6, meta_report = self.predict_top6()

            # 计算指标
            hit = 1 if actual in top6 else 0
            recent_30_hits = self.actual_history[-30:] if len(self.actual_history) >= 30 else self.actual_history
            rolling_30 = sum(recent_30_hits) / len(recent_30_hits) if recent_30_hits else 0
            mean_hit = sum(self.actual_history) / len(self.actual_history) if self.actual_history else 0

            # 计算max_drawdown
            cumulative = []
            running = 0
            for h in self.actual_history:
                running += h - BASELINE
                cumulative.append(running)
            max_drawdown = min(cumulative) if cumulative else 0

            results.append({
                "idx": idx,
                "prediction": top6,
                "actual": actual,
                "hit": hit,
                "mean_hit_rate": round(mean_hit, 4),
                "rolling_30_hit": round(rolling_30, 4),
                "max_drawdown": round(max_drawdown, 4),
                "stability_score": round(1 - np.std(self.actual_history[-50:]) if len(self.actual_history) >= 50 else 0.5, 4),
                "market_state": meta_report["market_state"],
                "expert_weights": meta_report["base_weights"]
            })

        return results

    def get_final_report(self) -> Dict:
        """生成最终报告"""
        recent_30 = self.actual_history[-30:] if len(self.actual_history) >= 30 else self.actual_history
        rolling_30 = sum(recent_30) / len(recent_30) if recent_30 else 0
        mean_hit = sum(self.actual_history) / len(self.actual_history) if self.actual_history else 0

        cumulative = []
        running = 0
        for h in self.actual_history:
            running += h - BASELINE
            cumulative.append(running)
        max_drawdown = min(cumulative) if cumulative else 0

        return {
            "market_state": self.state_detector.current_state,
            "expert_weights": self.state_router.get_base_weights(self.state_detector.current_state),
            "expert_recent_hit": self.expert_manager.get_recent_hit_rates(),
            "expert_drawdown": {expert: 0 for expert in EXPERTS},
            "disabled_experts": [e for e in EXPERTS if self.expert_manager.get_expert_state(e) == "FROZEN"],
            "mean_hit_rate": round(mean_hit, 4),
            "rolling_30_hit": round(rolling_30, 4),
            "max_drawdown": round(max_drawdown, 4),
            "stability_score": round(1 - np.std(self.actual_history[-50:]) if len(self.actual_history) >= 50 else 0.5, 4),
            "total_predictions": len(self.actual_history),
            "timestamp": datetime.now().isoformat()
        }
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /home/admin1/liuhecai_strategy_search && python -m pytest meta_v2/tests/test_meta_strategy_v2.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
cd /home/admin1/liuhecai_strategy_search
git add meta_v2/meta_strategy_v2.py meta_v2/tests/test_meta_strategy_v2.py
git commit -m "feat: add MetaStrategyV2 with state-switching architecture"
```

- [ ] **步骤 6：运行完整回测**

运行：`cd /home/admin1/liuhecai_strategy_search && python -c "
from schema import load_standardized
from meta_v2.meta_strategy_v2 import MetaStrategyV2
import json

df = load_standardized('truth_dataset.json')
meta = MetaStrategyV2(df)
results = meta.run_backtest(start_idx=200, end_idx=300)

with open('expert_state_report.json', 'w') as f:
    json.dump(meta.get_final_report(), f, ensure_ascii=False, indent=2)

print(f'回测完成: {len(results)} 期')
report = meta.get_final_report()
print(f'市场状态: {report[\"market_state\"]}')
print(f'平均命中率: {report[\"mean_hit_rate\"]:.2%}')
print(f'滚动30期: {report[\"rolling_30_hit\"]:.2%}')
print(f'最大回撤: {report[\"max_drawdown\"]:.4f}')
print(f'稳定性: {report[\"stability_score\"]:.4f}')
"
`
预期：输出回测结果

---

## 自检清单

1. **规格覆盖度检查**：
   - [x] MarketStateDetector - 四维特征检测器
   - [x] ExpertStateManager - 冻结/恢复机制
   - [x] StateRouter - 状态依赖权重
   - [x] TransitionController - 平滑过渡
   - [x] ChaosHandler - CHAOTIC处理
   - [x] ColorActivator - 动态COLOR注入
   - [x] ExpertDiversityPenalty - 相似度惩罚
   - [x] MetaStrategyV2 - 整合所有组件

2. **占位符扫描**：无占位符，所有步骤包含实际代码

3. **类型一致性**：各模块接口一致，StateRouter/TransitionController等方法签名匹配

---

**计划已完成并保存到 `docs/superpowers/plans/2026-05-21-market-state-meta-strategy-plan.md`**

两种执行方式：

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

选哪种方式？