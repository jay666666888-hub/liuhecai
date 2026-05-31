# 澳门六合预测系统 - 项目结构规范 v3.0

> **版本：** 3.0
> **更新：** 2026-05-24
> **核心原则：** 分层清晰，禁止跨层调用

---

## 1. 目录结构

```
liuhecai/
├── predictor/           # 预测器（唯一运行入口）
│   ├── base_predictor.py      # 基类接口
│   ├── v23_interval_predictor.py
│   ├── v24_interval_predictor.py
│   ├── ledger_writer.py     # 写入接口（唯一合法）
│   └── dashboard_server.py   # Web服务
│
├── features/           # 特征计算（信号源，非预测器）
│   └── sunday_effect.py
│
├── tools/              # 工具脚本
│   └── backfill.py
│
├── research/           # 实验性代码（研究用，不能上生产）
│   ├── multi_strategy_optimizer.py
│   ├── ensemble_optimizer.py
│   ├── dual_optimizer.py
│   ├── meta_learner.py
│   ├── brute_force_search.py
│   └── wuxing_predictor.py
│
├── archive/            # 归档
│   ├── retired_versions/  # 退役版本（只读，供分析）
│   │   ├── v5/, v7/, v9-v14/, v17/, v19/, v20/, v21/, v22/
│   │   └── (保留: metadata.json, backtest_ledger.jsonl)
│   └── *.py            # 旧预测器归档
│
├── storage/
│   ├── prediction_index.json    # 预测索引
│   ├── aggregated_live.jsonl    # 聚合层（所有版本实盘）
│   └── result_ledger.jsonl      # 开奖结果
│
├── version_book/       # 版本账本
│   ├── index.json             # 版本索引
│   └── v23/                   # 活跃版本
│       ├── live_ledger.jsonl
│       ├── backtest_ledger.jsonl
│       └── metadata.json
│   └── v24/
│       ├── live_ledger.jsonl
│       ├── backtest_ledger.jsonl
│       └── metadata.json
│
└── scripts/
    ├── sync_result_to_data.py   # 数据同步
    └── bootstrap_version.py     # 统一Bootstrap
```

---

## 2. 层级规则

| 层级 | 目录 | 规则 |
|------|------|------|
| 1. 运行层 | predictor/ | 唯一运行入口，包含预测器和dashboard |
| 2. 特征层 | features/ | 信号源计算，非预测器 |
| 3. 工具层 | tools/ | 数据处理工具 |
| 4. 研究层 | research/ | 实验代码，禁止上生产 |
| 5. 归档层 | archive/ | 只读，供分析回归测试 |

**禁止：**
- research/ 代码进入 predictor/
- features/ 代码直接写 storage/
- predictor/ 跨层调用 archive/

---

## 3. 活跃版本规则

**当前活跃：**
- v23 — 专注2026年策略
- v24 — 多策略投票

**所有其他版本：**
- 退役版本 → archive/retired_versions/
- 实验版本 → archive/ + research/

---

## 4. 版本账本规则

### index.json 格式
```json
{
  "active": ["v23", "v24"],
  "retired": [{"version": "v12", "reason": "..."}],
  "experimental": []
}
```

### metadata.json 格式
```json
{
  "id": "v24",
  "status": "active",
  "created_at": "2026-05-24T20:44:44",
  "predictor": "v24_interval_predictor",
  "data_source": "data_fetcher",
  "strategy_type": "multi_strategy_vote",
  "params": {...},
  "notes": "..."
}
```

---

## 5. 写入规则

**唯一合法写入途径：**
```python
from predictor.ledger_writer import write_live_prediction
write_live_prediction(version="v24", issue="2026145", prediction=["鼠", "牛", ...])
```

**禁止：**
- 直接写 `storage/prediction_ledger.jsonl`
- 直接写 `version_book/v24/live_ledger.jsonl`
- 跨版本目录扫描写入

---

## 6. Dashboard 规则

**只读：**
- `storage/aggregated_live.jsonl` — 实盘唯一来源
- `version_book/v{xx}/backtest_ledger.jsonl` — 回测数据
- `version_book/index.json` — 版本列表

**禁止：**
- 扫描版本目录下的 live_ledger.jsonl
- 手工读取 result_ledger.jsonl 做统计
- 缓存统计结果

---

## 7. Bootstrap 规则

**必须使用统一脚本：**
```bash
python3 scripts/bootstrap_version.py --version v25
```

**禁止：**
- `python v23_bootstrap.py`
- `python scripts/custom_bootstrap_v24.py`

---

## 8. 退役版本处理

退役版本移至 `archive/retired_versions/`，保留：
- metadata.json
- backtest_ledger.jsonl

删除：
- live_ledger.jsonl（含 pending 预测）
- 临时文件、缓存

---

## 9. 检查清单

| 检查项 | 状态 |
|--------|------|
| predictor/ 只有运行代码 | |
| features/ 是特征非预测器 | |
| research/ 不在 predictor/ | |
| 写入只用 ledger_writer.py | |
| Dashboard 只读 aggregated_live.jsonl | |
| Bootstrap 用统一脚本 | |
| 退役版本在 archive/retired_versions/ | |