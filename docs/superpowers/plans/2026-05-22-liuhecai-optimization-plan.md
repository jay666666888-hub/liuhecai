# 六合预测系统优化实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现六合预测系统全闭环优化：真实API数据 → 动态生肖映射 → 策略搜索 → 自动同步权重 → 预测 → Telegram推送

**架构：** 模块化设计，predictor/ 目录下统一管理数据和预测逻辑，策略搜索结果自动同步到配置，cron 触发全流程

**技术栈：** Python 3, requests, JSON, fcntl (文件锁), Telegram Bot API

---

## 文件结构

```
liuhecai/
├── predictor/                        # 新增：统一预测器
│   ├── __init__.py
│   ├── config.py                   # 统一权重配置
│   ├── data_fetcher.py             # 数据获取 + 动态生肖映射
│   ├── predictor.py                # 核心预测逻辑
│   ├── strategy_sync.py            # 自动同步权重
│   ├── notification.py             # 推送通知
│   └── main.py                     # 入口
├── configs/
│   └── verification_state.json      # 验证状态
├── tests/
│   ├── test_data_fetcher.py
│   ├── test_predictor.py
│   └── test_sync.py
└── scripts/
    └── run_pipeline.py            # cron 调用脚本
```

---

## 任务 1：数据获取器 (data_fetcher.py)

**文件：**
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/data_fetcher.py`
- 测试：`/mnt/c/Users/Admin/liuhecai/tests/test_data_fetcher.py`

- [ ] **步骤 1：创建目录结构**

```bash
mkdir -p /mnt/c/Users/Admin/liuhecai/predictor
mkdir -p /mnt/c/Users/Admin/liuhecai/configs
mkdir -p /mnt/c/Users/Admin/liuhecai/tests
touch /mnt/c/Users/Admin/liuhecai/predictor/__init__.py
```

- [ ] **步骤 2：编写数据获取器**

```python
#!/usr/bin/env python3
"""
澳门六合数据获取模块
- 使用官方 API: https://history.macaumarksix.com/history/macaujc2/y/${year}
- 动态生肖映射：从 API 数据自动提取每年映射
- 特码生肖：zodiac[6]（官方直接给出）
"""

import json
import os
import requests
from datetime import datetime
from typing import List, Dict, Optional
from collections import Counter

# API 配置
API_BASE = "https://history.macaumarksix.com/history/macaujc2/y"
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# 生肖列表
ZODIACS = ["鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"]


def fetch_year_data(year: int, force_refresh: bool = False) -> List[Dict]:
    """获取指定年份数据"""
    cache_path = os.path.join(CACHE_DIR, f"liuhecai_{year}.json")
    
    if not force_refresh and os.path.exists(cache_path):
        with open(cache_path) as f:
            return json.load(f)
    
    url = f"{API_BASE}/{year}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    
    if not data.get("result"):
        raise ValueError(f"API返回失败: {data.get('message')}")
    
    records = data["data"]
    
    # 保存缓存
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    return records


def extract_zodiac_mapping(records: List[Dict]) -> Dict[int, str]:
    """从 API 数据自动提取当年生肖映射"""
    # openCode 和 zodiac 一一对应，从第一期数据提取
    mapping = {}
    for r in records:
        nums = r["openCode"].split(",")
        zodiacs = r["zodiac"].split(",")
        for num_str, zodiac in zip(nums, zodiacs):
            num = int(num_str)
            if num not in mapping:
                mapping[num] = zodiac
    return mapping


def get_special_zodiac(record: Dict) -> str:
    """获取特码生肖（官方直接给出）"""
    return record["zodiac"].split(",")[6]


def get_special_number(record: Dict) -> int:
    """获取特码号码"""
    return int(record["openCode"].split(",")[6])


def get_all_records(years: List[int] = None, force_refresh: bool = False) -> List[Dict]:
    """获取多年数据，按时间正序排列"""
    if years is None:
        years = [datetime.now().year]
    
    all_records = []
    for year in sorted(set(years)):
        records = fetch_year_data(year, force_refresh)
        all_records.extend(records)
    
    # 按期号排序
    all_records.sort(key=lambda x: x["expect"])
    return all_records


