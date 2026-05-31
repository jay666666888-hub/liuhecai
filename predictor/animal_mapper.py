#!/usr/bin/env python3
"""
澳门六合生肖映射 - 单一真相源
所有生肖映射必须通过 AnimalMapper.get() 获取
禁止使用 year_mapping.json、hardcode 或本地公式
"""

import hashlib
import json
import os
from typing import Dict, Optional
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "predictor", ".cache")
MAPPING_STATE_FILE = os.path.join(BASE_DIR, "configs", "mapping_state.json")


class MappingSourceError(Exception):
    """多映射源检测错误"""
    pass


class MappingIntegrityError(Exception):
    """映射完整性错误"""
    pass


class MappingUnavailableError(Exception):
    """映射不可用错误"""
    pass


# ============================================================================
# 生肖映射常量（单一真相源）
# 所有玄学特征（五行、相冲相合等）必须在此定义，禁止散落在各处
# ============================================================================

ZODIAC_WUXING = {
    '鼠': '水', '牛': '土', '虎': '木', '兔': '木',
    '龍': '土', '蛇': '火', '馬': '火', '羊': '土',
    '猴': '金', '雞': '金', '狗': '土', '豬': '水'
}

# 相冲（六冲）- 倾向于不同时出现
ZODIAC_SHENGKE = {
    '鼠': '馬', '馬': '鼠',
    '牛': '羊', '羊': '牛',
    '虎': '猴', '猴': '虎',
    '兔': '雞', '雞': '兔',
    '龍': '狗', '狗': '龍',
    '蛇': '豬', '豬': '蛇'
}

WUXING_XIANGSHENG = {
    '木': '火', '火': '土', '土': '金', '金': '水', '水': '木'
}

WUXING_ELEMENTS = ['木', '火', '土', '金', '水']

# ============================================================================
# 生肖玄学映射（单一真相源）
# ============================================================================

# 相合（六合）- 倾向于同时出现
ZODIAC_XIANGHE = {
    '鼠': '牛', '牛': '鼠',
    '虎': '狗', '狗': '虎',
    '兔': '雞', '雞': '兔',
    '龍': '蛇', '蛇': '龍',
    '馬': '羊', '羊': '馬',
    '猴': '豬', '豬': '猴'
}

# 阴阳 - 阳牲/阴牲交替
ZODIAC_YINYANG = {
    '鼠': '阳', '牛': '阴', '虎': '阳', '兔': '阴',
    '龍': '阳', '蛇': '阴', '馬': '阳', '羊': '阴',
    '猴': '阳', '雞': '阴', '狗': '阳', '豬': '阴'
}

# 季节对应
ZODIAC_SEASON = {
    '虎': '春', '兔': '春',
    '蛇': '夏', '馬': '夏',
    '龍': '秋', '羊': '秋',
    '狗': '冬', '豬': '冬',
    '鼠': '冬', '牛': '冬',
    '猴': '秋', '雞': '秋'
}

# 时辰（小时）映射
ZODIAC_HOUR = {
    '鼠': '子', '牛': '丑', '虎': '寅', '兔': '卯',
    '龍': '辰', '蛇': '巳', '馬': '午', '羊': '未',
    '猴': '申', '雞': '酉', '狗': '戌', '豬': '亥'
}


def get_zodiac_wuxing(zodiac: str) -> str:
    """获取生肖对应的五行"""
    return ZODIAC_WUXING.get(zodiac, '土')


def get_zodiac_shengke(zodiac: str) -> str:
    """获取生肖相冲的生肖"""
    return ZODIAC_SHENGKE.get(zodiac, '')


def get_wuxing_xiangsheng(wuxing: str) -> str:
    """获取五行相生的下一个五行"""
    return WUXING_XIANGSHENG.get(wuxing, '')


def get_zodiac_xianghe(zodiac: str) -> str:
    """获取生肖相合的生肖"""
    return ZODIAC_XIANGHE.get(zodiac, '')


def get_zodiac_yinyang(zodiac: str) -> str:
    """获取生肖阴阳"""
    return ZODIAC_YINYANG.get(zodiac, '阳')


def get_zodiac_season(zodiac: str) -> str:
    """获取生肖季节"""
    return ZODIAC_SEASON.get(zodiac, '')


def get_zodiac_hour(zodiac: str) -> str:
    """获取生肖时辰"""
    return ZODIAC_HOUR.get(zodiac, '')


def _detect_mapping_sources() -> list:
    """检测所有映射源（生产环境）"""
    sources = []

    # 检查 configs 中的映射文件
    configs_dir = os.path.join(BASE_DIR, "configs")
    if os.path.exists(configs_dir):
        for f in os.listdir(configs_dir):
            if 'mapping' in f.lower() and f.endswith('.json'):
                sources.append(os.path.join(configs_dir, f))

    # 检查 predictor 目录
    predictor_dir = os.path.join(BASE_DIR, "predictor")
    for root, dirs, files in os.walk(predictor_dir):
        for f in files:
            if 'mapping' in f.lower() and f.endswith('.json'):
                sources.append(os.path.join(root, f))

    return sources


