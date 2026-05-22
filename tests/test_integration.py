#!/usr/bin/env python3
"""集成测试"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import get_all_records, extract_zodiac_mapping, build_standard_records
from predictor.predictor import predict_next, verify_prediction
from predictor.config import load_strategy, save_strategy, load_verification_state

def test_full_pipeline():
    """测试完整流程"""
    # 1. 获取数据
    records = get_all_records([2024, 2025])
    assert len(records) > 0

    # 2. 构建标准记录
    mapping = extract_zodiac_mapping(records)
    standard = build_standard_records(records, mapping)
    assert len(standard) > 0
    assert "特码生肖" in standard[0]

    # 3. 预测
    next_period, top6, scores = predict_next(standard)
    assert len(top6) == 6
    assert next_period > standard[-1]["期号"]

    # 4. 验证配置
    strategy = load_strategy()
    assert "weights" in strategy

    state = load_verification_state()
    assert "pending_period" in state

    print("集成测试通过!")

if __name__ == "__main__":
    test_full_pipeline()