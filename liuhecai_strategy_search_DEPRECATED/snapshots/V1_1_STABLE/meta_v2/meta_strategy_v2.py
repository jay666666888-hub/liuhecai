# meta_v2/meta_strategy_v2.py
"""状态切换型元策略V2 - 总控层"""
import numpy as np
import pandas as pd
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict, Counter

from meta_v2.state_detector import MarketStateDetector
from meta_v2.expert_manager import ExpertStateManager
from meta_v2.state_router import StateRouter
from meta_v2.chaos_handler import ChaosHandler
from meta_v2.color_activator import ColorActivator
from meta_v2.diversity_penalty import ExpertDiversityPenalty
from meta_v2.expert_aggregator import ExpertAggregator

# Expert modules (new structure)
try:
    from experts.gap_expert import compute_gap_scores
    from experts.cycle_expert import compute_cycle_scores
    from experts.trend_expert import compute_trend_scores
    from experts.momentum_expert import compute_momentum_scores
    from experts.color_expert import compute_color_scores
    from experts.frequency_expert import compute_frequency_scores
    from experts.antitrend_expert import compute_antitrend_scores
    HAS_NEW_EXPERTS = True
except ImportError:
    HAS_NEW_EXPERTS = False

# Feature flag: set to False to fallback to old embedded logic
ENABLE_NEW_EXPERTS = True

EXPERTS = ['Gap', 'Trend', 'Momentum', 'Frequency', 'Color', 'AntiTrend', 'Cycle']
ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']
BASELINE = 0.50


