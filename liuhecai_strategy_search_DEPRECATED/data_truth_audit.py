#!/usr/bin/env python3
"""
数据真实验证 (Data Truth Audit)
==============================

原则：
- 所有数据以真实开奖号码为唯一基准
- 任何衍生数据（生肖、波色、五行）必须由开奖号码自动计算
- 禁止手工维护映射

检查项：
1. 原始数据校验 - 逐期对比原始值 vs 计算值
2. 全量重算 - 从870期号码重新生成所有衍生数据
3. 数据完整性 - 检查重复、缺失、空值、非法号码
4. 抽样人工验证 - 随机50期供人工核对
5. 最终输出audit_status
"""

import sys
import os
import json
import random
from datetime import datetime
from collections import Counter

import pandas as pd
import numpy as np

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

# ============ 标准映射（固定规则）============
# 生肖对应：1=鼠, 2=牛, 3=虎, 4=兔, 5=龍, 6=蛇, 7=马, 8=羊, 9=猴, 10=雞, 11=狗, 12=豬
ZODIAC_MAP = {
    1: '鼠', 2: '牛', 3: '虎', 4: '兔', 5: '龍', 6: '蛇',
    7: '马', 8: '羊', 9: '猴', 10: '雞', 11: '狗', 12: '豬'
}

# 波色对应
COLOR_MAP = {
    'red': [1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46],
    'blue': [3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48],
    'green': [5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49]
}

# 五行对应
WUXING_MAP = {
    '金': [17, 18, 21, 22, 29, 30, 37, 38],
    '木': [13, 14, 21, 22, 27, 28, 35, 36],
    '水': [11, 12, 19, 20, 27, 28, 33, 34],
    '火': [5, 6, 13, 14, 23, 24, 31, 32],
    '土': [49, 1, 2, 9, 10, 41, 42, 49]
}

def number_to_zodiac(num):
    """号码 → 生肖"""
    n = int(num) % 12
    if n == 0:
        n = 12
    return ZODIAC_MAP[n]

def number_to_color(num):
    """号码 → 波色"""
    n = int(num)
    for color, nums in COLOR_MAP.items():
        if n in nums:
            return color
    return 'unknown'

def number_to_wuxing(num):
    """号码 → 五行"""
    n = int(num)
    for wx, nums in WUXING_MAP.items():
        if n in nums:
            return wx
    return 'unknown'

def number_to_size(num):
    """号码 → 大小"""
    n = int(num)
    return '大' if n > 24 else '小'

def number_to_parity(num):
    """号码 → 单双"""
    n = int(num)
    return '单' if n % 2 == 1 else '双'

def number_to_tail(num):
    """号码 → 尾数"""
    return int(num) % 10

# ============ 加载原始数据 ============
def load_raw_data():
    """加载原始数据"""
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    df = df.sort_values('period').reset_index(drop=True)

    print(f"[数据] {len(df)} 条记录")
    print(f"  期号范围: {df['period'].iloc[0]} ~ {df['period'].iloc[-1]}")

    return df