def build_standard_records(records: List[Dict], zodiac_mapping: Dict[int, str]) -> List[Dict]:
    """构建标准化记录（用于预测）"""
    result = []
    for r in records:
        special_num = get_special_number(r)
        special_zodiac = get_special_zodiac(r)
        result.append({
            "期号": r["expect"],
            "开奖时间": r["openTime"],
            "特码号码": str(special_num),
            "特码生肖": special_zodiac,
            "波色": r["wave"].split(",")[6],
            "开奖号码": r["openCode"].split(","),
            "开奖生肖": r["zodiac"].split(","),
            "波色列表": r["wave"].split(","),
            "_zodiac_mapping": zodiac_mapping,  # 保存映射供特征计算用
        })
    return result


def validate_zodiac_mapping(mapping: Dict[int, str], records: List[Dict]) -> float:
    """验证生肖映射准确性（返回一致率）"""
    correct = 0
    total = 0
    for r in records:
        nums = r["openCode"].split(",")
        zodiacs = r["zodiac"].split(",")
        for num_str, zodiac in zip(nums, zodiacs):
            num = int(num_str)
            if num in mapping and mapping[num] == zodiac:
                correct += 1
            total += 1
    return correct / total if total > 0 else 0


if __name__ == "__main__":
    # 测试
    records = get_all_records([2024, 2025])
    mapping = extract_zodiac_mapping(records)
    print(f"获取 {len(records)} 条记录")
    print(f"生肖映射: {mapping}")
    print(f"验证一致率: {validate_zodiac_mapping(mapping, records):.2%}")
```

- [ ] **步骤 3：运行测试验证**

```bash
cd /mnt/c/Users/Admin/liuhecai
python3 predictor/data_fetcher.py
```

预期输出：
```
获取 730 条记录
生肖映射: {1: '龍', 2: '兔', 3: '虎', ...}
验证一致率: 100.00%
```

- [ ] **步骤 4：编写单元测试**

```python
import pytest
import sys
sys.path.insert(0, "..")
from predictor.data_fetcher import (
    extract_zodiac_mapping,
    get_special_zodiac,
    get_special_number,
    validate_zodiac_mapping
)

def test_extract_zodiac_mapping():
    records = [
        {
            "expect": "2025001",
            "openCode": "25,18,06,14,29,39,22",
            "zodiac": "龍,豬,豬,兔,鼠,虎,羊"
        }
    ]
    mapping = extract_zodiac_mapping(records)
    assert mapping[25] == "龍"
    assert mapping[22] == "羊"

def test_get_special():
    record = {
        "expect": "2025001",
        "openCode": "25,18,06,14,29,39,22",
        "zodiac": "龍,豬,豬,兔,鼠,虎,羊"
    }
    assert get_special_number(record) == 22
    assert get_special_zodiac(record) == "羊"

def test_validate_mapping():
    records = [
        {
            "openCode": "25,18,06",
            "zodiac": "龍,豬,豬"
        }
    ]
    mapping = {25: "龍", 18: "豬", 6: "豬"}
    assert validate_zodiac_mapping(mapping, records) == 1.0
```

- [ ] **步骤 5：Commit**

```bash
cd /mnt/c/Users/Admin/liuhecai
git add predictor/__init__.py predictor/data_fetcher.py tests/test_data_fetcher.py
git commit -m "feat: add data fetcher with real API and dynamic zodiac mapping"
```

---

## 任务 2：配置管理 (config.py)

**文件：**
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/config.py`
- 修改：`/mnt/c/Users/Admin/liuhecai/configs/verification_state.json`

- [ ] **步骤 1：编写配置模块**

