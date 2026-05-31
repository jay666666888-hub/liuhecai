# meta_v2/tests/test_meta_strategy_v2.py
"""MetaStrategyV2 集成测试"""
import pytest
import sys
sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')
from schema import load_standardized
from meta_v2.meta_strategy_v2 import MetaStrategyV2


def test_initialization():
    """测试初始化"""
    df = load_standardized('/home/admin1/liuhecai_strategy_search/truth_dataset.json')
    meta = MetaStrategyV2(df)
    assert meta is not None
    assert len(meta.expert_histories) == 5


def test_predictions():
    """测试预测生成"""
    df = load_standardized('/home/admin1/liuhecai_strategy_search/truth_dataset.json')
    meta = MetaStrategyV2(df)

    # 获取200期的预测
    preds = meta._get_expert_predictions(200)
    assert len(preds) == 5
    for expert in ['Gap', 'Trend', 'Momentum', 'Frequency', 'Color']:
        assert len(preds[expert]) == 6


def test_backtest_small():
    """测试小规模回测"""
    df = load_standardized('/home/admin1/liuhecai_strategy_search/truth_dataset.json')
    meta = MetaStrategyV2(df)

    # 10期回测
    results = meta.run_backtest(start_idx=200, end_idx=210)
    assert len(results) == 10

    # 检查指标
    for r in results:
        assert 'mean_hit_rate' in r
        assert 'rolling_30_hit' in r
        assert 'max_drawdown' in r
        assert 'stability_score' in r


if __name__ == '__main__':
    pytest.main([__file__, '-v'])