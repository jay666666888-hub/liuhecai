# CHAIN_MODEL_FORENSIC_REPORT.md

## 审计时间
2026-05-27

## 问题
逻辑冲突 - 两个报告对断裂数的描述不一致

---

## 1. 模型分析

### 模型A: 全局链
```
GENESIS → v5 → v7 → v12 → v21 → v23 → v24 → v26 → v27 → v28 → v29 → v30
```
规则: version[i].first.prev_hash == version[i-1].last.record_hash

### 模型B: 版本独立链
```
GENESIS → v5 (独立)
GENESIS → v7 (独立)
GENESIS → v12 (独立)
...
GENESIS → v30 (独立)
```
规则: 每个版本的 prev_hash 都应该是 GENESIS

---

## 2. 模型判定

### 证据

第一条记录 (v12, index=0):
```
prev_hash: "GENESIS"
record_hash: 4821c3acad574c9e
```

所有其他版本的 prev_hash:
```
v21: GENESIS
v23: GENESIS
v24: GENESIS
v26: GENESIS
v27: GENESIS
v28: GENESIS
v29: GENESIS
v5:  GENESIS
v7:  GENESIS
v30: 98196124ac688288 ← 错误！
```

### 判定

**chosen_model: B (版本独立链)**

**reason**: 
- v12 第一条 prev_hash=GENESIS（正确，第一版本）
- v21-v7 版本首 prev_hash=GENESIS（正确）
- 只有 v30 版本首 prev_hash 不是 GENESIS（错误）

---

## 3. 真实断裂数 (Model B)

### 版本首断裂 (GENESIS 错误)
| version | issue | current_prev_hash | expected |
|---------|-------|-------------------|----------|
| v30 | 2026147 | 98196124ac688288 | GENESIS |

**版本首断裂: 1 条**

### 版本内断裂
| version | 断裂位置 | 说明 |
|---------|---------|------|
| v12 | 9处 | 记录间 prev_hash 不匹配 |

**版本内断裂: 9 条**

### 总断裂数
```
chain_breaks_recalculated: 10
```

---

## 4. 与之前报告的差异原因

### 之前报告: 19 断裂

之前报告使用 dashboard_server 的 `_check_hashchain_health()` 函数，它按全局顺序检测：
- 它把版本间的连接也当作断裂（错误）
- 因为 v21.first.prev_hash=GENESIS ≠ v12.last.record_hash

### 更正后: 10 断裂

按 Model B（版本独立链）重新计算：
- 版本间连接不计入断裂（设计如此）
- 只计算版本首 GENESIS 错误和版本内断裂

---

## 5. 断裂详情

### 版本首断裂 (1条)
```
[v30] index=7374, issue=2026147
  current: 98196124ac688288
  expected: GENESIS
```

### 版本内断裂 (9条)
```
[v12] 9处断裂 (index 1-867范围内)
```

---

## 6. 结论

| 指标 | 值 |
|------|-----|
| chosen_model | B (版本独立链) |
| reason | 版本首 prev_hash 应全部为 GENESIS，只有 v30 错误 |
| chain_breaks_recalculated | 10 |
| - 版本首断裂 | 1 (v30) |
| - 版本内断裂 | 9 (v12) |

---

*Report generated: 2026-05-27*
*CHAIN_MODEL_FORENSIC - 只分析，不修复*