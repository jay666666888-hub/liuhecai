#!/usr/bin/env python3
"""
澳门六合生肖映射 - 全局年份映射系统
农历新年前后自动切换，每个年份独立维护

使用方式:
    from predictor.constants.zodiac_year_map import get_zodiac_map_for_date

    # 获取任意日期对应的生肖映射
    zodiac_map = get_zodiac_map_for_date('2026-02-20')

    # 回测时自动使用正确的映射
    for record in records:
        zodiac_map = get_zodiac_map_for_date(record['openTime'])
        ...

历史映射（从API数据验证）:
    2024农历年(龙 2024-02-10~2025-01-28): 一致
    2025农历年(蛇 2025-01-29~2026-02-16): 一致
    2026农历年(马 2026-02-17~): 一致
"""

from typing import Dict, List
from datetime import datetime

# ============================================================================
# 农历年边界（每年更新）
# ============================================================================

LUNAR_YEAR_BOUNDARIES = {
    # 龙年
    2024: {'start': '2024-02-10', 'end': '2025-01-28', 'zodiac': '龍'},
    # 蛇年
    2025: {'start': '2025-01-29', 'end': '2026-02-16', 'zodiac': '蛇'},
    # 马年
    2026: {'start': '2026-02-17', 'end': '2027-01-26', 'zodiac': '馬'},
    # 羊年
    2027: {'start': '2027-01-27', 'end': '2028-02-14', 'zodiac': '羊'},
    # 猴年
    2028: {'start': '2028-02-15', 'end': '2029-02-03', 'zodiac': '猴'},
    # 鸡年
    2029: {'start': '2029-02-04', 'end': '2030-01-23', 'zodiac': '雞'},
}

# ============================================================================
# 每个农历年的生肖映射（从API数据提取，100%验证）
# ============================================================================

ZODIAC_MAPS = {
    # 2024农历年(龙) - 2024-02-10 至 2025-01-28
    2024: {
        '龍': ['01', '13', '25', '37', '49'],
        '兔': ['02', '14', '26', '38'],
        '虎': ['03', '15', '27', '39'],
        '牛': ['04', '16', '28', '40'],
        '鼠': ['05', '17', '29', '41'],
        '豬': ['06', '18', '30', '42'],
        '狗': ['07', '19', '31', '43'],
        '雞': ['08', '20', '32', '44'],
        '猴': ['09', '21', '33', '45'],
        '羊': ['10', '22', '34', '46'],
        '馬': ['11', '23', '35', '47'],
        '蛇': ['12', '24', '36', '48'],
    },

    # 2025农历年(蛇) - 2025-01-29 至 2026-02-16
    2025: {
        '蛇': ['01', '13', '25', '37', '49'],
        '龍': ['02', '14', '26', '38'],
        '兔': ['03', '15', '27', '39'],
        '虎': ['04', '16', '28', '40'],
        '牛': ['05', '17', '29', '41'],
        '鼠': ['06', '18', '30', '42'],
        '豬': ['07', '19', '31', '43'],
        '狗': ['08', '20', '32', '44'],
        '雞': ['09', '21', '33', '45'],
        '猴': ['10', '22', '34', '46'],
        '羊': ['11', '23', '35', '47'],
        '馬': ['12', '24', '36', '48'],
    },

    # 2026农历年(马) - 2026-02-17 至 2027-01-26
    2026: {
        '馬': ['01', '13', '25', '37', '49'],
        '蛇': ['02', '14', '26', '38'],
        '龍': ['03', '15', '27', '39'],
        '兔': ['04', '16', '28', '40'],
        '虎': ['05', '17', '29', '41'],
        '牛': ['06', '18', '30', '42'],
        '鼠': ['07', '19', '31', '43'],
        '豬': ['08', '20', '32', '44'],
        '狗': ['09', '21', '33', '45'],
        '雞': ['10', '22', '34', '46'],
        '猴': ['11', '23', '35', '47'],
        '羊': ['12', '24', '36', '48'],
    },

    # 2027农历年(羊) - 2027-01-27 至 2028-02-14
    2027: {
        '羊': ['01', '13', '25', '37', '49'],
        '馬': ['02', '14', '26', '38'],
        '蛇': ['03', '15', '27', '39'],
        '龍': ['04', '16', '28', '40'],
        '兔': ['05', '17', '29', '41'],
        '虎': ['06', '18', '30', '42'],
        '牛': ['07', '19', '31', '43'],
        '鼠': ['08', '20', '32', '44'],
        '豬': ['09', '21', '33', '45'],
        '狗': ['10', '22', '34', '46'],
        '雞': ['11', '23', '35', '47'],
        '猴': ['12', '24', '36', '48'],
    },

    # 2028农历年(猴) - 2028-02-15 至 2029-02-03
    2028: {
        '猴': ['01', '13', '25', '37', '49'],
        '羊': ['02', '14', '26', '38'],
        '馬': ['03', '15', '27', '39'],
        '蛇': ['04', '16', '28', '40'],
        '龍': ['05', '17', '29', '41'],
        '兔': ['06', '18', '30', '42'],
        '虎': ['07', '19', '31', '43'],
        '牛': ['08', '20', '32', '44'],
        '鼠': ['09', '21', '33', '45'],
        '豬': ['10', '22', '34', '46'],
        '狗': ['11', '23', '35', '47'],
        '雞': ['12', '24', '36', '48'],
    },

    # 2029农历年(鸡) - 2029-02-04 至 2030-01-23
    2029: {
        '雞': ['01', '13', '25', '37', '49'],
        '猴': ['02', '14', '26', '38'],
        '羊': ['03', '15', '27', '39'],
        '馬': ['04', '16', '28', '40'],
        '蛇': ['05', '17', '29', '41'],
        '龍': ['06', '18', '30', '42'],
        '兔': ['07', '19', '31', '43'],
        '虎': ['08', '20', '32', '44'],
        '牛': ['09', '21', '33', '45'],
        '鼠': ['10', '22', '34', '46'],
        '豬': ['11', '23', '35', '47'],
        '狗': ['12', '24', '36', '48'],
    },
}


