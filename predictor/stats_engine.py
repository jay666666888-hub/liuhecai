#!/usr/bin/env python3
"""
Stats Engine - 实时计算引擎
不再依赖预生成文件，接受 build_standard_records() 输出作为输入
"""

import json
import os
import time
from datetime import datetime
from typing import List, Dict

# 导入常量
from predictor.constants import ZODIACS, get_wave, get_all_waves, NUMBER_TO_WAVE


def _get_cache(key: str, ttl: int = 300):
    """获取内存缓存"""
    now = time.time()
    if hasattr(_get_cache, '_cache'):
        data, timestamp = _get_cache._cache.get(key, (None, 0))
        if data and now - timestamp < ttl:
            return data
    return None


def _set_cache(key: str, data):
    """设置内存缓存"""
    if not hasattr(_get_cache, '_cache'):
        _get_cache._cache = {}
    _get_cache._cache[key] = (data, time.time())


# ============================================================
# 保留的函数：load_aggregated()（用于 compute_number_miss）
# ============================================================

BASE_DIR = "/mnt/c/Users/Admin/liuhecai"
STORAGE_DIR = os.path.join(BASE_DIR, "storage")


def load_aggregated() -> List[Dict]:
    """加载 aggregated_live.jsonl（保留用于 compute_number_miss）"""
    path = os.path.join(STORAGE_DIR, "aggregated_live.jsonl")
    records = []
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


# ============================================================
# compute_special_number_miss() - 特码号码遗漏
# ============================================================

def compute_special_number_miss(standard_records: List[Dict]) -> Dict:
    """
    计算特码号码遗漏统计

    Args:
        standard_records: build_standard_records() 的输出
        每条记录包含:
        - 期号: str
        - 特码号码: str (如 "06")

    Returns:
        遗漏统计，包含 1-49 各号码作为特码的遗漏期数
        包含:
        - current_miss: 当前遗漏
        - max_miss: 历史最高遗漏
        - all_miss: 历史所有遗漏期数列表

    算法：
    - 从后往前扫，记录每个号码最后出现位置
    - current_miss = 总期数 - 1 - last_position
    - max_miss = 历史所有遗漏段的最大值
    """
    # 按期号排序（升序）
    records = sorted(standard_records, key=lambda x: x['期号'])

    if not records:
        return _empty_response("special_number_miss", "number_stats")

    total_records = len(records)
    latest_issue = records[-1]['期号']

    # 从后往前扫，记录每个号码出现位置（用于计算遗漏）
    number_positions = {}  # number -> [出现位置列表]
    for idx in range(total_records):
        special = records[idx].get('特码号码')
        if special is not None:
            special_normalized = f"{int(special):02d}"
            if special_normalized not in number_positions:
                number_positions[special_normalized] = []
            number_positions[special_normalized].append(idx)

    # 计算每个号码的当前遗漏和历史最高遗漏
    data = {}
    for num in range(1, 50):
        num_str = f"{num:02d}"
        positions = number_positions.get(num_str, [])

        if positions:
            # 当前遗漏 = 最后出现位置之后有多少期
            last_idx = positions[-1]
            current_miss = total_records - 1 - last_idx

            # 历史最高遗漏 = 相邻出现位置之间的最大间隔
            # 但第一个位置之前的间隔是 (第一个位置 + 1)，因为之前没出现过
            all_miss_intervals = []

            # 第一个遗漏：从记录开始到第一次出现
            first_start_issue = records[0]['期号']
            first_end_issue = records[positions[0]]['期号']
            all_miss_intervals.append({
                'miss': positions[0] + 1,
                'start_issue': first_start_issue,
                'end_issue': first_end_issue
            })

            # 后续遗漏：相邻出现之间的间隔
            for i in range(1, len(positions)):
                gap = positions[i] - positions[i-1] - 1
                start_issue = records[positions[i-1] + 1]['期号']
                end_issue = records[positions[i]]['期号']
                all_miss_intervals.append({
                    'miss': gap,
                    'start_issue': start_issue,
                    'end_issue': end_issue
                })

            # 找到最大遗漏的区间
            max_interval = max(all_miss_intervals, key=lambda x: x['miss']) if all_miss_intervals else {'miss': total_records, 'start_issue': None, 'end_issue': None}
            max_miss = max_interval['miss']
            max_miss_start = max_interval['start_issue']
            max_miss_end = max_interval['end_issue']
        else:
            # 从未出现，当前遗漏 = 总期数
            current_miss = total_records
            max_miss = total_records
            max_miss_start = records[0]['期号'] if records else None
            max_miss_end = records[-1]['期号'] if records else None
            all_miss_intervals = []

        data[num_str] = {
            "current_miss": current_miss,
            "max_miss": max_miss,
            "max_miss_start": max_miss_start,
            "max_miss_end": max_miss_end,
            "all_miss": all_miss_intervals
        }

    return {
        "type": "special_number_miss",
        "category": "number_stats",
        "version": "1.0",
        "map_version": "2026_v1",
        "computed_at": datetime.now().isoformat(),
        "source": "build_standard_records",
        "record_count": total_records,
        "latest_issue": latest_issue,
        "data": data
    }


