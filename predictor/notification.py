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


def get_last_push_info() -> Dict:
    """获取上次推送信息"""
    if os.path.exists(PUSH_HISTORY_FILE):
        with open(PUSH_HISTORY_FILE) as f:
            return json.load(f)
    return {}


def save_push_history(pending_period: str, pending_top6: list) -> None:
    """保存推送历史"""
    history = {
        "last_push_period": pending_period,
        "last_push_top6": pending_top6,
        "last_push_time": datetime.now().isoformat(),
    }
    temp_file = PUSH_HISTORY_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
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
    """加载最新预测结果"""
    state_file = os.path.join(BASE_DIR, "liuhecai_prediction.json")
    if os.path.exists(state_file):
        with open(state_file) as f:
            return json.load(f)
    return None


def format_message(result: Dict) -> str:
    """格式化推送消息"""
    verified_period = result.get("verified_period")
    verified_hit = result.get("verified_hit")
    verified_actual = result.get("verified_actual")
    pending_period = result.get("pending_period")
    pending_top6 = result.get("pending_top6", [])

    lines = [
        "🎯 澳门六合六肖预测",
        f"第{pending_period}期预测" if pending_period else "",
        f"推荐六肖: {' '.join(pending_top6)}",
    ]

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