# ============ 1. 原始数据校验 ============
def validate_original_data(df):
    """
    逐期对比：
    - 原始特码生肖 VS 计算生肖
    - 原始波色 VS 计算波色
    - 原始五行 VS 计算五行
    """
    print("\n[1] 原始数据校验...")

    mismatches = []
    checks = {
        'zodiac': {'total': 0, 'mismatch': 0, 'samples': []},
        'color': {'total': 0, 'mismatch': 0, 'samples': []},
        'wuxing': {'total': 0, 'mismatch': 0, 'samples': []},
    }

    for idx, row in df.iterrows():
        period = row['period']
        raw_num = row['special_number']

        # 计算值
        calc_zodiac = number_to_zodiac(raw_num)
        calc_color = number_to_color(raw_num)
        calc_wuxing = number_to_wuxing(raw_num)

        # 原始值
        raw_zodiac = row.get('special_zodiac', '')
        raw_color = row.get('special_color', '')
        raw_wuxing = row.get('special_wuxing', '')

        # 对比生肖
        checks['zodiac']['total'] += 1
        if raw_zodiac != calc_zodiac:
            checks['zodiac']['mismatch'] += 1
            mismatches.append({
                'issue': 'zodiac_mismatch',
                'period': str(period),
                'raw': raw_zodiac,
                'calculated': calc_zodiac,
                'number': raw_num
            })
            if len(checks['zodiac']['samples']) < 5:
                checks['zodiac']['samples'].append({
                    'period': str(period),
                    'raw': raw_zodiac,
                    'calculated': calc_zodiac,
                    'number': raw_num
                })

        # 对比波色
        checks['color']['total'] += 1
        if raw_color != calc_color:
            checks['color']['mismatch'] += 1
            mismatches.append({
                'issue': 'color_mismatch',
                'period': str(period),
                'raw': raw_color,
                'calculated': calc_color,
                'number': raw_num
            })
            if len(checks['color']['samples']) < 5:
                checks['color']['samples'].append({
                    'period': str(period),
                    'raw': raw_color,
                    'calculated': calc_color,
                    'number': raw_num
                })

        # 对比五行
        checks['wuxing']['total'] += 1
        if raw_wuxing != calc_wuxing:
            checks['wuxing']['mismatch'] += 1
            mismatches.append({
                'issue': 'wuxing_mismatch',
                'period': str(period),
                'raw': raw_wuxing,
                'calculated': calc_wuxing,
                'number': raw_num
            })
            if len(checks['wuxing']['samples']) < 5:
                checks['wuxing']['samples'].append({
                    'period': str(period),
                    'raw': raw_wuxing,
                    'calculated': calc_wuxing,
                    'number': raw_num
                })

    # 输出结果
    print(f"    生肖: {checks['zodiac']['mismatch']}/{checks['zodiac']['total']} 不一致")
    print(f"    波色: {checks['color']['mismatch']}/{checks['color']['total']} 不一致")
    print(f"    五行: {checks['wuxing']['mismatch']}/{checks['wuxing']['total']} 不一致")

    # 保存不匹配记录
    if mismatches:
        with open('/home/admin1/liuhecai_strategy_search/mapping_mismatch.json', 'w', encoding='utf-8') as f:
            json.dump(mismatches, f, ensure_ascii=False, indent=2)
        print(f"    保存不匹配记录: mapping_mismatch.json ({len(mismatches)}条)")

    return checks, mismatches

