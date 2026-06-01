# 号码选择体系实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 创建统一的 `number_selection` play_type，整合 24码/12码/6码/30码 等号码预测玩法

**架构：** 新增 `number_selection` play_type，通过 `mode` + `top_k` 配置区分玩法，统一版本号池管理

**技术栈：** Python, JSON, 现有 predictor 框架

---

## 文件清单

### 新建
- `predictor/validators.py` - 新增 NumberSelectionValidator
- `predictor/predictors/active/v36/predictor.py` - 24码预测器
- `predictor/predictors/active/v36/metadata.json` - 24码元数据
- `predictor/predictors/active/v37/predictor.py` - 12码预测器
- `predictor/predictors/active/v37/metadata.json` - 12码元数据
- `predictor/predictors/active/v38/predictor.py` - 6码预测器
- `predictor/predictors/active/v38/metadata.json` - 6码元数据
- `predictor/predictors/active/v39/predictor.py` - 30码预测器
- `predictor/predictors/active/v39/metadata.json` - 30码元数据

### 修改
- `predictor/index_generator.py:4` - ALLOWED_PLAY_TYPES 添加 number_selection
- `predictor/index_generator.py:35` - active_by_play_type 添加 number_selection key
- `predictor/predictors/active/v31/metadata.json` - play_type 改为 number_selection

### 删除
- `version_book/v31/` - 清理旧账本数据（目录及内容）

---

## Phase 1：基础设施

### 任务 1：创建 NumberSelectionValidator

**文件：**
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/validators.py`

- [ ] **步骤 1：编写测试**

```python
# tests/test_validators.py
import pytest
import sys
sys.path.insert(0, '/mnt/c/Users/Admin/liuhecai')

from predictor.validators import NumberSelectionValidator

def test_number_selection_evaluate_hit():
    """特码在预测列表中 = 命中"""
    validator = NumberSelectionValidator()
    prediction = ["01", "05", "12", "23", "34", "45"]
    actual = "45"
    actual_list = ["雞", "猴", "兔", "羊", "豬", "馬", "狗"]

    result = validator.evaluate(prediction, actual_list, actual)
    assert result == True

def test_number_selection_evaluate_miss():
    """特码不在预测列表中 = 未中"""
    validator = NumberSelectionValidator()
    prediction = ["01", "05", "12", "23", "34", "45"]
    actual = "47"  # 不在列表中
    actual_list = ["龍", "龍", "虎", "牛", "豬", "虎", "鼠"]

    result = validator.evaluate(prediction, actual_list, actual)
    assert result == False

def test_number_selection_evaluate_empty():
    """空预测列表 = 未中"""
    validator = NumberSelectionValidator()
    prediction = []
    actual = "45"

    result = validator.evaluate(prediction, [], actual)
    assert result == False
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd /mnt/c/Users/Admin/liuhecai && python3 -m pytest tests/test_validators.py -v`
预期：FAIL，ModuleNotFoundError: No module named 'predictor.validators'

- [ ] **步骤 3：创建 validators.py**

```python
#!/usr/bin/env python3
"""
验证器模块

提供统一的预测验证接口
"""

from typing import List, Optional


class BaseValidator:
    """验证器基类"""

    name = "base"

    def evaluate(self, prediction: list, actual_list: list, actual: str = None) -> bool:
        raise NotImplementedError


class LiuheValidator(BaseValidator):
    """六肖验证器 - 验证特码生肖是否在预测的6个生肖中"""

    name = "liuhe"

    def evaluate(self, prediction: list, actual_list: list, actual: str = None) -> bool:
        """
        prediction: 预测的生肖列表
        actual: 特码生肖
        """
        if not prediction or not actual:
            return False
        return actual in prediction[:6]  # 只看前6个


class PingteYixiaoValidator(BaseValidator):
    """平特一肖验证器 - 验证特码生肖是否匹配"""

    name = "pingte_yixiao"

    def evaluate(self, prediction: list, actual_list: list, actual: str = None) -> bool:
        """
        prediction: 预测的生肖（单一生肖列表）
        actual: 特码生肖
        """
        if not prediction or not actual:
            return False
        return actual in prediction


