# 澳门六合预测面板架构文档

## 数据流总览

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              入口 → 数据来源 → 聚合层 → 计算层 → 缓存层 → 渲染层      │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 1. 入口层 (Entry Point)

**文件**: `/mnt/c/Users/Admin/liuhecai/predictor/dashboard_server.py`

### 路由列表

| 路由 | 方法 | 功能 | 模板/响应 |
|------|------|------|----------|
| `/` | GET | 仪表盘主页 | `templates/design_v3.html` |
| `/api/data` | GET | 获取所有数据（含统计） | JSON |
| `/api/latest` | GET | 获取最新待验证预测 | JSON |
| `/api/versions` | GET | 获取所有版本信息 | JSON |
| `/api/records` | GET | 按 source 和 version 获取记录 | JSON |
| `/api/records/<version>` | GET | 获取指定版本的预测记录 | JSON |
| `/api/summary` | GET | 获取汇总统计（实时计算） | JSON |
| `/health` | GET | 总体健康状态 | JSON |
| `/health/data` | GET | 数据源健康检查 | JSON |
| `/health/cache` | GET | 缓存健康检查 | JSON |
| `/health/hashchain` | GET | 哈希链健康检查 | JSON |
| `/health/pipeline` | GET | Pipeline 健康检查 | JSON |

### 启动参数

```python
app.run(host='0.0.0.0', port=5188, debug=False)
```

### 核心规则

```python
# 规则：
# - Dashboard 只读 storage/aggregated_live.jsonl
# - Dashboard 不扫描版本目录
# - 统计从 ledger 实时计算，禁止手写 summary
```

---

## 2. 数据来源层 (Data Sources)

### 存储文件清单

| 文件路径 | 类型 | 用途 |
|----------|------|------|
| `storage/aggregated_live.jsonl` | JSONL | **唯一数据源** - 所有实盘预测聚合 |
| `storage/prediction_index.json` | JSON | 预测索引（版本→期号映射） |
| `version_book/index.json` | JSON | 版本账本索引 |
| `storage/prediction_ledger.jsonl` | JSONL | 原始预测账本（历史） |
| `storage/result_ledger.jsonl` | JSONL | 原始结果账本（历史） |

### 数据文件结构

#### aggregated_live.jsonl (唯一数据源)

```json
{
  "id": "2026125_v24_20250626_1622",
  "issue": "2026125",
  "version": "v24",
  "model": "v24_interval_predictor",
  "strategy": "v24_weighted_vote",
  "prediction": ["鼠", "牛", "虎", "兔", "龍", "蛇"],
  "play_type": "liuhe",
  "zodiac_list": ["鼠", "牛", "虎", "兔", "龍", "蛇", "馬"],
  "actual": "牛",
  "hit": true,
  "created_at": "2025-06-26T16:22:00",
  "source": "live",
  "status": "verified",
  "verified_at": "2025-06-26T20:30:00",
  "prev_hash": "abc123...",
  "record_hash": "def456..."
}
```

#### prediction_index.json

```json
{
  "version": 1,
  "updated_at": "2025-06-27T10:00:00",
  "versions": {
    "v24": {"latest_issue": "2026125", "pending_issue": "2026125"},
    "v23": {"latest_issue": "2026120", "pending_issue": null}
  }
}
```

#### version_book/index.json (兼容新旧结构)

```json
{
  "active": ["v24", "v23", "v21"],
  "active_by_play_type": {
    "liuhe": ["v24", "v23", "v21"],
    "pingte_yixiao": ["v12"]
  },
  "retired": [
    {"version": "v9", "status": "retired", "play_type": "liuhe"},
    {"version": "v10", "status": "retired", "play_type": "liuhe"}
  ],
  "experimental": [],
  "versions": ["v24", "v23", "v21", "v12", "v9", "v10"],
  "updated_at": "2025-06-27T10:00:00"
}
```

---

## 3. 聚合层 (Aggregation Layer)

### ledger_indexer.py

**文件**: `/mnt/c/Users/Admin/liuhecai/predictor/ledger_indexer.py`

**职责**:
- 按 version 分组聚合 ledger 数据
- 计算 hit_rate / max_streak 等统计
- 生成 version_book/vN/ 回测账本

**核心函数**:

```python
def load_ledger():
    """加载账本数据"""
    predictions = _read_jsonl("storage/prediction_ledger.jsonl")
    results = _read_jsonl("storage/result_ledger.jsonl")
    return predictions, results

def run_backtest_for_version(version: str, params: Dict) -> Dict:
    """对指定版本运行回测"""

def compute_live_stats(version: str, predictions: List, results: List) -> Dict:
    """计算实盘统计（基于回测账本）"""

def generate_version_books():
    """生成所有版本账本"""
```