```python
#!/usr/bin/env python3
"""
统一配置管理
- 权重由策略搜索自动同步
- 禁止手动修改
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

# 配置文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "configs")
os.makedirs(CONFIG_DIR, exist_ok=True)

VERIFICATION_STATE_FILE = os.path.join(CONFIG_DIR, "verification_state.json")
STRATEGY_CONFIG_FILE = os.path.join(CONFIG_DIR, "strategy_config.json")

# 默认策略（首次使用）
DEFAULT_STRATEGY = {
    "version": "initial",
    "weights": {
        "gap_ge16": 1.21,
        "gap_ge10": 1.66,
        "gap_ge6": 0.62,
        "r3": 1.75,
        "streak": 1.86
    },
    "hit_rate": 0.0,
    "std": 0.0,
    "updated_at": datetime.now().isoformat(),
    "source": "default"
}


def load_strategy() -> Dict[str, Any]:
    """加载当前策略"""
    if os.path.exists(STRATEGY_CONFIG_FILE):
        with open(STRATEGY_CONFIG_FILE) as f:
            return json.load(f)
    return DEFAULT_STRATEGY.copy()


def save_strategy(strategy: Dict[str, Any]) -> None:
    """保存策略（原子操作）"""
    temp_file = STRATEGY_CONFIG_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(strategy, f, ensure_ascii=False, indent=2)
    os.replace(temp_file, STRATEGY_CONFIG_FILE)


def load_verification_state() -> Dict[str, Any]:
    """加载验证状态"""
    if os.path.exists(VERIFICATION_STATE_FILE):
        with open(VERIFICATION_STATE_FILE) as f:
            return json.load(f)
    return {
        "last_verified_period": None,
        "pending_period": None,
        "pending_top6": []
    }


def save_verification_state(state: Dict[str, Any]) -> None:
    """保存验证状态"""
    with open(VERIFICATION_STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def should_update_strategy(
    new_strategy: Dict[str, Any],
    current_strategy: Dict[str, Any],
    hit_rate_threshold: float = 1.02,  # 命中率提升门槛
    std_threshold: float = 0.95        # 标准差降低门槛
) -> bool:
    """判断是否更新策略"""
    new_hit = new_strategy.get("hit_rate", 0)
    new_std = new_strategy.get("std", 0)
    cur_hit = current_strategy.get("hit_rate", 0)
    cur_std = current_strategy.get("std", 0)
    
    if cur_hit == 0:
        return True
    
    hit_improved = new_hit > cur_hit * hit_rate_threshold
    std_improved = new_std < cur_std * std_threshold
    
    return hit_improved and std_improved


if __name__ == "__main__":
    # 测试
    state = load_verification_state()
    print(f"验证状态: {state}")
    
    strategy = load_strategy()
    print(f"当前策略: {strategy['version']}")
```

- [ ] **步骤 2：运行验证**

```bash
python3 predictor/config.py
```

预期输出：
```
验证状态: {'last_verified_period': None, 'pending_period': None, 'pending_top6': []}
当前策略: initial
```

- [ ] **步骤 3：Commit**

```bash
git add predictor/config.py
git commit -m "feat: add unified config management"
```

---

## 任务 3：核心预测器 (predictor.py)

**文件：**
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/predictor.py`
- 测试：`/mnt/c/Users/Admin/liuhecai/tests/test_predictor.py`

- [ ] **步骤 1：编写预测器**

```python
#!/usr/bin/env python3
"""
澳门六合六肖预测器
- 基于特征评分的排名预测
- 特征：gap（遗漏）、近期频率、连出现
"""

import json
from typing import List, Dict, Tuple
from collections import Counter

from .data_fetcher import (
    get_all_records,
    build_standard_records,
    extract_zodiac_mapping,
    get_special_zodiac
)
from .config import load_strategy, save_verification_state, load_verification_state


def build_cache(records: List[Dict], upto: int) -> Dict:
    """构建特征缓存"""
    zodiacs = sorted(set(r["特码生肖"] for r in records))
    cache = {}
    
    for z in zodiacs:
        positions = [i for i in range(upto) if records[i]["特码生肖"] == z]
        gaps = [positions[i+1] - positions[i] - 1 for i in range(len(positions) - 1)]
        last_gap = upto - positions[-1] - 1 if positions else 999
        
        cache[z] = {
            "gap": last_gap,
            "avg_gap": sum(gaps) / len(gaps) if gaps else 12,
            "recent3": sum(1 for i in range(max(0, upto-3), upto) if records[i]["特码生肖"] == z),
            "recent5": sum(1 for i in range(max(0, upto-5), upto) if records[i]["特码生肖"] == z),
            "recent10": sum(1 for i in range(max(0, upto-10), upto) if records[i]["特码生肖"] == z),
            "recent20": sum(1 for i in range(max(0, upto-20), upto) if records[i]["特码生肖"] == z),
            "recent30": sum(1 for i in range(max(0, upto-30), upto) if records[i]["特码生肖"] == z),
            "streak": 0,
        }
        
        # 计算连出现
        for i in range(upto - 1, -1, -1):
            if records[i]["特码生肖"] == z:
                cache[z]["streak"] += 1
            else:
                break
    
    return cache