# ============ 2. 全量重算 ============
def rebuild_all_data(df):
    """从原始号码重新生成所有衍生数据"""
    print("\n[2] 全量重算...")

    # 重新计算所有字段
    df_rebuilt = df.copy()

    # 核心字段
    df_rebuilt['calc_zodiac'] = df_rebuilt['special_number'].apply(number_to_zodiac)
    df_rebuilt['calc_color'] = df_rebuilt['special_number'].apply(number_to_color)
    df_rebuilt['calc_wuxing'] = df_rebuilt['special_number'].apply(number_to_wuxing)
    df_rebuilt['calc_size'] = df_rebuilt['special_number'].apply(number_to_size)
    df_rebuilt['calc_parity'] = df_rebuilt['special_number'].apply(number_to_parity)
    df_rebuilt['calc_tail'] = df_rebuilt['special_number'].apply(number_to_tail)

    # 统计
    stats = {
        'total_records': len(df_rebuilt),
        'zodiac_distribution': df_rebuilt['calc_zodiac'].value_counts().to_dict(),
        'color_distribution': df_rebuilt['calc_color'].value_counts().to_dict(),
        'wuxing_distribution': df_rebuilt['calc_wuxing'].value_counts().to_dict(),
        'size_distribution': df_rebuilt['calc_size'].value_counts().to_dict(),
        'parity_distribution': df_rebuilt['calc_parity'].value_counts().to_dict(),
        'tail_distribution': df_rebuilt['calc_tail'].value_counts().to_dict(),
    }

    # 覆盖原始数据
    df_rebuilt['special_zodiac'] = df_rebuilt['calc_zodiac']
    df_rebuilt['special_color'] = df_rebuilt['calc_color']
    df_rebuilt['special_wuxing'] = df_rebuilt['calc_wuxing']
    df_rebuilt['special_size'] = df_rebuilt['calc_size']
    df_rebuilt['special_parity'] = df_rebuilt['calc_parity']
    df_rebuilt['special_tail'] = df_rebuilt['calc_tail']

    # 保存重建数据
    output_df = df_rebuilt[['period', 'date', 'special_number',
                           'special_zodiac', 'special_color', 'special_wuxing',
                           'special_size', 'special_parity', 'special_tail']]
    output_df.to_json('/home/admin1/liuhecai_strategy_search/liuhecai_rebuilt.json', orient='records', force_ascii=False, indent=2)

    # 保存报告
    report = {
        'timestamp': datetime.now().isoformat(),
        'records_rebuilt': len(df_rebuilt),
        'distributions': {
            'zodiac': stats['zodiac_distribution'],
            'color': stats['color_distribution'],
            'wuxing': stats['wuxing_distribution'],
            'size': stats['size_distribution'],
            'parity': stats['parity_distribution'],
            'tail': stats['tail_distribution'],
        }
    }

    with open('/home/admin1/liuhecai_strategy_search/rebuild_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"    重建记录: {stats['total_records']}")
    print(f"    生肖分布: {stats['zodiac_distribution']}")
    print(f"    波色分布: {stats['color_distribution']}")
    print(f"    五行分布: {stats['wuxing_distribution']}")
    print(f"    保存: liuhecai_rebuilt.json")

    return df_rebuilt

# ============ 3. 数据完整性 ============
def check_data_integrity(df):
    """检查数据完整性"""
    print("\n[3] 数据完整性检查...")

    issues = []
    details = {}

    # 重复期号
    dup_periods = df[df['period'].duplicated()]['period'].tolist()
    if dup_periods:
        issues.append(f'重复期号: {len(dup_periods)}个')
        details['duplicate_periods'] = dup_periods

    # 期号格式检查
    df['year'] = df['period'].astype(str).str[:4].astype(int)
    df['seq'] = df['period'].astype(str).str[4:].astype(int)

    # 缺失期号
    missing_periods = []
    for year in df['year'].unique():
        year_data = df[df['year'] == year]
        max_seq = year_data['seq'].max()
        if max_seq < 150:  # 假设每年最多150期
            expected = set(range(1, max_seq + 1))
            actual = set(year_data['seq'].tolist())
            missing = sorted(expected - actual)
            if missing:
                missing_periods.append({str(year): missing[:20]})  # 只显示前20个

    if missing_periods:
        issues.append(f'缺失期号: {len(missing_periods)}个年份')
        details['missing_periods'] = missing_periods

    # 空值检查
    null_counts = df[['period', 'date', 'special_number', 'special_zodiac']].isnull().sum().to_dict()
    null_fields = [k for k, v in null_counts.items() if v > 0]
    if null_fields:
        issues.append(f'空值字段: {null_fields}')
        details['null_counts'] = null_counts

    # 非法号码
    nums = pd.to_numeric(df['special_number'], errors='coerce')
    invalid = nums[(nums < 1) | (nums > 49)]
    if len(invalid) > 0:
        issues.append(f'非法号码(<1或>49): {len(invalid)}条')
        details['invalid_numbers'] = invalid.tolist()

    # 超范围号码（非整数）
    non_integer = df[df['special_number'].apply(lambda x: not str(x).isdigit())]
    if len(non_integer) > 0:
        issues.append(f'非整数号码: {len(non_integer)}条')
        details['non_integer'] = non_integer['special_number'].tolist()[:10]

    # 重复开奖（同一期号，不同号码）
    dup_special = df.groupby('period')['special_number'].nunique()
    dup_special = dup_special[dup_special > 1]
    if len(dup_special) > 0:
        issues.append(f'重复开奖期号: {len(dup_special)}个')
        details['duplicate_special'] = dup_special.to_dict()

    integrity = {
        'total_records': len(df),
        'issues_found': len(issues),
        'issues': issues if issues else ['无'],
        'details': details,
        'date_range': f"{df['period'].iloc[0]} ~ {df['period'].iloc[-1]}",
    }

    with open('/home/admin1/liuhecai_strategy_search/integrity_report.json', 'w', encoding='utf-8') as f:
        json.dump(integrity, f, ensure_ascii=False, indent=2)

    print(f"    总记录: {integrity['total_records']}")
    print(f"    问题数量: {integrity['issues_found']}")
    if issues:
        for issue in issues:
            print(f"      - {issue}")

    return integrity

# ============ 4. 抽样人工验证 ============
def sample_for_manual_check(df, n=50):
    """随机抽取50期供人工核对"""
    print(f"\n[4] 抽样人工验证 (随机{n}期)...")

    # 随机抽样
    df_sample = df.sample(n=n, random_state=42).sort_values('period')

    # 构建输出
    samples = []
    for _, row in df_sample.iterrows():
        sample = {
            'period': str(row['period']),
            'date': str(row.get('date', '')),
            'special_number': row['special_number'],
            'special_zodiac': row['special_zodiac'],
            'special_color': row.get('special_color', ''),
            'special_wuxing': row.get('special_wuxing', ''),
        }
        samples.append(sample)

    # 保存CSV
    df_out = pd.DataFrame(samples)
    df_out.to_csv('/home/admin1/liuhecai_strategy_search/manual_check.csv', index=False, encoding='utf-8-sig')

    # 保存JSON
    with open('/home/admin1/liuhecai_strategy_search/manual_check.json', 'w', encoding='utf-8') as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)

    # 显示前10条
    print(f"    抽样记录: {len(samples)}条")
    print(f"    保存: manual_check.csv, manual_check.json")
    print("\n    前10条预览:")
    print("    期号    日期       号码  生肖  波色  五行")
    print("    " + "-" * 50)
    for s in samples[:10]:
        print(f"    {s['period']}  {s['date']}  {s['special_number']:>2}   {s['special_zodiac']}   {s['special_color']}   {s['special_wuxing']}")

    return samples

