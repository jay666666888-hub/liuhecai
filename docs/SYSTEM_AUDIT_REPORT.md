# SYSTEM_AUDIT_REPORT.md
## 澳门六合预测系统 - 全量自发现式系统审计
**日期**: 2026-05-27
**审计方法**: Full Self-Discovery Audit（自动理解 → 自主发现 → 端到端验证）

---

## 第一部分：系统结构

### 1.1 系统架构图

```
                          ┌─────────────────────────────────────────┐
                          │         EXTERNAL API                       │
                          │  https://history.macaumarksix.com/        │
                          └──────────────────────┬──────────────────┘
                                                 │ HTTP (timeout=30s, no retry)
                          ┌──────────────────────▼──────────────────┐
                          │      data_fetcher.py                      │
                          │  fetch_year_data() → .cache/liuhecai_*   │
                          └──────────────────────┬──────────────────┘
                          ┌──────────────────────▼──────────────────┐
                          │   orchestrator.py / run_live_cycle()      │
                          │   [1] sync [2] verify [3] predict [4] write │
                          └──────────┬───────────────────────────────┘
                                    │
          ┌─────────────────────────┼───────────────────────────────┐
          │                         │                               │
┌─────────▼──────────┐   ┌──────────▼──────────┐   ┌───────────────▼────┐
│ PredictorRegistry │   │   LedgerWriter      │   │ data_fetcher       │
│ .scan()           │   │   .write_live()     │   │ .get_all_records() │
│ .evaluate()       │   │   .verify()         │   └────────────────────┘
│ .get_validator() │   │   Hash Chain        │
└─────────┬────────┘   └──────────┬──────────┘
          │                        │
  ┌───────▼─────────┐    ┌────────▼─────────────────────────────────┐
  │ validators/     │    │  storage/aggregated_live.jsonl              │
  │ liuhe_validator│    │  storage/prediction_index.json              │
  │ pingte_validator│   │  storage/__init__.py (security guard)        │
  └────────────────┘    └────────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
    ┌─────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
    │ dashboard_server │  │ notification   │  │ version_book/  │
    │ :5188           │  │ Telegram       │  │ index.json     │
    └─────────────────┘  └────────────────┘  └────────────────┘
```

### 1.2 模块关系图

```
scripts/run_pipeline.py ──────────────────────────────► cron/daily_update.sh
        │                                              (21:35 daily)
        ▼                                              ┌──────────────┐
orchestrator.py ──┬──► PredictorRegistry ───────────────┤ 2 个 cron   │
        │        │     (singleton, class-level cache)  │ 作业重叠！  │
        │        └──► validators/                       └──────────────┘
        │                    │
        ▼                    ▼
ledger_writer.py ────────────► storage/__init__.py
        │                    (security guard: monkey-patch builtins.open)
        ▼                    ⚠️ 仅对单进程有效，可被绕过
storage/aggregated_live.jsonl ◄─── 唯一真相源 ( Sole Source of Truth )
storage/prediction_index.json ◄─── 索引文件 ( 非原子读写 )
```

### 1.3 执行流程图

```
每日 Cron (21:35)
    │
    ▼
scripts/run_pipeline.py
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ orchestrator.run_live_cycle()                              │
├─────────────────────────────────────────────────────────────┤
│ [0] sync_latest_results()     ← API抓取开奖结果             │
│     └─ data_fetcher.get_all_records([2024,2025,2026])       │
│         └─ .cache/liuhecai_{year}.json                     │
│                                                             │
│ [1] get_all_records()        ← 读缓存构建标准数据           │
│     └─ build_standard_records()                            │
│                                                             │
│ [2] verify_prediction()      ← 验证上期预测                │
│     └─ ledger_writer.verify_prediction()                   │
│         └─ aggregated_live.jsonl (全文件重写)              │
│                                                             │
│ [3] orchestrator.predict()  ← 各版本预测                   │
│     └─ BasePredictor.predict(history, top_k)              │
│                                                             │
│ [4] write_live_prediction()  ← 追加新预测                   │
│     └─ ledger_writer.write_live_prediction()              │
│         └─ aggregated_live.jsonl (追加)                   │
│         └─ prediction_index.json (读写)                     │
│         └─ Hash Chain 维护                                 │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
notification.send_notification()
    │
    ▼
Telegram / Dashboard (:5188)
```

### 1.4 状态流图

```
PENDING (新预测) ─────────────────────────────────────────────────► VERIFIED (开奖后)
     │                                                                │
     │ write_live_prediction()                                        │
     ▼                                                                │
  ┌────────────────┐                                  ┌────────────▼────────────┐
  │ actual=None    │                                  │ actual=生肖            │
  │ hit=None       │                                  │ hit=bool               │
  │ status=pending │                                  │ status=verified        │
  └──────┬─────────┘                                  └────────────┬────────────┘
         │                                                        │
         │ verify_prediction()                                   │
         │ (ledger_writer.py:288-306)                            │
         │ ⚠️ 脏数据修复逻辑: 即使 status='verified'              │
         │    也允许修改 actual 和 hit                           │
         └──────────────────────────────────────────────────────┘
```

