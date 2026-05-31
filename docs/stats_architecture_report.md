# Foundation Stats 架构报告

## A. 目录结构

```
storage/stats_cache/foundation/
├── special_stats/          # 基于 actual（特码）
│   ├── zodiac_miss.json    # 生肖遗漏
│   ├── wave_miss.json      # 波色遗漏
│   └── _meta.json
│
└── draw_stats/            # 基于 actual_list（完整7码）
    ├── hot_stats.json       # 热度统计
    └── _meta.json
```

## B. 已验证 Stats（v1.0）

| Type | Category | 状态 |
|------|----------|------|
| zodiac_miss | special_stats | ✅ |
| wave_miss | special_stats | ✅ |
| hot_stats | draw_stats | ✅ |

## C. 实施阶段

### Phase 1: foundation stats platform 验证 ✅
- [x] zodiac_miss (special_stats)
- [x] wave_miss (special_stats)
- [x] hot_stats (draw_stats)

### Phase 2: v1.1 stats（待评审）
- [ ] size_balance
- [ ] odd_even_balance
- [ ] element_miss

### Phase 3: v2.0 predictor analytics layer（独立设计）
- 独立于 foundation stats
- 不可混用

## D. current_miss 算法（冻结）

❌ 错误：latest_issue - last_issue（issue gap 问题）

✅ 正确：按记录序列计数

```python
# 从后往前扫，记录最后一个出现位置
for idx in range(len(records) - 1, -1, -1):
    zodiac = records[idx]['actual']
    if zodiac not in zodiac_last_idx:
        zodiac_last_idx[zodiac] = idx

# current_miss = 之后有多少条记录
current_miss = total_records - 1 - last_idx
```

## E. 治理规范

详见：`docs/foundation_stats_governance_v1.md`

**冻结内容：**
- Schema v1.0
- Category（special_stats, draw_stats）
- Immutable boundary（actual, actual_list only）
- Dashboard boundary（discover + load + render）
- stats_engine boundary（read + compute + cache + write）
- Predictor boundary（禁止依赖 foundation stats）