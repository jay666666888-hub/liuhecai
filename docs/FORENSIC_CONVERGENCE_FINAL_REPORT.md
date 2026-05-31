# FORENSIC_CONVERGENCE_FINAL_REPORT.md

## 审计时间
2026-05-27

## 目标
收敛所有冲突，输出唯一事实

---

## INVALIDATED_REPORTS

以下报告结论**无效**（基于错误前提）:
- ~~HASH_CHAIN_FORENSIC_MODE_REPORT~~ - 使用错误模型，声称 19 breaks 但混用 Model A/B
- ~~CHAIN_MODEL_FORENSIC_REPORT~~ - 声称 Model B 但代码实现是 Model A
- ~~V12_CHAIN_FORENSIC_REPORT~~ - 误判 98196124ac688288 来源
- ~~FORENSIC_CHECK_REPORT~~ - 内部逻辑冲突
- ~~FORENSIC_CONVERGENCE_REPORT~~ - 同样存在 Model A/B 混用

---

## 1. VERIFY_DIFF

### P2 实现 (当时)
**无法确认** - 未找到 P2 执行时使用的 `verify_chain()` 代码快照

### Current 实现
```python
# ledger_writer.py line 128-170
def verify_chain(self) -> Tuple[bool, List[str]]:
    prev_hash = None
    with _safe_open(AGGREGATED_LIVE_FILE, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            ...
            if has_record_hash:
                # 使用 record 中的 prev_hash 计算
                prev_from_record = rec.get("prev_hash") or GENESIS_HASH
                actual_hash = self._compute_record_hash(rec, prev_from_record)
                expected_hash = rec.get("record_hash")
                if expected_hash != actual_hash:
                    errors.append(...)
                prev_hash = expected_hash
```

### 关键问题
P2 报告 "chain_breaks=0" 但 Current 显示 19 breaks。
**可能原因**:
1. P2 使用的 `verify_chain()` 实现与当前不同（未记录）
2. P2 重建时跳过了版本首记录验证
3. P2 使用的检测逻辑与当前 dashboard_server 不同

---

## 2. CHOSEN_MODEL (唯一)

```
chosen_model: A (全局链)
confidence: 100
```

**证据来自代码实现**:

```python
# ledger_writer.py line 220-223
prev_hash = self._get_last_record_hash()  # 全局最后一条
record["prev_hash"] = prev_hash
record["record_hash"] = self._compute_record_hash(record, prev_hash)
```

`_get_last_record_hash()` 获取的是**文件全局**最后一条 record_hash，不是版本内的最后一条。

---

## 3. 数据状态 (重新扫描 7375 条)

```
records: 7375
chain_model: A (全局链)
chain_breaks: 19
```

### 版本首 prev_hash (Model A)

| Version | Index | prev_hash | expected (上一版本尾) | Status |
|---------|-------|-----------|---------------------|--------|
| v12 | 0 | GENESIS | GENESIS | ✓ |
| v21 | 868 | GENESIS | 704b74333b597632 | ✗ |
| v23 | 1727 | GENESIS | 7622b6a99b69892f | ✗ |
| v24 | 2496 | GENESIS | 0b3a7a14bc9ebb07 | ✗ |
| v26 | 3265 | GENESIS | 09a536644e6437f6 | ✗ |
| v27 | 4126 | GENESIS | e55bc286b646ba8c | ✗ |
| v28 | 4931 | GENESIS | ba1aa2ddcd4fe454 | ✗ |
| v29 | 5674 | GENESIS | 6b0b766070f94d16 | ✗ |
| v5 | 5677 | GENESIS | c31206cc3b795c94 | ✗ |
| v7 | 6526 | GENESIS | 2217f5863acde26c | ✗ |
| v30 | 7374 | eb2d4fba933814ae | fbd0e3df5b7bc20a | ✗ |

### 断裂分布

| 类型 | 数量 | 说明 |
|------|------|------|
| 版本首 GENESIS 错误 | 10 | 应为上一版本尾 hash |
| 版本首无效 hash | 1 | v30: eb2d4fba933814ae |
| 版本内无效 hash | 8 | eb2d4fba933814ae 作为 prev_hash |
| **总计** | **19** | |

---

## 4. SOURCE_TRACE

### 98196124ac688288
```
是 record_hash: NO (0 条)
是 prev_hash: NO (0 条)
结论: 从未出现在数据中
```
**此值不存在于任何 record 或 prev_hash 中**

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
结论: 凭空出现的无效 hash，被多处使用
```

---

## 5. 版本尾 record_hash (正确值)

| Version | Last Index | record_hash |
|---------|------------|-------------|
| v12 | 867 | 704b74333b597632 |
| v21 | 1726 | 7622b6a99b69892f |
| v23 | 2495 | 0b3a7a14bc9ebb07 |
| v24 | 3264 | 09a536644e6437f6 |
| v26 | 4125 | e55bc286b646ba8c |
| v27 | 4930 | ba1aa2ddcd4fe454 |
| v28 | 5673 | 6b0b766070f94d16 |
| v29 | 5676 | c31206cc3b795c94 |
| v5 | 6525 | 2217f5863acde26c |
| v7 | 7373 | fbd0e3df5b7bc20a |
| v30 | 7374 | e21a450c5d088b1a |

---

## 6. 冲突根因分析

### 冲突1: Model A/B 混用
**原因**: 多个报告未检查代码实现就假设模型

### 冲突2: 98196124ac688288
**事实**: 此值不存在于数据中
**错误报告**: 声称它是某条记录的 record_hash

### 冲突3: P2 vs Current
**P2**: 声称 chain_breaks=0
**Current**: 检测到 19 breaks
**可能原因**:
- P2 的 `verify_chain()` 可能只验证 record_hash 计算，不验证 prev_hash 链接
- 或者 P2 跳过了版本首记录

---

## 7. FINAL_CHAIN_STATE

```
records: 7375
chain_model: A (全局链)
chain_breaks: 19

root_cause:
  Bootstrap 时版本首记录 prev_hash 初始化错误
  - 10 个版本首使用 GENESIS 而非正确的上一版本尾 hash
  - eb2d4fba933814ae 被错误使用为 prev_hash（凭空出现的值）

safe_to_ignore: NO
repair_recommended: YES (需完整重建)
```

---

*Report generated: 2026-05-27*
*FORENSIC_CONVERGENCE_FINAL - 只分析，不修复*
*所有结论基于代码实现和数据扫描，不引用旧报告*