### ledger_writer.py

**文件**: `/mnt/c/Users/Admin/liuhecai/predictor/ledger_writer.py`

**职责**:
- 实盘预测写入接口
- Hash Chain 防篡改
- 数据聚合到 aggregated_live.jsonl

**核心函数**:

```python
def write_live_prediction(version, issue, prediction, **kwargs) -> Dict:
    """写入实盘预测（唯一数据源写入 aggregated_live.jsonl）"""

def verify_prediction(version, issue, actual, zodiac_list) -> Tuple[bool, Dict]:
    """验证预测并更新 aggregated_live.jsonl"""

def read_live_predictions(version=None, limit=100) -> List[Dict]:
    """读取实盘预测（唯一数据源：aggregated_live.jsonl）"""

def aggregate_all_to_storage() -> int:
    """重新聚合所有版本到 storage/aggregated_live.jsonl"""

def verify_chain() -> Tuple[bool, List[str]]:
    """校验 hash 链完整性"""
```

### summary.py

**文件**: `/mnt/c/Users/Admin/liuhecai/predictor/summary.py`

**职责**:
- 从 aggregated_live.jsonl 实时计算 summary
- 不扫描版本目录
- 不手写 summary

**核心函数**:

```python
def compute_summary(index: Dict = None) -> Dict:
    """
    从 aggregated_live.jsonl 计算 summary（唯一数据源）
    """
```

### index_generator.py

**文件**: `/mnt/c/Users/Admin/liuhecai/predictor/index_generator.py`

**职责**:
- 扫描 predictors/active/ 目录
- 自动生成 index.json

**核心函数**:

```python
def generate_index(base_dir: str = None) -> dict:
    """
    扫描 predictors/active/ 和 predictors/retired/ 目录，生成 index 结构
    """

def write_index(base_dir: str = None):
    """生成并写入 index.json"""
```

### ledger.py (历史)

**文件**: `/mnt/c/Users/Admin/liuhecai/predictor/ledger.py`

**职责**:
- 预测账本 - 不可变记录系统
- append-only ledger

**核心类**:

```python
class PredictionLedger:
    def add_prediction(...) -> Dict:
        """添加预测记录"""

    def add_result(...) -> Dict:
        """添加开奖结果记录"""

    def get_prediction(issue: str) -> Optional[Dict]:
        """获取某期最新的预测"""

    def get_pending_predictions() -> List[Dict]:
        """获取待验证的预测列表"""

    def get_stats() -> Dict:
        """获取账本统计"""
```

---

## 4. 计算层 (Computation Layer)

### 统计数据计算

**位置**: `dashboard_server.py` - `compute_stats()` 函数

```python
def compute_stats(predictions, results, version=None) -> Dict:
    """
    返回:
    {
        'total_predictions': len(predictions),
        'total_results': total,
        'total_hits': hits,
        'hit_rate': hit_rate,
        'hit_rate_100': hits_100 / len(recent_100),
        'hit_rate_50': hits_50 / len(recent_50),
        'pending': len(predictions) - total,
        'max_streak': max_streak
    }
    """
```

### 缓存键策略 (CACHE_FIX_MODE)

```python
def _compute_cache_key(results, version):
    """
    缓存键规则：
    - stats:{version}:{latest_issue}:{latest_record_hash}
    - 若 record_hash 缺失，fallback 到 sha256(version+latest_issue+verified_count+total_hits)
    """
```

### 计算流程

1. 加载 aggregated_live.jsonl
2. 按 version 过滤（如指定）
3. 按 issue 倒序排序
4. 分离 predictions 和 results
5. 计算统计指标：
   - 总预测数
   - 已验证数
   - 命中数
   - 总命中率
   - 近100期命中率
   - 近50期命中率
   - 待验证数
   - 最高连错

---

## 5. 缓存层 (Caching Layer)

### 缓存实现

**文件**: `dashboard_server.py`

```python
_cache = {}
_cache_ttl = 30  # 秒

def _get_cached(key, loader, ttl=30):
    """带 TTL 的简单内存缓存"""
    now = datetime.now().timestamp()
    if key in _cache:
        data, timestamp = _cache[key]
        if now - timestamp < ttl:
            return data
    data = loader()
    _cache[key] = (data, now)
    return data

def _clear_cache():
    """清除缓存（数据更新时调用）"""
    _cache.clear()
```

### 缓存键清单

