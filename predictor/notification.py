#!/usr/bin/env python3
"""
推送通知模块
- Telegram Bot 推送
"""

import json
import os
import requests
from typing import Dict, Optional

# Telegram 配置
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    """发送通知"""
    message = format_message(result)
    print(f"推送消息:\n{message}")
    return send_telegram(message)


if __name__ == "__main__":
    result = load_latest_result()
    if result:
        send_notification(result)
    else:
        print("无预测结果")