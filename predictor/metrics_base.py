#!/usr/bin/env python3
"""
Metrics Base Class - Enforces source filtering contract

所有 metrics 计算必须继承此类，自动过滤 source_scope
禁止手动过滤 - 由基类保证
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set


# 全局常量：允许的 live 数据源
ALLOWED_LIVE_SOURCES: Set[str] = {"live", "live_update"}

# 回测数据源（仅用于分析，不用于 live metrics）
BACKTEST_SOURCES: Set[str] = {"backtest"}


class MetricsComputer(ABC):
    """
    Metrics 计算基类

    使用方法：
        class MyMetrics(MetricsComputer):
            def _compute_impl(self, filtered_records):
                # filtered_records 已经过滤了 source
                ...

    示例：
        computer = MyMetrics()
        result = computer.compute(raw_records)  # 自动过滤
    """

    def compute(self, records: List[Dict], source_scope: Set[str] = None) -> Any:
        """
        主入口：过滤 + 计算

        Args:
            records: 原始记录列表（从 aggregated_live.jsonl 读取）
            source_scope: 可选，默认 ALLOWED_LIVE_SOURCES

        Returns:
            子类实现的计算结果
        """
        if source_scope is None:
            source_scope = ALLOWED_LIVE_SOURCES

        filtered = [r for r in records if r.get("source") in source_scope]
        return self._compute_impl(filtered)

    @abstractmethod
    def _compute_impl(self, filtered_records: List[Dict]) -> Any:
        """
        子类实现：接收已过滤的 live 记录

        Args:
            filtered_records: 只包含 source_scope 内的记录

        Returns:
            计算结果（类型由子类定义）
        """
        pass


class LiveMetricsComputer(MetricsComputer):
    """
    Live 指标计算器（默认）

    自动过滤：source in {"live", "live_update"}
    """

    def _compute_impl(self, filtered_records: List[Dict]) -> Dict[str, Any]:
        """计算 live 相关指标"""
        raise NotImplementedError


class BacktestMetricsComputer(MetricsComputer):
    """
    Backtest 指标计算器

    自动过滤：source in {"backtest"}
    """

    def _compute_impl(self, filtered_records: List[Dict]) -> Dict[str, Any]:
        """计算 backtest 相关指标"""
        raise NotImplementedError