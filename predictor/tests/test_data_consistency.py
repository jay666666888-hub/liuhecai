#!/usr/bin/env python3
"""
数据一致性测试

验证：
1. API 数据完整性
2. 数据格式一致性
3. 关键字段存在性
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, build_standard_records, get_special_zodiac


def test_api_records_complete():
    """验证 API 返回的记录包含所有必要字段"""
    records = get_all_records([2024, 2025, 2026])

    required_fields = ['expect', 'openTime', 'openCode', 'zodiac']
    missing = []

    for i, r in enumerate(records[:100]):  # 检查前100条
        for field in required_fields:
            if field not in r or r[field] is None:
                missing.append(f"记录{i}: 缺少字段'{field}'")

    assert len(missing) == 0, f"发现{len(missing)}条不完整的记录:\n" + "\n".join(missing[:5])


def test_special_number_range():
    """验证特码号码在有效范围内 (1-49)"""
    records = get_all_records([2024, 2025, 2026])
    standard_records = build_standard_records(records)

    invalid = []
    for r in standard_records:
        num = r.get('特码号码')
        if num:
            try:
                n = int(num)
                if not (1 <= n <= 49):
                    invalid.append(f"期号{r.get('期号')}: 特码号码{n}无效")
            except ValueError:
                invalid.append(f"期号{r.get('期号')}: 特码号码{num}无法解析")

    assert len(invalid) == 0, f"发现{len(invalid)}条异常:\n" + "\n".join(invalid[:5])


def test_special_zodiac_valid():
    """验证特码生肖是有效的生肖"""
    valid_zodiacs = {'鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬'}
    records = get_all_records([2024, 2025, 2026])

    invalid = []
    for r in records:
        zodiac = get_special_zodiac(r)
        if zodiac not in valid_zodiacs:
            invalid.append(f"期号{r.get('expect')}: 生肖'{zodiac}'无效")

    assert len(invalid) == 0, f"发现{len(invalid)}条异常:\n" + "\n".join(invalid[:5])


def test_opencode_format():
    """验证开奖号码格式正确 (7个号码逗号分隔)"""
    records = get_all_records([2024, 2025, 2026])

    invalid = []
    for r in records[:100]:
        opencode = r.get('openCode', '')
        if opencode:
            parts = opencode.split(',')
            if len(parts) != 7:
                invalid.append(f"期号{r.get('expect')}: 开奖号码'{opencode}'格式错误")

    assert len(invalid) == 0, f"发现{len(invalid)}条格式错误:\n" + "\n".join(invalid[:5])


def test_zodiac_list_format():
    """验证生肖列表格式正确 (7个生肖逗号分隔)"""
    records = get_all_records([2024, 2025, 2026])

    invalid = []
    for r in records[:100]:
        zodiac = r.get('zodiac', '')
        if zodiac:
            parts = zodiac.split(',')
            if len(parts) != 7:
                invalid.append(f"期号{r.get('expect')}: 生肖列表'{zodiac}'格式错误")

    assert len(invalid) == 0, f"发现{len(invalid)}条格式错误:\n" + "\n".join(invalid[:5])


def test_build_standard_records_preserves_data():
    """验证 build_standard_records 不丢失数据"""
    records = get_all_records([2024, 2025, 2026])
    standard_records = build_standard_records(records)

    assert len(standard_records) == len(records), "标准记录数量不匹配"

    # 检查关键字段
    for i, (orig, std) in enumerate(zip(records, standard_records)):
        assert std.get('期号') == orig.get('expect'), f"记录{i}: 期号不匹配"
        assert std.get('开奖时间') == orig.get('openTime'), f"记录{i}: 开奖时间不匹配"

        # 验证特码生肖来自 zodiac[6]
        original_special_zodiac = get_special_zodiac(orig)
        assert std.get('特码生肖') == original_special_zodiac, f"记录{i}: 特码生肖不匹配"


def test_issue_ordering():
    """验证期号是递增的"""
    records = get_all_records([2024, 2025, 2026])
    standard_records = build_standard_records(records)

    issues = [r.get('期号') for r in standard_records]
    sorted_issues = sorted(issues)

    # 检查是否有重复
    from collections import Counter
    counts = Counter(issues)
    duplicates = [k for k, v in counts.items() if v > 1]

    assert len(duplicates) == 0, f"发现重复期号: {duplicates[:10]}"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])