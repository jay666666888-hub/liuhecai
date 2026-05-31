# 澳门六合预测系统 - 架构审查报告

> 日期：2026-05-25
> 版本：v1.0
> 状态：审查完成，待实施

---

## 第一部分：系统全景架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           澳门六合预测系统架构                                │
└─────────────────────────────────────────────────────────────────────────────┘

                          ┌─────────────────┐
                          │   数据源 API     │
                          │ (实时开奖结果)   │
                          └────────┬────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Layer 1: 数据获取 (data_fetcher)                                           │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ fetch_year_data │    │ build_standard  │    │ get_all_records │          │
│  │   (缓存机制)    │    │    _records     │    │  (多年份聚合)   │          │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Layer 2: 预测协调 (orchestrator)                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ sync_latest_    │    │ verify_         │    │ Predict         │          │
│  │ results()       │    │ prediction()    │    │ Orchestrator    │          │
│  │ (同步开奖)      │    │ (验证上期)      │    │ (多版本并行)    │          │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
          ┌────────────┐  ┌────────────┐  ┌────────────┐
          │   v5      │  │   v12     │  │   v23     │
          │ Adapter   │  │ Adapter   │  │ Native    │
          │ (Legacy)  │  │ (Legacy)  │  │ (Native)  │
          └────────────┘  └────────────┘  └────────────┘
                    │              │              │
                    └──────────────┼──────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Layer 3: 标准化 (normalizer)                                                │
│  ┌─────────────────┐    ┌─────────────────┐                                  │
│  │ ScoreNormalizer │    │ CrossVersion    │                                  │
│  │ (分数标准化)    │    │ Comparator      │                                  │
│  │                 │    │ (跨版本比较)    │                                  │
│  └─────────────────┘    └─────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Layer 4: 数据写入 (ledger_writer)                                           │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ write_live_     │    │ verify_         │    │ _update_        │          │
│  │ prediction()    │    │ prediction()    │    │ aggregated()    │          │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
          ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
          │ version_book/   │  │ version_book/  │  │ version_book/   │
          │ {v}/live_      │  │ {v}/backtest_   │  │ index.json      │
          │ ledger.jsonl    │  │ ledger.jsonl    │  │ (版本索引)      │
          └─────────────────┘  └─────────────────┘  └─────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Layer 5: Dashboard (dashboard_server)                                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐          │
│  │ /api/summary    │    │ /api/records    │    │ /api/versions   │          │
│  │ (统计汇总)      │    │ (记录查询)      │    │ (版本信息)      │          │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘          │
│                            │                                           │
│                            ▼                                           │
│                    ┌─────────────────┐                                 │
│                    │ design_v3.html  │                                 │
│                    │ (前端展示)      │                                 │
│                    └─────────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────────┘

                                  CRON
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                              ▼
          ┌─────────────────┐          ┌─────────────────┐
          │ daily_update.sh  │          │  predict_cycle  │
          │ (每日定时触发)   │          │  .py            │
          └─────────────────┘          └─────────────────┘