### 1.5 数据流图

```
API Data
  │
  ├─► zodiac[0-6] ──► 特码生肖 (预测目标)
  │                  actual_list (7码全表, 平特一肖用)
  │
  └─► build_standard_records()
         │
         ├─► history ──► [v5/v7/v12/v21/v23/v24/v27/v28/v29] predictors
         │                 │
         │                 └─► prediction[] ──► hit = actual in prediction
         │
         └─► aggregated_live.jsonl ──► Dashboard (:5188)
                                          │
                                          └─► summary.py ──► stats
```

---

## 第二部分：发现的问题

### A. 关键数据完整性问题（CRITICAL / HIGH）

| ID | 严重度 | 问题 | 位置 | 影响范围 |
|----|--------|------|------|---------|
| **A-1** | CRITICAL | Hash Chain 完全断裂: 7,372 条记录 prev_hash=GENESIS | aggregated_live.jsonl | 全部版本 |
| **A-2** | CRITICAL | 全文件重写无原子性: 进程崩溃则数据损坏 | ledger_writer.py:208-234 | 全部写入 |
| **A-3** | HIGH | prediction_index.json 与 ledger 计数不匹配: 9个版本不一致 | storage/ | v5/v7/v12/v21/v23/v24 |
| **A-4** | HIGH | 脏数据修复逻辑破坏不可变性: verified 记录仍可被修改 | ledger_writer.py:288-306 | 全部已验证记录 |
| **A-5** | HIGH | JSON解析错误静默回退: hash chain 断裂无警告 | ledger_writer.py:82-93 | 全部读取 |
| **A-6** | HIGH | v30/v35 metadata.json 缺失: registry 查找失败 | predictors/active/v30/, v35/ | v30/v35 |
| **A-7** | HIGH | version_book/index.json 与 predictors/index.json 不同步 | version_book/index.json | v27/v28/v29/v30 |
| **A-8** | HIGH | 7,372 条记录 status 字段缺失 | aggregated_live.jsonl | v12 等旧版本 |
| **A-9** | HIGH | index_generator.py 全文件重写: 非原子读写 | index_generator.py:126 | version_book/index.json |

### B. 并发与竞争条件问题（CRITICAL）

| ID | 严重度 | 问题 | 位置 |
|----|--------|------|------|
| **B-1** | CRITICAL | **无任何锁机制**: 多进程同时写入导致 Hash Chain 断裂 | ledger_writer.py (全文) |
| **B-2** | CRITICAL | **两个 Cron 作业重叠**: 21:30 + 21:35/40 可能同时运行 | crontab |
| **B-3** | CRITICAL | **无进程互斥**: run_pipeline.py 可与 cron 并发运行 | scripts/run_pipeline.py |
| **B-4** | CRITICAL | **非原子写入**: temp→rename 模式未使用 | ledger_writer.py (全文) |
| **B-5** | HIGH | **Index 文件读写竞争**: prediction_index.json 无锁 | ledger_writer.py:239-245 |
| **B-6** | MEDIUM | **安全护盾仅对单进程有效**: 可被其他进程绕过 | storage/__init__.py |
| **B-7** | MEDIUM | **安全护盾可被绕过**: `builtins.open = original` | storage/__init__.py |

### C. 异常处理与静默失败（HIGH / MEDIUM）

| ID | 严重度 | 问题 | 位置 |
|----|--------|------|------|
| **C-1** | CRITICAL | **bare `except:`**: 吞掉所有异常包括 SystemExit | six_zodiac_predictor.py:146 |
| **C-2** | CRITICAL | **predictor 失败返回空结果**: 无法与合法空结果区分 | orchestrator.py:80-86 |
| **C-3** | HIGH | **API 无 retry**: 网络失败直接崩溃 | data_fetcher.py:35-40 |
| **C-4** | HIGH | **API 无 cache 回退**: fetch失败无缓存 fallback | data_fetcher.py:39-40 |
| **C-5** | HIGH | **验证循环无 per-record try/except**: 单条坏JSON崩溃整验证 | ledger_writer.py:281-286 |
| **C-6** | MEDIUM | **空 history 返回 None**: 导致下游空预测 | six_zodiac_predictor.py:61 |
| **C-7** | MEDIUM | **v30 返回 None**: 条件不满足时静默失败 | v30/predictor.py:148,154,191 |

### D. 架构与代码质量问题（MEDIUM / LOW）

