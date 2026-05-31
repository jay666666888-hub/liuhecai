#!/usr/bin/env python3
"""
澳门六合 - 数据同步脚本
将 result_ledger.jsonl 的开奖结果同步到 liuhecai_data.json

用法：重建账本前必须先运行此脚本
python3 scripts/sync_result_to_data.py
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path("/mnt/c/Users/Admin/liuhecai")
DATA_FILE = BASE_DIR / "liuhecai_data.json"
LEDGER_FILE = BASE_DIR / "storage" / "result_ledger.jsonl"

def main():
    if not DATA_FILE.exists():
        print(f"错误：主数据文件不存在 {DATA_FILE}")
        sys.exit(1)

    if not LEDGER_FILE.exists():
        print(f"警告：账本文件不存在 {LEDGER_FILE}，无需同步")
        sys.exit(0)

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    issue_map = {item['期号']: item for item in data}
    original_count = len(data)

    updates = 0
    with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            issue = record.get('issue')
            actual = record.get('actual')
            if issue and actual and issue in issue_map:
                if issue_map[issue].get('特码生肖') != actual:
                    issue_map[issue]['特码生肖'] = actual
                    updates += 1

    if updates > 0:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ 同步完成：更新 {updates} 条记录")
    else:
        print("✓ 数据已是最新，无需同步")

    # 验证
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        verify = json.load(f)
    print(f"✓ 主数据文件记录数：{len(verify)}")

if __name__ == "__main__":
    main()