# ============================================================
# compute_zodiac_miss() - 生肖遗漏
# ============================================================

def compute_zodiac_miss(standard_records: List[Dict]) -> Dict:
    """
    计算生肖开奖遗漏
    使用 standard_records 中的 特码生肖 字段
    按记录序列计数，不是 issue 差值

    Args:
        standard_records: build_standard_records() 的输出
        每条记录包含:
        - 期号: str
        - 特码生肖: str

    Returns:
        生肖遗漏统计，包含当前遗漏和历史最高遗漏
    """
    # 按期号排序（升序）
    records = sorted(standard_records, key=lambda x: x['期号'])

    if not records:
        return _empty_response("zodiac_miss", "special_stats")

    total_records = len(records)
    latest_issue = records[-1]['期号']

    # 记录每个生肖出现位置列表
    zodiac_positions = {}  # zodiac -> [位置列表]
    for idx in range(total_records):
        zodiac = records[idx].get('特码生肖')
        if zodiac:
            if zodiac not in zodiac_positions:
                zodiac_positions[zodiac] = []
            zodiac_positions[zodiac].append(idx)

    # 计算当前遗漏和历史最高遗漏
    data = {}
    for zodiac in ZODIACS:
        positions = zodiac_positions.get(zodiac, [])

        if positions:
            # 当前遗漏 = 最后出现位置之后有多少期
            last_idx = positions[-1]
            current_miss = total_records - 1 - last_idx

            # 计算历史所有遗漏段
            all_miss_intervals = []

            # 第一个遗漏：从记录开始到第一次出现
            all_miss_intervals.append({
                'miss': positions[0] + 1,
                'start_issue': records[0]['期号'],
                'end_issue': records[positions[0]]['期号']
            })

            # 后续遗漏：相邻出现之间的间隔
            for i in range(1, len(positions)):
                gap = positions[i] - positions[i-1] - 1
                all_miss_intervals.append({
                    'miss': gap,
                    'start_issue': records[positions[i-1] + 1]['期号'],
                    'end_issue': records[positions[i]]['期号']
                })

            # 找到最大遗漏的区间
            max_interval = max(all_miss_intervals, key=lambda x: x['miss']) if all_miss_intervals else {'miss': total_records, 'start_issue': None, 'end_issue': None}
            max_miss = max_interval['miss']
            max_miss_start = max_interval['start_issue']
            max_miss_end = max_interval['end_issue']
        else:
            current_miss = total_records
            max_miss = total_records
            max_miss_start = records[0]['期号'] if records else None
            max_miss_end = records[-1]['期号'] if records else None
            all_miss_intervals = []

        data[zodiac] = {
            "current_miss": current_miss,
            "last_issue": records[last_idx]['期号'] if positions else None,
            "max_miss": max_miss,
            "max_miss_start": max_miss_start,
            "max_miss_end": max_miss_end,
            "all_miss": all_miss_intervals
        }

    return {
        "type": "zodiac_miss",
        "category": "special_stats",
        "version": "1.0",
        "map_version": "2026_v1",
        "computed_at": datetime.now().isoformat(),
        "source": "build_standard_records",
        "record_count": total_records,
        "latest_issue": latest_issue,
        "data": data
    }


# ============================================================
# 波色映射（支持英文和中文）
# ============================================================
WAVE_MAPPING = {
    # 英文
    'red': '红波',
    'blue': '蓝波',
    'green': '绿波',
    # 中文
    '红波': '红波',
    '蓝波': '蓝波',
    '绿波': '绿波',
}


# ============================================================
# compute_wave_miss() - 波色遗漏
# ============================================================