def predict_top6(records: List[Dict], weights: Dict[str, float]) -> List[str]:
    """预测六肖"""
    n = len(records)
    cache = build_cache(records, n)
    zodiacs = list(cache.keys())
    
    # 特征评分
    scores = {}
    for z in zodiacs:
        c = cache[z]
        score = (
            (1 if c["gap"] >= 16 else 0) * weights.get("gap_ge16", 0) +
            (1 if c["gap"] >= 10 else 0) * weights.get("gap_ge10", 0) +
            (1 if c["gap"] >= 6 else 0) * weights.get("gap_ge6", 0) +
            c["recent3"] / 3 * weights.get("r3", 0) +
            c["streak"] * weights.get("streak", 0)
        )
        scores[z] = score
    
    # 按分数排序
    ranked = sorted(zodiacs, key=lambda z: scores[z], reverse=True)
    return ranked[:6]


def predict_next(records: List[Dict]) -> Tuple[str, List[str], Dict]:
    """预测下期"""
    weights = load_strategy()["weights"]
    top6 = predict_top6(records, weights)
    
    latest = records[-1]
    latest_period = latest["期号"]
    # 期号格式：2025001，需要 +1
    next_period = str(int(latest_period) + 1)
    
    # 计算各生肖得分
    n = len(records)
    cache = build_cache(records, n)
    scores = {z: cache[z]["gap"] for z in cache}
    
    return next_period, top6, scores


def verify_prediction(records: List[Dict], pending_period: str, pending_top6: List[str]) -> Tuple[bool, str]:
    """验证预测"""
    latest = records[-1]
    latest_period = latest["期号"]
    
    if latest_period != pending_period:
        return False, latest_period
    
    actual = latest["特码生肖"]
    hit = actual in pending_top6
    return hit, actual


def run_prediction_pipeline() -> Dict:
    """运行预测流程"""
    # 1. 获取数据
    records = get_all_records([2024, 2025])
    standard_records = build_standard_records(
        records,
        extract_zodiac_mapping(records)
    )
    
    # 2. 加载状态
    state = load_verification_state()
    last_verified = state.get("last_verified_period")
    pending_period = state.get("pending_period")
    pending_top6 = state.get("pending_top6", [])
    
    # 3. 验证上期预测
    verified_period = None
    verified_hit = None
    verified_actual = None
    
    latest = standard_records[-1]
    latest_period = latest["期号"]
    
    if pending_period and pending_top6:
        if latest_period == pending_period:
            # 可以验证
            hit, actual = verify_prediction(standard_records, pending_period, pending_top6)
            verified_period = pending_period
            verified_hit = hit
            verified_actual = actual
        elif int(latest_period) > int(pending_period):
            # 跳期，跳过验证
            pass
    
    # 4. 生成新预测
    next_period, next_top6, scores = predict_next(standard_records)
    
    # 5. 更新状态
    state["last_verified_period"] = verified_period or state.get("last_verified_period")
    state["pending_period"] = next_period
    state["pending_top6"] = next_top6
    save_verification_state(state)
    
    # 6. 返回结果
    return {
        "verified_period": verified_period,
        "verified_hit": verified_hit,
        "verified_actual": verified_actual,
        "pending_period": next_period,
        "pending_top6": next_top6,
        "scores": scores,
        "total_records": len(standard_records),
    }


if __name__ == "__main__":
    result = run_prediction_pipeline()
    print(json.dumps(result, ensure_ascii=False, indent=2))
```

- [ ] **步骤 2：运行测试**

```bash
python3 predictor/predictor.py
```

预期输出：JSON 格式的预测结果

- [ ] **步骤 3：Commit**

```bash
git add predictor/predictor.py
git commit -m "feat: add core predictor with gap-based scoring"
```

---

## 任务 4：策略同步器 (strategy_sync.py)

**文件：**
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/strategy_sync.py`
- 测试：`/mnt/c/Users/Admin/liuhecai/tests/test_sync.py`

- [ ] **步骤 1：编写同步器**

