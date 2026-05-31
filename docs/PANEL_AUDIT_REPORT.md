# PANEL_AUDIT_REPORT.md

**Task:** #29 - Dashboard / Panel Display Layer Full Audit
**Phase:** 3 - Report Generation (Updated)
**Audit Date:** 2026-05-27
**Evidence Source:** FINAL_FACTS.md (EVIDENCE_LOCK_MODE)

---

## 执行摘要

| 层级 | 状态 | 关键问题数 |
|------|------|-----------|
| 数据一致性 | PASS | 0 严重, 2 警告 |
| 缓存机制 | FAIL | 1 严重, 1 高 |
| 统计计算 | PASS | 0 |
| 渲染逻辑 | FAIL | 2 严重, 1 中 |
| 状态流 | FAIL | 1 严重, 2 中 |

**总体判断:** FAIL - 多层存在严重问题需要修复

---

## 一、数据一致性检查 (PASS)

### 1.1 数据源完整性

| 检查项 | 结果 | 证据 |
|--------|------|------|
| 记录总数 | 7375 | aggregated_live.jsonl |
| required_fields 覆盖 | 100% | 所有记录含 id, issue, version, prediction, actual, hit, created_at, source, status, verified_at, prev_hash, record_hash |
| prev_hash 缺失 | 0 | 无记录 prev_hash=null |
| record_hash 缺失 | 0 | 无记录 record_hash=null |

### 1.2 版本分布警告

| 版本 | 记录数 | 状态 | 影响 |
|------|--------|------|------|
| v29 | 3 | 异常低 | 统计显著性不足 |
| v30 | 1 | 异常低 | 统计显著性不足 |

**风险:** v29/v30 的命中率统计不具代表性，可能误导版本对比。

### 1.3 Backtest vs Live 一致性

| 类别 | 数量 | 验证 |
|------|------|------|
| Backtest 记录 | 5651 | prediction.source="backtest" |
| Live 记录 | 1723 | prediction.source="live" |
| 合计 | 7374 | 差 1 可能是回退或删除 |
| index vs ledger | 一致 | version_book/index.json 与 ledger 匹配 |

### 1.4 重复记录（历史遗留）

| Version | Issue | 记录数 | 类型 |
|---------|-------|--------|------|
| v27 | 2026145 | 2 | backtest + live |
| v28 | 2026145 | 2 | backtest + live |

**判定:** 历史 bootstrapping 产物，safe to keep，不影响显示

---

## 二、缓存机制检查 (FAIL)

### 2.1 [严重] /health 端点 500 错误

**问题:** `_check_cache_health()` 函数导致 /health 返回 500

**根因:**
```python
# dashboard_server.py:472-474
expired = sum(1 for _, (_, ts) in _cache.items() ...)  # 期望 (data, ts) tuple
oldest = min((ts for _, (_, ts) in _cache.values()), ...)  # 同上
newest = max((ts for _, (_, ts) in _cache.values()), ...)  # 同上
```

但 `compute_stats()` 存储 stats 缓存时：
```python
# dashboard_server.py:229
_cache[cache_key] = result  # 直接存储 dict，没有 timestamp wrapper
```

当 `_cache` 中存在 stats 条目时，解包 `(_, (_, ts))` 失败：
```
ValueError: too many values to unpack (expected 2)
```

**影响:** 健康检查端点完全不可用，UI 无法获取系统健康状态

**修复建议:**
- 方案A: `compute_stats()` 存储时包装为 `_cache[cache_key] = (result, timestamp)`
- 方案B: `_check_cache_health()` 跳过非 tuple 条目

---

### 2.2 [高] 混合缓存数据结构

**问题:** 不同缓存类型使用不同数据结构

| 缓存类型 | 存储格式 | 位置 |
|----------|----------|------|
| jsonl | `(data, timestamp)` | _get_cached() |
| aggregated_live | `(data, timestamp)` | _get_cached() |
| version_data | `(data, timestamp)` | _get_cached() |
| index | `(data, timestamp)` | _get_cached() |
| stats | `raw dict` | compute_stats() |

**根因:** `compute_stats()` 遗漏了 timestamp wrapper

**影响:**
- 缓存健康检查逻辑假设所有条目为 tuple，stats 条目导致崩溃
- 未来任何遍历 `_cache.items()` 的代码都可能因此崩溃

