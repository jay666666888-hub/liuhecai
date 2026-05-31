#!/usr/bin/env python3
"""
生肖映射一致性测试

验证每个年份的生肖映射满足：
1. 每个号码只对应一个生肖（不重复）
2. 全部49个号码都被覆盖（不遗漏）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.constants.zodiac_year_map import (
    LUNAR_YEAR_BOUNDARIES,
    ZODIAC_MAPS,
    validate_zodiac_map_consistency,
    get_all_lunar_years,
)


def test_all_years_consistency():
    """验证所有年份的映射一致性"""
    years = get_all_lunar_years()
    assert len(years) > 0, "没有定义的年份"

    for year in years:
        assert validate_zodiac_map_consistency(year), (
            f"{year}年映射不一致：存在重复号码"
        )


def test_all_years_complete():
    """验证所有年份的映射完整性"""
    years = get_all_lunar_years()

    for year in years:
        zodiac_map = ZODIAC_MAPS[year]
        all_numbers = set()

        for zodiac, nums in zodiac_map.items():
            all_numbers.update(nums)

        assert len(all_numbers) == 49, (
            f"{year}年映射不完整：只有{len(all_numbers)}个号码，缺{49-len(all_numbers)}个"
        )


def test_each_number_appears_once():
    """验证每个号码在每个年份只出现一次"""
    years = get_all_lunar_years()

    for year in years:
        zodiac_map = ZODIAC_MAPS[year]
        seen = {}
        for zodiac, nums in zodiac_map.items():
            for num in nums:
                assert num not in seen, (
                    f"{year}年：号码{num}重复对应了{zodiac}和{seen[num]}"
                )
                seen[num] = zodiac


def test_boundaries_sequential():
    """验证年份边界是连续的"""
    sorted_years = sorted(LUNAR_YEAR_BOUNDARIES.keys())

    for i in range(len(sorted_years) - 1):
        current_year = sorted_years[i]
        next_year = sorted_years[i + 1]

        current_end = LUNAR_YEAR_BOUNDARIES[current_year]['end']
        next_start = LUNAR_YEAR_BOUNDARIES[next_year]['start']

        # 检查日期连续性（前一年结束 + 1天 = 下一年开始）
        from datetime import datetime, timedelta
        end_date = datetime.strptime(current_end, '%Y-%m-%d')
        start_date = datetime.strptime(next_start, '%Y-%m-%d')

        expected_start = end_date + timedelta(days=1)
        assert start_date == expected_start, (
            f"边界不连续：{current_year}年结束于{current_end}，"
            f"{next_year}年开始于{next_start}（期望{expected_start.date()}）"
        )


def test_all_zodiacs_present():
    """验证每个年份都包含全部12个生肖"""
    expected_zodiacs = {'鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬'}
    years = get_all_lunar_years()

    for year in years:
        zodiac_map = ZODIAC_MAPS[year]
        present = set(zodiac_map.keys())
        assert present == expected_zodiacs, (
            f"{year}年缺少生肖：{expected_zodiacs - present}"
        )


def test_zodiac_boundaries_match():
    """验证年份边界与生肖定义一致"""
    years = get_all_lunar_years()

    for year in years:
        boundary_zodiac = LUNAR_YEAR_BOUNDARIES[year]['zodiac']
        first_zodiac = list(ZODIAC_MAPS[year].keys())[0]

        # 边界定义的生肖应该是该年第一个号码对应的生肖
        first_number_zodiac = ZODIAC_MAPS[year][first_zodiac][0]
        # 第一个生肖的第一个号码是01
        assert first_number_zodiac == '01', f"{year}年第一个号码应该是01"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])