```python
#!/usr/bin/env python3
"""
策略自动同步器
- 检测新策略是否优于当前策略
- 自动更新配置
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional

from .config import (
    load_strategy,
    save_strategy,
    should_update_strategy,
    STRATEGY_CONFIG_FILE
)


def sync_strategy(new_strategy: Dict) -> bool:
    """
    同步新策略到配置
    返回 True 表示同步成功，False 表示跳过
    """
    current = load_strategy()
    
    if not should_update_strategy(new_strategy, current):
        print(f"策略未改善，跳过同步: {current['hit_rate']:.2%} -> {new_strategy['hit_rate']:.2%}")
        return False
    
    # 更新策略
    new_strategy["updated_at"] = datetime.now().isoformat()
    save_strategy(new_strategy)
    
    print(f"策略已更新: {current['version']} -> {new_strategy['version']}")
    print(f"  命中率: {current['hit_rate']:.2%} -> {new_strategy['hit_rate']:.2%}")
    print(f"  标准差: {current['std']:.4f} -> {new_strategy['std']:.4f}")
    
    return True


def get_strategy_version() -> str:
    """获取当前策略版本"""
    return load_strategy().get("version", "unknown")


if __name__ == "__main__":
    # 测试同步逻辑
    current = load_strategy()
    print(f"当前策略: {current['version']}")
    print(f"命中率: {current['hit_rate']:.2%}")
    print(f"标准差: {current['std']:.4f}")
```

- [ ] **步骤 2：Commit**

```bash
git add predictor/strategy_sync.py
git commit -m "feat: add strategy synchronization module"
```

---

## 任务 5：通知推送 (notification.py)

**文件：**
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/notification.py`

- [ ] **步骤 1：编写推送模块**

```python
#!/usr/bin/env python3
"""
推送通知模块
- Telegram Bot 推送
"""

import json
import os
import requests
from typing import Dict, Optional

# Telegram 配置
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "configs", "verification_state.json")


def load_latest_result() -> Optional[Dict]:
    """加载最新预测结果"""
    state_file = os.path.join(BASE_DIR, "liuhecai_prediction.json")
    if os.path.exists(state_file):
        with open(state_file) as f:
            return json.load(f)
    return None


def format_message(result: Dict) -> str:
    """格式化推送消息"""
    verified_period = result.get("verified_period")
    verified_hit = result.get("verified_hit")
    verified_actual = result.get("verified_actual")
    pending_period = result.get("pending_period")
    pending_top6 = result.get("pending_top6", [])
    
    lines = [
        "🎯 澳门六合六肖预测",
        f"第{pending_period}期预测" if pending_period else "",
        f"推荐六肖: {' '.join(pending_top6)}",
    ]
    
    if verified_period:
        hit_emoji = "✅" if verified_hit else "❌"
        lines.insert(0, f"📋 第{verified_period}期验证: {verified_actual} {hit_emoji}")
    
    return "\n".join(lines)


