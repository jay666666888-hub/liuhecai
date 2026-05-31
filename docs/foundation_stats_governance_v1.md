# Foundation Stats Governance v1.0

> **生效日期：2026-05-30**
> **状态：正式冻结**

---

## 1. 当前 Category 列表

| Category | 路径 | 依赖 | 说明 |
|----------|------|------|------|
| `special_stats` | `foundation/special_stats/` | `actual`（特码） | 遗漏统计 |
| `draw_stats` | `foundation/draw_stats/` | `actual_list`（完整7码） | 频率统计 |

**已验证 stats：**

| Type | Category | 依赖 | 状态 |
|------|----------|------|------|
| `zodiac_miss` | special_stats | actual | ✅ v1.0 |
| `wave_miss` | special_stats | actual | ✅ v1.0 |
| `hot_stats` | draw_stats | actual_list | ✅ v1.0 |

---

## 2. 已冻结 Schema v1.0

```json
{
  "type": "<stat_type>",
  "category": "<category>",
  "version": "1.0",
  "map_version": "<MAP_VERSION>",
  "computed_at": "<ISO8601>",
  "source": "aggregated_live.jsonl",
  "record_count": "<integer>",
  "latest_issue": "<issue_string>",
  "data": { ... }
}
```

**必填字段：**
- `type`：stats 类型标识
- `category`：属于哪个 category
- `version`：必须是 "1.0"
- `map_version`：映射表版本（如 "2026_v1"）
- `computed_at`：计算时间 ISO8601
- `source`：固定为 `aggregated_live.jsonl`
- `record_count`：原始记录数
- `latest_issue`：最新一期
- `data`：统计结果

**禁止字段：**
- `prediction`
- `hit`
- `version`（模型版本）
- `score`
- `ranking`
- `confidence`
- `ensemble`
- 任何 AI 相关字段

---

## 3. Immutable Boundary

```
immutable facts = actual + actual_list
```

**Foundation stats 只能依赖：**
- `actual`（特码开奖结果）
- `actual_list`（完整7码）

**Foundation stats 禁止依赖：**
- `prediction`
- `hit`
- `version`（模型版本字段）
- `model`
- `score`
- `confidence`
- `ranking`
- 任何 AI 推理结果

**边界注释：**

```
┌─────────────────────────────────────────────┐
│           immutable facts                   │
│  (actual, actual_list from aggregated_live)  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│         foundation stats engine             │
│    stats_engine.py / build_all_stats()       │
│                                             │
│  compute_zodiac_miss()     → zodiac_miss    │
│  compute_wave_miss()       → wave_miss      │
│  compute_hot_stats()       → hot_stats      │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│        storage/stats_cache/foundation/      │
│                                             │
│  special_stats/  │  draw_stats/              │
│    _meta.json   │    _meta.json             │
│    zodiac_miss  │    hot_stats              │
│    wave_miss    │                          │
└──────────────────┬──────────────────────────┘
```

**违反边界 = 架构污染**

---

## 4. Dashboard Boundary

```
Dashboard = discover + load + render
```

**Dashboard 只能做：**
- 读取 `foundation/` 下各 category 的 `_meta.json`
- 动态注册路由 `/api/stats/<category>/<type>`
- 从 `storage/stats_cache/foundation/` 加载 stats 文件
- 将数据传递给前端渲染

**Dashboard 禁止做：**
- 二次统计（不在 stats_engine.py 中计算）
- 聚合推理（运行时 ranking/sorting）
- 计算新字段（运行时派生指标）
- 缓存融合（多个 stats 合并）
- 任何 business logic

**Dashboard 代码必须保持：**
- 零 business logic
- 零 计算密集型操作
- 零 跨 stats 聚合

---

## 5. Stats_Engine Boundary

```
stats_engine.py = read + compute + cache + atomic_write
```

**stats_engine.py 只能做：**
1. 读取 `aggregated_live.jsonl`
2. 计算统计指标
3. 管理内存缓存（可选）
4. 原子写入 stats 文件

**stats_engine.py 禁止做：**
- ranking（任何形式的排序评分）
- prediction（预测推理）
- AI inference（AI 模型调用）
- ensemble logic（多模型融合）
- 跨 stats 聚合

**职责锁定：**

```
read:    load_aggregated()
compute: compute_xxx_stats()
cache:   _get_cache() / _set_cache()
write:   _atomic_write()
```

**违反边界 = stats_engine → predictor_engine 退化**

---

## 6. Predictor Boundary

```
predictor chain ⟜ foundation stats (禁止)
```

**绝对禁止：**

```
predictor.py → 读取/引用 foundation stats
```

**原因：**

foundation stats 的目的是为 Dashboard 提供 immutable facts，而非影响 predictor 行为。如果 predictor 依赖 foundation stats，会形成：

