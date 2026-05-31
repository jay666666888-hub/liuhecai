# 澳门六合预测系统 - 数据完整性规范 v1.0

> **版本：** 1.0
> **更新：** 2026-05-23
> **核心原则：** 所有统计必须来源于 ledger 单一真相，禁止任何二次计算路径或缓存统计结果作为最终数据。

---

## 1. 数据层（第一层）

### 1.1 强制唯一约束

**唯一键：** `(issue, version)`

写入 ledger 时必须校验：同一个 `(issue, version)` 禁止重复写，重复直接 reject。

```python
def add_prediction(issue, version, ...):
    key = (issue, version)
    if key in existing_keys:
        raise DuplicateKeyError(f"{key} already exists")
```

### 1.2 防重复写入

Bootstrap + 运行 + debug 过程中，同一期可能被写多次。

**规则：**
```python
if exists_in_ledger(issue, version):
    skip  # 或 raise error
else:
    write_to_ledger(...)
```

### 1.3 Ledger Hash 校验

每条记录加 hash 字段，用于检测数据被修改/重写/手动编辑：

```json
{
  "id": "2026141_v12",
  "issue": "2026141",
  "version": "v12",
  "prediction": ["龙", "马", ...],
  "actual": "鼠",
  "hit": true,
  "hash": "sha256(核心字段)"
}
```

**作用：**
- 检测数据被篡改
- 检测意外重复写入
- 审计数据来源

**计算方式：**
```python
def compute_record_hash(record):
    core = f"{record['issue']}|{record['version']}|{record['prediction']}|{record['actual']}"
    return sha256(core.encode()).hexdigest()[:16]
```

---

## 2. 计算层（第二层）

### 2.1 禁止"多路径统计"

**当前最大风险：**
- A: backtest_runner 统计
- B: dashboard 重新计算
- C: API 缓存统计

**必须收敛成：**
```
ledger → compute_metrics() → UI
```

所有统计只有一条计算路径。

### 2.2 强制 Walk-forward 验证

每次统计必须满足：
- `feature(t)` 只允许用 `< t` 的数据

**Debug 模式检测：**
```python
assert max(feature_time) < current_issue
```

禁止任何未来数据泄漏。

---

## 3. 版本层（第三层）

### 3.1 Version Freeze Hash

每个版本必须有版本快照，包含：

```json
{
  "version": "v12",
  "strategy_type": "pattern_based",
  "params": {
    "lookback": 11,
    "pattern_weight": 1.45,
    ...
  },
  "strategy_hash": "xxx",
  "feature_hash": "xxx",
  "mapping_hash": "xxx",
  "frozen_at": "2026-05-23T..."
}
```

**作用：** 防止"同一个 v12，代码偷偷变了"

### 3.2 禁止跨版本混算

**强制规则：**
```
v12 ledger 只能用 v12 config
```

不能混合使用 v12 + v11 的 feature 或参数。

---

## 4. 系统层（第四层）

### 4.1 Cache 全禁（或必须版本化）

**危险操作：**
- API cache
- Memory cache
- Index cache

**规则：**
```
cache key = version + ledger_hash
```
或直接禁止缓存统计结果。

### 4.2 双写保护（防 crash / 半写）

Ledger 写入必须使用原子操作：

```python
def safe_write(record):
    tmp_path = f"{ledger_path}.tmp"
    write_to_jsonl(tmp_path, record)
    fsync(tmp_path)
    rename(tmp_path, ledger_path)  # 原子替换
```

**防止：**
- 写一半 crash
- 数据损坏
- 半写状态

---

## 5. 一句话原则

> **所有统计必须来源于 ledger 单一真相，禁止任何二次计算路径或缓存统计结果作为最终数据。**

---

## 6. 违反示例（反面教材）

### ❌ 错误：多路径统计

```
prediction_ledger.jsonl → backtest_runner 计算统计 → version_book/index.json
                                               ↓
dashboard_server.py ← compute_stats_from_version_book() ← index.json
```

