# HASH_SOURCE_FORENSIC_REPORT.md

## 审计时间
2026-05-27

## 目标
追踪 eb2d4fba933814ae 的真实来源

---

## 1. SOURCE_PATH

### 搜索范围
- `_get_last_record_hash()`
- `last_hash`
- `prev_hash`
- `hash_cache`
- `cached_hash`
- `bootstrap`
- `rebuild_hash`
- `write_prediction`
- `run_live_cycle`

### 代码证据

#### ledger_writer.py:97-114
```python
def _get_last_record_hash(self) -> str:
    """获取最后一条记录的 hash（用于链式写入）"""
    if not AGGREGATED_LIVE_FILE.exists():
        return GENESIS_HASH

    with _safe_open(AGGREGATED_LIVE_FILE, 'r', encoding='utf-8') as f:
        last_line = None
        for line in f:
            line = line.strip()
            if line:
                last_line = line
        if last_line:
            try:
                rec = json.loads(last_line)
                return rec.get("record_hash") or rec.get("hash") or GENESIS_HASH
            except json.JSONDecodeError:
                return GENESIS_HASH
    return GENESIS_HASH
```
| source_type | line | confidence |
|-------------|------|------------|
| code | 97-114 | 100% |

#### ledger_writer.py:220-223
```python
prev_hash = self._get_last_record_hash()
record["prev_hash"] = prev_hash
record["record_hash"] = self._compute_record_hash(record, prev_hash)
```
| source_type | line | confidence |
|-------------|------|------------|
| code | 220-223 | 100% |

#### ledger_writer.py:43
```python
GENESIS_HASH = "GENESIS"
```
| source_type | line | confidence |
|-------------|------|------------|
| constant | 43 | 100% |

### 搜索结果

| pattern | found | evidence |
|---------|-------|----------|
| eb2d4fba933814ae in code | NO | 代码中无此值 |
| eb2d4fba933814ae in data | YES | 8条记录 prev_hash |
| _get_last_record_hash source | YES | line 97-114 |
| GENESIS_HASH source | YES | line 43 |

---

## 2. TARGET_TRACE

### eb2d4fba933814ae

```
是 record_hash: NO (0 条)
是 prev_hash: YES (8 条)
```

| Index | Version | Issue | 位置 |
|-------|---------|-------|------|
| 867 | v12 | 2026147 | 版本最后一条 |
| 1726 | v21 | 2026147 | 版本最后一条 |
| 2495 | v23 | 2026147 | 版本最后一条 |
| 3264 | v24 | 2026147 | 版本最后一条 |
| 4930 | v27 | 2026147 | 版本最后一条 |
| 5673 | v28 | 2026147 | 版本最后一条 |
| 5676 | v29 | 2026147 | 版本最后一条 |
| 7374 | v30 | 2026147 | 版本第一条 |

### 特征分析

1. **所有 2026147 期**: 全部出现在 issue=2026147 的记录
2. **版本切换点**: 7个是版本最后一条，1个是版本第一条(v30)
3. **同一值**: 所有8条都使用相同的 prev_hash

### 问题

根据 `_get_last_record_hash()`:
- 正常情况返回文件最后一条的 `record_hash`
- 异常情况返回 `GENESIS_HASH`

`eb2d4fba933814ae` 不是 `GENESIS_HASH`，也不是任何 `record_hash`。

这意味着 `_get_last_record_hash()` 在某些情况下返回了一个**从未被记录过的 hash**。

---

## 3. 98196124ac688288 追踪

```
是 record_hash: NO (0 条)
是 prev_hash: NO (0 条)
```

**此值从未出现在数据中**

---

## 4. ROOT_CAUSE_FINAL

```
root_cause: unknown
```

### 代码分析

根据当前代码 (`ledger_writer.py line 97-114`):

```python
def _get_last_record_hash(self) -> str:
    if not AGGREGATED_LIVE_FILE.exists():
        return GENESIS_HASH

    with _safe_open(AGGREGATED_LIVE_FILE, 'r', encoding='utf-8') as f:
        last_line = None
        for line in f:
            line = line.strip()
            if line:
                last_line = line
        if last_line:
            try:
                rec = json.loads(last_line)
                return rec.get("record_hash") or rec.get("hash") or GENESIS_HASH
            except json.JSONDecodeError:
                return GENESIS_HASH
    return GENESIS_HASH
```

**此函数只可能返回**:
1. `GENESIS_HASH` ("GENESIS")
2. `rec.get("record_hash")` - 文件最后一条的 record_hash
3. `rec.get("hash")` - 旧格式的 hash
4. `GENESIS_HASH` - 任何异常情况

**eb2d4fba933814ae 不在以上任何一项中**

---

## 5. 假设

### 假设A: Bootstrap初始化错误
- **可能性**: 低
- **证据**: 无法在当前代码中找到产生此值的逻辑

### 假设B: 未初始化变量
- **可能性**: 中
- **证据**: 16位 hex 像是未初始化内存，但当前代码无此类路径

### 假设C: 缓存污染
- **可能性**: 低
- **证据**: 无缓存机制涉及 hash 计算

### 假设D: 旧重建逻辑残留
- **可能性**: 高
- **证据**: P2 报告 "chain_breaks=0" 但当前为 19，说明 P2 后的某次操作引入了问题

### 假设E: 其他
- **可能性**: 无法评估

---

## 6. 最终结论

```
root_cause: unknown

原因:
1. eb2d4fba933814ae 不在任何代码中作为常量或默认值出现
2. 当前代码的 _get_last_record_hash() 无法产生此值
3. 此值仅作为 prev_hash 出现在8条记录中，都是版本切换点
4. 可能来自已删除或修改过的历史代码

建议:
- 检查 P2 之后的 git 提交历史
- 查找是否有 hash rebuild 脚本被修改或删除
- 或者接受此值为历史遗留的未知错误
```

---

*Report generated: 2026-05-27*
*HASH_SOURCE_FORENSIC - 只分析，不修复*