#!/usr/bin/env python3
"""
AB测试数据加载器
"""

import json
import os
from typing import List, Dict


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STRATEGIES_FILE = os.path.join(BASE_DIR, "liuhecai_66_strategies.json")


def load_strategy_names() -> List[str]:
    """加载所有策略名称"""
    with open(STRATEGIES_FILE) as f:
        data = json.load(f)

    return data.get("metadata", {}).get("策略", [])


def load_strategy_results() -> List[Dict]:
    """加载所有策略的回测结果"""
    with open(STRATEGIES_FILE) as f:
        data = json.load(f)

    return data.get("results", [])


def get_strategy_hit_series(strategy_name: str, results: List[Dict]) -> List[int]:
    """获取某个策略的命中序列"""
    hit_key = f"命中_{strategy_name}"
    return [r.get(hit_key, 0) for r in results]


def get_strategy_predictions(strategy_name: str, results: List[Dict]) -> List[str]:
    """获取某个策略的预测序列"""
    pred_key = f"预测_{strategy_name}"
    return [r.get(pred_key, "") for r in results]


def load_all_strategies() -> Dict[str, Dict]:
    """加载所有策略的完整数据"""
    strategy_names = load_strategy_names()
    results = load_strategy_results()

    all_data = {}
    for name in strategy_names:
        all_data[name] = {
            "hits": get_strategy_hit_series(name, results),
            "predictions": get_strategy_predictions(name, results),
            "periods": [r["期号"] for r in results],
            "actuals": [r["实际"] for r in results],
        }

    return all_data


if __name__ == "__main__":
    names = load_strategy_names()
    print(f"加载了 {len(names)} 个策略")
    print(f"前5个: {names[:5]}")