# ============ 5. 最终审计状态 ============
def determine_audit_status(validation, integrity, mismatches):
    """确定审计状态"""
    print("\n[5] 最终审计状态...")

    # 统计
    total_mismatches = sum(v['mismatch'] for v in validation.values())
    total_records = validation['zodiac']['total']
    mismatch_rate = total_mismatches / (total_records * 3)  # 3个字段

    # 问题统计
    data_issues = integrity['issues_found']
    mapping_issues = len(mismatches)

    # 判断等级
    if mismatch_rate == 0 and data_issues == 0:
        grade = 'GREEN'
    elif mismatch_rate < 0.01 and data_issues < 5:
        grade = 'YELLOW'
    else:
        grade = 'RED'

    # 详细状态
    status = {
        'timestamp': datetime.now().isoformat(),
        'grade': grade,
        'summary': {
            'total_records': total_records,
            'mapping_mismatches': mapping_issues,
            'mismatch_rate': round(mismatch_rate, 4),
            'data_issues': data_issues,
        },
        'checks': {
            'validation': {
                'zodiac_mismatches': validation['zodiac']['mismatch'],
                'color_mismatches': validation['color']['mismatch'],
                'wuxing_mismatches': validation['wuxing']['mismatch'],
            },
            'integrity': {
                'issues_found': integrity['issues_found'],
                'issues_list': integrity['issues'],
            }
        },
        'can_proceed': grade == 'GREEN',
        'message': {
            'GREEN': '所有数据一致，允许进入策略搜索',
            'YELLOW': f'发现{total_mismatches}处不一致，已自动修复，允许继续',
            'RED': f'存在严重问题（{mapping_issues}处不一致，{data_issues}处数据问题），禁止进入策略搜索'
        }[grade]
    }

    with open('/home/admin1/liuhecai_strategy_search/audit_status.json', 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    print(f"\n    审计等级: {grade}")
    print(f"    映射错误: {mapping_issues}处")
    print(f"    数据问题: {data_issues}处")
    print(f"    消息: {status['message']}")

    return status

# ============ 主程序 ============
def main():
    print("=" * 60)
    print("数据真实验证 (Data Truth Audit)")
    print("=" * 60)

    # 加载原始数据
    df = load_raw_data()

    # 执行验证
    print("\n" + "-" * 60)
    validation, mismatches = validate_original_data(df)

    print("\n" + "-" * 60)
    df_rebuilt = rebuild_all_data(df)

    print("\n" + "-" * 60)
    integrity = check_data_integrity(df_rebuilt)

    print("\n" + "-" * 60)
    samples = sample_for_manual_check(df_rebuilt, 50)

    print("\n" + "-" * 60)
    status = determine_audit_status(validation, integrity, mismatches)

    # 最终报告
    print("\n" + "=" * 60)
    print("审计结果")
    print("=" * 60)
    print(f"\n审计等级: {status['grade']}")
    print(f"消息: {status['message']}")

    print(f"\n输出文件:")
    print(f"  - mapping_mismatch.json ({len(mismatches)}条不匹配)")
    print(f"  - rebuild_report.json")
    print(f"  - integrity_report.json ({integrity['issues_found']}个问题)")
    print(f"  - manual_check.csv (50条抽样)")
    print(f"  - audit_status.json")
    print(f"  - liuhecai_rebuilt.json (重建数据)")

    print("\n" + "=" * 60)
    if status['can_proceed']:
        print("✓ 允许进入策略搜索")
    else:
        print("✗ 禁止进入策略搜索")

    return status

if __name__ == '__main__':
    main()