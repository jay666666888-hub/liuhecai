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