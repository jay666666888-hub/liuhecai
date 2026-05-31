#!/usr/bin/env python3
"""
预测器自动发现与注册表

扫描 predictors/active/ 目录，自动发现并加载预测器。
不再使用硬编码的 if/elif 分支。
"""

import os
import sys
import importlib
import json
from pathlib import Path
from typing import Dict, List, Optional

# 预测器基类
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base_predictor import BasePredictor, PredictionResult


class PredictorRegistry:
    """预测器注册表 - 自动发现"""

    _predictors: Dict[str, 'BasePredictor'] = {}
    _metadata: Dict[str, dict] = {}

    @classmethod
    def scan(cls, base_dir: str = None):
        """
        扫描 predictors/ 目录，自动发现预测器

        目录结构:
        predictors/
            active/
                v5/
                    predictor.py   ← 包含 V5Predictor 类
                    metadata.json
                v7/
                ...
        """
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        active_dir = os.path.join(base_dir, 'predictors', 'active')
        if not os.path.exists(active_dir):
            print(f"[Registry] active目录不存在: {active_dir}")
            return

        for version in os.listdir(active_dir):
            version_dir = os.path.join(active_dir, version)
            if not os.path.isdir(version_dir):
                continue

            predictor_file = os.path.join(version_dir, 'predictor.py')
            metadata_file = os.path.join(version_dir, 'metadata.json')

            # 加载 metadata
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    cls._metadata[version] = json.load(f)

            # 加载 predictor
            if os.path.exists(predictor_file):
                cls._load_from_file(version, predictor_file)

    @classmethod
    def _load_from_file(cls, version: str, predictor_file: str):
        """从文件加载预测器"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(f"active_{version}_predictor", predictor_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"active_{version}_predictor"] = module
            spec.loader.exec_module(module)

            # 使用模块内的 BasePredictor（避免导入缓存问题）
            module_bp = getattr(module, 'BasePredictor', None)
            if module_bp is None:
                print(f"[Registry] {version} 模块无 BasePredictor")
                return

            # 查找预测器类（搜索所有继承 BasePredictor 的类）
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type):
                    try:
                        is_sub = issubclass(attr, module_bp) and attr != module_bp
                    except TypeError:
                        is_sub = False
                    if is_sub:
                        cls._predictors[version] = attr
                        print(f"[Registry] 发现预测器: {version} -> {attr_name}")
                        break

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Registry] 加载 {version} 失败: {e}")

    @classmethod
    def get(cls, version: str) -> BasePredictor:
        """获取预测器实例"""
        if version not in cls._predictors:
            raise ValueError(f"Unknown predictor version: {version}")
        return cls._predictors[version](version)

    @classmethod
    def list_versions(cls) -> List[str]:
        """列出所有已注册版本"""
        return list(cls._predictors.keys())

    @classmethod
    def get_metadata(cls, version: str) -> Optional[dict]:
        """获取版本元数据"""
        return cls._metadata.get(version)

    @classmethod
    def list_all_metadata(cls) -> Dict[str, dict]:
        """列出所有版本元数据"""
        return cls._metadata

    @classmethod
    def get_active_versions(cls) -> List[str]:
        """获取活跃版本列表"""
        return [v for v in cls._predictors.keys()
                if cls._metadata.get(v, {}).get('status') == 'active']

    @classmethod
    def get_retired_versions(cls) -> List[str]:
        """获取退役版本列表"""
        return [v for v in cls._predictors.keys()
                if cls._metadata.get(v, {}).get('status') == 'retired']

    @classmethod
    def get_play_type(cls, version: str) -> str:
        """
        获取版本的 play_type

        Raises:
            MetadataError: metadata 缺少 play_type 字段
        """
        meta = cls._metadata.get(version, {})
        play_type = meta.get("play_type")
        if play_type is None:
            from validators import MetadataError
            raise MetadataError(f"Version '{version}' metadata 缺少 play_type 字段")
        return play_type

    @classmethod
    def get_validator(cls, version: str):
        """
        获取版本的验证器

        Returns:
            BaseValidator 实例
        """
        from validators import get_validator
        play_type = cls.get_play_type(version)
        return get_validator(play_type)

    @classmethod
    def evaluate(cls, version: str, prediction: list, actual_list: list, actual: str = None) -> bool:
        """
        使用对应验证器评估预测是否命中

        Args:
            version: 版本号
            prediction: 预测的生肖列表
            actual_list: 开奖的生肖列表
            actual: 特码（用于六肖验证）

        Returns:
            是否命中
        """
        validator = cls.get_validator(version)
        return validator.evaluate(prediction, actual_list, actual)


def load_all_predictors(base_dir: str = None) -> PredictorRegistry:
    """
    加载所有预测器

    Returns:
        PredictorRegistry 实例
    """
    registry = PredictorRegistry()
    registry.scan(base_dir)
    return registry


if __name__ == '__main__':
    # 测试自动发现
    registry = load_all_predictors()
    print(f"\n已注册版本: {registry.list_versions()}")
    print(f"活跃版本: {registry.get_active_versions()}")

    for version in registry.list_versions():
        meta = registry.get_metadata(version)
        play_type = registry.get_play_type(version)
        print(f"  {version}: strategy={meta.get('strategy_type', 'unknown') if meta else 'no metadata'}, play_type={play_type}")

    # 测试实例化
    for version in registry.list_versions()[:2]:
        p = registry.get(version)
        print(f"\n实例化 {version}: {p}")

    # 测试验证器
    print("\n验证器测试:")
    for version in registry.list_versions()[:5]:
        validator = registry.get_validator(version)
        print(f"  {version} -> validator: {validator.name}")