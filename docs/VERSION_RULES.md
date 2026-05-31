# 澳门六合预测系统 - 版本管理与回测规范

> **版本：** 1.1
> **更新：** 2026-05-23
> **核心原则：** 回测只做一次初始化，用来"校准系统"；之后系统只运行，不回头重算。**所有统计必须来源于 ledger 单一真相，禁止任何二次计算路径或缓存统计结果作为最终数据。**

---

## 0. 数据完整性原则（最高优先级）

> **所有统计必须来源于 ledger 单一真相，禁止任何二次计算路径或缓存统计结果作为最终数据。**

### 0.1 Ledger 只存原始数据

Ledger 记录**只允许包含**：
```json
{
  "id": "2026141_v12",
  "issue": "2026141",
  "version": "v12",
  "prediction": ["龙", "马", "兔", "牛", "狗", "猴"],
  "actual": "鼠",
  "hit": false,
  "created_at": "2026-05-23T21:35:22",
  "source": "backtest"
}
```

**禁止存储**：预计算的统计字段（`streak`、`max_streak`、`hit_rate`、`total_hits` 等）。

### 0.2 唯一键约束

**唯一键 = `(issue, version)`**

同一 `(issue, version)` 禁止重复写入，重复直接 reject。

### 0.3 单一计算路径

```
ledger → compute_metrics() → UI
```

**禁止**：
- 预计算统计缓存作为最终结果
- 多路径统计（backtest_runner 一套、dashboard 一套、API 缓存一套）
- 从 index.json 或 version_book/*.json 读取"最终统计"

### 0.4 Hash 校验

每条记录包含 `hash` 字段，用于检测数据被篡改：

```python
def compute_record_hash(record):
    core = f"{record['issue']}|{record['version']}|{record['prediction']}|{record['actual']}"
    return sha256(core.encode()).hexdigest()[:16]
```

---

## 1. 版本账本结构

```
version_book/
  v9/backtest_ledger.jsonl    # source="backtest"
  v10/backtest_ledger.jsonl     # source="backtest"
  v11/backtest_ledger.jsonl     # source="backtest"
  v12/backtest_ledger.jsonl     # source="backtest"
  index.json                    # 版本索引

storage/
  prediction_ledger.jsonl       # source="live" (append-only)
  result_ledger.jsonl           # 开奖结果 (append-only)
```

---

## 2. 记录格式（统一）

```json
{
  "id": "2026141_v12",
  "issue": "2026141",
  "version": "v12",
  "model": "v12_zigzag",
  "prediction": ["龙", "马", "兔", "牛", "狗", "猴"],
  "actual": "鼠",
  "hit": false,
  "created_at": "2026-05-23T21:35:22",
  "source": "backtest"
}
```

| 字段 | 说明 |
|------|------|
| `id` | 唯一键 = `{issue}_{version}_{timestamp}` |
| `source` | `backtest`=回测账本, `live`=实盘账本 |

---

## 3. 回测规范（强制）

### 3.1 Walk-forward 回测

```
for i in range(lookback, len(standard)):
    history = standard[:i]          # 只有历史数据
    top6 = predict_top6(history)     # 生成预测
    actual = standard[i]["特码"]    # 实际开奖
```

**规则：**
- 每期预测只能使用当前期之前的数据
- 不允许全量数据训练后统一回测
- 不允许未来数据参与特征计算

### 3.2 参数冻结

回测开始前，参数必须固定：
```json
{
  "version": "v12",
  "strategy": "pattern_based",
  "params": {
    "lookback": 11,
    "pattern_weight": 1.45,
    "gap_weight": 0.098,
    "trend_weight": 0.267,
    "variance_weight": 0.177,
    "alt_mode": "trend"
  }
}
```

回测过程中**禁止修改**任何参数。

### 3.3 映射一致

训练/回测/实盘统一使用 `AnimalMapper.get(number, issue)`。

**禁止：**
- year_mapping.json
- 本地公式
- 动态替换映射

---

## 4. 版本生命周期

### 4.1 Bootstrap（初始化）

每个版本确定后，**执行一次** bootstrap 回测：

```
1. 用该版本参数对全历史数据做 walk-forward 回测
2. 逐期生成预测，写入 version_book/{version}/backtest_ledger.jsonl
3. 回测记录格式：source="backtest"
```

### 4.2 冻结（Frozen）

回测完成后：
- 参数不再变
- 回测结果不再重跑覆盖（除非修 bug 重建）
- 版本作为"已验证基线"

### 4.3 正常运行

```
prediction_ledger.jsonl  ← 只追加 live 数据
result_ledger.jsonl      ← 只追加开奖结果
```

**禁止：**
- 重新跑回测覆盖 ledger
- 修改历史记录
- 混用 backtest 和 live 数据

---

## 5. Dashboard 规则

### 5.1 查询接口

```
/api/records?source=backtest&version=v12    # 回测账本
/api/records?source=live&version=v12        # 实盘账本
/api/records?source=backtest                # 所有版本回测
/api/records?source=live                    # 所有版本实盘
```

### 5.2 显示逻辑

- v12 → 显示 backtest ledger（最近100期）
- live → 以后才会有数据
- **不混算、不重算**

### 5.3 统计来源

Dashboard 只从 ledger 读取，不实时计算：
```
Dashboard
    ↓
ledger (backtest 或 live)
    ↓
filter(source, version)
```

---

## 6. 关键原则

### 6.1 回测只做一次

> **回测只做一次初始化，用来"校准系统"；之后系统只运行，不回头重算。**

初始化完成后：
- 回测账本固化
- 禁止重新生成覆盖
- 系统进入正常运行模式

### 6.2 版本是数据字段

- 版本是预测记录的天生字段
- 唯一键 = `(issue, version)`
- **禁止通过时间戳推断版本**

### 6.3 账本不可变

| 账本 | 规则 |
|------|------|
| `prediction_ledger.jsonl` | append-only，禁止修改删除 |
| `version_book/*/backtest_ledger.jsonl` | 可重新生成覆盖 |

---

## 7. 新版本上线流程

```
1. 确定新版本参数（如 v13）
2. 运行 bootstrap 回测
3. 生成 version_book/v13/backtest_ledger.jsonl
4. 冻结 v13
5. v13 切换为 current
6. 系统正常运行（prediction_ledger 只追加 v13）
```

**禁止在正常运行后重新跑旧版本的回测。**