#!/usr/bin/env python3
"""
常量映射表统一导出
"""

from .zodiac_map import (
    MAP_VERSION as ZODIAC_MAP_VERSION,
    ZODIACS,
    get_zodiac_index,
    get_all_zodiacs
)

from .wave_map import (
    MAP_VERSION as WAVE_MAP_VERSION,
    WAVES,
    WAVE_NUMBERS,
    NUMBER_TO_WAVE,
    get_wave,
    get_all_waves,
    get_wave_members,
    get_wave_by_number,
)

from .zodiac_year_map import (
    LUNAR_YEAR_BOUNDARIES,
    ZODIAC_MAPS,
    get_lunar_year_for_date,
    get_zodiac_map_for_date,
    get_zodiac_for_number,
    build_number_to_zodiac_map,
    validate_zodiac_map_consistency,
    get_all_lunar_years,
)

__all__ = [
    "ZODIAC_MAP_VERSION",
    "ZODIACS",
    "get_zodiac_index",
    "get_all_zodiacs",
    "WAVE_MAP_VERSION",
    "WAVES",
    "WAVE_NUMBERS",
    "NUMBER_TO_WAVE",
    "get_wave",
    "get_all_waves",
    "get_wave_members",
    "get_wave_by_number",
    "LUNAR_YEAR_BOUNDARIES",
    "ZODIAC_MAPS",
    "get_lunar_year_for_date",
    "get_zodiac_map_for_date",
    "get_zodiac_for_number",
    "build_number_to_zodiac_map",
    "validate_zodiac_map_consistency",
    "get_all_lunar_years",
]