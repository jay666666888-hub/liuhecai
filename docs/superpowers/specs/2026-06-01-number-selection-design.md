# 号码选择体系设计文档

**日期：** 2026-06-01
**版本：** 1.0
**状态：** 已批准

---

## 1. 目标

将 24码/12码/6码/30码 等号码预测整合成统一体系，类比六肖/平特的架构设计。

---

## 2. 核心设计

### 2.1 play_type 统一

| play_type | 说明 |
|-----------|------|
| `liuhe` | 六肖中特 |
| `pingte_yixiao` | 平特一肖 |
| `number_selection` | **号码选择（新增）** |

### 2.2 玩法区分

通过 metadata 的 `mode` + `top_k` 配置区分玩法：

```json
{
  "id": "v36",
  "play_type": "number_selection",
  "mode": "24ma",
  "top_k": 24
}
```

| mode | top_k | 说明 |
|------|-------|------|
| `24ma` | 24 | 24码中特 |
| `12ma` | 12 | 12码中特 |
| `6ma` | 6 | 6码中特 |
| `30ma` | 30 | 30码中特 |
| ... | ... | 可扩展 |

### 2.3 版本号管理

- **共享版本号池**：所有预测器（生肖 + 号码）统一编号
- v36, v37, v38... 用于号码选择体系
- 现有 v31 迁移到新体系，回测数据重置

### 2.4 验证方式

```python
class NumberSelectionValidator:
    name = "number_selection"

    def evaluate(self, prediction: list, actual_list: list, actual: str = None) -> bool:
        """
        prediction: 预测的号码列表 ["01", "05", "12", ...]
        actual: 开奖的特码号码 "45"
        """
        return actual in prediction
```

---

## 3. 目录结构

```
predictor/predictors/active/
├── v12/                    # 六肖
├── v21/                    # 六肖
├── v27/                    # 平特一肖
├── v31/                    # 号码选择（迁移）
├── v36/                    # 24码
├── v37/                    # 12码
├── v38/                    # 6码
├── v39/                    # 30码
└── ...
```

---

## 4. metadata.json 结构

```json
{
  "id": "v36",
  "status": "active",
  "play_type": "number_selection",
  "mode": "24ma",
  "top_k": 24,
  "params": {
    "lookback": 50,
    "strategy": "zodiac_partition_frequency"
  },
  "strategy_type": "zodiac_partition_frequency",
  "notes": "24码 - 生肖分区频率策略",
  "frozen": false,
  "created_at": "2026-06-01",
  "backtest": {
    "total": 0,
    "hits": 0,
    "hit_rate": 0.0
  },
  "live": {
    "total": 0,
    "hits": 0,
    "hit_rate": 0.0
  }
}
```

---

## 5. 组件适配

### 5.1 index_generator.py

```python
ALLOWED_PLAY_TYPES = {"liuhe", "pingte_yixiao", "number_selection"}

active_by_play_type = {"liuhe": [], "pingte_yixiao": [], "number_selection": []}
```

### 5.2 orchestrator.py

```python
if metadata['play_type'] == 'number_selection':
    top_k = metadata.get('top_k', 24)
    mode = metadata.get('mode', '24ma')
    result = predictor.predict(history, top_k=top_k)
    result.metadata['mode'] = mode
    result.metadata['play_type'] = 'number_selection'
```

### 5.3 ledger_writer.py

```python
{
    "id": "2026153_v36_20260601_221444",
    "issue": "2026153",
    "version": "v36",
    "mode": "24ma",
    "prediction": ["01", "05", "12", ...],
    "play_type": "number_selection",
    "actual": null,
    "hit": null,
    ...
}
```

### 5.4 dashboard_server.py

- 按 play_type 过滤展示
- number_selection 单独展示区域

---

## 6. v31 迁移

### 迁移前
```json
{
  "id": "v31",
  "play_type": "special_24ma",
  "mode": "24ma",
  "top_k": 24
}
```

### 迁移后
```json
{
  "id": "v31",
  "play_type": "number_selection",
  "mode": "24ma",
  "top_k": 24,
  "backtest": { "total": 0, "hits": 0, "hit_rate": 0.0 },
  "live": { "total": 0, "hits": 0, "hit_rate": 0.0 }
}
```

**迁移操作：**
1. 修改 v31/metadata.json 的 play_type
2. 重置 backtest/live 数据
3. 清理旧的 version_book/v31/ 账本数据

---

## 7. 实现计划

### Phase 1: 基础设施
1. 修改 `ALLOWED_PLAY_TYPES` 添加 `number_selection`
2. 修改 `index_generator.py` 适配新 play_type
3. 添加 `NumberSelectionValidator`

### Phase 2: v31 迁移
1. 更新 v31/metadata.json
2. 重置 v31 回测/实时数据
3. 清理旧账本

### Phase 3: 新版本开发
1. 创建 v36 (24码)
2. 创建 v37 (12码)
3. 创建 v38 (6码)
4. 创建 v39 (30码)

### Phase 4: 仪表盘适配
1. dashboard_server.py 按 play_type 分组展示
2. number_selection 独立区域

---

## 8. 约束

- 预测结果格式：`["01", "05", "12", ...]` 号码字符串列表
- 验证方式：号码精确匹配
- 禁止 predictor 自己 fetch data
- 禁止 predictor 自己写 ledger
