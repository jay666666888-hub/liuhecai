#!/usr/bin/env python3
"""
Stats Engine TDD Tests

测试 stats_engine.py 重构后的实时计算接口
"""

import pytest
from datetime import datetime


# ============================================================
# Test Fixtures - 标准记录格式
# ============================================================

@pytest.fixture
def sample_standard_records():
    """
    标准记录 fixture，模拟 build_standard_records() 输出

    包含 5 条测试记录，按期号升序排列
    波色使用英文格式（与实际 API 返回一致）
    """
    return [
        {
            "期号": "2026001",
            "开奖时间": "2026-01-04T21:30:00",
            "特码号码": "06",
            "特码生肖": "狗",
            "波色": "green",  # API 返回英文波色
            "开奖号码": ["01", "12", "15", "23", "28", "36", "06"],
            "开奖生肖": ["鼠", "牛", "虎", "兔", "龍", "馬", "狗"],
            "波色列表": ["red", "blue", "red", "red", "green", "blue", "green"],
        },
        {
            "期号": "2026002",
            "开奖时间": "2026-01-07T21:30:00",
            "特码号码": "15",
            "特码生肖": "虎",
            "波色": "blue",
            "开奖号码": ["03", "08", "15", "22", "31", "35", "15"],
            "开奖生肖": ["虎", "蛇", "虎", "马", "狗", "牛", "虎"],
            "波色列表": ["blue", "red", "blue", "red", "green", "red", "blue"],
        },
        {
            "期号": "2026003",
            "开奖时间": "2026-01-11T21:30:00",
            "特码号码": "23",
            "特码生肖": "牛",
            "波色": "red",
            "开奖号码": ["07", "11", "18", "23", "29", "33", "23"],
            "开奖生肖": ["狗", "兔", "蛇", "牛", "羊", "猪", "牛"],
            "波色列表": ["red", "green", "red", "red", "red", "green", "red"],
        },
        {
            "期号": "2026004",
            "开奖时间": "2026-01-14T21:30:00",
            "特码号码": "34",
            "特码生肖": "蛇",
            "波色": "red",
            "开奖号码": ["02", "09", "14", "21", "27", "34", "34"],
            "开奖生肖": ["牛", "猴", "虎", "马", "龙", "蛇", "蛇"],
            "波色列表": ["red", "blue", "blue", "green", "green", "red", "red"],
        },
        {
            "期号": "2026005",
            "开奖时间": "2026-01-18T21:30:00",
            "特码号码": "08",
            "特码生肖": "蛇",
            "波色": "red",
            "开奖号码": ["05", "08", "16", "19", "25", "38", "08"],
            "开奖生肖": ["龙", "蛇", "兔", "羊", "马", "狗", "蛇"],
            "波色列表": ["green", "red", "blue", "red", "blue", "green", "red"],
        },
    ]


@pytest.fixture
def empty_standard_records():
    """空记录 fixture"""
    return []


@pytest.fixture
def single_record():
    """单条记录 fixture"""
    return [
        {
            "期号": "2026001",
            "开奖时间": "2026-01-04T21:30:00",
            "特码号码": "06",
            "特码生肖": "狗",
            "波色": "green",
            "开奖号码": ["01", "12", "15", "23", "28", "36", "06"],
            "开奖生肖": ["鼠", "牛", "虎", "兔", "龍", "馬", "狗"],
            "波色列表": ["red", "blue", "red", "red", "green", "blue", "green"],
        }
    ]


# ============================================================
# compute_special_number_miss() Tests
# ============================================================