class NumberSelectionValidator(BaseValidator):
    """号码选择验证器 - 验证特码号码是否在预测的号码列表中"""

    name = "number_selection"

    def evaluate(self, prediction: list, actual_list: list, actual: str = None) -> bool:
        """
        prediction: 预测的号码列表 ["01", "05", "12", ...]
        actual: 开奖的特码号码 "45"
        """
        if not prediction or not actual:
            return False
        return actual in prediction


# 验证器注册表
VALIDATORS = {
    "liuhe": LiuheValidator(),
    "pingte_yixiao": PingteYixiaoValidator(),
    "number_selection": NumberSelectionValidator(),
}


def get_validator(play_type: str) -> BaseValidator:
    """获取指定 play_type 的验证器"""
    validator = VALIDATORS.get(play_type)
    if validator is None:
        raise ValueError(f"Unknown play_type: {play_type}")
    return validator
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd /mnt/c/Users/Admin/liuhecai && python3 -m pytest tests/test_validators.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
cd /mnt/c/Users/Admin/liuhecai
git add predictor/validators.py tests/test_validators.py
git commit -m "feat: add NumberSelectionValidator for number_selection play_type

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2：修改 index_generator.py

**文件：**
- 修改：`/mnt/c/Users/Admin/liuhecai/predictor/index_generator.py:4`

- [ ] **步骤 1：确认现有代码**

运行：`head -10 predictor/index_generator.py`

- [ ] **步骤 2：修改 ALLOWED_PLAY_TYPES**

将：
```python
ALLOWED_PLAY_TYPES = {"liuhe", "pingte_yixiao", "special_24ma"}
```

改为：
```python
ALLOWED_PLAY_TYPES = {"liuhe", "pingte_yixiao", "number_selection"}
```

- [ ] **步骤 3：修改 active_by_play_type 初始化**

将：
```python
active_by_play_type = {"liuhe": [], "pingte_yixiao": [], "special_24ma": []}
```

改为：
```python
active_by_play_type = {"liuhe": [], "pingte_yixiao": [], "number_selection": []}
```

- [ ] **步骤 4：验证修改**

运行：`grep -n "ALLOWED_PLAY_TYPES\|active_by_play_type" predictor/index_generator.py`

- [ ] **步骤 5：Commit**

```bash
cd /mnt/c/Users/Admin/liuhecai
git add predictor/index_generator.py
git commit -m "refactor: rename special_24ma to number_selection in index_generator

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 2：v31 迁移

### 任务 3：迁移 v31 metadata

**文件：**
- 修改：`/mnt/c/Users/Admin/liuhecai/predictor/predictors/active/v31/metadata.json`

- [ ] **步骤 1：读取当前 metadata**

运行：`cat predictor/predictors/active/v31/metadata.json`

- [ ] **步骤 2：更新 metadata.json**

将：
```json
{
  "id": "v31",
  "status": "active",
  "created_at": "2026-06-01T01:30:00",
  "predictor": "v31_special_24ma_predictor",
  "data_source": "data_fetcher",
  "strategy_type": "zodiac_partition_frequency",
  "params": {
    "lookback": 50,
    "nums_per_zodiac": 2,
    "top_k": 24
  },
  "notes": "24码预测：生肖分区频率策略，按特码生肖分区统计频率",
  "frozen": false,
  "play_type": "special_24ma",
  "updated_at": "2026-06-01T02:20:00",
  "schema_version": "1.0.0"
}
```

改为：
```json
{
  "id": "v31",
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
  },
  "schema_version": "1.0.0"
}
```

- [ ] **步骤 3：清理旧账本**

运行：`rm -rf version_book/v31/`

- [ ] **步骤 4：验证**

运行：`cat predictor/predictors/active/v31/metadata.json`

- [ ] **步骤 5：Commit**

```bash
cd /mnt/c/Users/Admin/liuhecai
git add predictor/predictors/active/v31/metadata.json
git rm -r version_book/v31/
git commit -m "refactor: migrate v31 from special_24ma to number_selection play_type

- Change play_type to number_selection
- Add mode: 24ma, top_k: 24
- Reset backtest/live stats to zero
- Remove old ledger data

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 3：新版本开发

### 任务 4：创建 v36 (24码)

**文件：**
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/predictors/active/v36/predictor.py`
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/predictors/active/v36/metadata.json`