| 缓存键 | TTL | 用途 |
|--------|-----|------|
| `jsonl:{file_path}` | 30s | JSONL 文件缓存 |
| `aggregated_live:{version}` | 30s | 实盘数据缓存 |
| `version_data:{version}` | 30s | 版本数据缓存 |
| `index` | 30s | 版本索引缓存 |
| `stats:{version}:{issue}:{hash}` | 永久* | 统计结果缓存 |

*stats 缓存键基于 record_hash，当数据变化时自动失效

### 缓存健康检查

```python
def _check_cache_health():
    """检查缓存健康状态"""
    return {
        "entries": entries,
        "hit_rate": hit_rate,
        "expired": expired,
        "oldest_entry": datetime.fromtimestamp(oldest),
        "newest_entry": datetime.fromtimestamp(newest)
    }
```

---

## 6. 渲染层 (Rendering Layer)

### 模板文件

**文件**: `/mnt/c/Users/Admin/liuhecai/predictor/templates/design_v3.html`

### 页面结构

```
┌─────────────────────────────────────┐
│  Header (澳门六合预测)               │
│  ├── 健康状态胶囊 (点击展开详情)      │
│  └── 刷新按钮                        │
├─────────────────────────────────────┤
│  Stats Row (4列)                    │
│  ├── 总命中率                        │
│  ├── 近100期                        │
│  ├── 近50期                         │
│  └── 最长连错                        │
├─────────────────────────────────────┤
│  Version Tabs (玩法分组)             │
│  ├── [六肖] v24 v23 v21 ...         │
│  └── [平特一肖] v12 ...             │
├─────────────────────────────────────┤
│  Prediction Card (下一期预测)        │
│  ├── 期号                           │
│  ├── 六肖标签（点击复制）             │
│  └── 状态：⚡️待开奖                 │
├─────────────────────────────────────┤
│  Section Header (近期记录)           │
├─────────────────────────────────────┤
│  Record List (最多100条)            │
│  ├── 状态图标（绿/红/黄）            │
│  ├── 期号                           │
│  ├── 预测标签                       │
│  ├── 实际生肖                       │
│  └── 命中状态                       │
├─────────────────────────────────────┤
│  Footer (数据自动同步)               │
└─────────────────────────────────────┘
```

### JavaScript 组件

#### 全局状态

```javascript
let allVersions = [];
let activeVersions = [];
let activeByPlayType = {};
let retiredVersions = [];
let selectedVersion = 'v24';
let versionRecords = {};  // { version: records }
let versionStats = {};   // { version: stats }
let isHistoricalMode = false;
```

#### 核心函数

| 函数名 | 用途 |
|--------|------|
| `loadData()` | 初始化加载（versions + records） |
| `checkAndRefresh()` | 每60秒检查待开奖状态变化 |
| `buildVersionTabs()` | 渲染版本切换标签 |
| `selectVersion(version)` | 切换版本并更新显示 |
| `displayVersionData(version)` | 渲染选中版本的数据 |
| `copyPrediction()` | 复制预测结果到剪贴板 |
| `fetchHealthSummary()` | 获取健康状态摘要 |
| `fetchDetailedHealth()` | 获取健康状态详情 |
| `toggleHealthPopover()` | 切换健康弹窗 |

#### API 调用

```javascript
// 加载版本列表
GET /api/versions

// 加载指定版本记录
GET /api/records/{version}

// 加载健康状态
GET /health
GET /health/data
GET /health/cache
GET /health/hashchain
GET /health/pipeline
```

### 健康状态指示器

| 状态 | 图标 | 颜色 | 含义 |
|------|------|------|------|
| healthy | 🟢 | 绿色 | 正常运行 |
| degraded | 🟡 | 黄色 | 部分异常 |
| critical | 🔴 | 红色 | 严重异常 |
| unknown | ⚪️ | 灰色 | 状态不可用 |

### 自动刷新机制

```javascript
// 每60秒检查待开奖状态
autoRefreshInterval = setInterval(checkAndRefresh, 60000);

// 每30秒刷新健康状态
setInterval(fetchHealthSummary, 30000);
```

---

## 7. 可观测性 (Observability)

### 健康检查端点

| 端点 | 检查项 |
|------|--------|
| `/health/data` | 文件存在、大小、记录数、JSON解析 |
| `/health/cache` | 缓存条目数、过期数 |
| `/health/hashchain` | Hash链完整性、断裂数 |
| `/health/pipeline` | Pipeline锁状态、最后运行时间 |

### Hash Chain 验证

```python
def _check_hashchain_health():
    """检查哈希链健康状态"""
    # 检查项：
    # - total_records: 总记录数
    # - chain_breaks: 链断裂数
    # - missing_hash: 缺失hash数
    # - latest_hash: 最新记录的hash
```