@pytest.mark.unit
def test_compute_special_number_miss_with_data(sample_standard_records):
    """测试 compute_special_number_miss 正常返回遗漏统计"""
    from predictor.stats_engine import compute_special_number_miss

    result = compute_special_number_miss(sample_standard_records)

    # 验证返回格式
    assert result["type"] == "special_number_miss"
    assert result["category"] == "number_stats"
    assert result["version"] == "1.0"
    assert result["source"] == "build_standard_records"
    assert result["record_count"] == 5
    assert result["latest_issue"] == "2026005"

    # 验证数据结构 - 49 个号码都应有遗漏值
    assert len(result["data"]) == 49

    # 验证已出现的特码号码的遗漏
    assert "06" in result["data"]
    assert "15" in result["data"]
    assert "23" in result["data"]
    assert "34" in result["data"]
    assert "08" in result["data"]


@pytest.mark.unit
def test_compute_special_number_miss_empty(empty_standard_records):
    """测试 compute_special_number_miss 空记录返回"""
    from predictor.stats_engine import compute_special_number_miss

    result = compute_special_number_miss(empty_standard_records)

    assert result["record_count"] == 0
    assert result["latest_issue"] is None
    assert result["data"] == {}


@pytest.mark.unit
def test_compute_special_number_miss_single(single_record):
    """测试 compute_special_number_miss 单条记录"""
    from predictor.stats_engine import compute_special_number_miss

    result = compute_special_number_miss(single_record)

    assert result["record_count"] == 1
    assert result["latest_issue"] == "2026001"
    # 最后出现的号码遗漏应为 0
    assert result["data"]["06"] == 0


@pytest.mark.unit
def test_compute_special_number_miss_computed_at_is_iso():
    """测试 computed_at 是 ISO 格式时间戳"""
    from predictor.stats_engine import compute_special_number_miss

    result = compute_special_number_miss(sample_standard_records)

    # 验证 computed_at 是有效 ISO 格式
    computed_at = result["computed_at"]
    datetime.fromisoformat(computed_at.replace('Z', '+00:00'))


# ============================================================
# compute_zodiac_miss() Tests
# ============================================================

@pytest.mark.unit
def test_compute_zodiac_miss_with_data(sample_standard_records):
    """测试 compute_zodiac_miss 正常返回遗漏统计"""
    from predictor.stats_engine import compute_zodiac_miss

    result = compute_zodiac_miss(sample_standard_records)

    # 验证返回格式
    assert result["type"] == "zodiac_miss"
    assert result["category"] == "special_stats"
    assert result["version"] == "1.0"
    assert result["source"] == "build_standard_records"
    assert result["record_count"] == 5
    assert result["latest_issue"] == "2026005"

    # 验证数据结构 - 12 个生肖都应有遗漏值
    assert len(result["data"]) == 12

    # 验证特码生肖存在
    zodiac_list = ["鼠", "牛", "虎", "兔", "龍", "蛇", "馬", "羊", "猴", "雞", "狗", "豬"]
    for zodiac in zodiac_list:
        assert zodiac in result["data"]
        assert "current_miss" in result["data"][zodiac]


@pytest.mark.unit
def test_compute_zodiac_miss_empty(empty_standard_records):
    """测试 compute_zodiac_miss 空记录返回"""
    from predictor.stats_engine import compute_zodiac_miss

    result = compute_zodiac_miss(empty_standard_records)

    assert result["record_count"] == 0
    assert result["latest_issue"] is None
    assert result["data"] == {}


@pytest.mark.unit
def test_compute_zodiac_miss_蛇_recency():
    """
    测试 蛇 生肖的遗漏计算
    根据 sample_standard_records:
    - 2026004: 特码生肖=蛇
    - 2026005: 特码生肖=蛇
    所以蛇的遗漏应该是 0 (最近刚出现)
    """
    from predictor.stats_engine import compute_zodiac_miss

    result = compute_zodiac_miss(sample_standard_records)

    # 蛇 在最近两条记录中出现，遗漏应为 0
    assert result["data"]["蛇"]["current_miss"] == 0