### ❌ 错误：预计算缓存

```json
{
  "issue": "2026141",
  "streak": 5,       "max_streak": 8,    ← 禁止预计算
  "hit_rate": 0.55   ← 禁止预计算
}
```

### ❌ 错误：跨版本混算

```
v12 回测使用了 v11 的 lookback 参数
```

---

## 7. 正确示例

### ✅ 正确：单一计算路径

```
prediction_ledger.jsonl ← 只有预测记录
version_book/v12/backtest_ledger.jsonl ← 只有回测记录

Dashboard:
  load_ledger() → compute_stats() → render UI
  （每次实时计算，无缓存）
```

### ✅ 正确：原子写入

```python
with open('.tmp', 'w') as f:
    f.write(json.dumps(record))
os.fsync('.tmp')
os.rename('.tmp', 'ledger.jsonl')
```

---

## 8. 数据源优先级（必须严格遵守）

### 8.1 优先级定义

| 优先级 | 数据源 | 说明 |
|--------|--------|------|
| P0 | `storage/result_ledger.jsonl` | 开奖结果真相源，开奖后实时写入 |
| P1 | `predictor/.cache/liuhecai_*.json` | API 缓存，cron 定时刷新 |
| P2 | `liuhecai_data.json` | **手动备份文件，禁止作为统计来源** |

### 8.2 回测必须用 P0 + P1 同步后的数据

**当前错误做法（已踩坑）：**
```
predict_cycle.py 更新了 API cache
但 liuhecai_data.json 是手动维护的，没有同步
手动跑 v23_interval_predictor.py 重建账本 → 用的是旧数据 → 丢期
```

**正确做法：重建账本前必须执行数据同步脚本**

### 8.3 同步脚本（必须步骤）

每次重建账本前必须运行：

```python
#!/usr/bin/env python3
"""同步开奖结果到主数据文件（必须在重建账本前运行）"""
import json
from pathlib import Path

DATA_FILE = Path("/mnt/c/Users/Admin/liuhecai/liuhecai_data.json")
LEDGER_FILE = Path("/mnt/c/Users/Admin/liuhecai/storage/result_ledger.jsonl")

with open(DATA_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

issue_map = {item['期号']: item for item in data}

updates = 0
with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        record = json.loads(line.strip())
        issue = record.get('issue')
        actual = record.get('actual')
        if issue and actual and issue in issue_map:
            if issue_map[issue].get('特码生肖') != actual:
                issue_map[issue]['特码生肖'] = actual
                updates += 1

if updates > 0:
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"同步完成：更新 {updates} 条记录")
else:
    print("无需同步，数据已是最新")
```

### 8.4 同步触发条件

以下操作**必须**先运行同步脚本：
- 重建任意版本账本（backtest_ledger）
- 回测任意策略
- 生成新预测

### 8.5 统一数据文件路径

| 模块 | 当前错误路径 | 正确路径 |
|------|-------------|---------|
| v5_predict.py | `/home/admin1/liuhecai_data.json` | `/mnt/c/Users/Admin/liuhecai/liuhecai_data.json` |
| v7_predict.py | `/home/admin1/liuhecai_data.json` | `/mnt/c/Users/Admin/liuhecai/liuhecai_data.json` |
| v22/v23/v24 | `/mnt/c/Users/Admin/liuhecai/liuhecai_data.json` | 正确（保留）|

---

## 9. 检查清单

| 检查项 | 状态 |
|--------|------|
| (issue, version) 唯一键校验 | |
| 重复写入检测 | |
| Record hash 校验 | |
| 单一计算路径 | |
| Walk-forward 数据边界 | |
| Version freeze hash | |
| 禁止跨版本混算 | |
| Cache 版本化或禁用 | |
| 原子写入（tmp → fsync → rename） | |
| **同步脚本已执行** | |
| **统一数据文件路径** | |