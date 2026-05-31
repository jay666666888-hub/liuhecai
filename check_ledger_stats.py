#!/usr/bin/env python3
"""检查ledger统计"""
import json

with open('version_book/v26/backtest_ledger.jsonl', 'r') as f:
    lines = f.readlines()

hits = 0
total = 0
for line in lines:
    record = json.loads(line)
    if record.get('hit'):
        hits += 1
    total += 1

print(f"Ledger记录: {total}条")
print(f"命中: {hits}")
print(f"命中率: {hits/total:.4f}")

# 检查前10条和后10条
print("\n前10条:")
for line in lines[:10]:
    r = json.loads(line)
    print(f"  {r['issue']}: pred={r['prediction']}, hit={r['hit']}")

print("\n后10条:")
for line in lines[-10:]:
    r = json.loads(line)
    print(f"  {r['issue']}: pred={r['prediction']}, hit={r['hit']}")
