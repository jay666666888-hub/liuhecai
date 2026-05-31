#!/usr/bin/env python3
"""
推送通知模块
- Telegram Bot 推送
"""

import json
import os
import requests
from datetime import datetime
from typing import Dict, Optional

# Telegram 配置
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUSH_HISTORY_FILE = os.path.join(BASE_DIR, "configs", "push_history.json")
MAX_HISTORY_ENTRIES = 100  # 最多保留历史记录条数


def get_last_push_info() -> Dict:
    """获取上次推送信息"""
    if os.path.exists(PUSH_HISTORY_FILE):
        with open(PUSH_HISTORY_FILE) as f:
            data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                return data[-1]  # 返回最近一条
            return data
    return {}


def save_push_history(pending_period: str, pending_top6: list) -> None:
    """保存推送历史（带清理机制）"""
    # 读取现有历史
    history_list = []
    if os.path.exists(PUSH_HISTORY_FILE):
        with open(PUSH_HISTORY_FILE) as f:
            data = json.load(f)
            # 支持旧格式（单条）或新格式（列表）
            if isinstance(data, list):
                history_list = data
            else:
                # 旧格式转为列表
                history_list = [data]

    # 添加新记录
    new_entry = {
        "last_push_period": pending_period,
        "last_push_top6": pending_top6,
        "last_push_time": datetime.now().isoformat(),
    }
    history_list.append(new_entry)

    # 清理：保留最近 MAX_HISTORY_ENTRIES 条
    if len(history_list) > MAX_HISTORY_ENTRIES:
        history_list = history_list[-MAX_HISTORY_ENTRIES:]

    # 原子写入
    temp_file = PUSH_HISTORY_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=2)
    os.replace(temp_file, PUSH_HISTORY_FILE)


def should_send_notification(pending_period: str, pending_top6: list) -> bool:
    """判断是否应该发送通知（防止重复推送）"""
    last = get_last_push_info()
    if not last:
        return True
    # 如果推送过相同的期号和相同的六肖，跳过
    if last.get("last_push_period") == pending_period:
        if last.get("last_push_top6") == pending_top6:
            print(f"推送历史记录相同，跳过: {pending_period}")
            return False
    return True


def load_latest_result() -> Optional[Dict]:
    """从 aggregated_live.jsonl 加载最新预测结果（多版本统一数据源）"""
    aggregated_file = os.path.join(BASE_DIR, "storage", "aggregated_live.jsonl")
    if not os.path.exists(aggregated_file):
        return None

    records = []
    with open(aggregated_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    if not records:
        return None

    # 按 issue 降序排列
    records.sort(key=lambda x: x.get('issue', ''), reverse=True)

    # 只读取 live 数据（排除 sampled_backtest）
    live_records = [r for r in records if r.get("source") == "live"]
    pending_records = [r for r in live_records if r.get("status") == "pending"]
    verified_records = [r for r in live_records if r.get("status") == "verified"]

    # 构建统一格式
    result = {
        "verified_period": None,
        "verified_hit": None,
        "verified_actual": None,
        "pending_period": None,
        "pending_top6": [],
        "versions": {}
    }

    # 最新待验证的 pending 信息
    # 优先使用 v12（主版本），其次是 active 中第一个
    if pending_records:
        result["pending_period"] = pending_records[0].get("issue")
        # 收集所有版本的 pending 预测
        for r in pending_records:
            v = r.get("version", "unknown")
            result["versions"][v] = {
                "prediction": r.get("prediction", []),
                "strategy": r.get("strategy", "")
            }
        # 默认 pending_top6 优先取 v12
        if "v12" in result["versions"]:
            result["pending_top6"] = result["versions"]["v12"]["prediction"]
        else:
            # 否则取 active 中的第一个
            active_first = pending_records[0]
            result["pending_top6"] = active_first.get("prediction", [])

    # 最新已验证信息
    if verified_records:
        latest_verified = verified_records[0]
        result["verified_period"] = latest_verified.get("issue")
        result["verified_actual"] = latest_verified.get("actual")
        result["verified_hit"] = latest_verified.get("hit")

    return result if result["pending_period"] else None


def format_message(result: Dict) -> str:
    """格式化推送消息（支持多版本）"""
    verified_period = result.get("verified_period")
    verified_hit = result.get("verified_hit")
    verified_actual = result.get("verified_actual")
    pending_period = result.get("pending_period")
    pending_top6 = result.get("pending_top6", [])
    versions = result.get("versions", {})

    lines = [
        "🎯 澳门六合六肖预测",
        f"第{pending_period}期预测" if pending_period else "",
    ]

    # 多版本显示
    if versions and len(versions) > 1:
        for v, vdata in versions.items():
            pred = vdata.get("prediction", [])
            lines.append(f"[{v}] {' '.join(pred)}")
    else:
        lines.append(f"推荐六肖: {' '.join(pending_top6)}")

    if verified_period:
        hit_emoji = "✅" if verified_hit else "❌"
        lines.insert(0, f"📋 第{verified_period}期验证: {verified_actual} {hit_emoji}")

    return "\n".join(lines)


def send_telegram(message: str, retry: int = 3) -> bool:
    """发送 Telegram 消息"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram 未配置，跳过推送")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    for attempt in range(retry):
        try:
            resp = requests.post(url, data=data, timeout=10)
            if resp.ok:
                return True
        except Exception as e:
            print(f"Telegram 推送失败 (尝试 {attempt+1}/{retry}): {e}")

    return False


def send_notification(result: Dict) -> bool:
    """发送通知（带去重）"""
    pending_period = result.get("pending_period", "")
    pending_top6 = result.get("pending_top6", [])

    # 去重检查
    if not should_send_notification(pending_period, pending_top6):
        print("推送内容与上次相同，跳过")
        return False

    message = format_message(result)
    print(f"推送消息:\n{message}")
    success = send_telegram(message)

    # 推送成功后保存历史
    if success:
        save_push_history(pending_period, pending_top6)

    return success


if __name__ == "__main__":
    result = load_latest_result()
    if result:
        send_notification(result)
    else:
        print("无预测结果")