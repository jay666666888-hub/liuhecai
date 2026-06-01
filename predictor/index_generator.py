#!/usr/bin/env python3
"""
index.json 自动生成器

从 predictors/active/ 目录扫描元数据，自动生成 index.json。
不再需要人工维护。
"""

import json
import os
from datetime import datetime
from pathlib import Path


ALLOWED_PLAY_TYPES = {"liuhe", "pingte_yixiao", "number_selection"}


def generate_index(base_dir: str = None) -> dict:
    """
    扫描 predictors/active/ 和 predictors/retired/ 目录，生成 index 结构

    单一数据源：
    - predictor/predictors/active/ → 活跃版本
    - predictor/predictors/retired/ → 退役版本（.json文件）

    version_book/ 仅用于账本数据，不再存储元数据。

    Returns:
        index dict {
            "active": [...],
            "active_by_play_type": {"liuhe": [...], "pingte_yixiao": [...]},
            "retired": [...],
            "experimental": [...],
            "versions": [...],
            "updated_at": "..."
        }
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    active_dir = os.path.join(base_dir, 'predictor', 'predictors', 'active')
    retired_dir = os.path.join(base_dir, 'predictor', 'predictors', 'retired')

    active_versions = []
    retired_versions = []
    active_by_play_type = {"liuhe": [], "pingte_yixiao": [], "number_selection": []}

    # 扫描 active/ 目录
    if os.path.exists(active_dir):
        for version in os.listdir(active_dir):
            version_dir = os.path.join(active_dir, version)
            if not os.path.isdir(version_dir):
                continue

            metadata_file = os.path.join(version_dir, 'metadata.json')
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                status = metadata.get('status', 'active')
                if status == 'retired':
                    retired_versions.append({
                        "version": version,
                        "status": "retired",
                        "play_type": metadata.get('play_type'),
                        "reason": metadata.get('notes', '') or '已退役',
                        "strategy_type": metadata.get('strategy_type'),
                        "hit_rate": metadata.get('hit_rate'),
                        "notes": metadata.get('notes')
                    })
                else:
                    active_versions.append(version)
                    # 按 play_type 分组
                    play_type = metadata.get('play_type')
                    if play_type in active_by_play_type:
                        active_by_play_type[play_type].append(version)

    # 扫描 retired/ 目录（.json文件）
    if os.path.exists(retired_dir):
        for filename in os.listdir(retired_dir):
            if not filename.endswith('.json'):
                continue
            version = filename[:-5]  # 去掉 .json 后缀
            metadata_file = os.path.join(retired_dir, filename)
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            retired_versions.append({
                "version": version,
                "status": "retired",
                "play_type": metadata.get('play_type'),
                "reason": metadata.get('notes', '') or metadata.get('retire_reason', '已退役'),
                "strategy_type": metadata.get('strategy_type'),
                "hit_rate": metadata.get('hit_rate'),
                "notes": metadata.get('notes')
            })

    # Sort
    active_versions.sort()
    for pt in active_by_play_type:
        active_by_play_type[pt].sort()
    retired_versions.sort(key=lambda x: x['version'] if isinstance(x, dict) else x)

    return {
        "_comment": "Auto-generated, do not edit manually",
        "active": active_versions,
        "active_by_play_type": active_by_play_type,
        "retired": retired_versions,
        "experimental": [],
        "versions": active_versions + [r['version'] if isinstance(r, dict) else r for r in retired_versions],
        "updated_at": datetime.now().isoformat()
    }


def write_index(base_dir: str = None):
    """生成并写入 index.json"""
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    index = generate_index(base_dir)
    index_file = os.path.join(base_dir, 'version_book', 'index.json')

    # 确保 version_book 目录存在
    os.makedirs(os.path.dirname(index_file), exist_ok=True)

    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"[Index] 生成 index.json: active={index['active']}, retired={len(index['retired'])}")
    print(f"  active_by_play_type: {index['active_by_play_type']}")
    return index


if __name__ == '__main__':
    # 测试
    index = write_index()
    print(f"Generated index: {json.dumps(index, indent=2)}")