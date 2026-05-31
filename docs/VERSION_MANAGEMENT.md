# 澳门六合预测系统 - 版本管理与数据规范 v2.0

> **版本：** 2.0
> **更新：** 2026-05-24
> **核心原则：**
> 1. Dashboard 只读 `storage/aggregated_live.jsonl`，不扫描版本目录
> 2. 所有统计必须实时从 ledger 计算，禁止手写 summary
> 3. predictor 只允许 `write_live_prediction()` 接口，禁止直接写文件

---

## 1. 目录结构

```
liuhecai/
├── storage/
│   ├── prediction_index.json    # 预测索引（自动生成）
│   ├── aggregated_live.jsonl    # 聚合层 - 所有版本实盘预测统一出口
│   ├── prediction_ledger.jsonl # (保留，用于兼容)
│   └── result_ledger.jsonl      # 开奖结果（append-only）
│
├── version_book/
│   ├── index.json               # 版本索引（自动生成，禁止手写）
│   ├── v12/
│   │   ├── live_ledger.jsonl     # 实盘账本
│   │   ├── backtest_ledger.jsonl# 回测账本
│   │   └── metadata.json        # 版本元数据（自动生成）
│   ├── v23/
│   │   ├── live_ledger.jsonl
│   │   ├── backtest_ledger.jsonl
│   │   └── metadata.json
│   └── v24/
│       ├── live_ledger.jsonl
│       ├── backtest_ledger.jsonl
│       └── metadata.json
│
├── predictor/
│   └── ledger_writer.py         # 写入接口（唯一合法写入途径）
│
└── scripts/
    ├── sync_result_to_data.py   # 数据同步脚本
    └── bootstrap_version.py     # 统一 Bootstrap 脚本
```

---

## 2. 写入流程

```
predict_cycle.py (cron)
    ↓ write_live_prediction(v24, data)
version_book/v24/live_ledger.jsonl
    ↓ (自动聚合)
storage/aggregated_live.jsonl
    ↓ (按需计算)
version_book/index.json (summary 字段)
```

**predictor 只能使用：**
```python
from predictor.ledger_writer import write_live_prediction, verify_prediction

write_live_prediction(
    version="v24",
    issue="2026144",
    prediction=["鼠", "牛", "虎", "兔", "龍", "蛇"],
    model="v24_interval_predictor",
    strategy="multi_strategy_vote"
)
```

**禁止：**
```python
# 禁止直接写入文件
open("storage/prediction_ledger.jsonl")

# 禁止直接读取文件
open("version_book/v24/live_ledger.jsonl")
```

---

## 3. Dashboard 规则

**只读：**
- `storage/aggregated_live.jsonl` — 实盘数据唯一来源
- `version_book/v{xx}/backtest_ledger.jsonl` — 回测数据
- `version_book/index.json` — 版本列表（summary 自动计算）

**禁止：**
- 扫描 `version_book/v{xx}/` 目录下的 live_ledger.jsonl
- 从 `storage/prediction_ledger.jsonl` 读取
- 手工读取 result_ledger.jsonl 做统计

---

## 4. index.json 规则

**禁止：**
```json
{
  "summary": {
    "live_predictions": 123
  }
}
```

**必须：**
```json
{
  "summary": [
    {
      "version": "v24",
      "live_predictions": 123,
      "live_hit_rate": 0.6056,
      "live_max_streak": 5
    }
  ]
}
```

**summary 必须从 ledger 实时计算：**
```python
def _compute_summary():
    # 遍历版本目录
    # 从 live_ledger.jsonl 计算 live_predictions, hit_rate, max_streak
    # 从 backtest_ledger.jsonl 计算 backtest_hit_rate
    return summary
```

---

## 5. 版本生命周期

### 5.1 上线流程

```
1. 确定新版本参数（如 v25）
2. 运行 scripts/bootstrap_version.py
   python3 scripts/bootstrap_version.py --version v25
3. Bootstrap 自动完成：
   - data_fetcher 同步数据
   - 创建版本目录 version_book/v25/
   - 初始化 live_ledger.jsonl
   - 初始化 backtest_ledger.jsonl (walk-forward)
   - 生成 metadata.json
   - 重建 index.json
   - 聚合到 storage/aggregated_live.jsonl
4. 系统正常运行
```

**禁止：**
```bash
python3 v25_bootstrap.py  # 禁止！
python3 scripts/custom_bootstrap_v25.py  # 禁止！
```

### 5.2 下线/停用流程

```
1. 从 index.json 的 versions 列表移除
2. 加入 retired 列表（原因）
3. 删除该版本的 pending predictions：
   - 读取 version_book/{version}/live_ledger.jsonl
   - 删除 status=pending 的记录
   - 已验证记录保留供历史统计
4. 更新 predict_cycle.py 的 ACTIVE_VERSIONS 移除该版本
```

---

## 6. 数据同步规则

**每次重建账本前必须执行：**
```bash
python3 scripts/sync_result_to_data.py
```

此脚本将 `storage/result_ledger.jsonl` 的开奖结果同步到 `liuhecai_data.json`。

**触发条件：**
- 重建任意版本账本
- 回测任意策略
- Bootstrap 新版本

---

## 7. Bootstrap 脚本用法

```bash
# 标准 Bootstrap
python3 scripts/bootstrap_version.py --version v25

# 重建模式（删除旧数据）
python3 scripts/bootstrap_version.py --version v25 --rebuild

# 跳过回测（只初始化 live ledger）
python3 scripts/bootstrap_version.py --version v25 --skip-backtest
```

---

## 8. predict_cycle.py 配置

```python
ACTIVE_VERSIONS = {
    "v12": {...},
    "v21": {...},
    "v23": {...},
    "v24": {...}
}
```

新增版本只需在 `ACTIVE_VERSIONS` 添加配置，无需修改写入逻辑。

---

## 9. 检查清单

| 检查项 | 状态 |
|--------|------|
| 版本目录有 metadata.json | |
| live_ledger.jsonl 存在 | |
| backtest_ledger.jsonl 存在 | |
| pending predictions 已清理（下线时） | |
| retired 列表已更新（下线时） | |
| Bootstrap 使用统一脚本 | |
| predict_cycle 使用 write_live_prediction | |
| Dashboard 只读 aggregated_live.jsonl | |
| index.json summary 实时计算 | |
| 同步脚本已执行（重建前） | |

---

## 10. 旧文件处理

**保留（兼容性）：**
- `storage/prediction_ledger.jsonl` — 旧实盘数据
- `version_book/v{xx}.json` — 已废弃，使用 metadata.json

**可删除（确认无数据后）：**
- 各版本目录下的旧账本文件
- 单独的 bootstrap 脚本（如 v23_bootstrap.py）