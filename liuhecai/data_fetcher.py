"""
澳门六合数据获取模块
- 使用官方zodiac字段，绝不用硬编码生肖映射
- 数据分层：每年农历正月初一生肖重排
- 所有接口统一返回标准化records列表
"""

import json
import os
import requests
from datetime import datetime
from typing import List, Dict, Optional

# 缓存路径
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# API配置
API_BASE = "https://api.jpj.com/v1"  # 占卜室API（示例）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}

# 生肖类型（仅供参考，不用作映射）
ZODIACS = ["鼠", "牛", "虎", "兔", "龍", "蛇", "马", "羊", "猴", "雞", "狗", "豬"]


def get_cache_path(year: int) -> str:
    return os.path.join(CACHE_DIR, f"liuhecai_{year}.json")


def save_cache(records: List[Dict], year: int) -> None:
    """保存到本地缓存"""
    path = get_cache_path(year)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def load_cache(year: int) -> Optional[List[Dict]]:
    """从本地缓存加载"""
    path = get_cache_path(year)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def fetch_history(year: int = None, force_refresh: bool = False) -> List[Dict]:
    """
    获取指定年份的六合历史记录
    
    Args:
        year: 年份，默认当前年份
        force_refresh: 强制从API重新获取（不使用缓存）
    
    Returns:
        records: 按时间正序排列的列表，每条记录包含：
            - period: 期号 str
            - date: 日期 str
            - zodiac: 官方生肖 str（必须用这个，不用自己映射！）
            - 特码: 开奖号码 int
            - 生肖: 官方生肖 str（冗余字段，同zodiac）
    """
    if year is None:
        year = datetime.now().year

    # 尝试从缓存加载
    if not force_refresh:
        cached = load_cache(year)
        if cached:
            print(f"[数据] 从缓存加载 {year} 年数据: {len(cached)} 条")
            return cached

    # ========== 这里是实际API调用 ==========
    # TODO: 替换为真实API端点
    # 以下为示例数据，用于演示结构
    records = _fetch_from_api(year)
    # ========================================

    if not records:
        raise ValueError(f"API返回空数据，请检查网络或API配置")

    # 验证数据结构
    for r in records:
        assert "period" in r, f"记录缺少period字段: {r}"
        assert "zodiac" in r, f"记录缺少zodiac字段: {r}"  # ← 关键：用官方zodiac
        assert r["zodiac"] in ZODIACS, f"生肖字段异常: {r['zodiac']}"

    # 保存缓存
    save_cache(records, year)
    print(f"[数据] 获取 {year} 年数据: {len(records)} 条（已缓存）")
    return records


def _fetch_from_api(year: int) -> List[Dict]:
    """
    从API获取数据（示例实现）
    实际使用时请替换为真实API
    """
    # 示例API端点
    # url = f"{API_BASE}/history?year={year}&type=liuhe"
    # response = requests.get(url, headers=HEADERS, timeout=10)
    # response.raise_for_status()
    # return response.json()

    # 占位：返回示例结构
    # 真实环境请删除此段，替换为上面真实API调用
    print(f"[警告] 使用占位数据，请替换为真实API")
    return _generate_placeholder_data(year)


def _generate_placeholder_data(year: int) -> List[Dict]:
    """
    生成占位数据（仅用于开发测试）
    真实环境不使用此函数
    """
    import random
    random.seed(year)  # 年份作为种子保证可复现

    records = []
    base_date = datetime(year, 1, 1)

    for i in range(1, 151):  # 每年约150期
        period = f"{year}{str(i).zfill(3)}"
        zodiac = ZODIACS[i % 12]
        te Ma = (i % 49) + 1

        # 计算日期（简化：每2.5天一期）
        days_offset = (i - 1) * 2
        date_str = (base_date + datetime.timedelta(days=days_offset)).strftime("%Y-%m-%d")

        records.append({
            "period": period,
            "date": date_str,
            "zodiac": zodiac,  # ← 官方生肖字段
            "生肖": zodiac,     # 冗余兼容
            "特码": teMa,
        })

    return records


def get_all_records(years: List[int] = None, force_refresh: bool = False) -> List[Dict]:
    """
    获取多年数据并按时间正序合并
    注意：跨年数据中生肖可能会重排（农历正月初一）
    """
    if years is None:
        current_year = datetime.now().year
        years = [current_year - 1, current_year]

    all_records = []
    for year in sorted(set(years)):
        records = fetch_history(year, force_refresh=force_refresh)
        all_records.extend(records)

    # 按日期排序
    all_records.sort(key=lambda x: x["date"])
    print(f"[数据] 合并 {len(years)} 年数据: 共 {len(all_records)} 条")
    return all_records


def validate_records(records: List[Dict]) -> Dict:
    """
    验证数据完整性
    返回诊断信息
    """
    issues = []

    # 检查zodiac字段
    missing_zodiac = sum(1 for r in records if "zodiac" not in r or not r["zodiac"])
    if missing_zodiac > 0:
        issues.append(f"警告: {missing_zodiac} 条记录缺少zodiac字段")

    # 检查生肖值域
    invalid_zodiac = sum(1 for r in records if r.get("zodiac") not in ZODIACS)
    if invalid_zodiac > 0:
        issues.append(f"错误: {invalid_zodiac} 条记录生肖字段异常")

    # 检查日期连续性
    for i in range(1, len(records)):
        prev = datetime.strptime(records[i-1]["date"], "%Y-%m-%d")
        curr = datetime.strptime(records[i]["date"], "%Y-%m-%d")
        if curr < prev:
            issues.append(f"日期倒序: {records[i-1]['date']} -> {records[i]['date']}")

    # 检查特码范围
    invalid_te = sum(1 for r in records if not (1 <= r.get("特码", 0) <= 49))
    if invalid_te > 0:
        issues.append(f"警告: {invalid_te} 条记录特码超出1-49范围")

    return {
        "total": len(records),
        "issues": issues,
        "valid": len(issues) == 0,
        "zodiac_distribution": {z: sum(1 for r in records if r.get("zodiac") == z) for z in ZODIACS},
    }


# ========== 测试入口 ==========
if __name__ == "__main__":
    records = get_all_records([2025, 2026])
    result = validate_records(records)
    print(f"验证结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