def compute_wave_miss(standard_records: List[Dict]) -> Dict:
    """
    计算波色开奖遗漏
    使用 constants.py 中的 get_wave() 或波色字段
    按记录序列计数，不是 issue 差值

    Args:
        standard_records: build_standard_records() 的输出
        每条记录包含:
        - 期号: str
        - 波色: str (特码波色，英文或中文) 或 特码号码: str

    Returns:
        波色遗漏统计，包含当前遗漏和历史最高遗漏
    """
    # 按期号排序（升序）
    records = sorted(standard_records, key=lambda x: x['期号'])

    if not records:
        return _empty_response("wave_miss", "special_stats")

    total_records = len(records)
    latest_issue = records[-1]['期号']

    # 记录每个波色出现位置列表
    wave_positions = {}  # wave -> [位置列表]
    for idx in range(total_records):
        record = records[idx]

        # 优先使用波色字段，否则从特码号码计算
        wave_raw = record.get('波色')
        if wave_raw:
            wave = WAVE_MAPPING.get(wave_raw.lower() if isinstance(wave_raw, str) else '')
            if not wave:
                special_num_str = record.get('特码号码', '0')
                try:
                    special_num = int(special_num_str)
                    wave = NUMBER_TO_WAVE.get(special_num)
                except (ValueError, TypeError):
                    wave = None
        else:
            special_num_str = record.get('特码号码', '0')
            try:
                special_num = int(special_num_str)
                wave = NUMBER_TO_WAVE.get(special_num)
            except (ValueError, TypeError):
                wave = None

        if wave:
            if wave not in wave_positions:
                wave_positions[wave] = []
            wave_positions[wave].append(idx)

    # 计算当前遗漏和历史最高遗漏
    data = {}
    for wave in ['红波', '蓝波', '绿波']:
        positions = wave_positions.get(wave, [])

        if positions:
            # 当前遗漏 = 最后出现位置之后有多少期
            last_idx = positions[-1]
            current_miss = total_records - 1 - last_idx

            # 计算历史所有遗漏段
            all_miss_intervals = []

            # 第一个遗漏：从记录开始到第一次出现
            all_miss_intervals.append({
                'miss': positions[0] + 1,
                'start_issue': records[0]['期号'],
                'end_issue': records[positions[0]]['期号']
            })

            # 后续遗漏：相邻出现之间的间隔
            for i in range(1, len(positions)):
                gap = positions[i] - positions[i-1] - 1
                all_miss_intervals.append({
                    'miss': gap,
                    'start_issue': records[positions[i-1] + 1]['期号'],
                    'end_issue': records[positions[i]]['期号']
                })

            # 找到最大遗漏的区间
            max_interval = max(all_miss_intervals, key=lambda x: x['miss']) if all_miss_intervals else {'miss': total_records, 'start_issue': None, 'end_issue': None}
            max_miss = max_interval['miss']
            max_miss_start = max_interval['start_issue']
            max_miss_end = max_interval['end_issue']
        else:
            current_miss = total_records
            max_miss = total_records
            max_miss_start = records[0]['期号'] if records else None
            max_miss_end = records[-1]['期号'] if records else None
            all_miss_intervals = []

        data[wave] = {
            "current_miss": current_miss,
            "last_issue": records[last_idx]['期号'] if positions else None,
            "max_miss": max_miss,
            "max_miss_start": max_miss_start,
            "max_miss_end": max_miss_end,
            "all_miss": all_miss_intervals
        }

    return {
        "type": "wave_miss",
        "category": "special_stats",
        "version": "1.0",
        "map_version": "2026_v1",
        "computed_at": datetime.now().isoformat(),
        "source": "build_standard_records",
        "record_count": total_records,
        "latest_issue": latest_issue,
        "data": data
    }


# ============================================================
# compute_hot_stats() - 生肖热度统计
# ============================================================

def compute_hot_stats(standard_records: List[Dict]) -> Dict:
    """
    计算特码生肖热度统计
    统计近 10/30/50 期各生肖出现次数

    Args:
        standard_records: build_standard_records() 的输出
        每条记录包含:
        - 期号: str
        - 特码生肖: str

    Returns:
        生肖热度统计
    """
    # 按期号排序（升序）
    records = sorted(standard_records, key=lambda x: x['期号'])

    if not records:
        return _empty_response("hot_stats", "draw_stats")

    total_records = len(records)
    latest_issue = records[-1]['期号']

    # 窗口配置
    windows = [10, 30, 50, 100, 200]

    # 初始化数据结构
    data = {zodiac: {} for zodiac in ZODIACS}

    for window in windows:
        # 取最近 window 条记录
        window_records = records[-window:] if len(records) >= window else records
        effective_window = len(window_records)

        # 统计每个生肖作为特码出现的次数
        counts = {zodiac: 0 for zodiac in ZODIACS}
        for record in window_records:
            zodiac = record.get('特码生肖')
            if zodiac and zodiac in counts:
                counts[zodiac] += 1

        for zodiac in ZODIACS:
            data[zodiac][f"hot_{window}"] = counts[zodiac]
            data[zodiac]["effective_window"] = effective_window

    return {
        "type": "hot_stats",
        "category": "draw_stats",
        "version": "1.0",
        "map_version": "2026_v1",
        "computed_at": datetime.now().isoformat(),
        "source": "build_standard_records",
        "record_count": total_records,
        "latest_issue": latest_issue,
        "data": data
    }


