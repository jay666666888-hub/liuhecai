# STRICT_EVIDENCE_MODE_REPORT.md

## 审计时间
2026-05-27

---

## A. CHAIN MODEL VERIFICATION

### Evidence from Code

**ledger_writer.py:97-114**
```python
def _get_last_last_record_hash(self) -> str:
    """获取最后一条记录的 hash（用于链式写入）"""
    if not AGGREGATED_LIVE_FILE.exists():
        return GENESIS_HASH

    with _safe_open(AGGREGATED_LIVE_FILE, 'r', encoding='utf-8') as f:
        last_line = None
        for line in f:
            line = line.strip()
            if line:
                last_line = line
        if last_line:
            try:
                rec = json.loads(last_line)
                return rec.get("record_hash") or rec.get("hash") or GENESIS_HASH
            except json.JSONDecodeError:
                return GENESIS_HASH
    return GENESIS_HASH
```

**ledger_writer.py:220-222 (write_live_prediction)**
```python
prev_hash = self._get_last_record_hash()
record["prev_hash"] = prev_hash
record["record_hash"] = self._compute_record_hash(record, prev_hash)
```

### Chain Model

```
chain_model: global
evidence: _get_last_record_hash() returns file's last record_hash, not per-version
```

---

## B. DATA SCAN (7375 records)

```
records: 7375
missing_hash: 0
chain_breaks: 19
```

### breaks[]

| index | version | issue | record_hash | prev_hash | expected_prev_hash | reason |
|-------|---------|-------|-------------|-----------|-------------------|--------|
| 867 | v12 | 2026147 | 704b74333b597632 | eb2d4fba933814ae | 565fa4627ee5ca1d | prev_hash != previous record_hash |
| 868 | v21 | 2024020 | 3d03fd9dcc09ec9a | GENESIS | 704b74333b597632 | prev_hash != previous record_hash |
| 1726 | v21 | 2026147 | 7622b6a99b69892f | eb2d4fba933814ae | 7fd9a3a1a0e7c6c6 | prev_hash != previous record_hash |
| 1727 | v23 | 2024110 | 1c72bf7a42f9b466 | GENESIS | 7622b6a99b69892f | prev_hash != previous record_hash |
| 2495 | v23 | 2026147 | 0b3a7a14bc9ebb07 | eb2d4fba933814ae | 19e38ca23544d7e6 | prev_hash != previous record_hash |
| 2496 | v24 | 2024110 | 77b5f9841d5a1e3e | GENESIS | 0b3a7a14bc9ebb07 | prev_hash != previous record_hash |
| 3264 | v24 | 2026147 | 09a536644e6437f6 | eb2d4fba933814ae | e1d0d71b412980b0 | prev_hash != previous record_hash |
| 3265 | v26 | 2024016 | 98d90c59f55aaeb9 | GENESIS | 09a536644e6437f6 | prev_hash != previous record_hash |
| 4126 | v27 | 2024075 | 824dbfe4bac5f64e | GENESIS | e55bc286b646ba8c | prev_hash != previous record_hash |
| 4930 | v27 | 2026147 | ba1aa2ddcd4fe454 | eb2d4fba933814ae | 620fce9f35145bb7 | prev_hash != previous record_hash |
| 4931 | v28 | 2024137 | c4a1a4eaa29c752d | GENESIS | ba1aa2ddcd4fe454 | prev_hash != previous record_hash |
| 5673 | v28 | 2026147 | 6b0b766070f94d16 | eb2d4fba933814ae | ac4585f8c2762c30 | prev_hash != previous record_hash |
| 5674 | v29 | 2026145 | c0b016c0b81d050d | GENESIS | 6b0b766070f94d16 | prev_hash != previous record_hash |
| 5676 | v29 | 2026147 | c31206cc3b795c94 | eb2d4fba933814ae | adf1a6f0b3f68e55 | prev_hash != previous record_hash |
| 5677 | v5 | 2024030 | f9f49c16efe2ef6a | GENESIS | c31206cc3b795c94 | prev_hash != previous record_hash |
| 6525 | v5 | 2026147 | 2217f5863acde26c | e21a450c5d088b1a | aeb1a1c7deec9463 | prev_hash != previous record_hash |
| 6526 | v7 | 2024030 | f502b65459dc5ec9 | GENESIS | 2217f5863acde26c | prev_hash != previous record_hash |
| 7373 | v7 | 2026147 | fbd0e3df5b7bc20a | e21a450c5d088b1a | 244d69f42c6b56b7 | prev_hash != previous record_hash |
| 7374 | v30 | 2026147 | e21a450c5d088b1a | eb2d4fba933814ae | fbd0e3df5b7bc20a | prev_hash != previous record_hash |

---

## C. HASH SOURCE SEARCH

### eb2d4fba933814ae

```
found: true
locations:
  - aggregated_live.jsonl (8 occurrences as prev_hash)
    lines: 868, 1727, 2496, 3265, 4931, 5674, 5677, 7375
  - docs/*.md (mentions only, no source code)
```

### 98196124ac688288

```
found: false
locations: []
```

**Note**: This hash appears only in old markdown reports, never in actual data or code.

---

## D. CONFIRMED FACTS

```
CONFIRMED_FACTS:
1. chain_model = global (code line 97-114)
2. records = 7375
3. missing_hash = 0
4. chain_breaks = 19
5. eb2d4fba933814ae exists in data as prev_hash (8 records)
6. 98196124ac688288 does NOT exist in any data file

UNKNOWN:
1. source of eb2d4fba933814ae - not in any code as constant or default
2. why P2 reported chain_breaks=0 but current shows 19
3. whether this value was created by deleted/modified historical code

INVALID_ASSUMPTIONS:
1. "98196124ac688288 is some record's hash" - FALSE (never found in data)
2. "Model B (per-version chain)" - FALSE (code shows global chain)
3. "P2 reconstruction fixed all breaks" - FALSE (19 breaks exist)
```

---

*Report generated: 2026-05-27*
*STRICT_EVIDENCE_MODE - no speculation, only evidence*