### 日志记录

```python
def _write_health_log(status, checks):
    """写健康检查日志到 logs/health.log"""
```

---

## 8. 完整数据流图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                  数据流                                          │
└─────────────────────────────────────────────────────────────────────────────────┘

[浏览器]
    │
    │ GET /
    ▼
[dashboard_server.py] ──render_template──▶ [design_v3.html]
    │                                              │
    │                                              │ JavaScript
    │                                              ▼
    │                                         [loadData()]
    │                                              │
    │◀─────────────────────────────────────────────┤
    │                                              │
    │ GET /api/versions                           │ GET /api/records/{version}
    ▼                                              ▼
[index_generator.py]                      [dashboard_server.py]
    │ generate_index()                                │
    │      │                                         │
    │      │ 读取 predictors/active/metadata.json     │
    │      ▼                                         │
    │ [index.json]                                    │
    │      │                                         │
    │◀─────┴─────────────────────────────────────────┤
    │                                                 │
    │ GET /api/data 或 /api/records                  │
    ▼                                                 │
[_load_aggregated_live()]                               │
    │                                                 │
    │ 读取 storage/aggregated_live.jsonl             │
    │ (唯一数据源)                                    │
    ▼                                                 │
[compute_stats()]                                      │
    │                                                 │
    │ 计算统计：hit_rate, max_streak 等              │
    │                                                 │
    │ 缓存键: stats:{version}:{issue}:{hash}         │
    ▼                                                 │
[_get_cached()]                                        │
    │                                                 │
    │ TTL: 30秒                                      │
    ▼                                                 │
[JSON 响应] ◀─────────────────────────────────────────┘
    │
    │ JavaScript 更新 DOM
    ▼
[浏览器渲染]

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                  写入流程                                         │
└─────────────────────────────────────────────────────────────────────────────────┘

[预测器调用]
    │
    │ write_live_prediction()
    ▼
[ledger_writer.py]
    │
    │ Hash Chain 计算
    │ record_hash = sha256(issue|version|prediction|actual|hit|prev_hash)
    ▼
[原子写入 storage/aggregated_live.jsonl]
    │
    │ 更新 prediction_index.json
    ▼
[_clear_cache()]
    │
    │ 清除 _cache
    ▼
[下次请求触发重新加载]
```

---

## 9. 关键规则汇总

### Dashboard 规则

1. **只读 aggregated_live.jsonl** - 不扫描版本目录
2. **禁止手写 summary** - 实时计算
3. **Hash Chain 防篡改** - 每条记录有 hash
4. **TTL 缓存** - 30秒自动过期
5. **唯一数据源** - 写入和读取统一

### 版本状态

| 状态 | 描述 | 行为 |
|------|------|------|
| active | 活跃版本 | 完整预测记录 |
| retired | 退役版本 | 仅统计摘要 |
| experimental | 实验版本 | 不显示在面板 |

### 玩法类型

| play_type | 描述 | 显示 |
|-----------|------|------|
| liuhe | 六肖预测 | 6个生肖标签 |
| pingte_yixiao | 平特一肖 | 7个生肖标签 + actual_list |

---

## 10. 文件清单

| 文件路径 | 类型 | 描述 |
|----------|------|------|
| `/mnt/c/Users/Admin/liuhecai/predictor/dashboard_server.py` | Python | Web服务入口 |
| `/mnt/c/Users/Admin/liuhecai/predictor/templates/design_v3.html` | HTML | 前端模板 |
| `/mnt/c/Users/Admin/liuhecai/predictor/ledger.py` | Python | 历史账本（只读） |
| `/mnt/c/Users/Admin/liuhecai/predictor/ledger_indexer.py` | Python | 版本账本生成 |
| `/mnt/c/Users/Admin/liuhecai/predictor/ledger_writer.py` | Python | 实盘写入接口 |
| `/mnt/c/Users/Admin/liuhecai/predictor/summary.py` | Python | 统计计算模块 |
| `/mnt/c/Users/Admin/liuhecai/predictor/index_generator.py` | Python | 索引生成器 |
| `/mnt/c/Users/Admin/liuhecai/storage/aggregated_live.jsonl` | JSONL | 唯一数据源 |
| `/mnt/c/Users/Admin/liuhecai/storage/prediction_index.json` | JSON | 预测索引 |
| `/mnt/c/Users/Admin/liuhecai/version_book/index.json` | JSON | 版本索引 |

---

*文档生成时间: 2025-06-27*
*最后更新: 架构文档 v1.0*