# ============================================================
# compute_number_miss() - 号码遗漏（保留原有实现）
# ============================================================

def compute_number_miss() -> Dict:
    """
    计算号码遗漏统计
    基于 actual_list（完整7码），统计 1-49 各号码距离上次出现的遗漏期数
    使用 load_aggregated() 作为数据源
    """
    records = [r for r in load_aggregated() if r.get('actual_list')]
    records.sort(key=lambda x: x['issue'])  # 升序

    if not records:
        return {
            "type": "number_miss",
            "category": "draw_stats",
            "version": "1.0",
            "map_version": "2026_v1",
            "computed_at": datetime.now().isoformat(),
            "source": "aggregated_live.jsonl",
            "record_count": 0,
            "latest_issue": None,
            "data": {}
        }

    total_records = len(records)
    latest_issue = records[-1]['issue']

    # 从后往前扫，记录每个号码最后一次出现的位置
    number_last_idx = {}
    for idx in range(total_records - 1, -1, -1):
        actual_list = records[idx].get('actual_list', [])
        for num in actual_list:
            if num not in number_last_idx:
                number_last_idx[num] = idx

    # 计算遗漏：从未出现的号码，遗漏=总期数
    data = {}
    for num in range(1, 50):
        num_str = f"{num:02d}"
        if num_str in number_last_idx:
            last_idx = number_last_idx[num_str]
            current_miss = total_records - 1 - last_idx
        else:
            current_miss = total_records

        data[num_str] = current_miss

    return {
        "type": "number_miss",
        "category": "draw_stats",
        "version": "1.0",
        "map_version": "2026_v1",
        "computed_at": datetime.now().isoformat(),
        "source": "aggregated_live.jsonl",
        "record_count": total_records,
        "latest_issue": latest_issue,
        "data": data
    }


# ============================================================
# 辅助函数
# ============================================================

def _empty_response(type_name: str, category: str) -> Dict:
    """生成空记录响应格式"""
    return {
        "type": type_name,
        "category": category,
        "version": "1.0",
        "map_version": "2026_v1",
        "computed_at": datetime.now().isoformat(),
        "source": "build_standard_records",
        "record_count": 0,
        "latest_issue": None,
        "data": {}
    }


# ============================================================
# 已删除的函数（不再需要）
# ============================================================
# 以下函数已被删除：
# - load_numbers() - 不再需要，从文件读取改为接受参数
# - _ensure_dirs() - 不再写入文件
# - _safe_read_json() - 不再读取文件
# - _atomic_write() - 不再写入文件
# - build_special_stats() - 不再预生成
# - build_all_stats() - 不再预生成


if __name__ == "__main__":
    # 测试代码
    from predictor.data_fetcher import get_all_records, build_standard_records

    print("=" * 60)
    print("Stats Engine - 实时计算测试")
    print("=" * 60)

    # 获取数据
    records = get_all_records([2024, 2025, 2026])
    standard_records = build_standard_records(records)

    print(f"\n获取 {len(records)} 条原始记录")
    print(f"生成 {len(standard_records)} 条标准记录")
    print(f"最新期号: {standard_records[-1]['期号'] if standard_records else 'N/A'}")

    # 测试各函数
    print("\n--- compute_special_number_miss ---")
    special_number_result = compute_special_number_miss(standard_records)
    print(f"record_count: {special_number_result['record_count']}")
    print(f"latest_issue: {special_number_result['latest_issue']}")

    print("\n--- compute_zodiac_miss ---")
    zodiac_result = compute_zodiac_miss(standard_records)
    print(f"record_count: {zodiac_result['record_count']}")
    print(f"latest_issue: {zodiac_result['latest_issue']}")
    print("Top 3 missing:")
    sorted_zodiac = sorted(
        zodiac_result['data'].items(),
        key=lambda x: x[1]['current_miss'],
        reverse=True
    )[:3]
    for zodiac, info in sorted_zodiac:
        print(f"  {zodiac}: {info['current_miss']}期")

    print("\n--- compute_wave_miss ---")
    wave_result = compute_wave_miss(standard_records)
    print(f"record_count: {wave_result['record_count']}")
    print(f"latest_issue: {wave_result['latest_issue']}")
    for wave, info in wave_result['data'].items():
        print(f"  {wave}: {info['current_miss']}期")

    print("\n--- compute_hot_stats ---")
    hot_result = compute_hot_stats(standard_records)
    print(f"record_count: {hot_result['record_count']}")
    print("Top 3 hot (10期):")
    hot_list = [(z, d['hot_10']) for z, d in hot_result['data'].items()]
    sorted_hot = sorted(hot_list, key=lambda x: x[1], reverse=True)[:3]
    for zodiac, count in sorted_hot:
        print(f"  {zodiac}: {count}次")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)