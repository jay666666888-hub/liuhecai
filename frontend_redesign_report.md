# 麻将预测系统前端完整调研报告

## 1. 页面结构

- 路由：/ (index)
- 文件：predictor/templates/design_v3.html (2877行)
- 视图切换：通过 .view-switcher-btn 切换 predictor-view / foundation-view

Flask 路由：
- / → 渲染 design_v3.html
- /api/data → aggregated_live.jsonl
- /api/records → 按 source/version 获取记录
- /api/records/<version> → 获取指定版本记录
- /api/summary → 汇总统计
- /api/stats/all → 获取所有统计
- /api/stats/<category>/<stat_type> → 实时计算指定统计
- /api/stats/zodiac_number_map → 生肖→号码映射

## 2. 预测模块 (Predictor View)

内容区域：class="predictor-view-content"

数据结构：
{
  version: "v31",
  play_type: "liuhe",
  prediction: ["鼠","牛","虎"],
  issue: "2026150",
  actual: null,
  actual_list: null,
  special_number: null,
  hit: null,
  status: "pending"
}

数据来源：storage/aggregated_live.jsonl (只读此文件)

## 3. 统计模块 (Foundation View)

内容区域：class="foundation-stats-section"
数据来源：stats_engine.py 实时计算

统计类型：
- 生肖遗漏：compute_zodiac_miss()
- 波色遗漏：compute_wave_miss()
- 生肖热度：compute_hot_stats()
- 特码号码遗漏：compute_special_number_miss()

## 4. 未展示的统计数据

- 号码遗漏 (number_miss) - 已实现但未在UI展示
- 生肖→号码映射 - API存在但UI未展示

## 5. API 列表

数据 API：
- /api/records?source=live
- /api/records/<version>
- /api/summary

统计 API：
- /api/stats/all (全量统计)
- /api/stats/special_stats/zodiac_miss
- /api/stats/draw_stats/hot_stats
- /api/stats/zodiac_number_map

## 6. 屏幕布局

双视图结构：
- Header + 刷新按钮
- View Switcher [预测版][统计版]
- Stats Row (总预测/验证/命中率)
- Version Tabs (按玩法类型分组)
- Predictor View: Prediction Card + Record List
- Foundation View: 统计面板

## 7. 性能分析

- HTML 2877行，含大量内联CSS/JS
- 最大数据接口：/api/stats/all
- 缓存策略：30s TTL
- gzip 压缩 (JSON >1KB)

## 8. 最终总结

可复用组件：
- .view-switcher - 视图切换
- .stats-row - 统计摘要行
- .version-tabs - 版本标签组
- .zodiac-tag - 生肖标签
- .record-item - 记录项

需新增：
1. 点击交互：点击统计面板中的生肖/号码→跳转专项统计
2. 生肖→号码映射展示
3. 号码遗漏热力图：1-49号码遗漏可视化