1. 循环依赖风险
2. 预测链脆弱性
3. 架构耦合

**未来扩展：**

如需 predictor 专用分析，需单独设计 `storage/stats_cache/predictor/` 层：

```
storage/stats_cache/
├── foundation/      # immutable facts only
│   ├── special_stats/
│   └── draw_stats/
└── predictor/        # 未来独立设计
    └── <predictor analytics>
```

**v2.0 之前：predictor chain 禁止依赖 foundation stats。**

---

## 7. Category 扩展规则

**允许的 category（v1.0）：**

| Category | 路径 | 约束 |
|----------|------|------|
| `special_stats` | `foundation/special_stats/` | 基于 actual |
| `draw_stats` | `foundation/draw_stats/` | 基于 actual_list |

**新增 category 条件：**

1. 有明确的 immutable data source
2. 与现有 category 不重叠
3. 需要修改 `_meta.json` 路径结构
4. 需经过 governance review
5. 需更新本规范文档

**禁止新增的 category：**
- `trend_stats`
- `ai_stats`
- `fusion_stats`
- `model_stats`
- 任何含有 AI/prediction 语义的 category

**Category 数量上限：2（v1.0）**

---

## 8. Stats 新增审批规则

**新增 stats 必须满足：**

1. **Schema 验证**：符合 v1.0 schema
2. **Immutable 验证**：只依赖 actual/actual_list
3. **Category 归属**：明确属于 special_stats 或 draw_stats
4. **计算隔离**：不依赖其他 stats
5. **Dashboard 兼容**：无需修改 dashboard_server.py

**新增 stats 流程：**

```
1. 提出需求（明确 stats 类型和用途）
2. 检查 immutable boundary
3. 确定 category 归属
4. 验证 schema v1.0 合规
5. 实现 compute_xxx_stats()
6. 更新 build_all_stats()
7. 运行 build_stats_cache.py
8. 验证 /api/stats/<category>/<type> 可访问
9. 更新文档
```

**禁止的 stats 特征：**
- 依赖 prediction/hit/version
- 计算权重/指数衰减
- AI ranking/similarity
- 跨 stats 聚合
- 运行时实时计算

---

## 9. Runtime-Safe 原则

**Atomic Write 流程：**

```
tmp file → fsync → os.rename
```

**Commit Signal 规则：**

`_meta.json` 必须最后写入，作为 atomic write 的 commit signal。

**Cache TTL：**

- Memory cache TTL: 300s（5分钟）
- 允许 cron 覆盖刷新

**Dashboard 动态发现：**

- 启动时读取所有 `foundation/*/_meta.json`
- 动态注册路由
- 不重启 Dashboard 即可发现新 stats

**错误处理：**

- stats 文件损坏 → 返回 cached_at 旧数据 + error 标记
- _meta.json 丢失 → category 显示 "meta not found"
- 计算异常 → 不写入 partial 数据

---

## 10. v1.0 冻结声明

**冻结范围：**

| 组件 | 状态 | 冻结内容 |
|------|------|----------|
| Schema | ✅ 冻结 | v1.0 字段定义 |
| Category | ✅ 冻结 | special_stats, draw_stats |
| API | ✅ 冻结 | /api/stats/<category>/<type> |
| Immutable boundary | ✅ 冻结 | actual, actual_list only |
| Dashboard | ✅ 冻结 | discover + load + render |
| stats_engine | ✅ 冻结 | read + compute + cache + write |
| Predictor boundary | ✅ 冻结 | 禁止依赖 foundation stats |

**v1.0 验证 stats：**

- ✅ `zodiac_miss` (special_stats)
- ✅ `wave_miss` (special_stats)
- ✅ `hot_stats` (draw_stats)

**v1.1 规划 stats（待评审）：**

- `size_balance`
- `odd_even_balance`
- `element_miss`

**v2.0 规划（独立设计）：**

- `predictor analytics layer`

**v1.0 冻结期间禁止：**

1. 新增 category
2. 修改 schema 字段
3. 引入 AI/prediction 逻辑
4. predictor 依赖 foundation stats
5. Dashboard 添加 business logic
6. stats_engine 添加 ranking/inference

**规范维护：**

本文档为 Foundation Stats Governance v1.0 的唯一权威来源。

如需变更，必须经过正式 governance review 流程。

---

## 附录：目录结构

```
storage/stats_cache/foundation/
├── special_stats/
│   ├── _meta.json          # commit signal
│   ├── zodiac_miss.json
│   └── wave_miss.json
│
└── draw_stats/
    ├── _meta.json          # commit signal
    └── hot_stats.json

docs/
└── foundation_stats_governance_v1.md  # 本文档
```