```

---

## 第二部分：模块职责图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              模块职责矩阵                                    │
├──────────────────┬────────────────────────┬─────────────────────────────────┤
│      模块        │         职责          │           边界                  │
├──────────────────┼────────────────────────┼─────────────────────────────────┤
│ data_fetcher     │ • 从 API 获取开奖数据  │ • 只读 API，不写任何 ledger     │
│                  │ • 缓存管理             │ • 不做预测                       │
│                  │ • 多年份聚合           │                                 │
├──────────────────┼────────────────────────┼─────────────────────────────────┤
│ orchestrator     │ • 多版本预测协调       │ • 不直接调用 data_fetcher       │
│                  │ • sync_latest_results  │   (通过 ledger_writer)         │
│                  │ • 验证上期             │ • 不写具体预测逻辑              │
│                  │ • 生成下期预测         │                                 │
├──────────────────┼────────────────────────┼─────────────────────────────────┤
│ base_predictor   │ • 定义预测器接口       │ • 只定义规范，不实现预测       │
│                  │ • load_predictor()    │                                 │
│                  │ • PredictorRegistry     │                                 │
├──────────────────┼────────────────────────┼─────────────────────────────────┤
│ v5/v7/v12/v21    │ • 封装旧版预测逻辑     │ • 不读写任何 ledger            │
│ _adapter         │ • 实现 predict()        │ • 不直接访问 API               │
│                  │ • 保持 legacy 兼容性     │                                 │
├──────────────────┼────────────────────────┼─────────────────────────────────┤
│ v23/v24          │ • 原生预测器实现       │ • 不读写任何 ledger            │
│ _interval_predictor │ • 多策略组合投票     │ • 不直接访问 API               │
├──────────────────┼────────────────────────┼─────────────────────────────────┤
│ normalizer       │ • 分数标准化           │ • 不写 ledger                  │
│                  │ • 跨版本比较           │ • 不做预测                      │
├──────────────────┼────────────────────────┼─────────────────────────────────┤
│ ledger_writer    │ • 写入 live_ledger     │ • 不做预测                      │
│                  │ • 验证预测结果         │                                 │
│                  │ • 更新 aggregated       │                                 │
├──────────────────┼────────────────────────┼─────────────────────────────────┤
│ dashboard_server │ • 读取 live_ledger     │ • 不写任何 ledger              │
│                  │ • 统计计算             │ • 不做预测                      │
│                  │ • 提供 API 和前端      │                                 │
├──────────────────┼────────────────────────┼─────────────────────────────────┤
│ index.json       │ • 版本索引             │ • 只读配置                      │
│                  │ • active/retired 列表   │                                 │
├──────────────────┼────────────────────────┼─────────────────────────────────┤
│ version_book/    │ • 运行时数据存储       │ • 不参与业务逻辑                │
│ {v}/            │ • 预测记录             │ • 不直接被 Dashboard 读取       │
│                  │ • backtest 数据        │                                 │
└──────────────────┴────────────────────────┴─────────────────────────────────┘
```

---

## 第三部分：数据流图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据流图                                        │
└─────────────────────────────────────────────────────────────────────────────┘

【实盘流程】
                         API
                          │
                          ▼
              ┌─────────────────────┐
              │   data_fetcher      │
              │  get_all_records()  │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   result_ledger     │ ◄── 存储开奖结果
              │  (storage/)         │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   sync_latest      │
              │   _results()       │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   verify_          │
              │   prediction()     │
              └──────────┬──────────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ live_ledger │ │ live_ledger │ │ live_ledger │
    │ (v5)        │ │ (v12)       │ │ (v23)       │
    │ version_book│ │ version_book│ │ version_book│
    └─────────────┘ └─────────────┘ └─────────────┘

【预测流程】
                         API
                          │
                          ▼
              ┌─────────────────────┐
              │   data_fetcher      │
              │  build_standard_    │
              │  records()          │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ PredictOrchestrator │
              │   predict()        │
              └──────────┬──────────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ V5Predictor │ │ V12Predictor│ │ V23Predictor│
    │ predict()  │ │ predict()   │ │ predict()   │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                           ▼
              ┌─────────────────────┐
              │ write_live_        │
              │ prediction()       │
              └──────────┬──────────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ live_ledger │ │ live_ledger │ │ live_ledger │
    │ (v5)        │ │ (v12)       │ │ (v23)       │
    └─────────────┘ └─────────────┘ └─────────────┘

【Dashboard 展示流程】
              ┌─────────────────────┐
              │   _compute_summary()│
              │   (dashboard_server)│
              └──────────┬──────────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ live_ledger │ │ live_ledger │ │ live_ledger │
    │ (v5)        │ │ (v12)       │ │ (v23)       │
    │ version_book│ │ version_book│ │ version_book│
    └─────────────┘ └─────────────┘ └─────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   API Response      │
              │   JSON + HTML       │
              └─────────────────────┘
