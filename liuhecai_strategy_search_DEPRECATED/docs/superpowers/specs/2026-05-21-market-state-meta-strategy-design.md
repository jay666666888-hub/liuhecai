# 状态切换型元策略设计文档

## 目标

重构 `meta_strategy.py`：从静态投票 → MarketStateDetector + ExpertRouter 架构

**核心问题：** 静态加权平均在市场状态切换时失效（近期30期增益-0.83%）

---

## 一、市场状态检测

### 1.1 四维特征

| 特征 | 计算方式 | 阈值来源 |
|------|---------|---------|
| `entropy_20` | 信息熵 `H = -∑p·log(p)` | 滚动20期p80/p20 |
| `volatility_20` | 生肖频率标准差 | 滚动20期p80/p20 |
| `regime_shift` | 布尔标记：前10期均值vs再前10期 | 二元判定 |
| `hit_stability` | 专家预测一致性 | 滚动20期p80/p20 |

### 1.2 独立检测器投票

```
entropy_detector:
  entropy > p80 → CHAOTIC +2
  entropy < p20 → HOT +1

volatility_detector:
  volatility > p80 → COLD +2
  volatility < p20 → HOT +1

stability_detector:
  hit_stability < p20 → TRANSITION +2
  hit_stability > p80 → HOT +1

regime_detector:
  regime_shift == True → TRANSITION +2
```

### 1.3 最终状态判定

```
scores = {HOT:0, COLD:0, TRANSITION:0, CHAOTIC:0}
state = max(scores)

冲突处理:
  if top1_score - top2_score < 2:
    state = "UNCERTAIN"
```

### 1.4 UNCERTAIN 权重

```
UNCERTAIN:
  weight = expert_recent_hit × expert_stability
  normalize()

原因：动态权重避免退化成像另一套静态策略
```

---

## 二、状态依赖权重

### 2.1 基础权重

| 状态 | Trend | Momentum | Gap | Color |
|------|-------|----------|-----|-------|
| HOT | 0.7 | 0.2 | 0.1 | 0 |
| COLD | 0.2 | 0.2 | 0.6 | 0 |
| TRANSITION | 0.25 | 0.5 | 0.25 | 0 |
| CHAOTIC | 0.25 | 0.25 | 0.25 | 0.25 |

### 2.2 COLOR 动态注入

```
color_weight = min(0.15, 0.15 × color_confidence)
color_confidence = rolling_hit_20 / baseline

约束:
  if confidence < 1.05 → color_weight = 0
  if confidence > 1.5 → confidence = 1.5

注入:
  other_weights *= (1 - color_weight)
  final_weights = other_weights × scale + color_weight
  重新归一化 sum = 1
```

### 2.3 CHAOTIC 扰动机制

```
base_weights: Trend=Gap=Momentum=Color=0.25
noise ~ N(0, 0.03)
new_weight = base_weight + noise

约束:
  clip to [0.10, 0.40]
  禁止单专家 > 0.4
  禁止连续10期主导 → weight × 0.8

explore_probability = 0.05 + entropy_score × 0.25
  clip [0.05, 0.30]

原因：低混乱≈5%，高混乱≈30%，动态更合理
```

---

## 三、专家冻结机制

### 3.1 冻结条件

```
baseline = 0.50
rolling_hit_30 < baseline 连续30次更新 → freeze=True
weight = 0，不参与投票/权重更新/状态贡献
保留后台监控
```

原因：连续10次太敏感，容易频繁冻结/恢复造成专家状态抖动

### 3.2 恢复条件

```
rolling_hit_50 > baseline + 0.03 AND zscore_50 > 1
连续50次更新 → unfreeze=True
```

原因：避免恢复后两期变差再冻结的震荡循环

### 3.3 安全机制

```
MAX_FREEZE = 200期
超限 → 强制恢复观察30期 (weight=0.05)
观察通过 → ACTIVE
观察失败 → FROZEN
```

---

## 四、状态切换过渡

### 4.1 Adaptive Blend Transition