| ID | 严重度 | 问题 | 位置 |
|----|--------|------|------|
| **D-1** | MEDIUM | **ZODIACS 常量重复定义12次**: 应抽取到 constants.py | 所有 predictor 文件 |
| **D-2** | MEDIUM | **v23/v24_interval_predictor.py 重复**: 与 active/ 下文件重复 | predictor/ |
| **D-3** | MEDIUM | **main.py 已废弃但仍可执行**: 可能导致双数据源 | predictor/main.py |
| **D-4** | MEDIUM | **硬编码路径**: `/mnt/c/Users/Admin` 跨平台失败 | ledger_writer.py:32 |
| **D-5** | LOW | **orphan 文件未清理**: liuhecai_v26_*.py (25+), ml_exp_v4.py | 根目录 |
| **D-6** | LOW | **策略配置漂移**: configs/strategy_config.json 仅含 v12 | configs/ |
| **D-7** | LOW | **TODO 分散**: 无法集中追踪 | 代码中 |

### E. 潜在数据漂移 / 统计偏差（HIGH）

| ID | 严重度 | 问题 | 位置 | 影响 |
|----|--------|------|------|------|------|
| **E-1** | HIGH | **v26/v27/v28 评估逻辑不匹配**: 存储时用liuhe，hit用pingte_yixiao算 | aggregated_live.jsonl | 1080条命中错误 |
| **E-2** | HIGH | **Dashboard 缓存 TTL=30s**: 统计计算可能被缓存 | dashboard_server.py:34 | 统计延迟 |
| **E-3** | HIGH | **compute_stats 缓存 key 仅有 len(results)**: 不同版本共享缓存 | dashboard_server.py:162 | 命中率错乱 |
| **E-4** | MEDIUM | **历史数据回填未维护 Hash Chain**: 导致 A-1 | aggregated_live.jsonl | 无法验证完整性 |
| **E-5** | MEDIUM | **backtest 数据混入 live 数据**: 时间线不一致 | aggregated_live.jsonl | 回测结果偏差 |

---

## 第三部分：根因树

```
污染源 (Root Causes)
│
├── 写入层
│   ├── ledger_writer.py:208-234
│   │   └─ 全文件重写 = 非原子 = 进程崩溃即损坏
│   │
│   ├── ledger_writer.py:288-306
│   │   └─ "脏数据修复" 逻辑
│   │       └─ 允许修改 status='verified' 的记录
│   │           ├─ 导致 v5 的 134 条 hit 被错误翻转
│   │           └─ 导致 v26/v27/v28 的 1080 条 hit 评估错误
│   │
│   └── ledger_writer.py:82-93
│       └─ JSON 解析错误时静默返回 GENESIS_HASH
│           └─ 破坏 Hash Chain 完整性
│
├── 缓存层
│   ├── dashboard_server.py:162
│   │   └─ 缓存 key = f"stats:{len(results)}"
│   │       └─ v23/v24 同 len(results) 共享缓存 → 50.52%/50.39% 混淆
│   │
│   └── data_fetcher.py
│       └─ API fetch 无 retry 无 cache fallback
│           └─ 网络抖动 → 数据缺失
│
├── 聚合层
│   └── aggregated_live.jsonl
│       ├─ v26/v27 存储时无 play_type
│       ├─ 评估时却用 pingte_yixiao 逻辑
│       │   └─ 1080 条记录 hit 值错误
│       │
│       └─ 历史数据回填未维护 Hash Chain
│           └─ 7,372 条 prev_hash = GENESIS
│
├── 并发层
│   ├── crontab
│   │   └─ 21:30 + 21:35 + 21:40 三个作业
│   │       └─ 无 flock / 互斥锁
│   │
│   ├── scripts/run_pipeline.py
│   │   └─ 无 PID 检查 / 重叠运行保护
│   │
│   └── storage/__init__.py
│       └─ 猴子补丁仅对单进程有效
│           └─ 其他进程可直接写入 ledger
│
└── 模型层
    ├── predictors/index.json vs version_book/index.json
    │   └─ 双索引不同步
    │       └─ v27/v28/v29 不在 version_book
    │
    ├── v30/v35/metadata.json 缺失
    │   └─ registry.get_play_type() 抛出 MetadataError
    │
    └── PredictorRegistry._predictors (class variable)
        └─ 多实例共享状态 → 线程不安全
```

---

## 第四部分：风险矩阵