@pytest.mark.unit
def test_compute_zodiac_miss_牛_recency():
    """
    测试 牛 生肖的遗漏计算
    根据 sample_standard_records:
    - 2026003: 特码生肖=牛
    - 之后没有出现
    所以牛遗漏应该是 2 (从第5期往前数2期)
    """
    from predictor.stats_engine import compute_zodiac_miss

    result = compute_zodiac_miss(sample_standard_records)

    # 牛 在第3期出现，之后未出现，遗漏应为 2
    assert result["data"]["牛"]["current_miss"] == 2


# ============================================================
# compute_wave_miss() Tests
# ============================================================

@pytest.mark.unit
def test_compute_wave_miss_with_data(sample_standard_records):
    """测试 compute_wave_miss 正常返回遗漏统计"""
    from predictor.stats_engine import compute_wave_miss

    result = compute_wave_miss(sample_standard_records)

    # 验证返回格式
    assert result["type"] == "wave_miss"
    assert result["category"] == "special_stats"
    assert result["version"] == "1.0"
    assert result["source"] == "build_standard_records"
    assert result["record_count"] == 5
    assert result["latest_issue"] == "2026005"

    # 验证数据结构 - 3 个波色都应有遗漏值
    assert len(result["data"]) == 3
    for wave in ["红波", "蓝波", "绿波"]:
        assert wave in result["data"]
        assert "current_miss" in result["data"][wave]


@pytest.mark.unit
def test_compute_wave_miss_empty(empty_standard_records):
    """测试 compute_wave_miss 空记录返回"""
    from predictor.stats_engine import compute_wave_miss

    result = compute_wave_miss(empty_standard_records)

    assert result["record_count"] == 0
    assert result["latest_issue"] is None
    assert result["data"] == {}


@pytest.mark.unit
def test_compute_wave_miss_绿波_recency():
    """
    测试绿波遗漏计算
    根据 sample_standard_records:
    - 2026001: 特码波色=绿波
    - 之后没有绿波
    所以绿波遗漏应该是 4 (从第5期往前数4期)
    """
    from predictor.stats_engine import compute_wave_miss

    result = compute_wave_miss(sample_standard_records)

    # 绿波在第1期出现，之后未出现，遗漏应为 4
    assert result["data"]["绿波"]["current_miss"] == 4


@pytest.mark.unit
def test_compute_wave_miss_红波_recency():
    """
    测试红波遗漏计算
    根据 sample_standard_records:
    - 2026005: 特码波色=红波
    所以红波遗漏应该是 0 (最近刚出现)
    """
    from predictor.stats_engine import compute_wave_miss

    result = compute_wave_miss(sample_standard_records)

    # 红波在最近出现，遗漏应为 0
    assert result["data"]["红波"]["current_miss"] == 0


# ============================================================
# compute_hot_stats() Tests
# ============================================================

@pytest.mark.unit
def test_compute_hot_stats_with_data(sample_standard_records):
    """测试 compute_hot_stats 正常返回热度统计"""
    from predictor.stats_engine import compute_hot_stats

    result = compute_hot_stats(sample_standard_records)

    # 验证返回格式
    assert result["type"] == "hot_stats"
    assert result["category"] == "draw_stats"
    assert result["version"] == "1.0"
    assert result["source"] == "build_standard_records"
    assert result["record_count"] == 5
    assert result["latest_issue"] == "2026005"

    # 验证数据结构 - 12 个生肖都应有热度值
    assert len(result["data"]) == 12

    # 验证窗口配置
    for zodiac_data in result["data"].values():
        assert "hot_10" in zodiac_data
        assert "hot_30" in zodiac_data
        assert "hot_50" in zodiac_data


@pytest.mark.unit
def test_compute_hot_stats_empty(empty_standard_records):
    """测试 compute_hot_stats 空记录返回"""
    from predictor.stats_engine import compute_hot_stats

    result = compute_hot_stats(empty_standard_records)

    assert result["record_count"] == 0
    assert result["latest_issue"] is None
    assert result["data"] == {}