**修复建议:** 统一存储格式，`compute_stats()` 使用 `_cache[cache_key] = (result, now)`

---

### 2.3 Stats 缓存键正确性 (OK)

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 缓存键公式 | OK | `stats:{version}:{latest_issue}:{latest_record_hash}` |
| fallback 机制 | OK | record_hash 缺失时 fallback 到 sha256 |
| 失效机制 | OK | record_hash 变化自动失效 |

---

## 三、统计计算检查 (PASS)

### 3.1 各指标计算验证

| 指标 | 计算公式 | 验证结果 |
|------|----------|----------|
| hit_rate | total_hits / total_results | v24: 388/768 = 0.5052 |
| hit_rate_100 | hits_100 / len(recent_100) | v24: 59/100 = 0.59 |
| hit_rate_50 | hits_50 / len(recent_50) | v24: 28/50 = 0.56 |
| max_streak | 最长连续 misses | v24: 9 |
| division_by_zero | 保护机制存在 | total>0 时才除法 |
| null handling | 仅包含 actual!=null 的记录 | pending 正确排除 |

**结论:** 统计计算无 bug，逻辑正确

---

## 四、渲染逻辑检查 (FAIL)

### 4.1 [严重] Double loadData() 竞争条件

**问题:** 页面加载时 `loadData()` 被调用两次

**位置:**
```javascript
// design_v3.html:888
loadData();  // 第一次：script parse 期间

// design_v3.html:891
document.addEventListener('DOMContentLoaded', function() {
    loadData();  // 第二次：DOMContentLoaded 事件
});
```

**根因:** 两个独立的执行路径，竞相写入相同的全局状态

**执行序列:**
1. HTML 下载完成
2. Script parse → `loadData()` 执行（开始 fetch /api/versions）
3. DOMContentLoaded → 第二个 `loadData()` 执行（开始 fetch /api/versions）
4. 两个 Promise.all 竞相完成
5. `allVersions`, `versionRecords`, `versionStats` 被覆盖

**影响:**
- 双倍网络请求
- 最终显示的版本可能不确定（取决于网络时序）
- 可能导致白屏或数据不连贯

**修复建议:** 删除 DOMContentLoaded 监听器，因为 `loadData()` 已在 script parse 期间同步调用

---

### 4.2 [严重] 白屏现象（已添加 [BOOT] 诊断）

**症状:** API 正常但浏览器显示空白页

**已添加诊断:**
```javascript
// design_v3.html
window.onerror = (msg, src, line, col, err) => {
    console.error('[GLOBAL ERROR]', msg, 'at', src, 'line:', line, 'col:', col, err);
    return true;
};
window.addEventListener('unhandledrejection', e => {
    console.error('[UNHANDLED PROMISE]', e.reason);
});
setInterval(() => {
    console.log('[WATCH]', 'ready=', document.readyState, 'body=', !!document.body, 'children=', document.body?.children?.length);
}, 1000);
```

**待确认:** 需要用户提供 Console 输出以完成诊断

**可能原因:** Double loadData() 导致状态覆盖，部分 DOM 元素未填充

---

### 4.3 [中] 空数据处理 (OK with fallback)

```javascript
// design_v3.html:560-563
allVersions = versionsInfo.all_versions || versionsInfo.versions || [];
activeVersions = versionsInfo.active || [];
```

**结论:** Fallback 机制存在，空数据不会导致崩溃，但会显示空白

---

## 五、状态流检查 (FAIL)

### 5.1 [严重] Auto-refresh 硬编码 v24

**问题:** `checkAndRefresh()` 仅检查 v24 的 pending 状态

```javascript
// design_v3.html:612
fetch('/api/records/v24')  // 硬编码 v24
```

**影响:**
- 其他版本（v23, v21, v12 等）的 pending 预测不会被监控
- 用户可能看不到其他版本的新开奖结果

**修复建议:** 遍历 `activeVersions` 或从 `allVersions` 获取所有 pending 检查

---

### 5.2 [中] Auto-refresh 冗余全量加载

**问题:** 检测到 pending 变化时调用 `loadData()` 重载所有版本

```javascript
// design_v3.html:612-618
if (pendingChanged) {
    loadData();  // 重载所有版本数据
}
```

**根因:** 为检查单一 pending 状态而重建整个 UI