| ID | 风险类型 | 严重度 | 可能性 | 影响 | 综合评分 |
|----|---------|--------|--------|------|---------|
| A-1 | 数据完整性 | CRITICAL | HIGH | 数据完全不可信 | ⬛⬛⬛⬛⬛ |
| A-2 | 稳定性 | CRITICAL | MEDIUM | 数据损坏 | ⬛⬛⬛⬛ |
| A-4 | 数据完整性 | HIGH | HIGH | 历史数据失真 | ⬛⬛⬛⬛ |
| B-1 | 并发安全 | CRITICAL | HIGH | Hash Chain 断裂 | ⬛⬛⬛⬛⬛ |
| B-2 | 并发安全 | CRITICAL | HIGH | 多进程冲突 | ⬛⬛⬛⬛⬛ |
| B-3 | 并发安全 | CRITICAL | MEDIUM | 数据竞争 | ⬛⬛⬛⬛ |
| C-1 | 异常处理 | CRITICAL | LOW | 异常被吞 | ⬛⬛⬛ |
| C-2 | 异常处理 | CRITICAL | MEDIUM | 结果不可区分 | ⬛⬛⬛⬛ |
| A-3 | 数据一致性 | HIGH | HIGH | 计数不匹配 | ⬛⬛⬛⬛ |
| A-6 | 架构 | HIGH | HIGH | v30/v35 不可用 | ⬛⬛⬛⬛ |
| E-1 | 数据偏差 | HIGH | HIGH | 1080条命中错误 | ⬛⬛⬛⬛ |
| B-5 | 并发安全 | HIGH | MEDIUM | 索引损坏 | ⬛⬛⬛ |
| C-3 | 异常处理 | HIGH | MEDIUM | 网络抖动→失败 | ⬛⬛⬛ |
| D-1 | 可维护性 | MEDIUM | HIGH | 代码重复 | ⬛⬛ |
| D-2 | 可维护性 | MEDIUM | MEDIUM | 文件重复 | ⬛⬛ |

---

## 第五部分：架构评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 模块边界 | 70/100 | ledger_writer 过耦合（读写+索引+哈希） |
| 状态管理 | 55/100 | class variable 单例 + 模块级缓存 + 全局 singleton |
| 可测试性 | 75/100 | 单元测试覆盖较好，但并发场景未测试 |
| 可维护性 | 60/100 | ZODIACS 重复12次，文件重复，多处硬编码 |
| 数据安全 | 45/100 | Hash Chain断裂，脏数据修复，无原子写入 |
| 扩展性 | 80/100 | 插件化 predictor 注册，策略可扩展 |
| 稳定性 | 50/100 | 无重试，无原子写入，无进程互斥 |
| **总分** | **61/100** | **低于及格线** |

---

## 第六部分：Repair Plan

> **在执行任何修复之前，请用户确认以下方案**

### RP-1: Hash Chain 重建 (A-1)
**方案**: 遍历 aggregated_live.jsonl，按 record 顺序重建 prev_hash 和 record_hash
**风险**: 低 - 仅重新计算，不改数据
**影响**: 恢复 Hash Chain 完整性验证能力
**执行**: 新增脚本 `scripts/rebuild_hash_chain.py`

### RP-2: 脏数据修复逻辑删除 (A-4)
**方案**: 删除 ledger_writer.py:288-306 的"脏数据修复"代码，改为只读
**风险**: 高 - 改变核心逻辑，旧记录修复会丢失
**替代方案**: 将脏数据修复改为仅报告，不修改数据
**优先级**: 待定（已有 v5 的 134 条被错误修复）

### RP-3: v26/v27/v28 hit 重算 (E-1)
**方案**: 使用 PredictorRegistry.evaluate() 重新计算 1080 条 v26/v27/v28 的 hit
**风险**: 中 - 需要重写存储数据
**优先级**: 高（影响 1080 条记录命中率）

### RP-4: 进程互斥保护 (B-1, B-2, B-3)
**方案**: 
1. scripts/run_pipeline.py 添加 PID 文件检查
2. Cron 作业合并为单一脚本 + flock
3. ledger_writer 添加 fcntl.flock()
**风险**: 中 - 改变并发逻辑
**优先级**: 高（防止数据竞争）

### RP-5: 原子写入 (A-2, B-4)
**方案**: ledger_writer 所有写入改用 temp file + atomic rename
**风险**: 中 - 实现复杂性
**优先级**: 高

### RP-6: metadata 补充 (A-6, A-7)
**方案**: 
1. 为 v30 创建 metadata.json
2. 清理空的 v35 目录
3. 同步 version_book/index.json
**风险**: 极低
**优先级**: 中

### RP-7: API 重试 + Cache 回退 (C-3, C-4)
**方案**: data_fetcher.py 添加 retry=3，失败时 fallback 到缓存
**风险**: 低
**优先级**: 中

### RP-8: 异常处理修复 (C-1, C-2, C-6, C-7)
**方案**: 
1. 替换 `six_zodiac_predictor.py:146` 的 bare except
2. orchestrator 返回结构增加 error 字段
3. v30 返回明确错误而非 None
**风险**: 低
**优先级**: 中

---

**报告结束**
**下次建议**: 优先修复 RP-1 → RP-4 → RP-5 → RP-3（按风险优先级）