- [ ] **步骤 1：创建目录**

运行：`mkdir -p predictor/predictors/active/v36`

- [ ] **步骤 2：创建 metadata.json**

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
  },
  "schema_version": "1.0.0"
}
```

- [ ] **步骤 3：创建 predictor.py**

```python
#!/usr/bin/env python3
"""
澳门六合 - v36 24码预测器

策略：生肖分区综合得分
- 使用全局生肖年份映射系统
- 根据开奖时间自动选择对应农历年的生肖映射
- 计算每个号码的遗漏值 + 近17期出现频率
- 按生肖分区加权
- 综合取24个
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from predictor.base_predictor import BasePredictor, PredictionResult
from predictor.constants import get_zodiac_map_for_date, get_lunar_year_for_date

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


class V36NumberPredictor(BasePredictor):
    """v36 24码预测器 - 生肖分区综合得分策略"""

    def __init__(self, version: str = "v36"):
        super().__init__(version)
        self.params = {
            "lookback": 50,
            "top_k": 24
        }

    def predict(self, history, top_k=24):
        """
        生成24码预测 - 生肖分区综合得分策略

        Args:
            history: 历史记录列表
            top_k: 返回前k个预测（默认24个）

        Returns:
            PredictionResult 对象
        """
        if not history:
            return PredictionResult(
                prediction=[f"{i:02d}" for i in range(1, top_k + 1)],
                scores={},
                metadata={"error": "no history"}
            )

        n = len(history)
        lookback = min(self.params["lookback"], n)
        recent = history[-lookback:]

        # 获取生肖映射
        latest_record = history[-1]
        zodiac_map = get_zodiac_map_for_date(latest_record['开奖时间'])

        # 反向映射：生肖 -> 号码列表
        zodiac_to_nums = {z: [] for z in ZODIACS}
        for num in range(1, 50):
            num_str = f"{num:02d}"
            zodiac = zodiac_map.get(num_str)
            if zodiac:
                zodiac_to_nums[zodiac].append(num_str)

        # 计算每个生肖的权重（基于近期出现频率）
        zodiac_scores = {}
        for zodiac in ZODIACS:
            count = sum(1 for r in recent if r.get('特码生肖') == zodiac)
            zodiac_scores[zodiac] = count / lookback

        # 为每个号码打分
        num_scores = {}
        for num in range(1, 50):
            num_str = f"{num:02d}"
            zodiac = zodiac_map.get(num_str, '未知')

            # 遗漏值
            gap = 0
            for i in range(len(history) - 1, -1, -1):
                if any(n in history[i].get('开奖号码', []) for n in [num_str, num]):
                    break
                gap += 1

            # 频率得分
            freq_score = zodiac_scores.get(zodiac, 0)

            # 综合得分
            num_scores[num_str] = gap * 0.6 + freq_score * 100

        # 按生肖分区选取
        result = []
        nums_per_zodiac = max(1, top_k // 12)

        # 按得分排序每个生肖的号码
        for zodiac in ZODIACS:
            nums = zodiac_to_nums.get(zodiac, [])
            scored_nums = [(n, num_scores.get(n, 0)) for n in nums]
            scored_nums.sort(key=lambda x: x[1], reverse=True)
            result.extend([n for n, s in scored_nums[:nums_per_zodiac]])

        # 按得分排序取前 top_k
        all_scored = [(n, num_scores.get(n, 0)) for n in result]
        all_scored.sort(key=lambda x: x[1], reverse=True)
        final_prediction = [n for n, s in all_scored[:top_k]]

        # 如果不够24个，用得分最高的补齐
        if len(final_prediction) < top_k:
            all_nums = set(f"{i:02d}" for i in range(1, 50))
            remaining = list(all_nums - set(final_prediction))
            remaining.sort(key=lambda x: num_scores.get(x, 0), reverse=True)
            final_prediction.extend(remaining[:top_k - len(final_prediction)])

        return PredictionResult(
            prediction=final_prediction[:top_k],
            scores={n: num_scores.get(n, 0) for n in final_prediction[:top_k]},
            metadata={"mode": "24ma", "top_k": top_k}
        )
```

- [ ] **步骤 4：Commit**

```bash
cd /mnt/c/Users/Admin/liuhecai
mkdir -p predictor/predictors/active/v36
git add predictor/predictors/active/v36/
git commit -m "feat: add v36 24码 predictor

- New number_selection play_type
- Mode: 24ma, top_k: 24
- Strategy: zodiac partition frequency

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 5：创建 v37 (12码)

**文件：**
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/predictors/active/v37/predictor.py`
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/predictors/active/v37/metadata.json`

- [ ] **步骤 1：创建目录和文件**

```bash
mkdir -p predictor/predictors/active/v37
```

metadata.json:
```json
{
  "id": "v37",
  "status": "active",
  "play_type": "number_selection",
  "mode": "12ma",
  "top_k": 12,
  "params": {
    "lookback": 50,
    "strategy": "zodiac_partition_frequency"
  },
  "strategy_type": "zodiac_partition_frequency",
  "notes": "12码 - 生肖分区频率策略",
  "frozen": false,
  "created_at": "2026-06-01",
  "backtest": { "total": 0, "hits": 0, "hit_rate": 0.0 },
  "live": { "total": 0, "hits": 0, "hit_rate": 0.0 },
  "schema_version": "1.0.0"
}
```

predictor.py (复制 v36，修改 top_k=12):

```python
#!/usr/bin/env python3
"""
澳门六合 - v37 12码预测器