```
old_state != new_state → transition=True

confidence = (top1_score - top2_score) / top1_score

transition_period:
  confidence > 0.5 → 3期
  confidence > 0.3 → 5期
  else → 8期

权重混合:
  alpha = t / transition_period
  final_weight = (1-alpha) × old_weight + alpha × new_weight
```

### 4.2 异常处理

```
过渡期间若第三状态成为新第一：
  取消当前过渡
  old_state = current_blend_state
  new_state = CHAOTIC
```

---

## 五、专家多样性惩罚

### 5.1 目的

避免多个专家输出高度重叠，实际上只是同一策略复制多份

### 5.2 相似度计算

```
corr = jaccard(expertA.top6, expertB.top6)

if corr > 0.8:
  weaker.weight *= 0.7
```

### 5.3 输出

```json
{
  "expert_a": "",
  "expert_b": "",
  "similarity": "",
  "penalty": ""
}
```

---

## 六、状态确认机制

### 6.1 三期确认

```
new_state连续3期领先 → 确认切换
否则 → 保持当前状态

原因：避免频繁切换 HOT→COLD→HOT→TRANSITION→HOT
```

---

## 七、评价指标

### 7.1 核心指标（不再只看best_hit_rate）

| 指标 | 说明 |
|------|------|
| `mean_hit_rate` | 平均命中率 |
| `rolling_30_hit` | 滚动30期命中率 |
| `max_drawdown` | 最大回撤 |
| `stability_score` | 稳定性分数 |

### 7.2 元策略目标

```
不是：56%→65%
而是：56%→57% 同时 回撤 -15%→-5%
这才是状态型元策略真正的价值
```

---

## 八、输出文件

### 8.1 expert_state_report.json

```json
{
  "market_state": "",
  "expert_weights": {},
  "expert_recent_hit": {},
  "expert_drawdown": {},
  "disabled_experts": []
}
```

### 8.2 chaotic_report.json

```json
{
  "market_entropy": "",
  "weights_before": {},
  "weights_after": {},
  "explore_triggered": "",
  "replaced_zodiac": "",
  "replacement_reason": ""
}
```

### 8.3 color_activation_report.json

```json
{
  "state": "",
  "color_confidence": "",
  "color_weight": "",
  "activated": "",
  "rolling_hit_20": "",
  "baseline": ""
}
```

### 8.4 market_state_report.json

```json
{
  "entropy_signal": "",
  "volatility_signal": "",
  "stability_signal": "",
  "regime_signal": "",
  "scores": {},
  "winner": "",
  "confidence": ""
}
```

### 8.5 expert_freeze_report.json

```json
{
  "expert": "",
  "freeze_reason": "",
  "freeze_start": "",
  "freeze_duration": "",
  "rolling_hit_30": "",
  "rolling_hit_50": "",
  "zscore": "",
  "status": "ACTIVE/FROZEN/OBSERVE"
}
```

### 8.6 state_transition_report.json

```json
{
  "old_state": "",
  "new_state": "",
  "confidence": "",
  "transition_period": "",
  "current_step": "",
  "alpha": "",
  "weights_before": {},
  "weights_after": {}
}
```

### 8.7 expert_diversity_report.json

```json
{
  "expert_a": "",
  "expert_b": "",
  "similarity": "",
  "penalty": ""
}
```

---

## 九、实现计划

1. **MarketStateDetector** - 独立检测器 + 投票聚合
2. **ExpertStateManager** - 冻结/恢复机制
3. **StateRouter** - 状态依赖权重
4. **TransitionController** - 平滑过渡
5. **ChaosHandler** - CHAOTIC特殊处理
6. **ColorActivator** - 动态COLOR注入
7. **ExpertDiversityPenalty** - 相似度惩罚
8. **MetaStrategyV2** - 整合所有组件

---

*文档创建: 2026-05-21*
*最后更新: 2026-05-21（修正冻结/恢复条件，增加多样性惩罚，确认机制，评价指标）*