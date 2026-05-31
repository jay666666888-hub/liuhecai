#!/usr/bin/env python3
"""
六肖预测微信推送
- 已验证的上期结果（永不改变）
- 当前预测的下期（最新生成）
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

# ========== 微信推送内容 ==========
v5_hit_str = "✅" if v5_verify_hit else "❌"
v7_hit_str = "✅" if v7_verify_hit else "❌"

sep = "  "
print(f"""🎯 澳门六合
第{本期}期开奖
{open_str}

V5
第{v5_verify_period}期验证
{sep.join(v5_verify_top6)} → {v5_verify_actual} {v5_hit_str}

第{v5_pending_period}期预测
{sep.join(v5_pending_top6)}

V7
第{v7_verify_period}期验证
{sep.join(v7_verify_top6)} → {v7_verify_actual} {v7_hit_str}

第{v7_pending_period}期预测
{sep.join(v7_pending_top6)}""".strip())