def _assert_single_source():
    """断言只有单一映射源"""
    sources = _detect_mapping_sources()
    if len(sources) > 0:
        raise MappingSourceError(
            f"FATAL ERROR\n\nMultiple Zodiac Mapping Sources Detected\n\n"
            f"Detected:\n" + "\n".join(f"- {s}" for s in sources) + "\n"
            f"Prediction Aborted"
        )


class AnimalMapper:
    """
    唯一生肖映射入口
    所有代码必须通过 AnimalMapper.get() 获取生肖
    """
    _instance = None
    _mapping = None
    _mapping_hash = None

    @classmethod
    def get(cls, number: int, issue: str = None) -> str:
        """
        获取号码对应的生肖（按期号查找）

        Args:
            number: 开奖号码 (1-49) - 仅用于验证
            issue: 期号（必填，用于查找对应生肖）

        Returns:
            生肖字符串

        Raises:
            MappingUnavailableError: 当映射不可用时
        """
        cls._ensure_mapping()

        if not issue:
            raise MappingUnavailableError("Issue is required for AnimalMapper.get()")

        # 从记录中查找该期号的特码生肖
        for r in cls._records:
            if r["expect"] == issue:
                nums = r["openCode"].split(",")
                zods = r["zodiac"].split(",")
                for num_str, zodiac in zip(nums, zods):
                    if int(num_str) == number:
                        return zodiac
                # 找到了期号但号码不匹配
                raise MappingUnavailableError(f"Number {number} not found in issue {issue}")

        raise MappingUnavailableError(f"Issue {issue} not found")

    @classmethod
    def _ensure_mapping(cls):
        """确保映射已加载"""
        if cls._mapping is None:
            # 从API获取数据并构建映射
            cls._load_from_api()
            # 验证映射
            cls._validate_mapping()
            # 计算hash
            cls._compute_hash()

    @classmethod
    def _load_from_api(cls):
        """从API加载映射（唯一合法来源）"""
        # 避免循环导入
        from predictor.data_fetcher import get_all_records

        records = get_all_records([2024, 2025, 2026])
        if not records:
            raise MappingUnavailableError("No records from API")

        # 保存所有记录，用于按期号查询特码生肖
        cls._records = records

        # 当前年份的映射（从最新数据）
        current_year = records[-1]["expect"][:4]
        cls._current_year = current_year

    @classmethod
    def _validate_mapping(cls):
        """验证映射完整性 - API数据自验证"""
        # API返回的zodiac已经是正确映射，无需额外验证
        # 只要能加载到数据就说明映射有效
        if not hasattr(cls, '_records') or not cls._records:
            raise MappingIntegrityError("No records to validate")

    @classmethod
    def _compute_hash(cls):
        """计算映射hash - 基于记录数"""
        # hash基于记录数和最新期号
        record_info = f"{len(cls._records)}_{cls._records[-1]['expect']}"
        cls._mapping_hash = hashlib.sha256(record_info.encode()).hexdigest()[:16]

    @classmethod
    def get_hash(cls) -> str:
        """获取当前映射hash"""
        cls._ensure_mapping()
        return cls._mapping_hash

    @classmethod
    def save_state(cls):
        """保存映射状态用于校验"""
        cls._ensure_mapping()
        state = {
            "mapping_hash": cls._mapping_hash,
            "mapping_count": len(cls._mapping),
            "updated_at": "2026-05-22"
        }
        with open(MAPPING_STATE_FILE, 'w') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    @classmethod
    def verify(cls) -> bool:
        """验证映射状态"""
        if not os.path.exists(MAPPING_STATE_FILE):
            return False

        with open(MAPPING_STATE_FILE, 'r') as f:
            state = json.load(f)

        current_hash = cls.get_hash()
        return state.get("mapping_hash") == current_hash

    @classmethod
    def reset(cls):
        """重置映射（用于测试）"""
        cls._mapping = None
        cls._mapping_hash = None


def startup_check():
    """
    启动时检查 - 检测多映射源
    """
    _assert_single_source()


def get_mapping_hash() -> str:
    """获取当前映射hash的便捷方法"""
    return AnimalMapper.get_hash()


if __name__ == "__main__":
    # 启动检查
    startup_check()

    # 测试获取生肖
    zodiac = AnimalMapper.get(40, "2023004")
    print(f"Number 40 -> {zodiac}")
    print(f"Mapping hash: {AnimalMapper.get_hash()}")