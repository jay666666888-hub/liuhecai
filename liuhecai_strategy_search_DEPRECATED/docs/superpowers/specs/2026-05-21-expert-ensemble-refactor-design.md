# Expert Ensemble 重构设计文档

日期: 2026-05-21
状态: 已批准执行

## 目标

重构三个专家（GapExpert, CycleExpert, TrendExpert）以降低结构重叠，提高 error diversity。

## 验证优先级

1. **Hard Gate**（必须通过）:
   - max_error_corr < 0.30
   - feature_family_overlap < 0.25
   - max_jaccard_overlap < 0.50

2. **Soft Gate**:
   - max_prediction_corr < 0.40

3. **System Performance**（Hard Gate 通过后才看）:
   - walk-forward mean_hit 提升
   - regime range 收敛
   - stability 下降或保持

## 执行顺序（强制单步）

### STEP 1: GapExpert
### STEP 2: CycleExpert
### STEP 3: TrendExpert

每次只允许一个变量变化，确保可归因性。

---

## GapExpert 设计

### 允许特征
- `last_seen_distance`: 上次出现至今的间隔
- `missing_rank`: 在 zodiac 列表中的排名（gap 越大排名越高）
- `gap_acceleration`: gap(t) - gap(t-1)，一阶差分

### 禁止特征
- 周期统计 (cycle_mean, cycle_std)
- 趋势特征
- 窗口统计

### 评分公式
```python
score = missing_rank * 2.0 + gap_acceleration * 0.5
```

### 标准化
所有特征使用 z-score 标准化后再组合。

### 验证指标
- feature_overlap_matrix
- prediction_corr vs Cycle, Trend
- error_corr vs Cycle, Trend

---

## CycleExpert 设计

### 允许特征
- `fft_peak_strength`: FFT 峰值强度
- `dominant_cycle_length`: 主周期长度
- `spectral_entropy`: 归一化频谱熵
- `cycle_phase`: 当前相位

### 禁止特征
- gap, trend, moving_average, streak

### 评分公式
```python
score = dominant_cycle_strength * (1 - entropy_norm)
```

其中 `entropy_norm` 是归一化到 [0,1] 的 spectral_entropy。

### 核心原则
CycleExpert 回答："这个序列是否存在稳定周期结构？"
而不是："这个周期有多好用于预测"

---

## TrendExpert 设计

### 允许特征
- `EMA_slope`: 双尺度 EMA 斜率 (span=12 vs span=50)
- `direction_strength`: 方向强度

### 禁止特征
- cycle, gap, periodicity, rolling_mean

### 评分公式
```python
short_ema = EMA(span=12)
long_ema = EMA(span=50)
trend_signal = short_ema - long_ema
EMA_slope = slope(trend_signal)
score = EMA_slope + direction_strength
```

### 核心原则
TrendExpert 捕捉 "方向变化的加速度"
不是：趋势水平、趋势周期、趋势强度

---

## 代码组织

```
experts/
  gap_expert.py      # 独立模块
  cycle_expert.py    # 独立模块
  trend_expert.py    # 独立模块

MetaStrategyV2:
  - 单一入口 (get_expert_scores)
  - 仅做 orchestration
  - 支持 ENABLE_NEW_EXPERTS 回滚
```

### 回滚机制
```python
ENABLE_NEW_EXPERTS = True  # 使用新模块
ENABLE_NEW_EXPERTS = False # fallback 到旧 _get_expert_scores()
```

---

## 约束

1. **不做架构重写** — 仅逻辑搬迁
2. **保持单一入口** — MetaStrategyV2.get_expert_scores()
3. **score 必须标准化** — z-score 或 min-max normalization
4. **禁止外部参数化** — 避免调参黑箱

---

## 验证流程

每次 STEP 完成后：
1. 跑 feature_overlap_matrix
2. 跑 prediction_corr matrix
3. 跑 error_corr matrix
4. Hard Gate 判断

通过后才允许进入下一步。