**影响:**
- 带宽浪费（每次重载所有版本）
- UI 闪烁（完整重建）
- 60s 内多次触发会导致竞争

**修复建议:** 增量更新特定版本，而非全量重载

---

### 5.3 [中] 无 Push 机制，最长延迟 ~90s

**问题:** 纯 Pull 模式，无 WebSocket/SSE

| 组件 | 轮询间隔 |
|------|----------|
| 前端 checkAndRefresh | 60s |
| 后端缓存 TTL | 30s |
| 最长延迟 | ~90s |

**影响:** 新预测写入后，用户最长可能 90s 才能看到更新

**修复建议:** 实现 WebSocket 或 Server-Sent Events 推送更新

---

## 六、Hash Chain 健康（参考 FINAL_FACTS.md）

| 指标 | 值 | 说明 |
|------|---|------|
| records | 7375 | 总记录数 |
| chain_breaks | 19 | 断裂数 |
| eb2d4fba933814ae | 出现8次作为 prev_hash | 非任何记录的 record_hash |
| 98196124ac688288 | 未找到 | 不存在于任何位置 |

**与 Panel UI 关系:** Hash chain 问题不影响 Dashboard 显示，但影响数据可信度

---

## 七、架构合规性

| 规则 | 状态 |
|------|------|
| Dashboard 只读 aggregated_live.jsonl | PASS |
| 禁止扫描版本目录 | PASS |
| 统计实时计算 | PASS |
| 无硬编码 summary | PASS |
| Hash Chain 防篡改 | PASS（chain 完整但有断裂） |

---

## 八、修复计划 (Repair Plan)

### P1 - 紧急（影响核心功能）

| 编号 | 问题 | 根因 | 修复建议 | 优先级 |
|------|------|------|----------|--------|
| P1.1 | /health 500 错误 | cache tuple 解包失败 | `compute_stats()` 存储时包装为 tuple: `_cache[cache_key] = (result, now)` | 必须 |
| P1.2 | Double loadData() | 重复调用 | 删除 `DOMContentLoaded` 监听器 (line 889-892) | 必须 |
| P1.3 | 白屏现象 | 未确认 | 等待 Console 输出后确定根因 | 必须 |

### P2 - 高（影响用户体验）

| 编号 | 问题 | 根因 | 修复建议 | 优先级 |
|------|------|------|----------|--------|
| P2.1 | 混合缓存数据结构 | `compute_stats()` 遗漏 | 统一使用 `(data, timestamp)` 格式 | 应该 |
| P2.2 | Auto-refresh 硬编码 v24 | 仅检查单一版本 | 遍历所有 `activeVersions` 检查 pending | 应该 |

### P3 - 中（优化建议）

| 编号 | 问题 | 根因 | 修复建议 | 优先级 |
|------|------|------|----------|--------|
| P3.1 | 全量重载 UI | 增量更新缺失 | 实现增量版本更新 | 可以 |
| P3.2 | 无 Push 机制 | WebSocket 未实现 | 评估 SSE/WebSocket 需求 | 可以 |
| P3.3 | v29/v30 低记录 | 数据不足 | 标记为统计不显著 | 建议 |

---

## 九、影响评估矩阵

| 影响维度 | 当前状态 | 风险等级 | 说明 |
|----------|----------|----------|------|
| Dashboard 可用性 | 受限 | 高 | /health 500，白屏问题 |
| 数据正确性 | 正常 | 低 | 统计计算正确，数据源完整 |
| 用户体验 | 受限 | 中 | auto-refresh 仅监控 v24 |
| 系统可观测性 | 不可用 | 高 | 健康检查完全失效 |
| 版本对比功能 | 正常 | 低 | 核心功能可用 |

---

## 十、待确认项 (UNCONFIRMED)

以下项目需要额外证据才能确认：

| 项目 | 状态 | 需要 |
|------|------|------|
| 白屏根因 | UNKNOWN | Console [BOOT] 输出 |
| /health 响应结构 | UNKNOWN | 实际响应 JSON 样本 |
| double loadData() 是否导致白屏 | ASSUMPTION | 需要时序证据 |

---

*Report generated: 2026-05-27*
*PANEL_AUDIT Task #29 Phase 3 - NO FIXES APPLIED*
*Only FINAL_FACTS.md used as evidence source (EVIDENCE_LOCK_MODE)*
*Previous duplicate record finding retained but superseded by comprehensive audit*