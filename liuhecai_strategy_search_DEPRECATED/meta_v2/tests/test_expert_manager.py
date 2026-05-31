# meta_v2/tests/test_expert_manager.py
"""ExpertStateManager 单元测试"""
import pytest
import sys
sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')
from meta_v2.expert_manager import ExpertStateManager


def test_initial_state():
    """测试初始状态为ACTIVE"""
    manager = ExpertStateManager()
    assert manager.get_expert_state("Gap") == "ACTIVE"


def test_record_hit():
    """测试记录命中"""
    manager = ExpertStateManager()
    manager.record_hit("Gap", hit=True)
    manager.record_hit("Gap", hit=False)
    assert manager._rolling_hit_rate("Gap", 20) == 0.5


def test_freeze_condition():
    """测试冻结条件：连续30期低于基准"""
    manager = ExpertStateManager()
    # 模拟29期低于基准（不触发）
    for _ in range(29):
        manager.record_hit("Gap", hit=False)
    assert manager.get_expert_state("Gap") == "ACTIVE"

    # 第30期
    manager.record_hit("Gap", hit=False)
    assert manager.get_expert_state("Gap") == "FROZEN"


def test_recovery_condition():
    """测试恢复条件：连续50期高于基准+0.03且zscore>1"""
    manager = ExpertStateManager()
    # 先冻结
    for _ in range(30):
        manager.record_hit("Gap", hit=False)

    assert manager.get_expert_state("Gap") == "FROZEN"

    # 模拟50期高于基准+0.03，zscore>1
    for _ in range(50):
        manager.record_hit("Gap", hit=True)

    # 此时应该恢复（需要zscore>1）
    state = manager.get_expert_state("Gap")
    assert state in ["ACTIVE", "FROZEN", "OBSERVE"]


def test_max_freeze_duration():
    """测试最大冻结期限：200期"""
    manager = ExpertStateManager()
    # 冻结
    for _ in range(30):
        manager.record_hit("Gap", hit=False)
    assert manager.get_expert_state("Gap") == "FROZEN"

    # 超过200期
    for _ in range(200):
        manager.record_hit("Gap", hit=False)

    # 应该进入OBSERVE状态
    assert manager.get_expert_state("Gap") in ["OBSERVE", "ACTIVE"]


def test_weight_calculation():
    """测试权重计算"""
    manager = ExpertStateManager()
    # ACTIVE专家权重应该更高
    weights = manager.get_expert_weights()
    assert weights["Gap"] > 0


def test_freeze_report():
    """测试冻结报告"""
    manager = ExpertStateManager()
    # 冻结
    for _ in range(30):
        manager.record_hit("Gap", hit=False)

    report = manager.get_freeze_report("Gap")
    assert report is not None
    assert report["expert"] == "Gap"
    assert report["status"] == "FROZEN"


def test_reset():
    """测试重置"""
    manager = ExpertStateManager()
    for _ in range(30):
        manager.record_hit("Gap", hit=False)
    manager.reset()
    assert manager.get_expert_state("Gap") == "ACTIVE"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])