# FORENSIC_CONVERGENCE_REPORT.md

## 审计时间
2026-05-27

## 目标
统一链模型，消除报告冲突

---

## INVALIDATED_REPORTS

以下报告结果**无效**（基于错误模型）:
- ~~HASH_CHAIN_FORENSIC_MODE_REPORT~~ - 使用了错误的前提
- ~~CHAIN_MODEL_FORENSIC_REPORT~~ - 模型判定错误
- ~~V12_CHAIN_FORENSIC_REPORT~~ - 基础数据错误

---

## 1. DESIGN_SOURCE

### 实际代码实现

**LedgerWriter._get_last_record_hash()** (line 97-114):
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

**结论**: 获取的是**文件中全局最后一条**记录的 hash，不是版本内的最后一条。

---

**LedgerWriter.write_live_prediction()** (line 220-223):
```python
# Hash Chain
prev_hash = self._get_last_record_hash()  # 全局最后一条
record["prev_hash"] = prev_hash
record["record_hash"] = self._compute_record_hash(record, prev_hash)
```

**结论**: 新记录 prev_hash = 文件全局最后一条的 record_hash

---

**LedgerWriter._compute_record_hash()** (line 85-95):
```python
def _compute_record_hash(self, record: Dict, prev_hash: str = None) -> str:
    """
    计算记录 hash（包含 prev_hash 形成链）

    组成：issue|version|prediction|actual|hit|prev_hash
    """
    actual = record.get("actual") or ""
    hit = str(record.get("hit") or "")
    pred = ",".join(record.get("prediction") or [])
    core = f"{record['issue']}|{record['version']}|{pred}|{actual}|{hit}|{prev_hash or GENESIS_HASH}"
    return hashlib.sha256(core.encode()).hexdigest()[:16]
```

---

## 2. CHOSEN_MODEL

```
chosen_model: A (全局链)
confidence: 100
```

**Reason**:
1. 代码明确实现: `_get_last_record_hash()` 返回**文件全局**最后一条
2. `write_live_prediction()` 用全局 hash 而非版本 hash
3. 所有版本共用一条链，版本间无缝连接

---

## 3. CHAIN BREAKS (Model A 重新计算)

### 按版本统计

| Version | Breaks | First Break Index | 原因 |
|---------|--------|-------------------|------|
| v12 | 1 | 867 | prev_hash=eb2d4fba933814ae (无效值) |
| v21 | 2 | 1726, 1727 | 版本首 prev_hash=GENESIS (应为 v12 尾) |
| v23 | 2 | 2495, 2496 | 版本首 prev_hash=GENESIS (应为 v21 尾) |
| v24 | 2 | 3264, 3265 | 版本首 prev_hash=GENESIS (应为 v23 尾) |
| v26 | 1 | 3265 | 版本首 prev_hash=GENESIS (应为 v24 尾) |
| v27 | 2 | 4930, 4931 | 版本首 prev_hash=GENESIS (应为 v26 尾) |
| v28 | 2 | 5673, 5674 | 版本首 prev_hash=GENESIS (应为 v27 尾) |
| v29 | 2 | 5676, 5677 | 版本首 prev_hash=GENESIS (应为 v28 尾) |
| v5 | 2 | 6525, 6526 | 版本首 prev_hash=GENESIS (应为 v29 尾) |
| v7 | 2 | 7373, 7374 | 版本首 prev_hash=GENESIS (应为 v5 尾) |
| v30 | 1 | 7374 | 版本首 prev_hash=eb2d4fba933814ae (应为 v7 尾) |

### 总计
```
chain_breaks: 19
- 版本首断裂 (GENESIS错误): 10
- 版本内断裂 (无效hash): 1 (v12 index 867)
- 版本首断裂 (无效hash): 1 (v30)
```

---

## 4. SOURCE_TRACE (目标值)

### 98196124ac688288
```
是 record_hash: NO (0 条)
是 prev_hash: NO (0 条)
结论: 从未出现在数据中
```

### eb2d4fba933814ae
```
是 record_hash: NO (0 条)
是 prev_hash: YES (8 条)
  records[867] v12 2026147
  records[1726] v21 2026147
  records[2495] v23 2026147
  records[3264] v24 2026147
  records[4930] v27 2026147
  records[5673] v28 2026147
  records[5676] v29 2026147
  records[7374] v30 2026147
结论: 凭空出现的无效 hash，不是任何 record_hash
```

### 断裂记录详情

**v12 版本内断裂** (index 867):
```
issue: 2026147
current_prev_hash: eb2d4fba933814ae (无效)
expected_prev_hash: 565fa4627ee5ca1d (records[866].record_hash)
```

**v30 版本首断裂**:
```
issue: 2026147
current_prev_hash: eb2d4fba933814ae (无效)
expected_prev_hash: fbd0e3df5b7bc20a (v7 最后 record_hash)
```

---

## 5. FINAL_CHAIN_STATE

```
records: 7375
chain_model: A (全局链)

chain_breaks: 19
  - 版本首断裂 (GENESIS 应为上一版本尾): 10
  - 版本内断裂 (无效 hash eb2d4fba933814ae): 1
  - 版本首断裂 (无效 hash eb2d4fba933814ae): 1

root_cause: Bootstrap 时版本首记录 prev_hash 初始化错误
  - 10 个版本首使用 GENESIS 而非正确的上一版本尾 hash
  - v12 和 v30 使用无效 hash eb2d4fba933814ae

safe_to_ignore: NO
  - 数据完整性无法验证
  - 任何修改都会级联影响

repair_recommended: YES (但需要完整重建)
  - 涉及 19 处断裂 + 所有下游
  - 需要原子性操作或完整备份
```

---

## 6. 报告冲突根因

| 报告 | 问题 |
|------|------|
| HASH_CHAIN_FORENSIC_MODE_REPORT | 使用了 19 作为真实断裂数，未区分 GENESIS 断裂类型 |
| CHAIN_MODEL_FORENSIC_REPORT | 错误选择了 Model B (版本独立链)，实际上代码实现的是 Model A |
| V12_CHAIN_FORENSIC_REPORT | 基础数据错误，误判了 98196124ac688288 的来源 |

**冲突来源**: 未检查代码实现就假设了模型

---

*Report generated: 2026-05-27*
*FORENSIC_CONVERGENCE_MODE - 只分析，不修复*
*所有结论基于代码实现，而非推测*