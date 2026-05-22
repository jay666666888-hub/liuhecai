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