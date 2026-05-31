#!/usr/bin/env python3
"""
六肖预测推送 — 通过 Hermes Gateway send_message 发 Telegram
"""
import json, pathlib

# ========== 读取数据 ==========
with open('/home/admin1/liuhecai_data.json') as f:
    all_data = json.load(f)
latest = all_data[-1]
本期 = latest['期号']
开奖号码 = latest.get('开奖号码', [])
开奖生肖 = latest.get('开奖生肖', [])
open_nums = []
for i, (num, zodiac) in enumerate(zip(开奖号码[:7], 开奖生肖[:7])):
    tag = '特' if i == 6 else str(i+1)
    open_nums.append(f"{num}{zodiac}")
open_str = "  ".join(open_nums)

# ========== 读取 V5 预测 ==========
v5 = json.loads(pathlib.Path('/home/admin1/liuhecai_latest_prediction.json').read_text())
v5_verify_period = v5.get('verified_period', 本期)
v5_verify_top6 = v5.get('verified_top6', [])
v5_verify_actual = v5.get('verified_actual', '')
v5_verify_hit = v5.get('verified_hit')
v5_pending_period = v5.get('pending_period', '')
v5_pending_top6 = v5.get('pending_top6', [])

# ========== 读取 V7 预测 ==========
v7 = json.loads(pathlib.Path('/home/admin1/liuhecai_v7_prediction.json').read_text())
v7_verify_period = v7.get('verified_period', v7.get('期号', 本期))
v7_verify_top6 = v7.get('prev_top6', [])
v7_verify_actual = v7.get('prev_actual', '')
v7_verify_hit = v7.get('prev_hit')
v7_pending_period = v7.get('预测期号', '')
v7_pending_top6 = v7.get('推荐6肖', [])

# ========== 格式化消息 ==========
v5_hit_str = "✅" if v5_verify_hit else "❌"
v7_hit_str = "✅" if v7_verify_hit else "❌"

sep = "  "
msg_text = f"""🎯 澳门六合
第{本期}期开奖
{open_str}
──
V5验证 {v5_verify_period}期: {' '.join(v5_verify_top6)} → {v5_verify_actual} {v5_hit_str}
V5预测 {v5_pending_period}期: {' '.join(v5_pending_top6)}
──
V7验证 {v7_verify_period}期: {' '.join(v7_verify_top6)} → {v7_verify_actual} {v7_hit_str}
V7预测 {v7_pending_period}期: {' '.join(v7_pending_top6)}"""

# 输出消息内容供 Hermes send_message 发送
print(msg_text)
