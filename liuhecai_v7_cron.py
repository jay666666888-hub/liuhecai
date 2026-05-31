#!/usr/bin/env python3
"""
V7优化版预测 - 定时任务入口
输出到 liuhecai_latest_prediction.json，格式兼容 send_prediction.py
"""
import json, sys, pathlib
from datetime import datetime

# 加载V7预测结果
v7_file = pathlib.Path('/home/admin1/liuhecai_v7_prediction.json')
if not v7_file.exists():
    print("❌ V7预测文件不存在，先运行 liuhecai_v7_predict.py")
    sys.exit(1)

v7 = json.loads(v7_file.read_text())

# 兼容send_prediction.py的格式
# send_prediction.py 读取字段: version, top6, 期号, strategy, verification{wf_single_all, wf_two_all, r20}, prev_hit, prev_actual, prev_top6
output = {
    'version': 'v7_optimized',
    'top6': v7['推荐6肖'],
    '期号': v7['期号'],
    '策略': '排名法: gap=2.5, recent5=1.5, recent10=1.5, recent20=0.0, recent30=1.0, recent3=1.0, streak=0.3',
    'verification': {
        'wf_single_all': 0,    # V7用WF验证，不用单期OOS
        'wf_two_all': 83.11,   # 滚动两期组WF
        'r20': 0,
    },
    'prev_hit': None,
    'prev_actual': '',
    'prev_top6': [],
    '备选7肖': v7.get('备选7肖', []),
    'scores': v7.get('scores', {}),
}

out_file = pathlib.Path('/home/admin1/liuhecai_latest_prediction.json')
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ V7预测已写入 liuhecai_latest_prediction.json")
print(f"   期号: {output['期号']}")
print(f"   推荐6肖: {' '.join(output['top6'])}")
print(f"   备选7肖: {' '.join(output.get('备选7肖', []))}")