```

---

## 第四部分：发现的问题

### Critical（必须修复）

| ID | 问题 | 位置 | 描述 |
|----|------|------|------|
| C1 | **数据同步不一致** | ledger_writer._update_aggregated_record | verify_prediction 更新 live_ledger 后，aggregated_live.jsonl 同步可能失败/丢失 |
| C2 | **Dashboard 读取来源不一致** | dashboard_server._compute_summary | 之前读 aggregated_live.jsonl，与 live_ledger 可能不同步（已部分修复：现直接读 live_ledger） |
| C3 | **版本目录缺少 metadata.json** | version_book/v5,v7,v21/ | 目录存在但缺少 metadata.json，导致 Dashboard 无法获取 strategy_type |
| C4 | **backtest_ledger 未纳入 live_ledger** | version_book/v5,v7,v21,v23,v24/ | 6 个版本都有 backtest_ledger，但部分版本未合并到 live_ledger |

### Medium（建议修复）

| ID | 问题 | 位置 | 描述 |
|----|------|------|------|
| M1 | **orchestrator 硬编码 years** | orchestrator.run_live_cycle | 硬编码 `[2024, 2025, 2026]`，应从配置读取 |
| M2 | **没有统一的配置管理** | cron/predict_cycle.py | ACTIVE_VERSIONS 在 cron 和 orchestrator 两处定义 |
| M3 | **index.json 没有自动更新机制** | version_book/index.json | 退役版本时需要手动更新 index.json |
| M4 | **cron 没有错误告警** | cron/daily_update.sh | 失败时没有通知机制 |
| M5 | **storage 目录存在多个遗留文件** | storage/ | prediction_ledger.jsonl 等旧文件未被清理 |
| M6 | **dashboard_server 没有健康检查** | dashboard_server.py | 无心跳/健康检查接口 |

### Suggestion（未来升级）

| ID | 问题 | 位置 | 描述 |
|----|------|------|------|
| S1 | **没有版本健康度评分** | - | 无法量化哪个版本表现更好 |
| S2 | **没有 A/B 测试框架** | predictor/abtest/ | abtest/ 目录存在但未集成到主流程 |
| S3 | **没有模型版本控制** | - | 新模型上线没有灰度发布机制 |
| S4 | **缺少完整的测试套件** | tests/ | 单元测试覆盖不足 |
| S5 | **没有数据质量监控** | - | 缺少数据完整性校验 |

---

## 第五部分：重构方案

### Phase 1：必须修（保证系统基本可用）

#### 1.1 统一配置管理

**问题**：ACTIVE_VERSIONS 在多处定义，orchestrator 硬编码 years

**方案**：
```
configs/
├── active_versions.json    # 活跃版本列表
└── data_years.json          # 数据年份配置

改动点：
1. 创建 configs/active_versions.json
2. orchestrator.run_live_cycle() 从配置读取
3. cron/predict_cycle.py 从配置读取
```

#### 1.2 修复 metadata.json 缺失

**问题**：v5, v7, v21 缺少 metadata.json

**方案**：
```
version_book/
├── v5/metadata.json    # 补充
├── v7/metadata.json    # 补充
├── v12/metadata.json   # 已有
├── v21/metadata.json   # 补充
├── v23/metadata.json   # 已有
└── v24/metadata.json   # 已有
```

#### 1.3 清理 storage 目录

**问题**：storage/ 存在未使用的旧文件

**方案**：
```
storage/
├── result_ledger.jsonl          # 保留，开奖结果
├── aggregated_live.jsonl         # 保留，Dashboard 数据源
├── prediction_index.json         # 保留，索引
└── prediction_ledger.jsonl       # 删除，遗留文件
└── ledger_snapshot/              # 删除或归档
```

#### 1.4 Dashboard 健康检查接口

**方案**：添加 `/api/health` 接口

```python
@app.route('/api/health')
def api_health():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "versions": list_versions(),
        "latest_result_issue": get_latest_issue()
    })