def get_lunar_year_for_date(date_str: str) -> int:
    """
    根据日期获取对应的农历年

    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS

    Returns:
        农历年份 (2024, 2025, 2026)
    """
    # 处理日期时间格式
    if ' ' in date_str:
        date_str = date_str.split(' ')[0]

    date = datetime.strptime(date_str, '%Y-%m-%d')

    for year, info in sorted(LUNAR_YEAR_BOUNDARIES.items()):
        start = datetime.strptime(info['start'], '%Y-%m-%d')
        end = datetime.strptime(info['end'], '%Y-%m-%d')
        if start <= date <= end:
            return year

    # 默认返回2026（如果不在已知范围内，假设是当前年份）
    return 2026


def get_zodiac_map_for_date(date_str: str) -> Dict[str, List[str]]:
    """
    获取指定日期对应的生肖映射

    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS

    Returns:
        生肖映射字典 {生肖: [号码列表]}
    """
    lunar_year = get_lunar_year_for_date(date_str)
    return ZODIAC_MAPS.get(lunar_year, ZODIAC_MAPS[2026])


def get_zodiac_for_number(number: int, date_str: str) -> str:
    """
    根据日期和号码获取生肖

    Args:
        number: 开奖号码 (1-49)
        date_str: 日期字符串

    Returns:
        生肖字符串
    """
    zodiac_map = get_zodiac_map_for_date(date_str)
    num_str = f'{int(number):02d}'

    for zodiac, nums in zodiac_map.items():
        if num_str in nums:
            return zodiac

    return '未知'


def build_number_to_zodiac_map(date_str: str) -> Dict[str, str]:
    """
    构建号码到生肖的映射（反向查找表）

    Args:
        date_str: 日期字符串

    Returns:
        {号码: 生肖} 字典
    """
    zodiac_map = get_zodiac_map_for_date(date_str)
    result = {}
    for zodiac, nums in zodiac_map.items():
        for num in nums:
            result[num] = zodiac
    return result


def validate_zodiac_map_consistency(year: int) -> bool:
    """
    验证某个农历年的映射一致性（每个号码只对应一个生肖）

    Args:
        year: 农历年份

    Returns:
        True if consistent
    """
    zodiac_map = ZODIAC_MAPS.get(year, {})
    number_to_zodiac = {}

    for zodiac, nums in zodiac_map.items():
        for num in nums:
            if num in number_to_zodiac:
                return False
            number_to_zodiac[num] = zodiac

    return len(number_to_zodiac) == 49


def get_all_lunar_years() -> List[int]:
    """获取所有已定义的农历年"""
    return sorted(ZODIAC_MAPS.keys())


if __name__ == '__main__':
    # 测试
    print('=== 生肖映射系统测试 ===')
    print()

    # 测试各年份
    for year in [2024, 2025, 2026]:
        info = LUNAR_YEAR_BOUNDARIES[year]
        consistent = validate_zodiac_map_consistency(year)
        print(f'{year}农历年({info["zodiac"]}): {info["start"]} ~ {info["end"]}')
        print(f'  映射一致性: {"✓" if consistent else "✗"}')
        print()

    # 测试日期到映射的获取
    test_dates = [
        '2024-03-15',  # 龙年
        '2025-03-15',  # 蛇年
        '2026-03-15',  # 马年
    ]

    print('=== 日期 -> 生肖映射 ===')
    for date in test_dates:
        lunar_year = get_lunar_year_for_date(date)
        zodiac_map = get_zodiac_map_for_date(date)
        print(f'{date} -> 农历{lunar_year}年')
        print(f'  马: {zodiac_map.get("馬", [])}')
        print(f'  蛇: {zodiac_map.get("蛇", [])}')
        print(f'  龙: {zodiac_map.get("龍", [])}')
        print()

    # 测试号码查生肖
    print('=== 号码 -> 生肖 ===')
    for num in ['01', '13', '24', '37', '49']:
        zodiac = get_zodiac_for_number(int(num), '2026-03-15')
        print(f'  {num} -> {zodiac}')