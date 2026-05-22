# 六合预测系统全面优化设计

## 1. 背景与目标

**现状问题：**
- v5/v7 预测脚本使用硬编码权重，策略搜索结果未被实际使用
- 无自动闭环：策略搜索产出的最优权重需人工同步
- 代码分散，配置不统一
- **旧数据文件（liuhecai_data.json, truth_dataset.json）使用的是假占位数据**

**数据源验证：**
- API: `https://history.macaumarksix.com/history/macaujc2/y/${year}`
- **动态生肖映射**：每年按农历年重排，映射不同
  - 2024: 1→龍, 2→兔, 3→虎...
  - 2025: 1→蛇, 2→龍, 3→兔... (偏移+1)
  - **解决方案：从API数据自动提取当年映射**
- 特码生肖: `zodiac[6]`（官方直接给出）
- 数据分布均衡（5.8% ~ 11.2%/生肖），验证通过

**目标：**
- 命中率 >65%，标准差 <5%
- 全自动闭环：策略搜索 → 权重同步 → 预测 → 推送
- 代码重构，统一架构

---

## 2. 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                        定时 cron (21:35)                     │
└──────────────────────────┬────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    1. DataFetcher                            │
│  - 获取最新开奖数据                                           │
│  - 验证上期预测，更新状态                                     │
│  - 输出: liuhecai_data.json                                 │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    2. StrategySearcher                       │
│  - 运行遗传算法搜索最优权重                                    │
│  - Walk Forward 验证                                        │
│  - 输出: best_strategy.json (仅当优于当前权重)                │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    3. StrategySynchronizer                   │
│  - 检测新策略是否优于当前策略 (hit_rate↑, std↓)               │
│  - 自动更新 predictor/config.py 权重                          │
│  - 输出: 同步确认 + 版本记录                                  │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    4. Predictor (v5/v7)                     │
│  - 统一配置读取权重                                          │
│  - 生成预测结果                                              │
│  - 输出: liuhecai_prediction.json                            │
└──────────────────────────┬───────────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    5. NotificationSender                      │
│  - Telegram / WeChat 推送                                    │
│  - 格式: 验证结果 + 预测 + 统计                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 目录结构

```
liuhecai/
├── docs/
│   └── superpowers/specs/
├── predictor/                    # 新增：统一预测器
│   ├── __init__.py
│   ├── config.py                 # 统一权重配置（自动同步目标）
│   ├── data_fetcher.py           # 数据获取
│   ├── predictor.py              # 核心预测逻辑
│   ├── strategy_searcher.py       # 策略搜索封装
│   ├── strategy_sync.py           # 自动同步权重
│   ├── notification.py            # 推送通知
│   └── main.py                   # 入口
├── liuhecai_strategy_search/     # 现有策略搜索系统
├── tests/
│   ├── test_predictor.py
│   ├── test_sync.py
│   └── test_integration.py
├── scripts/                      # cron 调用脚本
│   └── run_pipeline.py           # 一键运行全流程
└── configs/
    └── strategy_state.json       # 当前策略状态记录
```

---

## 4. 核心组件设计

### 4.1 predictor/config.py — 统一配置

```python
# 权重由策略搜索自动同步，禁止手动修改
CURRENT_STRATEGY = {
    'version': 'auto_sync_v1',
    'weights': {...},  # 自动同步
    'hit_rate': 0.6512,
    'std': 0.042,
    'updated_at': '2026-05-22T21:35:00',
    'source': 'strategy_searcher'
}
```

### 4.2 strategy_sync.py — 自动同步逻辑

```python
def should_update(new_strategy, current_strategy) -> bool:
    """判断是否更新：命中率↑ 且 标准差↓"""
    improvement = (
        new_strategy['hit_rate'] > current_strategy['hit_rate'] * 1.02  # 提升>2%
        and new_strategy['std'] < current_strategy['std'] * 0.95          # 波动降低>5%
    )
    return improvement

def sync_weights(new_weights):
    """写入 config.py，原子操作"""
    # 读取模板
    # 替换权重
    # 写入 temp
    # mv temp -> config.py
```

### 4.3 predictor/main.py — 主流程

```python
def pipeline():
    # 1. 数据获取 & 验证
    fetcher.run()

    # 2. 策略搜索 (可选，基于 schedule)
    searcher.run_if_needed()  # 每天/每周运行

    # 3. 同步权重
    sync.run()

    # 4. 预测
    result = predictor.run()

    # 5. 推送
    notifier.send(result)
```

### 4.4 验证机制

```python
# 防覆盖：状态文件记录已验证期号
STATE_FILE = 'configs/verification_state.json'
{
    "last_verified_period": "2026139",
    "pending_period": "2026140",
    "pending_top6": ["鼠", "牛", ...]
}
```

---

## 5. 性能目标与验证

| 指标 | 目标 | 验证方式 |
|------|------|----------|
| 命中率 | >65% | Walk Forward 回测 |
| 标准差 | <5% | Monte Carlo 稳定性测试 |
| 自动化 | 100% | 无人工干预连续运行 30 天 |
| 同步延迟 | <24h | 策略更新到生效 |

---

## 6. 错误处理

| 场景 | 处理 |
|------|------|
| 策略搜索失败 | 保持当前权重，跳过同步 |
| 同步写入失败 | 回滚，保留旧权重 |
| 数据获取失败 | 跳过本期，等待下期 |
| 推送失败 | 重试 3 次，失败后记录 |

---

## 7. 分阶段实施

### Phase 1: 重构 (1-2天)
- 抽取 predictor/ 统一预测器
- 统一配置管理
- 保持现有 v5/v7 功能兼容

### Phase 2: 闭环 (2-3天)
- 实现 strategy_sync.py
- 打通搜索→同步→预测流程
- 单元测试

### Phase 3: 自动化 (1-2天)
- cron 调度配置
- 推送通知完善
- 全流程集成测试

### Phase 4: 验证 (长期)
- 每日监控命中率/标准差
- 策略更新日志
- 异常告警

---

## 8. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 过拟合 | 中 | 高 | Walk Forward + 保守更新阈值 |
| 权重突变 | 低 | 高 | 2% 提升门槛 + 人工可干预 |
| 推送风暴 | 低 | 低 | 每日一次，合并通知 |

---

## 9. 待决策

- [ ] cron 调度频率：每日 / 每周？
- [ ] 权重更新阈值：2% 是否合适？
- [ ] 是否保留 v5/v7 独立运行能力？
