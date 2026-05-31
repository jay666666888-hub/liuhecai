# API_HEALTH_REPORT.md

## 生成时间
2026-05-27 07:10:23

---

## 统计数据概览

| 指标 | 值 | 百分比 |
|------|-----|--------|
| Total API Calls | 0 | 100% |
| Success | 0 | 0.0% |
| Fallback (Cache) | 0 | 0.0% |
| Failures | 0 | 0.0% |
| Retries | 0 | 0.0% |

---

## 指标详情

### success_rate
```
0.00%
```
API 调用成功（返回数据且来源为 API）的比例。

### fallback_rate
```
0.00%
```
API 失败后回退到缓存的比例。

### retry_rate
```
0.00%
```
触发重试的比例（不包括最终失败）。

### error_rate
```
0.00%
```
最终失败（缓存也无数据）的比例。

---

## Circuit Breaker 状态

| 状态 | 值 |
|------|-----|
| Status | **CLOSED** |
| Consecutive Failures | 0 |
| Last Error | None |
| Last API Success | 2026-05-27T07:09:52.888316 |

---

## Cache 状态

| 状态 | 值 |
|------|-----|
| Availability | fresh |
| Last Source | api |
| Last Cache Read | Never |

---

## RESILIENCE_MODE 配置

```python
RETRY_CONFIG = {
    "attempts": 3,
    "backoff": [1, 2, 4],  # seconds
    "connect_timeout": 5,
    "read_timeout": 10,
}

CIRCUIT_BREAKER_CONFIG = {
    "failure_threshold": 3,
    "recovery_timeout": 30 * 60,  # 30 minutes
}
```

---

## 数据保护规则

🚫 禁止修改：
- ledger (历史记录)
- prediction (预测数据)
- actual (实际结果)
- hit (命中标记)

✓ 允许的操作：
- API retry
- Timeout handling
- Cache fallback
- Circuit breaker

---

## 健康检查命令

```bash
python3 -c "
from predictor.data_fetcher import get_stats, get_api_health_status
print('Stats:', get_stats())
print('Health:', get_api_health_status())
"
```

---

*Report generated: 2026-05-27 07:10:23*