策略：生肖分区综合得分
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from predictor.base_predictor import BasePredictor, PredictionResult
from predictor.constants import get_zodiac_map_for_date

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


class V37NumberPredictor(BasePredictor):
    """v37 12码预测器"""

    def __init__(self, version: str = "v37"):
        super().__init__(version)
        self.params = {"lookback": 50, "top_k": 12}

    def predict(self, history, top_k=12):
        if not history:
            return PredictionResult(
                prediction=[f"{i:02d}" for i in range(1, top_k + 1)],
                scores={},
                metadata={"error": "no history"}
            )

        n = len(history)
        lookback = min(self.params["lookback"], n)
        recent = history[-lookback:]

        zodiac_map = get_zodiac_map_for_date(history[-1]['开奖时间'])

        zodiac_to_nums = {z: [] for z in ZODIACS}
        for num in range(1, 50):
            num_str = f"{num:02d}"
            zodiac = zodiac_map.get(num_str)
            if zodiac:
                zodiac_to_nums[zodiac].append(num_str)

        zodiac_scores = {}
        for zodiac in ZODIACS:
            count = sum(1 for r in recent if r.get('特码生肖') == zodiac)
            zodiac_scores[zodiac] = count / lookback

        num_scores = {}
        for num in range(1, 50):
            num_str = f"{num:02d}"
            zodiac = zodiac_map.get(num_str, '未知')

            gap = 0
            for i in range(len(history) - 1, -1, -1):
                if any(n in history[i].get('开奖号码', []) for n in [num_str, num]):
                    break
                gap += 1

            freq_score = zodiac_scores.get(zodiac, 0)
            num_scores[num_str] = gap * 0.6 + freq_score * 100

        result = []
        nums_per_zodiac = max(1, 12 // 12)

        for zodiac in ZODIACS:
            nums = zodiac_to_nums.get(zodiac, [])
            scored_nums = [(n, num_scores.get(n, 0)) for n in nums]
            scored_nums.sort(key=lambda x: x[1], reverse=True)
            result.extend([n for n, s in scored_nums[:nums_per_zodiac]])

        all_scored = [(n, num_scores.get(n, 0)) for n in result]
        all_scored.sort(key=lambda x: x[1], reverse=True)
        final_prediction = [n for n, s in all_scored[:12]]

        if len(final_prediction) < 12:
            all_nums = set(f"{i:02d}" for i in range(1, 50))
            remaining = list(all_nums - set(final_prediction))
            remaining.sort(key=lambda x: num_scores.get(x, 0), reverse=True)
            final_prediction.extend(remaining[:12 - len(final_prediction)])

        return PredictionResult(
            prediction=final_prediction[:12],
            scores={n: num_scores.get(n, 0) for n in final_prediction[:12]},
            metadata={"mode": "12ma", "top_k": 12}
        )
```

- [ ] **步骤 2：Commit**

```bash
cd /mnt/c/Users/Admin/liuhecai
git add predictor/predictors/active/v37/
git commit -m "feat: add v37 12码 predictor

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 6：创建 v38 (6码)

**文件：**
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/predictors/active/v38/predictor.py`
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/predictors/active/v38/metadata.json`

- [ ] **步骤 1：创建目录和文件**

```bash
mkdir -p predictor/predictors/active/v38
```

metadata.json:
```json
{
  "id": "v38",
  "status": "active",
  "play_type": "number_selection",
  "mode": "6ma",
  "top_k": 6,
  "params": {
    "lookback": 50,
    "strategy": "zodiac_partition_frequency"
  },
  "strategy_type": "zodiac_partition_frequency",
  "notes": "6码 - 生肖分区频率策略",
  "frozen": false,
  "created_at": "2026-06-01",
  "backtest": { "total": 0, "hits": 0, "hit_rate": 0.0 },
  "live": { "total": 0, "hits": 0, "hit_rate": 0.0 },
  "schema_version": "1.0.0"
}
```

predictor.py (修改 top_k=6):

- [ ] **步骤 2：Commit**

```bash
cd /mnt/c/Users/Admin/liuhecai
git add predictor/predictors/active/v38/
git commit -m "feat: add v38 6码 predictor

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 7：创建 v39 (30码)

**文件：**
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/predictors/active/v39/predictor.py`
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/predictors/active/v39/metadata.json`

- [ ] **步骤 1：创建目录和文件**

```bash
mkdir -p predictor/predictors/active/v39
```

metadata.json:
```json
{
  "id": "v39",
  "status": "active",
  "play_type": "number_selection",
  "mode": "30ma",
  "top_k": 30,
  "params": {
    "lookback": 50,
    "strategy": "zodiac_partition_frequency"
  },
  "strategy_type": "zodiac_partition_frequency",
  "notes": "30码 - 生肖分区频率策略",
  "frozen": false,
  "created_at": "2026-06-01",
  "backtest": { "total": 0, "hits": 0, "hit_rate": 0.0 },
  "live": { "total": 0, "hits": 0, "hit_rate": 0.0 },
  "schema_version": "1.0.0"
}
```

predictor.py (修改 top_k=30):

- [ ] **步骤 2：Commit**

```bash
cd /mnt/c/Users/Admin/liuhecai
git add predictor/predictors/active/v39/
git commit -m "feat: add v39 30码 predictor

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Phase 4：验证与测试

### 任务 8：验证 index 生成

**文件：**
- 验证：`version_book/index.json`

- [ ] **步骤 1：运行 index 生成**

运行：`cd /mnt/c/Users/Admin/liuhecai && python3 -c "from predictor.index_generator import write_index; write_index()"`

- [ ] **步骤 2：检查输出**

运行：`cat version_book/index.json | python3 -m json.tool | grep -A5 "number_selection"`

预期：
```json
"number_selection": [
  "v31",
  "v36",
  "v37",
  "v38",
  "v39"
]
```

- [ ] **步骤 3：Commit**

```bash
cd /mnt/c/Users/Admin/liuhecai
git add version_book/index.json
git commit -m "chore: update index.json with number_selection versions

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 9：运行预测周期测试

**文件：**
- 验证：`/mnt/c/Users/Admin/liuhecai/cron/predict_cycle.py`

- [ ] **步骤 1：运行预测**

运行：`cd /mnt/c/Users/Admin/liuhecai && python3 cron/predict_cycle.py 2>&1 | tail -50`

- [ ] **步骤 2：检查输出**

确认：
- v31, v36, v37, v38, v39 都加载成功
- 预测结果格式正确（号码列表）
- 没有报错

---

### 任务 10：整体验证

- [ ] **步骤 1：检查 git status**

运行：`cd /mnt/c/Users/Admin/liuhecai && git status`

预期：
```
nothing to commit, working tree clean
```

或只有未跟踪的必要文件。

- [ ] **步骤 2：推送**

```bash
git push origin main
```

---

## 自检清单

- [ ] 规格覆盖度：所有需求都有对应任务
- [ ] 无占位符：无 "TODO"、"待定"、"后续实现"
- [ ] 类型一致性：所有命名和方法签名一致
- [ ] 测试覆盖：validators 有测试
- [ ] 验证通过：predict_cycle 运行成功