class MetaStrategyV2:
    """状态切换型元策略V2 - 总控层（只负责调度和生命周期管理）"""

    def __init__(self, df: pd.DataFrame):
        self.df = df

        # Layer1 组件
        self.state_detector = MarketStateDetector(window=20)
        self.expert_manager = ExpertStateManager()

        # Layer2 组件（可插拔）
        self.state_router = StateRouter()
        # transition.py deprecated and moved to archive/ - no longer used
        self.chaos_handler = ChaosHandler()
        self.color_activator = ColorActivator()
        self.diversity_penalty = ExpertDiversityPenalty()
        self.aggregator = ExpertAggregator()

        # 内部状态
        self.expert_histories = {name: [] for name in EXPERTS}
        self.prediction_history = []
        self.actual_history = []  # zodiac strings
        self.hit_history = []  # 0/1 hits
        self.state_history = []

    def _get_expert_scores(self, upto_idx: int) -> Dict[str, Dict[str, float]]:
        """获取各专家评分（Dict[expert_name, Dict[zodiac, score]]）"""
        scores_map = {}

        for expert_name in EXPERTS:
            if ENABLE_NEW_EXPERTS and HAS_NEW_EXPERTS:
                if expert_name == 'Gap':
                    scores_map['Gap'] = compute_gap_scores(self.df, upto_idx)
                elif expert_name == 'Trend':
                    scores_map['Trend'] = compute_trend_scores(self.df, upto_idx)
                elif expert_name == 'Momentum':
                    scores_map['Momentum'] = compute_momentum_scores(self.df, upto_idx)
                elif expert_name == 'Frequency':
                    scores_map['Frequency'] = compute_frequency_scores(self.df, upto_idx)
                elif expert_name == 'Color':
                    scores_map['Color'] = compute_color_scores(self.df, upto_idx)
                elif expert_name == 'AntiTrend':
                    scores_map['AntiTrend'] = compute_antitrend_scores(self.df, upto_idx)
                elif expert_name == 'Cycle':
                    scores_map['Cycle'] = compute_cycle_scores(self.df, upto_idx)
            else:
                # Fallback: all zeros if no expert modules
                scores_map[expert_name] = {z: 0.0 for z in ZODIACS}

        return scores_map

    def _get_expert_predictions(self, upto_idx: int) -> Dict[str, List[str]]:
        """获取各专家预测TOP6列表（兼容性别名）"""
        scores_map = self._get_expert_scores(upto_idx)
        return {
            expert: [z for z, s in sorted(
                score_map.items(), key=lambda x: x[1], reverse=True
            )[:6]]
            for expert, score_map in scores_map.items()
        }

    def _calc_state_features(self, upto_idx: int) -> Tuple[float, float, float, bool]:
        """计算市场状态特征（特征计算，不在总控）"""
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
            for j, pred in enumerate(recent_preds):
                # pred is {expert: {zodiac: score}}, actual_history aligned with predictions
                actual_idx = len(self.actual_history) - 10 + j
                if 0 <= actual_idx < len(self.actual_history):
                    actual = self.actual_history[actual_idx]
                    # Get top6 from first expert's score dict
                    first_expert_scores = pred.get(list(EXPERTS)[0], {})
                    top6 = [z for z, s in sorted(first_expert_scores.items(), key=lambda x: x[1], reverse=True)[:6]]
                    hit_counts.append(1 if actual in top6 else 0)
            hit_stability = np.std(hit_counts) if len(hit_counts) > 1 else 0
            stability = 1 - hit_stability
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
        """更新所有组件生命周期"""
        self.actual_history.append(actual_zodiac)

        # Compute hit once per prediction (not per expert)
        hit = 0
        for expert_name in EXPERTS:
            top6 = predictions.get(expert_name, [])
            expert_hit = 1 if actual_zodiac in top6 else 0
            self.expert_histories[expert_name].append(expert_hit)
            self.expert_manager.record_hit(expert_name, expert_hit > 0)
            hit += expert_hit

        # hit_history: one entry per prediction (aggregate hit)
        self.hit_history.append(hit)

        # Store full scores not just top6 lists
        if hasattr(self, '_current_expert_scores'):
            self.prediction_history.append(self._current_expert_scores)
            self._current_expert_scores = None

    def predict_top6(self) -> Tuple[List[str], Dict]:
        """预测TOP6（调度各组件）"""
        # 1. 获取市场状态
        current_state = self.state_detector.current_state

        # 2. 获取专家评分（当前期，来自_update后存储的_current_expert_scores）
        expert_scores = getattr(self, '_current_expert_scores', None)
        if expert_scores is None:
            expert_scores = {name: {z: 1.0 for z in ZODIACS} for name in EXPERTS}

        # 3. 获取基础权重（StateRouter）
        if current_state == "UNCERTAIN":
            recent_hits = self.expert_manager.get_recent_hit_rates()
            stability = {name: 1 - np.std(self.expert_histories[name][-20:]) if len(self.expert_histories[name]) >= 20 else 0.5 for name in EXPERTS}
            self.state_router.update(current_state, recent_hits, stability)
        else:
            self.state_router.update(current_state)

        base_weights = self.state_router.get_weight()

        # 4. 应用COLOR（ColorActivator）
        recent_hits = self.expert_manager.get_recent_hit_rates()
        color_weight = self.color_activator.get_color_weight(recent_hits.get("Color", 0.5))
        if color_weight > 0:
            base_weights = self.color_activator.inject_color(base_weights, recent_hits.get("Color", 0.5))

        # 5. CHAOTIC特殊处理（ChaosHandler - 权重扰动）
        if current_state == "CHAOTIC":
            entropy = self.state_detector.entropy_history[-1] if self.state_detector.entropy_history else 2.0
            base_weights = self.chaos_handler.get_weight(base_weights, entropy)

        # 6. 多样性惩罚（DiversityPenalty - 权重惩罚）
        # 将当前top6列表传给diversity_penalty用于权重调整
        top6_lists = {
            expert: [z for z, s in sorted(
                expert_scores[expert].items(), key=lambda x: x[1], reverse=True
            )[:6]]
            for expert in EXPERTS
        }
        base_weights = self.diversity_penalty.get_weight(base_weights, top6_lists)

        # 7. 获取熵值用于探索
        entropy = self.state_detector.entropy_history[-1] if self.state_detector.entropy_history else 2.0

        # 8. 使用ExpertAggregator完成最终聚合
        top6, agg_report = self.aggregator.aggregate(
            expert_scores, base_weights, entropy,
            diversity_scores={z: 1.0 for z in ZODIACS}
        )

        report = {
            "market_state": current_state,
            "base_weights": base_weights,
            "color_weight": color_weight,
            "aggregation": agg_report
        }

        return top6, report

    def run_backtest(self, start_idx: int = 200, end_idx: Optional[int] = None) -> List[Dict]:
        """运行回测"""
        if end_idx is None:
            end_idx = len(self.df) - 1

        results = []
        for idx in range(start_idx, end_idx):
            # 1. 计算状态特征并更新检测器
            entropy, volatility, stability, regime_shift = self._calc_state_features(idx)
            self.state_detector.update(entropy, volatility, stability, regime_shift)
            new_state = self.state_detector.detect_state()

            # 2. 检测状态切换（TransitionController）
            # 只有new_state连续3次领先才会真正切换（磁滞已在detector中处理）
            pass  # 状态切换由detector的三期确认机制处理

            # 3. 获取专家评分（分数形式的原始评分）
            expert_scores = self._get_expert_scores(idx)
            self._current_expert_scores = expert_scores

            # 转换为top6列表（用于ExpertManager更新）
            preds = {
                expert: [z for z, s in sorted(
                    score_map.items(), key=lambda x: x[1], reverse=True
                )[:6]]
                for expert, score_map in expert_scores.items()
            }
            actual = self.df.iloc[idx + 1]['zodiac']

            # 4. 预测（必须在update之前，否则_current_expert_scores被清除）
            top6, meta_report = self.predict_top6()

            # 5. 更新（ExpertManager） - 会清除_current_expert_scores
            self.update(preds, actual)

            # 6. 恢复scores用于下一轮（可选，帮助调试）
            # self._current_expert_scores = expert_scores  # 保留到下一轮

            # 6. 计算指标
            hit = 1 if actual in top6 else 0
            recent_30_hits = self.hit_history[-30:] if len(self.hit_history) >= 30 else self.hit_history
            rolling_30 = sum(recent_30_hits) / len(recent_30_hits) if recent_30_hits else 0
            mean_hit = sum(self.hit_history) / len(self.hit_history) if self.hit_history else 0

            # 计算max_drawdown
            cumulative = []
            running = 0
            for h in self.hit_history:
                running += h - BASELINE
                cumulative.append(running)
            max_drawdown = min(cumulative) if cumulative else 0

            # 计算stability
            stability_score = 1 - np.std(self.hit_history[-50:]) if len(self.hit_history) >= 50 else 0.5

            # 状态分布（按每轮实际状态统计）
            per_result_state_counts = dict(Counter(self.state_history + [meta_report["market_state"]]))

            results.append({
                "idx": idx,
                "prediction": top6,
                "actual": actual,
                "hit": hit,
                "mean_hit_rate": round(mean_hit, 4),
                "rolling_30_hit": round(rolling_30, 4),
                "max_drawdown": round(max_drawdown, 4),
                "stability_score": round(stability_score, 4),
                "dominant_state": new_state,
                "market_state": meta_report["market_state"],
                "expert_weights": meta_report["base_weights"],
                "state_distribution": per_result_state_counts
            })

            self.state_history.append(meta_report["market_state"])

        return results

    def get_final_report(self) -> Dict:
        """生成最终报告"""
        recent_30 = self.hit_history[-30:] if len(self.hit_history) >= 30 else self.hit_history
        rolling_30 = sum(recent_30) / len(recent_30) if recent_30 else 0
        mean_hit = sum(self.hit_history) / len(self.hit_history) if self.hit_history else 0

        cumulative = []
        running = 0
        for h in self.hit_history:
            running += h - BASELINE
            cumulative.append(running)
        max_drawdown = min(cumulative) if cumulative else 0

        state_counts = defaultdict(int)
        for s in self.state_history:
            state_counts[s] += 1

        frozen_experts = [e for e in EXPERTS if self.expert_manager.get_expert_state(e) == "FROZEN"]

        return {
            "market_state": self.state_detector.current_state,
            "expert_weights": self.state_router.report()["weights"],
            "expert_recent_hit": self.expert_manager.get_recent_hit_rates(),
            "expert_drawdown": {expert: 0 for expert in EXPERTS},
            "disabled_experts": frozen_experts,
            "mean_hit_rate": round(mean_hit, 4),
            "rolling_30_hit": round(rolling_30, 4),
            "max_drawdown": round(max_drawdown, 4),
            "stability_score": round(1 - np.std(self.hit_history[-50:]) if len(self.hit_history) >= 50 else 0.5, 4),
            "state_distribution": dict(state_counts),
            "expert_utilization": {e: len(self.expert_histories[e]) for e in EXPERTS},
            "freeze_count": len(frozen_experts),
            "transition_count": sum(1 for i in range(1, len(self.state_history)) if self.state_history[i] != self.state_history[i-1]),
            "total_predictions": len(self.hit_history),
            "timestamp": datetime.now().isoformat()
        }