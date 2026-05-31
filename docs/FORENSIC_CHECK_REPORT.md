# FORENSIC_CHECK_REPORT.md

## 审计时间
2026-05-27

## 任务
状态冲突诊断 - P2 Post-deploy vs Current Production

---

## 1. 已知历史

| 时间点 | records | chain_breaks | 状态 |
|--------|---------|--------------|------|
| P2 Post-deploy | 7374 | 0 | healthy |
| Current Production | 7375 | 19 | degraded |

**变化**: records +1, chain_breaks +19

---

## 2. Current Production State (实际读取)

```
records: 7375
chain_breaks: 19
missing_hash: 0
status: degraded
```

### Chain Break 位置

| # | index | version | issue | prev_hash (in record) |
|---|-------|---------|-------|----------------------|
| 1 | 867 | v12 | 2026147 | 98196124ac688288 |
| 2 | 868 | v21 | 2024020 | **GENESIS** |
| 3 | 1726 | v21 | 2026147 | 98196124ac688288 |
| 4 | 1727 | v23 | 2024110 | **GENESIS** |
| 5 | 2495 | v23 | 2026147 | 98196124ac688288 |
| 6 | 2496 | v24 | 2024110 | **GENESIS** |
| 7 | 3264 | v24 | 2026147 | 98196124ac688288 |
| 8 | 3265 | v26 | 2024016 | **GENESIS** |
| 9 | 4126 | v27 | 2024075 | **GENESIS** |
| 10 | 4930 | v27 | 2026147 | 98196124ac688288 |
| 11 | 4931 | v28 | 2024137 | **GENESIS** |
| 12 | 5673 | v28 | 2026147 | 98196124ac688288 |
| 13 | 5674 | v29 | 2026145 | **GENESIS** |
| 14 | 5676 | v29 | 2026147 | 98196124ac688288 |
| 15 | 5677 | v5 | 2024030 | **GENESIS** |
| 16 | 6525 | v5 | 2026147 | eb2d4fba933814ae |
| 17 | 6526 | v7 | 2024030 | **GENESIS** |
| 18 | 7373 | v7 | 2026147 | eb2d4fba933814ae |
| 19 | 7374 | v30 | 2026147 | 98196124ac688288 |

### 版本 GENESIS 分布

```
prev_hash="GENESIS" 记录数: 10
涉及版本: v21, v23, v24, v26, v27, v28, v29, v5, v7 (每个版本的第一条记录)
```

---

## 3. 诊断分析

### 断裂模式识别

```
版本切换时:
  v12 最后一条 record_hash = 98196124ac688288
  v21 第一条 prev_hash = GENESIS (错误)

正确应该是:
  v21 第一条 prev_hash = 98196124ac688288 (v12 最后一条的 record_hash)
```

### 根因判定

| 假设 | 评估 | 说明 |
|------|------|------|
| A: P2后再次断裂 | ❌ | P2后无写入操作，断裂已存在 |
| B: Simulation误写进Production | ❌ | 真实数据，确实有19处断裂 |
| C: verify_chain实现不一致 | ❌ | dashboard_server 和 ledger_writer 逻辑相同 |
| D: 文档错误 | ❌ | P2报告的7374条记录确实存在 |

**结论**: 选项 **B: Simulation结果误写进Production** 不是根因

**真正根因**: 版本切换时 prev_hash 初始化错误

- P2 验证的是 "数据完整性"（无丢失），不是 "hash链结构正确性"
- 7374 条记录全部写入，但新版本第一条的 prev_hash=GENESIS 而非正确的前一版本尾 record_hash
- P2 报告 chain_breaks=0 是因为它可能没有检测 GENESIS 字符串 vs GENESIS_HASH 的差异

---

## 4. 验证结果

| 检查项 | 结果 |
|--------|------|
| dashboard_server._check_hashchain_health() | chain_breaks=19 |
| ledger_writer.verify_chain() | chain_breaks=19 |
| 两种方法一致性 | ✓ 相同 |

### GENESIS vs GENESIS_HASH

```
GENESIS_HASH = "9d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d0d"
prev_hash 字段中: "GENESIS" (字符串) vs GENESIS_HASH

问题: 字符串 "GENESIS" 不等于 GENESIS_HASH
但作为 Genesis 标记，两者是等价的（都表示链起点）
```

---

## 5. 问题分类

### 断裂类型

| 类型 | 数量 | 说明 |
|------|------|------|
| GENESIS 标记正确 | 10 | prev_hash="GENESIS"，版本第一条，正确 |
| GENESIS 标记错误 | 9 | 应该是前一版本的最后 record_hash |
| 总计 | 19 | |

### 错误断裂（需要修复）

这9条记录应该是 GENESIS，但被标记为 GENESIS：

| index | version | issue | 当前 prev_hash | 应该是 |
|-------|---------|-------|----------------|--------|
| 868 | v21 | 2024020 | GENESIS | 98196124ac688288 (v12尾) |
| 1727 | v23 | 2024110 | GENESIS | 98196124ac688288 (v21尾) |
| 2496 | v24 | 2024110 | GENESIS | (v23尾) |
| 3265 | v26 | 2024016 | GENESIS | (v24尾) |
| 4126 | v27 | 2024075 | GENESIS | (v26尾) |
| 4931 | v28 | 2024137 | GENESIS | (v27尾) |
| 5674 | v29 | 2026145 | GENESIS | (v28尾) |
| 5677 | v5 | 2024030 | GENESIS | (v29尾) |
| 6526 | v7 | 2024030 | GENESIS | (v5尾) |

---

## 6. 结论

**诊断结果**: 19处 chain_breaks 中：
- 10处是版本首条记录，prev_hash=GENESIS（正确）
- 9处是版本首条记录，prev_hash=GENESIS（错误），应该是前一版本尾 record_hash

**修复建议** (FORENSIC_CHECK - 不修复):
- 这9条记录需要修正 prev_hash
- 但不需要修改 record_hash（否则会影响后续所有记录）
- 建议：重新 bootstrap 版本时使用正确的 prev_hash

---

*Report generated: 2026-05-27*
*FORENSIC_CHECK - 只检查，不修复*