#!/usr/bin/env python3
"""
数据Schema统一模块
================

统一字段定义，禁止使用特殊字段名。

字段规范：
- period: str, 期号
- date: str, 日期 (YYYY-MM-DD)
- number: int, 开奖号码 (1-49)
- zodiac: str, 生肖 (鼠/牛/虎/兔/龍/蛇/马/羊/猴/雞/狗/豬)
- color: str, 波色 (red/blue/green)
- size: str, 大小 (大/小)
- parity: str, 单双 (单/双)
- tail: int, 尾数 (0-9)
- lunar_year: int, 农历年
- lunar_month: int, 农历月 (1-12)
- lunar_day: int, 农历日 (1-30)
- solar_term: str, 节气 (可选)
"""

import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
from lunardate import LunarDate
import json

# 标准字段
STANDARD_FIELDS = [
    'period', 'date', 'number', 'zodiac', 'color',
    'size', 'parity', 'tail', 'lunar_year', 'lunar_month', 'lunar_day', 'solar_term'
]

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
VALID_COLORS = ['red', 'blue', 'green']
VALID_SIZES = ['大', '小']
VALID_PARITIES = ['单', '双']


class DataSchema:
    """数据Schema管理器"""

    # 字段映射表（处理历史兼容）
    FIELD_ALIASES = {
        'special_zodiac': 'zodiac',
        'zodiac_generated': 'zodiac',
        'special_color': 'color',
        'color_generated': 'color',
        'size_generated': 'size',
        'parity_generated': 'parity',
        'tail_generated': 'tail',
    }

    def __init__(self):
        self.errors = []

    def standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        将任意格式的DataFrame转换为标准Schema
        自动识别并转换字段别名
        """
        df = df.copy()

        # 1. 重命名别名字段
        for old_name, new_name in self.FIELD_ALIASES.items():
            if old_name in df.columns:
                df.rename(columns={old_name: new_name}, inplace=True)

        # 2. 检查缺失字段
        missing = set(STANDARD_FIELDS) - set(df.columns)
        if missing:
            self.errors.append(f"Missing required fields: {missing}")

        # 3. 计算缺失字段
        if 'lunar_year' not in df.columns or 'lunar_month' not in df.columns:
            df = self._compute_lunar_fields(df)

        # 4. 验证数据完整性
        self._validate(df)

        return df[STANDARD_FIELDS]  # 确保字段顺序

    def _compute_lunar_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """使用lunardate库计算农历字段"""
        if 'date' not in df.columns:
            self.errors.append("Cannot compute lunar fields: 'date' column missing")
            return df

        lunar_data = []
        for idx, row in df.iterrows():
            try:
                date_str = str(row['date'])
                # Parse date (supports YYYY-MM-DD or YYYYMMDD)
                if '-' in date_str:
                    parts = date_str.split('-')
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                else:
                    year = int(date_str[:4])
                    month = int(date_str[4:6])
                    day = int(date_str[6:8])

                # 使用LunarDate.fromSolarDate (注意API名称)
                lunar = LunarDate.fromSolarDate(year, month, day)

                lunar_info = {
                    'lunar_year': int(lunar.year),
                    'lunar_month': int(lunar.month),
                    'lunar_day': int(lunar.day),
                    'solar_term': ''
                }
            except Exception as e:
                lunar_info = {
                    'lunar_year': int(year) if 'year' in locals() else 0,
                    'lunar_month': 0,
                    'lunar_day': 0,
                    'solar_term': ''
                }

            lunar_data.append(lunar_info)

        lunar_df = pd.DataFrame(lunar_data)
        for col in ['lunar_year', 'lunar_month', 'lunar_day', 'solar_term']:
            if col in lunar_df.columns:
                df[col] = lunar_df[col]

        return df

    def _validate(self, df: pd.DataFrame):
        """验证数据完整性"""
        # 检查日期合法性
        if 'date' in df.columns:
            invalid_dates = []
            for idx, val in enumerate(df['date']):
                try:
                    pd.to_datetime(val)
                except:
                    invalid_dates.append(idx)
            if invalid_dates:
                self.errors.append(f"Invalid dates at rows: {invalid_dates[:10]}")

        # 检查生肖合法性
        if 'zodiac' in df.columns:
            invalid_zodiacs = df[~df['zodiac'].isin(ZODIACS)]['zodiac'].unique()
            if len(invalid_zodiacs) > 0:
                self.errors.append(f"Invalid zodiacs found: {invalid_zodiacs}")

        # 检查号码完整性
        if 'number' in df.columns:
            out_of_range = df[(df['number'] < 1) | (df['number'] > 49)]
            if len(out_of_range) > 0:
                self.errors.append(f"Numbers out of range [1-49]: {len(out_of_range)} rows")

    def get_errors(self) -> List[str]:
        """获取验证错误"""
        return self.errors


class DataGate:
    """数据完整性门控"""

    @staticmethod
    def check(df: pd.DataFrame) -> Dict:
        """
        检查数据完整性
        返回门控报告
        """
        report = {
            'status': 'PASS',
            'missing_fields': [],
            'field_missing_rates': {},
            'date_validity': {},
            'zodiac_validity': {},
            'number_completeness': {},
            'time_continuity': {},
            'errors': []
        }

        # 1. 检查字段缺失率
        for col in STANDARD_FIELDS:
            if col in df.columns:
                missing = df[col].isna().sum()
                rate = missing / len(df) if len(df) > 0 else 1
                report['field_missing_rates'][col] = f"{rate:.2%}"
                if missing > 0:
                    report['errors'].append(f"Field '{col}': {missing} missing ({rate:.2%})")
            else:
                report['missing_fields'].append(col)
                report['field_missing_rates'][col] = '100%'

        # 2. 日期合法性
        if 'date' in df.columns:
            invalid_dates = 0
            for val in df['date']:
                try:
                    pd.to_datetime(val)
                except:
                    invalid_dates += 1
            report['date_validity'] = {
                'invalid_count': invalid_dates,
                'invalid_rate': f"{invalid_dates/len(df):.2%}" if len(df) > 0 else "N/A"
            }
            if invalid_dates > 0:
                report['errors'].append(f"Invalid dates: {invalid_dates}")

        # 3. 生肖合法性
        if 'zodiac' in df.columns:
            invalid = df[~df['zodiac'].isin(ZODIACS)]
            report['zodiac_validity'] = {
                'invalid_count': len(invalid),
                'invalid_values': list(invalid['zodiac'].unique())[:10]
            }
            if len(invalid) > 0:
                report['errors'].append(f"Invalid zodiacs: {len(invalid)}")

        # 4. 号码完整性
        if 'number' in df.columns:
            out_of_range = df[(df['number'] < 1) | (df['number'] > 49)]
            missing = df['number'].isna().sum()
            report['number_completeness'] = {
                'out_of_range': len(out_of_range),
                'missing': missing,
                'valid_count': len(df) - len(out_of_range) - missing
            }
            if len(out_of_range) > 0 or missing > 0:
                report['errors'].append(f"Number issues: {len(out_of_range)} out of range, {missing} missing")

        # 5. 时间连续性
        if 'period' in df.columns:
            # 检查period是否连续
            periods = df['period'].astype(str).tolist()
            sorted_periods = sorted(periods)
            gaps = []
            for i in range(1, len(sorted_periods)):
                p1 = int(sorted_periods[i-1][-4:])
                p2 = int(sorted_periods[i][-4:])
                if p2 - p1 > 1:
                    gaps.append((sorted_periods[i-1], sorted_periods[i]))
            report['time_continuity'] = {
                'total_records': len(df),
                'gaps_found': len(gaps),
                'sample_gaps': gaps[:5] if gaps else []
            }

        # 最终判定
        if report['errors']:
            report['status'] = 'FAIL'

        return report


def load_standardized(path: str) -> pd.DataFrame:
    """加载并标准化数据"""
    # 读取原始数据
    with open(path) as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    # 标准化
    schema = DataSchema()
    df_std = schema.standardize_dataframe(df)

    # 门控检查
    gate = DataGate()
    report = gate.check(df_std)

    # 保存报告
    def convert_to_serializable(obj):
        """Convert numpy types to native Python types"""
        if hasattr(obj, 'item'):  # numpy types
            return obj.item()
        elif isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(i) for i in obj]
        return obj

    report = convert_to_serializable(report)

    with open(path.replace('.json', '_gate_report.json'), 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    if report['status'] == 'FAIL':
        raise ValueError(f"DataGate failed: {report['errors']}")

    return df_std


# 测试
if __name__ == '__main__':
    import os

    data_path = '/home/admin1/liuhecai_strategy_search/truth_dataset.json'

    if os.path.exists(data_path):
        try:
            df = load_standardized(data_path)
            print(f"Standardized data: {len(df)} rows")
            print(f"Columns: {list(df.columns)}")
            print(f"Sample:\n{df.head()}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"File not found: {data_path}")