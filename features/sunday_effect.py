#!/usr/bin/env python3
"""
周日效应特征

不是预测器，是信号源。
计算每个生肖的周日效应得分，用于调整预测权重。
"""

import datetime
from typing import List, Dict, Optional

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']


class SundayEffectFeature:
    """周日效应特征计算器"""

    def __init__(self):
        self.name = "sunday_effect"

    def get_weekday(self, record: Dict) -> Optional[int]:
        """获取开奖日期的星期几"""
        try:
            dt = datetime.datetime.strptime(record.get('开奖时间', ''), '%Y-%m-%d %H:%M:%S')
            return dt.weekday()  # 0=周一, 6=周日
        except:
            return None

    def compute_gap_scores(self, history: List[Dict]) -> Dict[str, float]:
        """计算各生肖的遗漏值（归一化）"""
        n = len(history)
        last_appear = {}

        for i, r in enumerate(history):
            z = r.get('特码生肖')
            last_appear[z] = i

        gaps = {z: n - last_appear.get(z, -1) - 1 for z in ZODIACS}
        max_gap = max(gaps.values()) if gaps else 1

        return {z: gaps[z] / max_gap for z in ZODIACS}

    def compute(self, history: List[Dict], is_sunday: bool = None) -> Dict[str, float]:
        """
        计算周日效应得分

        Args:
            history: 历史记录列表
            is_sunday: 是否周日（自动检测 if None）

        Returns:
            每个生肖的周日效应得分
        """
        if is_sunday is None:
            if history:
                is_sunday = self.get_weekday(history[-1]) == 6
            else:
                is_sunday = False

        gap_scores = self.compute_gap_scores(history)

        if is_sunday:
            # 周日：增加gap权重（gap在周日更有效）
            return {z: gap_scores.get(z, 0) * 1.2 for z in ZODIACS}
        else:
            # 非周日：正常分数
            return gap_scores

    def is_sunday_draw(self, record: Dict) -> bool:
        """判断是否为周日开奖"""
        return self.get_weekday(record) == 6

    def get_sunday_stats(self, records: List[Dict]) -> Dict:
        """统计周日 vs 非周日的表现差异"""
        sunday_hits = 0
        sunday_total = 0
        weekday_hits = 0
        weekday_total = 0

        for r in records:
            wd = self.get_weekday(r)
            if wd is None:
                continue

            if wd == 6:
                sunday_total += 1
            else:
                weekday_total += 1

        return {
            "sunday_count": sunday_total,
            "weekday_count": weekday_total,
            "sunday_ratio": sunday_total / (sunday_total + weekday_total) if (sunday_total + weekday_total) > 0 else 0
        }


def compute_sunday_adjustment(history: List[Dict]) -> float:
    """
    快捷函数：计算周日调整系数

    如果近期是周日，返回1.2（增加gap权重）
    否则返回1.0
    """
    feature = SundayEffectFeature()
    is_sunday = feature.get_weekday(history[-1]) == 6 if history else False
    return 1.2 if is_sunday else 1.0


if __name__ == "__main__":
    # 测试
    from predictor.data_fetcher import get_all_records, build_standard_records

    records = get_all_records([2024, 2025, 2026])
    standard = build_standard_records(records)

    feature = SundayEffectFeature()
    stats = feature.get_sunday_stats(standard)

    print(f"周日开奖: {stats['sunday_count']} 期")
    print(f"非周日开奖: {stats['weekday_count']} 期")
    print(f"周日比例: {stats['sunday_ratio']*100:.1f}%")

    # 测试周日效应计算
    gap_scores = feature.compute(standard[-100:])
    print(f"\n最近100期gap分数: {list(gap_scores.items())[:3]}")