```

---

### Phase 2：建议修（提升系统健壮性）

#### 2.1 建立版本生命周期管理

**问题**：退役版本需要手动更新 index.json

**方案**：
```
scripts/
├── activate_version.py    # 激活版本
├── retire_version.py      # 退役版本
└── sync_versions.py       # 同步版本状态

流程：
1. activate_version v25 → 更新 index.json active
2. retire_version v12 → 移动到 retired，更新 index.json
```

#### 2.2 建立数据同步验证机制

**问题**：aggregated_live 和 live_ledger 可能不一致

**方案**：
```python
def verify_data_consistency():
    """验证所有 live_ledger 与 aggregated 一致"""
    for version in active_versions:
        live_records = read_live_ledger(version)
        agg_records = [r for r in aggregated if r['version'] == version]

        # 检查期号一致性
        live_issues = set(r['issue'] for r in live_records)
        agg_issues = set(r['issue'] for r in agg_records)

        if live_issues != agg_issues:
            log_warning(f"{version}: ledger 不一致")
```

#### 2.3 完善错误告警

**问题**：cron 失败没有通知

**方案**：
```bash
# cron/daily_update.sh
python3 cron/predict_cycle.py >> /tmp/liuhecai_update.log 2>&1
if [ $? -ne 0 ]; then
    # 发送告警
    curl -X POST "http://notify.example.com/alert" -d "预测流程失败"
fi
```

---

### Phase 3：未来升级

#### 3.1 版本健康度评分

```python
def compute_version_score(version: str) -> dict:
    """
    计算版本健康度
    - 命中率 (40%)
    - 连对 (20%)
    - 稳定性 (20%)
    - 样本量 (20%)
    """
    records = read_live_ledger(version)
    verified = [r for r in records if r.get('actual')]

    return {
        'hit_rate': hits/len(verified),
        'max_streak': compute_max_streak(verified),
        'stability': compute_stability(verified),
        'sample_size': len(verified)
    }
```

#### 3.2 A/B 测试框架

```python
class ABTestFramework:
    """A/B 测试框架"""

    def assign(self, user_id: str, version_a: str, version_b: str) -> str:
        """流量分配"""
        bucket = hash(user_id) % 100
        return version_a if bucket < 50 else version_b

    def track(self, experiment_id: str, version: str, outcome: dict):
        """记录实验结果"""
        pass

    def analyze(self, experiment_id: str) -> dict:
        """分析实验结果"""
        pass
```

#### 3.3 模型灰度发布

```python
def deploy_version(version: str, traffic_percent: int):
    """
    灰度发布新版本
    1. 激活版本（但不加入 orchestrator）
    2. 分配指定比例流量
    3. 监控效果
    4. 全量切换或回滚
    """
    pass
```

---

## 第六部分：迁移计划

### 步骤 1：创建统一配置（1天）

```
1.1 创建 configs/active_versions.json
    - 包含 active: ["v5", "v7", "v12", "v21", "v23", "v24"]

1.2 修改 orchestrator.py
    - 从 configs/ 读取 active_versions
    - 从 configs/ 读取 data_years

1.3 修改 cron/predict_cycle.py
    - 从配置读取，不再硬编码

1.4 测试
    - 运行 predict_cycle.py 验证
```

### 步骤 2：补充 metadata.json（1天）

```
2.1 为 v5, v7, v21 创建 metadata.json

2.2 验证 Dashboard 能正确显示 strategy_type

2.3 更新 index.json 确保与配置一致
```

### 步骤 3：数据清理（1天）

```
3.1 删除 storage/prediction_ledger.jsonl

3.2 检查其他遗留文件

