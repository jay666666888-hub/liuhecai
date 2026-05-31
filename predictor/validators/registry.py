#!/usr/bin/env python3
"""
澳门六合 - 验证器注册表
负责根据 play_type 分发到对应的验证器
"""
from typing import Dict
from .base_validator import BaseValidator
from .liuhe_validator import LiuheValidator
from .pingte_yixiao_validator import PingteYixiaoValidator
from .special_24ma_validator import Special24maValidator

ALLOWED_PLAY_TYPES = {"liuhe", "pingte_yixiao", "special_24ma"}


class MetadataError(Exception):
    """元数据错误"""
    pass


class ValidatorRegistry:
    """验证器注册表"""

    _validators: Dict[str, BaseValidator] = {}
    _initialized = False

    @classmethod
    def _init(cls):
        """初始化注册表"""
        if cls._initialized:
            return
        cls._validators = {
            "liuhe": LiuheValidator(),
            "pingte_yixiao": PingteYixiaoValidator(),
            "special_24ma": Special24maValidator(),
        }
        cls._initialized = True

    @classmethod
    def get(cls, play_type: str) -> BaseValidator:
        """
        根据 play_type 获取验证器

        Args:
            play_type: 玩法类型

        Returns:
            对应的验证器实例

        Raises:
            MetadataError: 未知的 play_type
        """
        cls._init()
        if play_type not in ALLOWED_PLAY_TYPES:
            raise MetadataError(f"Unknown play_type: '{play_type}'. Allowed: {ALLOWED_PLAY_TYPES}")
        return cls._validators[play_type]

    @classmethod
    def register(cls, play_type: str, validator: BaseValidator):
        """手动注册验证器"""
        cls._init()
        if play_type not in ALLOWED_PLAY_TYPES:
            raise MetadataError(f"Cannot register unknown play_type: {play_type}")
        cls._validators[play_type] = validator

    @classmethod
    def list_play_types(cls) -> list:
        """列出所有已注册的玩法类型"""
        cls._init()
        return list(cls._validators.keys())


def get_validator(play_type: str) -> BaseValidator:
    """便捷函数：获取验证器"""
    return ValidatorRegistry.get(play_type)