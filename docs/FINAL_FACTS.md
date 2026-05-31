# FINAL_FACTS.md

## 审计时间
2026-05-27

---

## CONFIRMED_FACTS

```
chain_model: global
evidence: ledger_writer.py:97-114 _get_last_record_hash() returns file's last record_hash

records: 7375
missing_hash: 0
chain_breaks: 19

eb2d4fba933814ae:
  exists_as_record_hash: false
  exists_as_prev_hash: true (8 records)
  locations: aggregated_live.jsonl lines 868,1727,2496,3265,4931,5674,5677,7375
  found_in_code: false (no constant, no default value)

98196124ac688288:
  exists_as_record_hash: false
  exists_as_prev_hash: false
  found_in_code: false
  found_in_data: false
```

---

## UNKNOWN

```
generation_path_of_eb2d4fba933814ae
  - not found in any source code
  - not found as constant or default
  - appears only in aggregated_live.jsonl as prev_hash
  - no evidence explaining its origin

P2_vs_current_discrepancy:
  - P2 reported chain_breaks=0
  - current shows chain_breaks=19
  - No evidence that P2 resulted in a persistent chain_breaks=0 state
```

---

## INVALID_ASSUMPTIONS

```
98196124ac688288 is some record's hash: FALSE (never found in data or code)
Model B (per-version chain): FALSE (code shows global chain)
P2 reconstruction fixed all breaks: FALSE
  evidence: No evidence that P2 resulted in a persistent chain_breaks=0 state
GENESIS is correct for version starts: FALSE
  evidence: Under current verify_chain implementation, GENESIS at version starts contributes to chain_breaks.
```

---

## breaks[]

| index | version | issue | record_hash | prev_hash | expected_prev_hash | detected_condition | root_cause |
|-------|---------|-------|-------------|-----------|-------------------|-------------------|------------|
| 867 | v12 | 2026147 | 704b74333b597632 | eb2d4fba933814ae | 565fa4627ee5ca1d | prev_hash != previous_record.record_hash | UNKNOWN |
| 868 | v21 | 2024020 | 3d03fd9dcc09ec9a | GENESIS | 704b74333b597632 | prev_hash != previous_record.record_hash | UNKNOWN |
| 1726 | v21 | 2026147 | 7622b6a99b69892f | eb2d4fba933814ae | 7fd9a3a1a0e7c6c6 | prev_hash != previous_record.record_hash | UNKNOWN |
| 1727 | v23 | 2024110 | 1c72bf7a42f9b466 | GENESIS | 7622b6a99b69892f | prev_hash != previous_record.record_hash | UNKNOWN |
| 2495 | v23 | 2026147 | 0b3a7a14bc9ebb07 | eb2d4fba933814ae | 19e38ca23544d7e6 | prev_hash != previous_record.record_hash | UNKNOWN |
| 2496 | v24 | 2024110 | 77b5f9841d5a1e3e | GENESIS | 0b3a7a14bc9ebb07 | prev_hash != previous_record.record_hash | UNKNOWN |
| 3264 | v24 | 2026147 | 09a536644e6437f6 | eb2d4fba933814ae | e1d0d71b412980b0 | prev_hash != previous_record.record_hash | UNKNOWN |
| 3265 | v26 | 2024016 | 98d90c59f55aaeb9 | GENESIS | 09a536644e6437f6 | prev_hash != previous_record.record_hash | UNKNOWN |
| 4126 | v27 | 2024075 | 824dbfe4bac5f64e | GENESIS | e55bc286b646ba8c | prev_hash != previous_record.record_hash | UNKNOWN |
| 4930 | v27 | 2026147 | ba1aa2ddcd4fe454 | eb2d4fba933814ae | 620fce9f35145bb7 | prev_hash != previous_record.record_hash | UNKNOWN |
| 4931 | v28 | 2024137 | c4a1a4eaa29c752d | GENESIS | ba1aa2ddcd4fe454 | prev_hash != previous_record.record_hash | UNKNOWN |
| 5673 | v28 | 2026147 | 6b0b766070f94d16 | eb2d4fba933814ae | ac4585f8c2762c30 | prev_hash != previous_record.record_hash | UNKNOWN |
| 5674 | v29 | 2026145 | c0b016c0b81d050d | GENESIS | 6b0b766070f94d16 | prev_hash != previous_record.record_hash | UNKNOWN |
| 5676 | v29 | 2026147 | c31206cc3b795c94 | eb2d4fba933814ae | adf1a6f0b3f68e55 | prev_hash != previous_record.record_hash | UNKNOWN |
| 5677 | v5 | 2024030 | f9f49c16efe2ef6a | GENESIS | c31206cc3b795c94 | prev_hash != previous_record.record_hash | UNKNOWN |
| 6525 | v5 | 2026147 | 2217f5863acde26c | e21a450c5d088b1a | aeb1a1c7deec9463 | prev_hash != previous_record.record_hash | UNKNOWN |
| 6526 | v7 | 2024030 | f502b65459dc5ec9 | GENESIS | 2217f5863acde26c | prev_hash != previous_record.record_hash | UNKNOWN |
| 7373 | v7 | 2026147 | fbd0e3df5b7bc20a | e21a450c5d088b1a | 244d69f42c6b56b7 | prev_hash != previous_record.record_hash | UNKNOWN |
| 7374 | v30 | 2026147 | e21a450c5d088b1a | eb2d4fba933814ae | fbd0e3df5b7bc20a | prev_hash != previous_record.record_hash | UNKNOWN |

---

*Report generated: 2026-05-27*
*FINAL_EVIDENCE_LOCK - no speculation, only evidence*