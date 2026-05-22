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