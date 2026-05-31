# 生肖映射架构约束

> **强制规则 - 违反直接拒绝合并**

## 核心原则

澳门六合生肖映射是**动态的**，按农历年变化。每年的映射都不同：
- 2024农历年(龙): 2024-02-10 ~ 2025-01-28
- 2025农历年(蛇): 2025-01-29 ~ 2026-02-16
- 2026农历年(马): 2026-02-17 ~ 2027-01-26

## 架构约束

### 规则 1：禁止新增固定生肖映射

**禁止**在任何位置创建硬编码生肖映射：

```python
# ✗ 禁止
ZODIAC_MAP = {
    '鼠': ['05', '17', ...],
    ...
}

# ✓ 必须
from predictor.constants import get_zodiac_map_for_date

zodiac_map = get_zodiac_map_for_date(draw_date)
```

### 规则 2：所有生肖计算必须调用 get_zodiac_map_for_date()

任何需要生肖映射的地方**必须**使用：

```python
from predictor.constants import get_zodiac_map_for_date

# 预测时
zodiac_map = get_zodiac_map_for_date(history[-1]['开奖时间'])

# 回测时（每条记录使用自己的日期）
for record in history:
    zodiac_map = get_zodiac_map_for_date(record['开奖时间'])
```

### 规则 3：回测必须使用历史开奖日期映射

回测数据跨越多个农历年时，**必须**按记录的实际日期选择对应年份的映射：

```python
# ✗ 禁止 - 全部使用当前年份映射
current_map = get_zodiac_map_for_date('2026-03-15')  # 2026年映射
for record in history:
    # 错误：2024年的数据也用2026年映射

# ✓ 正确 - 每条记录使用自己对应的年份映射
for record in history:
    zodiac_map = get_zodiac_map_for_date(record['开奖时间'])  # 自动选择正确年份
```

### 规则 4：预测必须使用当前开奖日期映射

实时预测时，使用最近一期历史记录的日期：

```python
latest_date = history[-1]['开奖时间']
zodiac_map = get_zodiac_map_for_date(latest_date)
```

### 规则 5：PR 出现硬编码生肖表直接拒绝

Code Review 时检测以下模式直接**拒绝合并**：

```bash
# 检测命令
grep -rn "'鼠':\|'牛':\|'虎':\|'兔':\|'龍':\|'蛇':\|'馬':\|'羊':\|'猴':\|'雞':\|'狗':\|'豬':" --include="*.py" predictor/ | grep -E "\[.*\]|\{.*"

# 允许的唯一位置
predictor/constants/zodiac_year_map.py  # 官方定义的年份映射表（唯一合法来源）
```

## 统一入口

```python
from predictor.constants import (
    get_zodiac_map_for_date,      # 获取日期对应的生肖映射
    get_lunar_year_for_date,      # 获取日期对应的农历年
    build_number_to_zodiac_map,   # 构建号码→生肖反向表
    get_zodiac_for_number,         # 直接查询号码对应生肖
    ZODIAC_MAPS,                   # 访问所有年份映射（只读）
    LUNAR_YEAR_BOUNDARIES,         # 农历年边界定义
)
```

## 验证

每次代码变更后运行验证：

```python
from predictor.constants import validate_zodiac_map_consistency

for year in [2024, 2025, 2026]:
    assert validate_zodiac_map_consistency(year), f"{year}年映射不一致"
```

## 历史映射表

| 农历年 | 生肖 | 起始日期 | 结束日期 |
|--------|------|----------|----------|
| 2024 | 龍 | 2024-02-10 | 2025-01-28 |
| 2025 | 蛇 | 2025-01-29 | 2026-02-16 |
| 2026 | 馬 | 2026-02-17 | 2027-01-26 |

---

**违反以上任何规则，PR 直接拒绝。**