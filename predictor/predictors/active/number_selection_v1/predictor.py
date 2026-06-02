#!/usr/bin/env python3
"""
澳门六合 - 多码预测器 v1

统一的多码预测器，通过 strategy 参数控制预测策略：
{
  "strategy": {
    "freq_weight": 0.5,    # 频率权重
    "gap_weight": 0.5,      # 遗漏值权重
    "zodiac_weight": 0.0    # 生肖分区权重
  }
}

策略模式：
- freq_only:     freq_weight=1.0, gap_weight=0.0, zodiac_weight=0.0
- gap_priority:  freq_weight=0.0, gap_weight=1.0, zodiac_weight=0.0
- balanced:      freq_weight=0.5, gap_weight=0.5, zodiac_weight=0.0
- zodiac_tuned:  freq_weight=0.4, gap_weight=0.4, zodiac_weight=0.2
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from predictor.base_predictor import BasePredictor, PredictionResult
from predictor.constants import get_zodiac_map_for_date

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

# 区间频率权重（基于历史数据统计，31-40区间偏低给予更高权重）
# 频率: 01-10=20.8%, 11-20=19.9%, 21-30=20.7%, 31-40=17.8%, 41-49=20.8%
# 权重 = 理论比例(20%) / 实际比例
RANGE_WEIGHTS = {
    '01-10': 0.962,   # 20.0 / 20.8
    '11-20': 1.005,   # 20.0 / 19.9
    '21-30': 0.966,   # 20.0 / 20.7
    '31-40': 1.124,   # 20.0 / 17.8 (最高权重，补偿低频)
    '41-49': 0.962,   # 20.0 / 20.8
}

# 尾数频率权重（基于历史数据统计，884期分析）
# 0尾(4个号码): 实际9.6% vs 理论8.2% → 偏低，降权
# 7尾(5个号码): 实际9.3% vs 理论10.2% → 偏低，加权
# 8尾(5个号码): 实际9.2% vs 理论10.2% → 偏低，加权
# 4尾(5个号码): 实际11.0% vs 理论10.2% → 偏高，降权
TAIL_WEIGHTS = {
    0: 0.847,
    1: 0.989,
    2: 1.071,
    3: 0.978,
    4: 0.927,
    5: 1.046,
    6: 0.957,
    7: 1.097,
    8: 1.111,
    9: 0.978,
}


def get_range_for_number(num):
    """获取号码所属区间"""
    num = int(num)
    if 1 <= num <= 10:
        return '01-10'
    elif 11 <= num <= 20:
        return '11-20'
    elif 21 <= num <= 30:
        return '21-30'
    elif 31 <= num <= 40:
        return '31-40'
    elif 41 <= num <= 49:
        return '41-49'
    return 'unknown'


def get_tail_for_number(num):
    """获取号码的尾数 (0-9)"""
    return int(num) % 10


class NumberSelectionPredictorV1(BasePredictor):
    """多码预测器 v1 - 参数化策略"""

    DEFAULT_STRATEGY = "balanced"  # freq=0.5, gap=0.5
    STRATEGY_PRESETS = {
        "freq_only": {"freq_weight": 1.0, "gap_weight": 0.0, "zodiac_weight": 0.0},
        "gap_priority": {"freq_weight": 0.0, "gap_weight": 1.0, "zodiac_weight": 0.0},
        "balanced": {"freq_weight": 0.5, "gap_weight": 0.5, "zodiac_weight": 0.0},
        "balanced_zodiac": {"freq_weight": 0.45, "gap_weight": 0.45, "zodiac_weight": 0.1},
        "zodiac_tuned": {"freq_weight": 0.4, "gap_weight": 0.4, "zodiac_weight": 0.2},
        "multi_window_union": {"windows": [20, 50, 100], "mode": "union", "top_k_mode": "window"},
        "multi_window_intersection": {"windows": [20, 50, 100], "mode": "intersection", "top_k_mode": "window"},
        # fusion strategies: multi_window + gap_freq
        "fusion_mw_gap_30": {"windows": [10, 30, 50], "mode": "union", "gap_weight": 0.3, "top_k_mode": "fusion"},
        "fusion_mw_gap_50": {"windows": [10, 30, 50], "mode": "union", "gap_weight": 0.5, "top_k_mode": "fusion"},
        "fusion_mw_gap_70": {"windows": [10, 30, 50], "mode": "union", "gap_weight": 0.7, "top_k_mode": "fusion"},
        # multi_window with different windows
        "multi_window_103050": {"windows": [10, 30, 50], "mode": "union", "top_k_mode": "window"},
        "multi_window_union_103050": {"windows": [10, 30, 50], "mode": "union", "top_k_mode": "window"},
        "multi_window_intersection_103050": {"windows": [10, 30, 50], "mode": "intersection", "top_k_mode": "window"},
        # dynamic window weight strategies (exponential decay - smaller window = higher weight)
        # decay values 0.5-0.8 all achieve 49.76% (best), 0.85+ drops to 49.52%
        "multi_window_decay_50": {"windows": [10, 30, 50], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential"},
        "multi_window_decay_70": {"windows": [10, 30, 50], "mode": "union", "top_k_mode": "window", "decay": 0.7, "decay_type": "exponential"},
        "multi_window_decay_85": {"windows": [10, 30, 50], "mode": "union", "top_k_mode": "window", "decay": 0.85, "decay_type": "exponential"},
        # linear decay - step=0.2 achieves 49.76% (best)
        "multi_window_linear_20": {"windows": [10, 30, 50], "mode": "union", "top_k_mode": "window", "decay": 0.2, "decay_type": "linear"},
        # multi_window + range weighting (31-40区间加权)
        "multi_window_range_weighted": {"windows": [10, 30, 50], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential", "range_weight": True},
        # multi_window + tail weighting (尾数加权：8尾7尾加权，4尾降权)
        "multi_window_tail_weighted": {"windows": [10, 30, 50], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential", "tail_weight": True},
        # multi_window + range + tail weighting (双重加权)
        "multi_window_range_tail_weighted": {"windows": [10, 30, 50], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential", "range_weight": True, "tail_weight": True},
        # tiny window experiments - smaller windows with decay=0.5
        "multi_window_tiny_3_10_20": {"windows": [3, 10, 20], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential"},
        "multi_window_tiny_5_15_30": {"windows": [5, 15, 30], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential"},
        "multi_window_tiny_5_10_20": {"windows": [5, 10, 20], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential"},
        "multi_window_tiny_8_20_40": {"windows": [8, 20, 40], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential"},
        "multi_window_tiny_10_20_30": {"windows": [10, 20, 30], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential"},
        # tiny window experiments - smaller windows with decay=0.5
        "multi_window_tiny_3_10_20": {"windows": [3, 10, 20], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential"},
        "multi_window_tiny_5_15_30": {"windows": [5, 15, 30], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential"},
        "multi_window_tiny_5_10_20": {"windows": [5, 10, 20], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential"},
        "multi_window_tiny_8_20_40": {"windows": [8, 20, 40], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential"},
        "multi_window_tiny_10_20_30": {"windows": [10, 20, 30], "mode": "union", "top_k_mode": "window", "decay": 0.5, "decay_type": "exponential"},
        # ========== Fusion Strategies ==========
        # 方法A: 投票法 (多策略共同推荐)
        "strategy_vote_2of3": {
            "top_k_mode": "vote",
            "vote_threshold": 2,
            "strategies": ["mw_103050", "gap", "freq"],
            "top_k_each": 24
        },
        "strategy_vote_all": {
            "top_k_mode": "vote",
            "vote_threshold": 3,  # 必须三个策略都推荐
            "strategies": ["mw_103050", "gap", "freq"],
            "top_k_each": 24
        },
        # 方法B: 评分加权法
        "strategy_score_weighted": {
            "top_k_mode": "score_weighted",
            "weights": [0.5, 0.3, 0.2],  # [mw, gap, freq]
            "strategies": ["mw_103050", "gap", "freq"]
        },
        # 方法C: 串联法 (multi_window选30个，再gap_priority选24个)
        "strategy_tandem_30_24": {
            "top_k_mode": "tandem",
            "first_stage_k": 30,
            "second_stage_k": 24,
            "first_strategy": "mw_103050",
            "second_strategy": "gap"
        },
    }

    def __init__(self, version: str = "number_selection_v1"):
        super().__init__(version)
        self.params = {
            "lookback": 50,
            "strategy": self.DEFAULT_STRATEGY,
        }

    def predict(self, history, top_k=24, strategy=None):
        """
        生成多码预测 - 参数化策略

        Args:
            history: 历史记录列表
            top_k: 返回前k个预测（默认24个）
            strategy: 策略名称或自定义权重 dict

        Returns:
            PredictionResult 对象
        """
        if not history:
            return PredictionResult(
                prediction=[f"{i:02d}" for i in range(1, top_k + 1)],
                scores={},
                metadata={"error": "no history"}
            )

        # 解析策略权重
        weights = self._parse_strategy(strategy or self.params["strategy"])

        # 多窗口策略特殊处理
        if weights.get("top_k_mode") == "window":
            windows = weights.get("windows", [20, 50, 100])
            mode = weights.get("mode", "union")
            decay = weights.get("decay")
            decay_type = weights.get("decay_type")
            range_weight = weights.get("range_weight", False)
            tail_weight = weights.get("tail_weight", False)
            window_scores = self._compute_multi_window_scores(history, windows, mode, decay, decay_type, range_weight, tail_weight)

            # 排序取前 top_k
            sorted_nums = sorted(window_scores.items(), key=lambda x: x[1], reverse=True)
            final_prediction = [n for n, s in sorted_nums[:top_k]]

            # 如果不够top_k，补齐
            if len(final_prediction) < top_k:
                all_nums = set(f"{i:02d}" for i in range(1, 50))
                remaining = list(all_nums - set(final_prediction))
                remaining.sort(key=lambda x: window_scores.get(x, 0), reverse=True)
                final_prediction.extend(remaining[:top_k - len(final_prediction)])

            return PredictionResult(
                prediction=final_prediction[:top_k],
                scores={n: window_scores.get(n, 0) for n in final_prediction[:top_k]},
                metadata={
                    "mode": f"{top_k}ma",
                    "top_k": top_k,
                    "strategy": weights,
                    "strategy_name": strategy or self.params["strategy"]
                }
            )

        # Fusion策略: multi_window + gap_freq 融合
        if weights.get("top_k_mode") == "fusion":
            windows = weights.get("windows", [10, 30, 50])
            mode = weights.get("mode", "union")
            gap_weight = weights.get("gap_weight", 0.5)
            fusion_scores = self._compute_fusion_scores(history, windows, mode, gap_weight)

            # 排序取前 top_k
            sorted_nums = sorted(fusion_scores.items(), key=lambda x: x[1], reverse=True)
            final_prediction = [n for n, s in sorted_nums[:top_k]]

            # 如果不够top_k，补齐
            if len(final_prediction) < top_k:
                all_nums = set(f"{i:02d}" for i in range(1, 50))
                remaining = list(all_nums - set(final_prediction))
                remaining.sort(key=lambda x: fusion_scores.get(x, 0), reverse=True)
                final_prediction.extend(remaining[:top_k - len(final_prediction)])

            return PredictionResult(
                prediction=final_prediction[:top_k],
                scores={n: fusion_scores.get(n, 0) for n in final_prediction[:top_k]},
                metadata={
                    "mode": f"{top_k}ma",
                    "top_k": top_k,
                    "strategy": weights,
                    "strategy_name": strategy or self.params["strategy"]
                }
            )

        # ========== Fusion: 投票法 ==========
        if weights.get("top_k_mode") == "vote":
            vote_threshold = weights.get("vote_threshold", 2)
            strategies = weights.get("strategies", ["mw_103050", "gap", "freq"])
            top_k_each = weights.get("top_k_each", 24)
            predictions = self._compute_vote_predictions(history, strategies, top_k_each)

            # 统计每个号码的出现次数
            from collections import Counter
            all_nums_flat = [n for pred in predictions for n in pred]
            vote_counts = Counter(all_nums_flat)

            # 过滤出达到阈值的号码
            if vote_threshold == 3:
                # 必须三个策略都推荐
                final_set = set(predictions[0])
                for pred in predictions[1:]:
                    final_set &= set(pred)
                final_list = list(final_set)
            else:
                # 达到阈值(>=2)的号码
                final_list = [n for n, c in vote_counts.items() if c >= vote_threshold]

            # 如果不够top_k，补齐
            if len(final_list) < top_k:
                all_nums = set(f"{i:02d}" for i in range(1, 50))
                remaining = list(all_nums - set(final_list))
                # 按投票次数和总分排序补齐
                remaining.sort(key=lambda x: (vote_counts.get(x, 0), sum(s.get(x, 0) for s in [self._get_strategy_scores(history, s) for s in strategies])), reverse=True)
                final_list.extend(remaining[:top_k - len(final_list)])

            # 如果还不够，补充得票最多的
            while len(final_list) < top_k:
                for n, c in vote_counts.most_common(50):
                    if n not in final_list:
                        final_list.append(n)
                        break

            return PredictionResult(
                prediction=final_list[:top_k],
                scores={n: vote_counts.get(n, 0) for n in final_list[:top_k]},
                metadata={
                    "mode": f"{top_k}ma",
                    "top_k": top_k,
                    "strategy": weights,
                    "strategy_name": strategy or self.params["strategy"]
                }
            )

        # ========== Fusion: 评分加权法 ==========
        if weights.get("top_k_mode") == "score_weighted":
            weights_list = weights.get("weights", [0.5, 0.3, 0.2])
            strategies = weights.get("strategies", ["mw_103050", "gap", "freq"])

            # 获取各策略得分
            strategy_scores = [self._get_strategy_scores(history, s) for s in strategies]

            # 归一化并加权融合
            fusion_scores = {}
            all_nums = set()
            for ss in strategy_scores:
                all_nums |= set(ss.keys())

            for num in all_nums:
                num_str = f"{int(num):02d}" if isinstance(num, float) else num
                total = 0
                for i, ss in enumerate(strategy_scores):
                    ss_num = ss.get(num_str, ss.get(num, 0))
                    # 归一化
                    max_s = max(ss.values()) if ss else 1
                    norm = ss_num / max_s if max_s > 0 else 0
                    total += norm * weights_list[i]
                fusion_scores[num_str] = total

            # 排序取前 top_k
            sorted_nums = sorted(fusion_scores.items(), key=lambda x: x[1], reverse=True)
            final_prediction = [n for n, s in sorted_nums[:top_k]]

            # 如果不够top_k，补齐
            if len(final_prediction) < top_k:
                all_nums_set = set(f"{i:02d}" for i in range(1, 50))
                remaining = list(all_nums_set - set(final_prediction))
                remaining.sort(key=lambda x: fusion_scores.get(x, 0), reverse=True)
                final_prediction.extend(remaining[:top_k - len(final_prediction)])

            return PredictionResult(
                prediction=final_prediction[:top_k],
                scores={n: fusion_scores.get(n, 0) for n in final_prediction[:top_k]},
                metadata={
                    "mode": f"{top_k}ma",
                    "top_k": top_k,
                    "strategy": weights,
                    "strategy_name": strategy or self.params["strategy"]
                }
            )

        # ========== Fusion: 串联法 ==========
        if weights.get("top_k_mode") == "tandem":
            first_k = weights.get("first_stage_k", 30)
            second_k = weights.get("second_stage_k", 24)
            first_strategy = weights.get("first_strategy", "mw_103050")
            second_strategy = weights.get("second_strategy", "gap")

            # 第一阶段：用第一个策略选 first_k 个
            first_scores = self._get_strategy_scores(history, first_strategy)
            first_sorted = sorted(first_scores.items(), key=lambda x: x[1], reverse=True)
            first_selection = [n for n, s in first_sorted[:first_k]]

            # 第二阶段：用第二个策略从第一阶段结果中选 second_k 个
            second_scores = self._get_strategy_scores(history, second_strategy)
            second_sorted = sorted(second_scores.items(), key=lambda x: x[1], reverse=True)

            final_prediction = []
            for n, s in second_sorted:
                if n in first_selection and n not in final_prediction:
                    final_prediction.append(n)
                    if len(final_prediction) >= second_k:
                        break

            # 如果不够，补齐
            if len(final_prediction) < second_k:
                remaining = [n for n in first_selection if n not in final_prediction]
                remaining.sort(key=lambda x: second_scores.get(x, 0), reverse=True)
                final_prediction.extend(remaining[:second_k - len(final_prediction)])

            # 再不够，从所有号码补
            if len(final_prediction) < second_k:
                all_nums = set(f"{i:02d}" for i in range(1, 50))
                for n in sorted(all_nums - set(final_prediction), key=lambda x: second_scores.get(x, 0), reverse=True):
                    final_prediction.append(n)
                    if len(final_prediction) >= second_k:
                        break

            return PredictionResult(
                prediction=final_prediction[:top_k],
                scores={n: second_scores.get(n, 0) for n in final_prediction[:top_k]},
                metadata={
                    "mode": f"{top_k}ma",
                    "top_k": top_k,
                    "strategy": weights,
                    "strategy_name": strategy or self.params["strategy"]
                }
            )

        n = len(history)
        lookback = min(self.params["lookback"], n)
        recent = history[-lookback:]

        # 获取生肖映射
        latest_record = history[-1]
        zodiac_map = get_zodiac_map_for_date(latest_record['开奖时间'])

        # 计算每个号码的频率得分
        freq_scores = self._compute_frequency_scores(recent)

        # 计算每个号码的遗漏值
        gap_scores = self._compute_gap_scores(history)

        # 计算生肖权重
        zodiac_weights = self._compute_zodiac_weights(recent, lookback)

        # 综合打分
        num_scores = {}
        max_gap = max(gap_scores.values()) if gap_scores else 1

        for num in range(1, 50):
            num_str = f"{num:02d}"
            zodiac = zodiac_map.get(num_str, '未知')

            freq = freq_scores.get(num_str, 0)
            gap = gap_scores.get(num_str, 0) / max_gap if max_gap > 0 else 0  # 归一化
            z_weight = zodiac_weights.get(zodiac, 0)

            score = (
                freq * weights["freq_weight"] +
                gap * weights["gap_weight"] +
                z_weight * weights["zodiac_weight"]
            )
            num_scores[num_str] = score

        # 按得分排序取前 top_k
        sorted_nums = sorted(num_scores.items(), key=lambda x: x[1], reverse=True)
        final_prediction = [n for n, s in sorted_nums[:top_k]]

        # 如果不够top_k，补齐
        if len(final_prediction) < top_k:
            all_nums = set(f"{i:02d}" for i in range(1, 50))
            remaining = list(all_nums - set(final_prediction))
            remaining.sort(key=lambda x: num_scores.get(x, 0), reverse=True)
            final_prediction.extend(remaining[:top_k - len(final_prediction)])

        return PredictionResult(
            prediction=final_prediction[:top_k],
            scores={n: num_scores.get(n, 0) for n in final_prediction[:top_k]},
            metadata={
                "mode": f"{top_k}ma",
                "top_k": top_k,
                "strategy": weights,
                "strategy_name": strategy or self.DEFAULT_STRATEGY
            }
        )

    def _parse_strategy(self, strategy):
        """解析策略配置"""
        if isinstance(strategy, dict):
            return strategy
        if isinstance(strategy, str):
            return self.STRATEGY_PRESETS.get(strategy, self.STRATEGY_PRESETS[self.DEFAULT_STRATEGY])
        return self.STRATEGY_PRESETS[self.DEFAULT_STRATEGY]

    def _compute_frequency_scores(self, recent):
        """计算每个号码的频率得分（只统计特码）"""
        freq_scores = {}
        for num in range(1, 50):
            num_str = f"{num:02d}"
            # 只统计特码号码出现的次数
            count = 0
            for r in recent:
                special_num = r.get('特码号码')
                if special_num == num_str or special_num == str(num) or special_num == num:
                    count += 1
            freq_scores[num_str] = count / len(recent) if recent else 0
        return freq_scores

    def _compute_gap_scores(self, history):
        """计算每个号码的遗漏值（只统计特码）"""
        gap_scores = {}
        for num in range(1, 50):
            num_str = f"{num:02d}"
            gap = 0
            for i in range(len(history) - 1, -1, -1):
                # 只检查特码号码
                special_num = history[i].get('特码号码')
                if special_num == num_str or special_num == str(num) or special_num == num:
                    break
                gap += 1
            gap_scores[num_str] = gap
        return gap_scores

    def _compute_zodiac_weights(self, recent, lookback):
        """计算每个生肖的权重"""
        zodiac_weights = {}
        for zodiac in ZODIACS:
            count = sum(1 for r in recent if r.get('特码生肖') == zodiac)
            zodiac_weights[zodiac] = count / lookback if lookback > 0 else 0
        return zodiac_weights

    def _compute_multi_window_scores(self, history, windows=None, mode="union", decay=None, decay_type=None, range_weight=False, tail_weight=False):
        """
        多窗口频率融合 - 支持动态权重（指数/线性衰减）和区间/尾数加权

        Args:
            history: 历史记录列表
            windows: 滚动窗口列表
            mode: "union"(并集) 或 "intersection"(交集)
            decay: 衰减率（指数衰减：用于 exponent；线性衰减：step 值）
            decay_type: "exponential" 或 "linear"
            range_weight: 是否启用区间加权（给低频区间更高权重）
            tail_weight: 是否启用尾数加权（给低频尾数更高权重）

        Returns:
            dict: 号码得分
        """
        from collections import Counter

        if windows is None:
            windows = [20, 50, 100]

        all_scores = {}
        for i, w in enumerate(windows):
            # 计算动态权重
            if decay is not None and decay_type == "exponential":
                weight = decay ** i  # 指数衰减: [1.0, decay, decay^2, ...]
            elif decay is not None and decay_type == "linear":
                weight = 1.0 - (i * decay)  # 线性衰减: [1.0, 1-decay, 1-2*decay, ...]
            else:
                weight = 1.0

            recent = history[-w:] if w > 0 else history
            nums = [r.get('特码号码') for r in recent if r.get('特码号码')]
            freq = Counter(nums)

            # 归一化窗口得分，避免大窗口自然产生更多计数
            window_weight = weight / w
            for num, count in freq.items():
                if num not in all_scores:
                    all_scores[num] = 0
                # 归一化后的得分相加
                raw_score = count * window_weight
                # 如果启用区间加权
                if range_weight:
                    rng = get_range_for_number(num)
                    range_mult = RANGE_WEIGHTS.get(rng, 1.0)
                    raw_score *= range_mult
                # 如果启用尾数加权
                if tail_weight:
                    tail = get_tail_for_number(num)
                    tail_mult = TAIL_WEIGHTS.get(tail, 1.0)
                    raw_score *= tail_mult
                all_scores[num] += raw_score

        # 并集：所有窗口分数相加（已归一化）
        # 交集：取平均
        if mode == "intersection":
            for num in all_scores:
                all_scores[num] /= len(windows)

        return all_scores

    def _compute_fusion_scores(self, history, windows=None, mode="union", gap_weight=0.5):
        """
        multi_window + gap_freq 融合评分

        Args:
            history: 历史记录列表
            windows: 滚动窗口列表
            mode: "union"(并集) 或 "intersection"(交集)
            gap_weight: gap分数的权重 (0.0-1.0)
                        multi_window权重 = 1.0 - gap_weight

        Returns:
            dict: 融合后的号码得分
        """
        if windows is None:
            windows = [10, 30, 50]

        # 获取multi_window分数
        mw_scores = self._compute_multi_window_scores(history, windows, mode)

        # 获取gap分数
        gap_scores = self._compute_gap_scores(history)

        # 归一化到同一尺度
        max_mw = max(mw_scores.values()) if mw_scores else 1
        max_gap = max(gap_scores.values()) if gap_scores else 1

        # 融合
        fusion = {}
        all_nums = set(mw_scores.keys()) | set(gap_scores.keys())
        for num in all_nums:
            mw_norm = mw_scores.get(num, 0) / max_mw if max_mw > 0 else 0
            gap_norm = gap_scores.get(num, 0) / max_gap if max_gap > 0 else 0
            fusion[num] = (1 - gap_weight) * mw_norm + gap_weight * gap_norm

        return fusion

    def _get_strategy_scores(self, history, strategy_name):
        """
        根据策略名称获取该策略的得分

        Args:
            history: 历史记录列表
            strategy_name: 策略名称

        Returns:
            dict: 号码得分字典
        """
        if strategy_name == "mw_103050":
            # multi_window [10,30,50] with decay=0.5 (最优)
            return self._compute_multi_window_scores(history, [10, 30, 50], "union", 0.5, "exponential")
        elif strategy_name == "gap":
            # gap_priority (纯遗漏值)
            return self._compute_gap_scores(history)
        elif strategy_name == "freq":
            # freq_only (纯频率)
            lookback = min(self.params["lookback"], len(history))
            recent = history[-lookback:]
            return self._compute_frequency_scores(recent)
        elif strategy_name == "freq_30":
            # freq with lookback=30
            recent = history[-30:]
            return self._compute_frequency_scores(recent)
        elif strategy_name == "gap_norm":
            # 归一化后的gap
            gap_scores = self._compute_gap_scores(history)
            max_gap = max(gap_scores.values()) if gap_scores else 1
            return {k: v / max_gap for k, v in gap_scores.items()}
        else:
            # 默认返回空
            return {}

    def _compute_vote_predictions(self, history, strategies, top_k_each=24):
        """
        计算各策略的top_k预测列表

        Args:
            history: 历史记录列表
            strategies: 策略名称列表
            top_k_each: 每个策略选出的号码数

        Returns:
            list: 各策略的预测列表
        """
        predictions = []
        for strat in strategies:
            scores = self._get_strategy_scores(history, strat)
            sorted_nums = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            top_nums = [n for n, s in sorted_nums[:top_k_each]]
            predictions.append(top_nums)
        return predictions