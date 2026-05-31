# METADATA_NORMALIZATION_REPORT.md

## 审计时间
2026-05-27

---

## 1. 发现的问题

### 问题记录

| # | version | issue | prediction | actual | 正确 play_type | 当前 play_types |
|---|---------|-------|------------|--------|----------------|-----------------|
| 1 | v27 | 2026145 | ['蛇'] | 虎 | pingte_yixiao | {None, 'liuhe'} |
| 2 | v28 | 2026145 | ['羊'] | 虎 | pingte_yixiao | {'liuhe', 'pingte_yixiao'} |

---

## 2. 详细记录

### Fix 1: v27_2026145

| record_id | before | after |
|-----------|--------|-------|
| 2026145_v27_backtest | play_type=None | play_type=pingte_yixiao |
| 2026145_v27_20260526_202313. | play_type=liuhe | play_type=pingte_yixiao |

**metadata.json 定义**: `play_type=pingte_yixiao`

### Fix 2: v28_2026145

| record_id | before | after |
|-----------|--------|-------|
| 2026145_v28_backtest | play_type=pingte_yixiao | play_type=pingte_yixiao |
| 2026145_v28_20260526_202313. | play_type=liuhe | play_type=pingte_yixiao |

**metadata.json 定义**: `play_type=pingte_yixiao`

---

## 3. 验证：每个 version 内 play_type 唯一性

### 修复后预期状态

| version | 正确 play_type | 当前记录中的 play_types | 唯一性 |
|---------|----------------|-------------------------|--------|
| v12 | liuhe | {liuhe} | ✓ |
| v21 | liuhe | {liuhe} | ✓ |
| v23 | liuhe | {liuhe} | ✓ |
| v24 | liuhe | {liuhe} | ✓ |
| v27 | pingte_yixiao | {None, 'liuhe'} → {pingte_yixiao} | 修复后 ✓ |
| v28 | pingte_yixiao | {'liuhe', 'pingte_yixiao'} → {pingte_yixiao} | 修复后 ✓ |
| v29 | pingte_yixiao | {pingte_yixiao} | ✓ |
| v30 | liuhe | {liuhe} | ✓ |
| v5 | liuhe | {liuhe} | ✓ |
| v7 | liuhe | {liuhe} | ✓ |

---

## 4. 执行规则

**禁止修改**:
- prediction
- actual
- hit
- source
- created_at
- record_hash (防篡改)

**允许修改**:
- play_type (元数据语义一致性)
- schema_version (如需要)
- predictor_class (如需要)

---

## 5. 版本元数据来源

```
predictor/predictors/active/{version}/metadata.json
```

| version | play_type | status |
|---------|-----------|--------|
| v12 | liuhe | active |
| v21 | liuhe | active |
| v23 | liuhe | active |
| v24 | liuhe | active |
| v27 | pingte_yixiao | active |
| v28 | pingte_yixiao | active |
| v29 | pingte_yixiao | active |
| v30 | liuhe | active |
| v5 | liuhe | active |
| v7 | liuhe | active |

---

## 6. 结论

**需要修复**: 2条记录 (v27 2条, v28 2条)

**修复方式**: 将 play_type 统一为 metadata.json 中定义的值

**风险**: 低 - 只修改元数据，不触碰实际预测/结果

---

*Report generated: 2026-05-27*