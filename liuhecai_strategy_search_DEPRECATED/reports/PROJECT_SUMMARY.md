# 六合采策略搜索系统 - 项目总览

## 项目状态: 进行中 (非75%目标)

---

## 1. 数据分析结论

### 数据特征
| 指标 | 值 |
|------|-----|
| 总期数 | 870期 (2023-2026) |
| 数据性质 | 接近随机均匀分布 |
| 每生肖理论命中率 | 8.33% (1/12) |
| TOP6理论命中率 | 50% (6/12) |

### 关键发现
- **Number→Zodiac公式**: `(number_mod12 + year - 2021) % 12 → zodiac_index`
  - 同周期内100%准确
  - 但跨期预测只有7-8%,无预测价值
- 所有测试信号(TOP1)强度: 7-10%,接近随机
- **75%目标在当前数据上不可实现**

### 信号强度汇总
| 信号 | TOP1准确率 | 高于随机 |
|------|-----------|---------|
| 随机基准 | 8.33% | - |
| 历史频率最优 | 8.97% | +0.6% |
| Period尾号最强 | ~16% | +8% |
| 其他所有信号 | 7-10% | <2% |

---

## 2. 系统架构

### 文件结构
```
liuhecai_strategy_search/
├── zodiac_validation.csv          # 历史数据 (870期)
├── generated_validation.csv       # 生成数据
├── experts/                       # 7个专家模块
│   ├── gap_expert.py             # 时间间隔专家
│   ├── cycle_expert.py           # 周期专家
│   ├── trend_expert.py           # 趋势专家
│   ├── momentum_expert.py       # 动量专家
│   ├── frequency_expert.py       # 频率专家
│   ├── color_expert.py           # 颜色专家
│   └── antitrend_expert.py       # 反趋势专家
├── meta_v2/                      # 元策略层
│   ├── meta_strategy_v2.py       # 总控层
│   ├── state_detector.py         # 状态检测器
│   ├── expert_manager.py        # 专家管理器
│   ├── state_router.py           # 状态路由
│   ├── chaos_handler.py         # 混沌处理器
│   ├── color_activator.py        # 颜色激活器
│   ├── diversity_penalty.py      # 多样性惩罚
│   ├── expert_aggregator.py     # 专家聚合器
│   ├── confidence_filter.py     # 置信度过滤器 (新增)
│   └── diversity_config.py       # 多样性配置
├── archive/                      # 归档
│   └── transition.py.deprecated  # 已废弃
├── reports/                      # 报告 (29个)
│   ├── FINAL_SYSTEM_REPORT.json
│   ├── performance_audit.json
│   ├── confidence_filter_v2.json
│   └── ...
└── venv/                         # Python虚拟环境
```

### 系统流程
```
数据输入 → Expert评分 → State检测 → 权重路由 → 聚合 → 置信度过滤 → 输出TOP6
```

---

## 3. 性能指标

### 当前性能
| 指标 | 值 | 说明 |
|------|-----|------|
| 样本量 | 602期 | 索引200-801 |
| Walk-forward均值 | 0.418 | - |
| 基准线 | 0.5402 | - |
| 差距 | -0.1222 | 系统低于基准 |

### 问题诊断
- 现有系统48%低于随机基准50%
- 聚合逻辑可能在损害而非提升性能

---

## 4. 已修复问题

| 问题 | 状态 |
|------|------|
| hit_history重复bug | ✅ 已修复 |
| ExpertManager 5专家硬编码 | ✅ 已修复 |
| TransitionController死代码 | ⚠️ 已废弃 |
| 稳定性计算虚假值 | ✅ 已修复为真实计算 |
| 状态检测器阈值校准 | ✅ 已校准 |

---

## 5. 置信度过滤模块

### 配置
- 文件: `meta_v2/confidence_filter.py`
- 阈值: 0.55
- 状态: COMPLETE

### 公式
```
confidence = (Top1 - Top2) / Top1 * state_stability_weight - entropy_penalty * (1 - expert_agreement)
```

### State权重
| State | Weight |
|-------|--------|
| HOT | 0.7 |
| COLD | 0.8 |
| CHAOTIC | 0.5 |
| TRANSITION | 0.9 |
| UNCERTAIN | 1.0 |

### 决策策略
- confidence < 0.55 → **SKIP** (不预测)
- confidence >= 0.55 → **SELECT** (输出TOP1-3)

---

## 6. 状态系统设计决策

### 诊断
- 症状: TRANSITION dominates at 71%
- 根因: 状态检测器阈值与数据分布不匹配
- 性质: 设计不匹配,非bug

### 决策
- 选择: **Option A** - 接受TRANSITION作为基础/默认状态
- 理由:
  - 真实市场大部分时间处于"中性"状态
  - HOT/COLD/CHAOTIC代表极端事件(占~24%)
  - 所有4个状态都存在,非崩溃

### 当前状态分布
| State | Count | Ratio |
|-------|-------|-------|
| HOT | 18 | 6% |
| COLD | 21 | 7% |
| CHAOTIC | 28 | 9% |
| TRANSITION | 214 | 71% |
| UNCERTAIN | 19 | 6% |

---

## 7. 目标调整

### 原始目标
- TOP6命中率: 75%

### 现实评估
- 数据性质: 接近随机
- 可达到目标: **55-60%** (通过优化)
- 随机基准: 50%

### 优化方向
1. **修复聚合逻辑** - 当前48%低于随机50%
2. **置信度过滤** - 只在信号强时预测
3. **简化策略** - 避免过度复杂化损害性能

---

## 8. 下一步建议

### 短期 (可达55%)
1. 修复现有系统使达到50%+ (修复数据格式不匹配问题)
2. 启用置信度过滤模块
3. 移除损害性能的聚合逻辑

### 中期 (可达55-58%)
1. 优化Expert权重分配
2. 调整状态检测阈值
3. 验证置信度过滤效果

### 长期 (不可达)
- 75%目标需要外部信号,当前数据不支持

---

## 9. 报告文件列表

| 报告 | 说明 |
|------|------|
| FINAL_SYSTEM_REPORT.json | 最终系统报告 |
| performance_audit.json | 性能审计 |
| confidence_filter_v2.json | 置信度过滤模块 |
| state_system_design_decision.json | 状态系统设计决策 |
| stability_fix_retry.json | 稳定性修复 |
| expert_contribution_v3.json | 专家贡献分析 |
| ... | 共29个报告 |

---

*最后更新: 2026-05-22*