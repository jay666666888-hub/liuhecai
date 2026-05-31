#!/usr/bin/env python3
"""
Phase 3A: 验证扫描
检查所有 active 版本的 metadata 和 validator 配置
"""
import sys
import os
from typing import Dict, List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from predictor.predictor_registry import load_all_predictors
from predictor.validators import ValidatorRegistry

ALLOWED_PLAY_TYPES = {"liuhe", "pingte_yixiao"}


class ValidationError(Exception):
    """验证错误"""
    pass


class MetadataValidator:
    """元数据验证器"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def validate_all(self) -> bool:
        """
        执行全量验证

        Returns:
            是否全部通过
        """
        print("=" * 60)
        print("Phase 3A: 验证扫描")
        print("=" * 60)

        # 1. 加载所有预测器
        print("\n[1/6] 加载预测器...")
        try:
            registry = load_all_predictors()
            versions = registry.list_versions()
            print(f"  已注册版本: {versions}")
            if not versions:
                self.add_error("没有发现任何预测器")
                return False
        except Exception as e:
            self.add_error(f"加载预测器失败: {e}")
            return False

        # 2. 检查每个版本都有 metadata
        print("\n[2/6] 检查 metadata 存在性...")
        for version in versions:
            meta = registry.get_metadata(version)
            if meta is None:
                self.add_error(f"  {version}: 缺少 metadata.json")
            else:
                print(f"  {version}: OK")

        # 3. 检查 metadata 都有 play_type
        print("\n[3/6] 检查 play_type 字段...")
        for version in versions:
            meta = registry.get_metadata(version)
            if meta is None:
                continue
            play_type = meta.get("play_type")
            if play_type is None:
                self.add_error(f"  {version}: metadata 缺少 play_type 字段")
            elif play_type == "__legacy__":
                self.add_warning(f"  {version}: play_type='__legacy__'，应该迁移")
            else:
                print(f"  {version}: play_type={play_type}")

        # 4. 检查 play_type 属于允许枚举
        print("\n[4/6] 检查 play_type 枚举值...")
        for version in versions:
            meta = registry.get_metadata(version)
            if meta is None:
                continue
            play_type = meta.get("play_type")
            if play_type and play_type not in ALLOWED_PLAY_TYPES:
                self.add_error(f"  {version}: play_type='{play_type}' 不在允许列表 {ALLOWED_PLAY_TYPES}")
            elif play_type in ALLOWED_PLAY_TYPES:
                print(f"  {version}: {play_type} ✓")

        # 5. 检查 validator 可注册
        print("\n[5/6] 检查 validator 可实例化...")
        for version in versions:
            meta = registry.get_metadata(version)
            if meta is None:
                continue
            play_type = meta.get("play_type")
            if not play_type:
                continue
            try:
                validator = ValidatorRegistry.get(play_type)
                print(f"  {version} ({play_type}): {validator.name} ✓")
            except Exception as e:
                self.add_error(f"  {version}: validator.get('{play_type}') 失败: {e}")

        # 6. 检查 play_type ↔ validator 一一对应
        print("\n[6/6] 检查 play_type ↔ validator 映射...")
        for play_type in ALLOWED_PLAY_TYPES:
            try:
                validator = ValidatorRegistry.get(play_type)
                print(f"  {play_type} -> {validator.name} ✓")
            except Exception as e:
                self.add_error(f"  {play_type}: 无法获取 validator: {e}")

        # 输出结果
        print("\n" + "=" * 60)
        if self.errors:
            print(f"❌ 验证失败，发现 {len(self.errors)} 个错误:")
            for e in self.errors:
                print(f"  - {e}")
        else:
            print("✅ 验证通过")

        if self.warnings:
            print(f"\n⚠️  警告 ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"  - {w}")

        print("=" * 60)
        return len(self.errors) == 0


def run_validation() -> bool:
    """运行验证，返回是否通过"""
    validator = MetadataValidator()
    passed = validator.validate_all()

    # 如果有错误，返回非零退出码
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    run_validation()