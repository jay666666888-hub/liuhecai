#!/usr/bin/env python3
"""
六合数据整理工具
- 标准化开奖数据结构
- 生成玩法规则说明
- 输出优化后的数据
"""

import json
from datetime import datetime

# ============ 玩法规则定义 ============
RULES = """
# 六合玩法规则

## 基本信息
- **游戏类型**: 澳门六合（乐透型）
- **开奖频率**: 每天一期
- **开奖时间**: 21:32 (北京时间)

## 投注选项

### 特码
- 从1-49中选择1个号码
- 赔率: 1:49

### 六肖
- 从12生肖中选择最多6个生肖
- 开奖结果为7个号码，对应7个生肖
- 只要6肖中有任意一个出现在开奖结果中即算中奖

### 波色
- 红波: 01,02,07,08,12,13,18,19,23,24,29,30,34,35,40,45,46
- 蓝波: 03,04,09,10,14,15,20,25,26,31,36,37,41,42,47,48
- 绿波: 05,06,11,16,17,21,22,27,28,32,33,38,39,43,44,49

### 生肖对应
- 鼠: 02,14,26,38
- 牛: 01,13,25,37,49
- 虎: 12,24,36,48
- 兔: 11,23,35,47
- 龍: 10,22,34,46
- 蛇: 09,21,33,45
- 马: 08,20,32,44
- 羊: 07,19,31,43
- 猴: 06,18,30,42
- 雞: 05,17,29,41
- 狗: 04,16,28,40
- 豬: 03,15,27,39

## 数据格式说明

每条开奖记录包含:
- `period`: 期号 (如 "2025001")
- `date`: 开奖日期
- `draw_numbers`: 开奖的7个号码列表
- `special_number`: 特码 (第7个号码)
- `zodiacs`: 7个生肖列表
- `special_zodiac`: 特码生肖
- `colors`: 7个波色列表
- `special_color`: 特码波色

## 预测策略说明

### 排名法 (Rank-based)
将特征转成排名(0~11)，加权求和避免异常值影响

### 遗漏追踪
追踪每个生肖/号码的遗漏期数

### 冷热分析
统计近期出现频率

### 组合策略
结合多种特征进行综合评分
"""

# ============ 数据转换 ============
def convert_record(r):
    """将原数据转换为标准格式"""
    return {
        'period': r['期号'],
        'date': r['开奖时间'].split(' ')[0],
        'draw_numbers': r['开奖号码'],
        'special_number': r['特码号码'],
        'zodiacs': r['开奖生肖'],
        'special_zodiac': r['特码生肖'],
        'colors': r['波色列表'],
        'special_color': r['波色'],
    }

def convert_data(input_file, output_file):
    """转换所有数据"""
    with open(input_file) as f:
        raw = json.load(f)

    converted = [convert_record(r) for r in raw]

    with open(output_file, 'w') as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)

    print(f"转换完成: {len(converted)} 条记录")
    print(f"时间范围: {converted[0]['period']} ~ {converted[-1]['period']}")

    return converted

def generate_summary(data):
    """生成数据摘要"""
    # 统计各生肖出现次数
    zodiac_count = {}
    color_count = {}
    number_count = {}

    for r in data:
        # 特码统计
        z = r['special_zodiac']
        zodiac_count[z] = zodiac_count.get(z, 0) + 1

        c = r['special_color']
        color_count[c] = color_count.get(c, 0) + 1

        n = r['special_number']
        number_count[n] = number_count.get(n, 0) + 1

    summary = {
        'total_records': len(data),
        'period_range': f"{data[0]['period']} ~ {data[-1]['period']}",
        'date_range': f"{data[0]['date']} ~ {data[-1]['date']}",
        'zodiac_distribution': zodiac_count,
        'color_distribution': color_count,
        'number_distribution': dict(sorted(number_count.items(), key=lambda x: int(x[0]))),
    }

    return summary

# ============ 主程序 ============
if __name__ == '__main__':
    import sys

    INPUT = '/home/admin1/liuhecai_data.json'
    OUTPUT = '/home/admin1/liuhecai_standard.json'

    data = convert_data(INPUT, OUTPUT)
    summary = generate_summary(data)

    with open('/home/admin1/liuhecai_summary.json', 'w') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n摘要:")
    print(f"  总记录数: {summary['total_records']}")
    print(f"  时间范围: {summary['period_range']}")
    print(f"  生肖分布: {summary['zodiac_distribution']}")
    print(f"  波色分布: {summary['color_distribution']}")

    # 保存玩法规则
    with open('/home/admin1/liuhecai_rules.md', 'w') as f:
        f.write(RULES)
    print(f"\n玩法规则已保存到: /home/admin1/liuhecai_rules.md")
    print(f"标准化数据已保存到: {OUTPUT}")