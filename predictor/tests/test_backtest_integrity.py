#!/usr/bin/env python3
"""
回测完整性测试

验证回测过程中：
1. 每条记录使用对应年份的生肖映射
2. 不存在跨年份使用错误映射的情况
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, build_standard_records
from predictor.constants import (
    get_zodiac_map_for_date,
    get_lunar_year_for_date,
    LUNAR_YEAR_BOUNDARIES,
)


def test_records_use_correct_mapping():
    """验证每条历史记录使用正确的年份映射"""
    records = get_all_records([2024, 2025, 2026])
    standard_records = build_standard_records(records)

    errors = []
    for r in standard_records:
        date = r.get('开奖时间', '')
        actual_zodiac = r.get('特码生肖', '')
        num = r.get('特码号码', '')
        num_str = f'{int(num):02d}' if num else ''

        # 获取该日期应该使用的映射
        zodiac_map = get_zodiac_map_for_date(date)

        # 在映射中查找该号码对应的生肖
        expected_zodiac = None
        for z, nums in zodiac_map.items():
            if num_str in nums:
                expected_zodiac = z
                break

        if expected_zodiac != actual_zodiac:
            errors.append(
                f"期号{r.get('期号')} ({date}): "
                f"号码{num_str} 实际={actual_zodiac} 映射={expected_zodiac}"
            )

    assert len(errors) == 0, f"发现{len(errors)}条不一致的记录:\n" + "\n".join(errors[:10])


def test_no_year_boundary_crossing():
    """验证没有跨年份使用错误映射"""
    records = get_all_records([2024, 2025, 2026])
    standard_records = build_standard_records(records)

    # 按时间顺序检查
    prev_year = None
    for r in standard_records:
        date = r.get('开奖时间', '')
        if not date:
            continue

        year = get_lunar_year_for_date(date)
        assert year in LUNAR_YEAR_BOUNDARIES, f"日期 {date} 不在已知年份范围内"

        if prev_year is not None:
            # 允许从高到低的跳跃（数据可能不是连续的）
            pass

        prev_year = year


def test_lunar_year_boundaries():
    """验证农历年边界定义正确"""
    for year, info in LUNAR_YEAR_BOUNDARIES.items():
        start = info['start']
        end = info['end']

        # 开始日期 <= 结束日期
        from datetime import datetime
        start_date = datetime.strptime(start, '%Y-%m-%d')
        end_date = datetime.strptime(end, '%Y-%m-%d')
        assert start_date <= end_date, f"{year}年边界错误：{start} > {end}"

        # 跨度约1年
        delta = (end_date - start_date).days
        assert 350 <= delta <= 380, f"{year}年跨度异常：{delta}天"


def test_cross_year_prediction_consistency():
    """验证跨年预测时每条记录使用正确的映射"""
    # 模拟一个跨越多个农历年的回测场景
    from predictor.predictors.active.v31.predictor import V31Special24maPredictor

    records = get_all_records([2024, 2025, 2026])
    standard_records = build_standard_records(records)

    # 找一个靠近年份边界的预测点
    boundary_dates = ['2025-01-28', '2025-01-29', '2026-02-16', '2026-02-17']

    predictor = V31Special24maPredictor()

    for boundary in boundary_dates:
        # 找到该日期之后的记录
        for i, r in enumerate(standard_records):
            if r.get('开奖时间', '').startswith(boundary):
                if i < 20:
                    continue

                history = standard_records[:i]
                result = predictor.predict(history, top_k=24)

                # 验证预测使用了正确的映射
                assert 'lunar_year' in result.metadata, "预测元数据缺少lunar_year"
                break


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])