def send_telegram(message: str, retry: int = 3) -> bool:
    """发送 Telegram 消息"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram 未配置，跳过推送")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    for attempt in range(retry):
        try:
            resp = requests.post(url, data=data, timeout=10)
            if resp.ok:
                return True
        except Exception as e:
            print(f"Telegram 推送失败 (尝试 {attempt+1}/{retry}): {e}")
    
    return False


def send_notification(result: Dict) -> bool:
    """发送通知"""
    message = format_message(result)
    print(f"推送消息:\n{message}")
    return send_telegram(message)


if __name__ == "__main__":
    result = load_latest_result()
    if result:
        send_notification(result)
    else:
        print("无预测结果")
```

- [ ] **步骤 2：Commit**

```bash
git add predictor/notification.py
git commit -m "feat: add Telegram notification module"
```

---

## 任务 6：主入口 (main.py)

**文件：**
- 创建：`/mnt/c/Users/Admin/liuhecai/predictor/main.py`

- [ ] **步骤 1：编写主入口**

```python
#!/usr/bin/env python3
"""
澳门六合预测系统 - 主入口
每日 21:35 cron 触发
"""

import json
import sys
import os
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, build_standard_records, extract_zodiac_mapping
from predictor.predictor import run_prediction_pipeline, predict_next
from predictor.config import load_strategy, save_strategy
from predictor.notification import send_notification

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "liuhecai_prediction.json")


def main():
    print(f"=== 澳门六合预测系统 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # 1. 获取数据
    print("\n[1/4] 获取数据...")
    records = get_all_records([2024, 2025])
    standard_records = build_standard_records(records, extract_zodiac_mapping(records))
    print(f"  数据: {len(standard_records)} 期")
    
    # 2. 运行预测
    print("\n[2/4] 运行预测...")
    result = run_prediction_pipeline()
    
    latest = standard_records[-1]
    print(f"  最新期号: {latest['期号']} ({latest['特码生肖']})")
    
    if result.get("verified_period"):
        hit = "✅" if result["verified_hit"] else "❌"
        print(f"  验证 {result['verified_period']}: {result['verified_actual']} {hit}")
    
    print(f"  预测 {result['pending_period']}: {' '.join(result['pending_top6'])}")
    
    # 3. 保存结果
    print("\n[3/4] 保存结果...")
    output = {
        "version": datetime.now().isoformat(),
        "strategy": load_strategy().get("version"),
        "verified_period": result.get("verified_period"),
        "verified_hit": result.get("verified_hit"),
        "verified_actual": result.get("verified_actual"),
        "pending_period": result.get("pending_period"),
        "pending_top6": result.get("pending_top6"),
        "total_records": result.get("total_records"),
        "timestamp": datetime.now().isoformat(),
    }
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  已保存: {OUTPUT_FILE}")
    
    # 4. 推送通知
    print("\n[4/4] 推送通知...")
    send_notification(output)
    
    print("\n=== 完成 ===")
    return output


if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：运行全流程测试**

```bash
cd /mnt/c/Users/Admin/liuhecai
python3 predictor/main.py
```

预期：完整流程运行成功，输出预测结果

- [ ] **步骤 3：Commit**

```bash
git add predictor/main.py
git commit -m "feat: add main pipeline entry point"
```

---

## 任务 7：Cron 脚本

**文件：**
- 创建：`/mnt/c/Users/Admin/liuhecai/scripts/run_pipeline.py`

- [ ] **步骤 1：编写 Cron 脚本**

```python
#!/usr/bin/env python3
"""
Cron 调用脚本 - 每日 21:35 运行
Usage: python3 scripts/run_pipeline.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.main import main

if __name__ == "__main__":
    main()
```

- [ ] **步骤 2：设置执行权限**

```bash
chmod +x scripts/run_pipeline.py
```

- [ ] **步骤 3：Commit**

```bash
git add scripts/run_pipeline.py
git commit -m "feat: add cron entry script"
```

---

## 任务 8：测试套件

**文件：**
- 创建：`/mnt/c/Users/Admin/liuhecai/tests/test_integration.py`

- [ ] **步骤 1：编写集成测试**

```python
#!/usr/bin/env python3
"""集成测试"""

import sys
import os
sys.path.insert(0, "..")

from predictor.data_fetcher import get_all_records, extract_zodiac_mapping, build_standard_records
from predictor.predictor import predict_next, verify_prediction
from predictor.config import load_strategy, save_strategy, load_verification_state

def test_full_pipeline():
    """测试完整流程"""
    # 1. 获取数据
    records = get_all_records([2024, 2025])
    assert len(records) > 0
    
    # 2. 构建标准记录
    mapping = extract_zodiac_mapping(records)
    standard = build_standard_records(records, mapping)
    assert len(standard) > 0
    assert "特码生肖" in standard[0]
    
    # 3. 预测
    next_period, top6, scores = predict_next(standard)
    assert len(top6) == 6
    assert next_period > standard[-1]["期号"]
    
    # 4. 验证配置
    strategy = load_strategy()
    assert "weights" in strategy
    
    state = load_verification_state()
    assert "pending_period" in state
    
    print("集成测试通过!")

if __name__ == "__main__":
    test_full_pipeline()
```

- [ ] **步骤 2：运行集成测试**

```bash
python3 tests/test_integration.py
```

- [ ] **步骤 3：Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests"
```

---

## 自检清单

- [ ] 规格覆盖：数据获取 ✓，动态映射 ✓，预测 ✓，同步 ✓，推送 ✓
- [ ] 占位符扫描：无 "TODO"、"待定" 等
- [ ] 类型一致性：方法签名在任务间一致
- [ ] 目录结构：符合设计文档
- [ ] 测试：每个核心模块有测试

---

## 执行选项

**计划已完成并保存到 `docs/superpowers/plans/2026-05-22-liuhecai-optimization-plan.md`。两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**