3.3 验证系统仍正常工作
```

### 步骤 4：健康检查接口（1天）

```
4.1 添加 /api/health 接口

4.2 添加 /api/version/{v}/status 接口

4.3 测试健康检查
```

### 步骤 5：版本生命周期脚本（2天）

```
5.1 创建 scripts/activate_version.py

5.2 创建 scripts/retire_version.py

5.3 创建 scripts/sync_versions.py

5.4 测试退役和激活流程
```

### 步骤 6：数据一致性验证（1天）

```
6.1 添加 verify_data_consistency() 函数

6.2 添加定时任务检查一致性

6.3 修复发现的不一致问题
```

---

## 第七部分：风险分析

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 配置不一致 | 中 | 高 | 统一配置中心，单点修改 |
| 数据丢失 | 低 | 极高 | 保留备份，变更前验证 |
| 版本冲突 | 中 | 中 | 灰度发布，监控指标 |
| API 不可用 | 低 | 高 | 本地缓存，降级策略 |
| 预测器回归 | 中 | 高 | 定期回测，阈值告警 |

---

## 第八部分：未来扩展建议

### 8.1 多模型并行

```python
# 未来架构
class ModelRouter:
    """模型路由"""

    def route(self, issue: str) -> List[PredictionResult]:
        """根据issue选择模型组合"""
        pass

class EnsemblePredictor:
    """集成预测器"""

    def predict(self, history: List[Dict]) -> PredictionResult:
        """多模型加权投票"""
        pass
```

### 8.2 实时特征工程

```python
class FeatureEngine:
    """特征工程引擎"""

    def extract(self, records: List[Dict]) -> Dict[str, float]:
        """提取实时特征"""
        return {
            'momentum': compute_momentum(records),
            'seasonality': compute_seasonality(records),
            'gap_factor': compute_gap_factor(records)
        }
```

### 8.3 自适应预测

```python
class AdaptivePredictor:
    """自适应预测器"""

    def __init__(self):
        self.weights = {}  # 动态调整
        self.performance = {}  # 追踪每个版本表现

    def adjust_weights(self):
        """根据近期表现调整权重"""
        pass
```

---

## 附录：文件清单

### 当前项目结构

```
liuhecai/
├── predictor/
│   ├── base_predictor.py          # 预测器基类
│   ├── orchestrator.py            # 协调器
│   ├── normalizer.py              # 标准化
│   ├── ledger_writer.py           # 数据写入
│   ├── dashboard_server.py        # Dashboard
│   ├── v5_adapter.py              # v5 封装
│   ├── v7_adapter.py              # v7 封装
│   ├── v12_adapter.py             # v12 封装
│   ├── v21_adapter.py             # v21 封装
│   ├── v23_interval_predictor.py   # v23 原生
│   ├── v24_interval_predictor.py   # v24 原生
│   └── templates/
│       └── design_v3.html         # 前端
├── cron/
│   ├── predict_cycle.py           # 预测入口
│   └── daily_update.sh            # 定时任务
├── version_book/
│   ├── index.json                 # 版本索引
│   ├── v5/                         # v5 目录
│   ├── v7/
│   ├── v12/
│   ├── v21/
│   ├── v23/
│   └── v24/
├── storage/
│   ├── result_ledger.jsonl        # 开奖结果
│   ├── aggregated_live.jsonl       # 聚合数据
│   └── prediction_index.json      # 索引
├── configs/                        # 配置目录（待创建）
├── scripts/                        # 工具脚本（待创建）
└── docs/                           # 文档
```

### 建议新增文件

```
configs/
├── active_versions.json           # 活跃版本
├── data_years.json               # 数据年份
└── notification.json              # 通知配置

scripts/
├── activate_version.py           # 激活版本
├── retire_version.py             # 退役版本
├── sync_versions.py              # 同步版本
└── verify_consistency.py         # 验证一致性
```

---

**报告完成**