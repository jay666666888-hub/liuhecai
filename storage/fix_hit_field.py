#!/usr/bin/env python3
"""修复 aggregated_live.jsonl 中被错误修改的 hit 字段"""
import json
from datetime import datetime

# Load backup (trustworthy reference)
backup_path = '/mnt/c/Users/Admin/liuhecai/storage/backup_20260525_0152/aggregated_live.jsonl'
current_path = '/mnt/c/Users/Admin/liuhecai/storage/aggregated_live.jsonl'
backup_path

backup_by_id = {}
with open(backup_path) as f:
    for line in f:
        if line.strip():
            r = json.loads(line)
            backup_by_id[r['id']] = r

# Load current
current_records = []
with open(current_path) as f:
    for line in f:
        if line.strip():
            current_records.append(json.loads(line))

# Find discrepancies across ALL versions
all_discrepancies = []
for r in current_records:
    id_ = r['id']
    if id_ in backup_by_id:
        b_hit = backup_by_id[id_].get('hit')
        c_hit = r.get('hit')
        if b_hit != c_hit:
            all_discrepancies.append({
                'id': id_,
                'issue': r['issue'],
                'version': r['version'],
                'old_hit': c_hit,
                'new_hit': b_hit,
            })

print(f'总不一致记录: {len(all_discrepancies)}')

# Per version
from collections import Counter
vc = Counter(d['version'] for d in all_discrepancies)
for v, c in sorted(vc.items()):
    print(f'  {v}: {c}条')

# Apply fixes
fixed_count = 0
for r in current_records:
    id_ = r['id']
    if id_ in backup_by_id:
        b_hit = backup_by_id[id_].get('hit')
        if b_hit != r.get('hit'):
            r['hit'] = b_hit
            fixed_count += 1

print(f'\n修复了 {fixed_count} 条记录')

# Backup current file
ts = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = f'{current_path}.broken_{ts}'
import shutil
shutil.copy(current_path, backup_file)
print(f'原文件已备份到: {backup_file}')

# Write fixed data
with open(current_path, 'w') as f:
    for r in current_records:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print(f'已写入修复后的数据到: {current_path}')

# Verify v5 stats
print('\n=== 修复后验证 ===')
for version in ['v5', 'v7', 'v12', 'v21', 'v23', 'v24', 'v26', 'v27', 'v28']:
    records = [r for r in current_records if r.get('version') == version and r.get('actual') is not None]
    if not records:
        continue
    records.sort(key=lambda x: x['issue'], reverse=True)
    total = len(records)
    hits = sum(1 for r in records if r.get('hit', False))
    recent_100 = records[:100]
    recent_50 = records[:50]
    hits_100 = sum(1 for r in recent_100 if r.get('hit', False))
    hits_50 = sum(1 for r in recent_50 if r.get('hit', False))
    max_streak = 0
    cs = 0
    for r in records:
        if not r.get('hit', False):
            cs += 1
            max_streak = max(max_streak, cs)
        else:
            cs = 0
    print(f'{version}: 总={total} 命中率={round(hits/total*100,2)}% 近100={round(hits_100/len(recent_100)*100,2)}% 近50={round(hits_50/len(recent_50)*100,2)}% 最长连错={max_streak}期')