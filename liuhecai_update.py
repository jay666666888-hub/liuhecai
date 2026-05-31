#!/usr/bin/env python3
"""澳门六合开奖数据采集脚本 - 追加模式，只更新新期"""
import urllib.request, json, ssl, os, sys

DATA_FILE = '/home/admin1/liuhecai_data.json'
API_URL = "https://history.macaumarksix.com/history/macaujc2/y/{year}"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch_year(year):
    url = API_URL.format(year=year)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=15, context=ctx).read())
    
    records = {}
    seen = set()
    for d in data['data']:
        exp = d['expect']
        if exp not in seen:
            seen.add(exp)
            codes = d['openCode'].split(',')
            zodiacs = d['zodiac'].split(',')
            waves = d['wave'].split(',')
            # 第7个号码是特码
            records[exp] = {
                '期号': exp,
                '开奖时间': d['openTime'],
                '特码号码': codes[6],
                '特码生肖': zodiacs[6],
                '波色': waves[6],
                '开奖号码': codes,
                '开奖生肖': zodiacs,
                '波色列表': waves,
            }
    return records

def update():
    # 读取现有数据
    existing = {}
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            for r in json.load(f):
                existing[r['期号']] = r
    
    # 采集2025+2026
    all_new = {}
    for year in [2025, 2026]:
        try:
            all_new.update(fetch_year(year))
        except Exception as e:
            print(f"获取{year}年数据失败: {e}")
            sys.exit(1)
    
    # 合并
    existing.update(all_new)
    records = sorted(existing.values(), key=lambda x: int(x['期号']))
    
    # 保存
    with open(DATA_FILE, 'w') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    
    new_count = len(all_new)
    total = len(records)
    print(f"✅ 更新完成: 新增{new_count}期, 共{total}期, 最新={records[-1]['期号']}")

if __name__ == '__main__':
    update()