@pytest.mark.unit
def test_compute_hot_stats_counts():
    """
    测试热度统计计数
    根据 sample_standard_records (5条记录):
    - 特码生肖: 狗, 虎, 牛, 蛇, 蛇

    10期窗口 (只有5条记录):
    - 蛇: 2次
    - 狗/虎/牛: 各1次

    验证计数正确性
    """
    from predictor.stats_engine import compute_hot_stats

    result = compute_hot_stats(sample_standard_records)

    # 蛇出现2次
    assert result["data"]["蛇"]["hot_10"] == 2

    # 其他单次出现的
    assert result["data"]["狗"]["hot_10"] == 1
    assert result["data"]["虎"]["hot_10"] == 1
    assert result["data"]["牛"]["hot_10"] == 1


# ============================================================
# deleted functions should raise ImportError
# ============================================================

@pytest.mark.unit
def test_load_numbers_deleted():
    """验证 load_numbers() 已删除"""
    import sys
    import importlib

    # 重新加载模块以确保获取最新版本
    import predictor.stats_engine
    importlib.reload(predictor.stats_engine)

    # load_numbers 不应该存在于模块中
    assert not hasattr(predictor.stats_engine, 'load_numbers')


@pytest.mark.unit
def test_build_special_stats_deleted():
    """验证 build_special_stats() 已删除"""
    import predictor.stats_engine

    assert not hasattr(predictor.stats_engine, 'build_special_stats')


@pytest.mark.unit
def test_build_all_stats_deleted():
    """验证 build_all_stats() 已删除"""
    import predictor.stats_engine

    assert not hasattr(predictor.stats_engine, 'build_all_stats')


@pytest.mark.unit
def test_internal_functions_deleted():
    """验证内部文件操作函数已删除"""
    import predictor.stats_engine

    assert not hasattr(predictor.stats_engine, '_ensure_dirs')
    assert not hasattr(predictor.stats_engine, '_safe_read_json')
    assert not hasattr(predictor.stats_engine, '_atomic_write')


# ============================================================
# load_aggregated() 应该保留 (用于 compute_number_miss)
# ============================================================

@pytest.mark.unit
def test_load_aggregated_preserved():
    """验证 load_aggregated() 函数保留"""
    from predictor.stats_engine import load_aggregated

    # 函数应该存在且可调用
    result = load_aggregated()
    assert isinstance(result, list)


# ============================================================
# Response Format Tests
# ============================================================

@pytest.mark.unit
def test_response_format_special_number_miss(sample_standard_records):
    """验证 special_number_miss 返回格式完整性"""
    from predictor.stats_engine import compute_special_number_miss

    result = compute_special_number_miss(sample_standard_records)

    required_fields = ["type", "category", "version", "map_version",
                       "computed_at", "source", "record_count", "latest_issue", "data"]
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"


@pytest.mark.unit
def test_response_format_zodiac_miss(sample_standard_records):
    """验证 zodiac_miss 返回格式完整性"""
    from predictor.stats_engine import compute_zodiac_miss

    result = compute_zodiac_miss(sample_standard_records)

    required_fields = ["type", "category", "version", "map_version",
                       "computed_at", "source", "record_count", "latest_issue", "data"]
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"


@pytest.mark.unit
def test_response_format_wave_miss(sample_standard_records):
    """验证 wave_miss 返回格式完整性"""
    from predictor.stats_engine import compute_wave_miss

    result = compute_wave_miss(sample_standard_records)

    required_fields = ["type", "category", "version", "map_version",
                       "computed_at", "source", "record_count", "latest_issue", "data"]
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"


@pytest.mark.unit
def test_response_format_hot_stats(sample_standard_records):
    """验证 hot_stats 返回格式完整性"""
    from predictor.stats_engine import compute_hot_stats

    result = compute_hot_stats(sample_standard_records)

    required_fields = ["type", "category", "version", "map_version",
                       "computed_at", "source", "record_count", "latest_issue", "data"]
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])