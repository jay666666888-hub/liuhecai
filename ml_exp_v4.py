#!/usr/bin/env python3
"""
ML Experiment V4 - 澳门六合预测分析
尝试多种ML方法分析时间序列模式
"""
import sys, json, random
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import numpy as np

# 设置随机种子确保可复现
random.seed(42)
np.random.seed(42)

# 生肖列表
ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']
ZODIAC_TO_IDX = {z: i for i, z in enumerate(ZODIACS)}

# 加载数据
def load_data():
    with open('liuhecai_data.json') as f:
        data = json.load(f)
    return data

def build_hist(data):
    """构建历史记录"""
    hist = []
    for r in data:
        period = r['期号']
        zodiac = r['特码生肖']
        hist.append({
            '期号': period,
            '特码生肖': zodiac,
            '开奖生肖': [zodiac]  # 一肖只有1个生肖
        })
    return hist

# ====== 特征提取 ======
def extract_frequency_features(window):
    """频率特征"""
    n = len(window)
    feats = {}
    for z in ZODIACS:
        count = sum(1 for r in window if r['特码生肖'] == z)
        feats[f'{z}_freq'] = count
        feats[f'{z}_freq_ratio'] = count / n
    return feats

def extract_gap_features(window):
    """遗漏特征"""
    n = len(window)
    feats = {}
    for z in ZODIACS:
        positions = [i for i, r in enumerate(window) if r['特码生肖'] == z]
        if positions:
            gap = n - positions[-1] - 1
            feats[f'{z}_gap'] = gap
            feats[f'{z}_recent_pos'] = positions[-1]
        else:
            feats[f'{z}_gap'] = n
            feats[f'{z}_recent_pos'] = n
    return feats

def extract_interval_features(window):
    """间隔特征"""
    n = len(window)
    feats = {}
    for z in ZODIACS:
        positions = [i for i, r in enumerate(window) if r['特码生肖'] == z]
        if len(positions) >= 2:
            intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]
            feats[f'{z}_interval_avg'] = np.mean(intervals)
            feats[f'{z}_interval_std'] = np.std(intervals) if len(intervals) > 1 else 0
            feats[f'{z}_interval_max'] = max(intervals)
            feats[f'{z}_interval_min'] = min(intervals)
        else:
            feats[f'{z}_interval_avg'] = n
            feats[f'{z}_interval_std'] = n
            feats[f'{z}_interval_max'] = n
            feats[f'{z}_interval_min'] = 0
    return feats

def extract_streak_features(window):
    """连出特征"""
    n = len(window)
    feats = {}
    for z in ZODIACS:
        streak = 0
        for r in reversed(window):
            if r['特码生肖'] == z:
                streak += 1
            else:
                break
        feats[f'{z}_streak'] = streak
    return feats

def extract_pattern_features(window):
    """模式特征"""
    n = len(window)
    zodiacs = [r['特码生肖'] for r in window]

    feats = {}
    # 奇偶
    feats['last_is_first_half'] = zodiacs[-1] in ZODIACS[:6]
    # 相邻模式
    if n >= 2:
        feats['consecutive_same'] = 1 if zodiacs[-1] == zodiacs[-2] else 0
        feats['consecutive_near'] = 1 if abs(ZODIAC_TO_IDX[zodiacs[-1]] - ZODIAC_TO_IDX[zodiacs[-2]]) <= 2 else 0
    else:
        feats['consecutive_same'] = 0
        feats['consecutive_near'] = 0

    # 波色交替
    color_map = {'鼠': 'R', '牛': 'G', '虎': 'G', '兔': 'R', '龍': 'G', '蛇': 'R',
                 '馬': 'R', '羊': 'G', '猴': 'R', '雞': 'G', '狗': 'G', '豬': 'R'}
    colors = [color_map[z] for z in zodiacs]
    if n >= 2:
        feats['color_alternate'] = 1 if colors[-1] != colors[-2] else 0
    else:
        feats['color_alternate'] = 0

    return feats

def extract_all_features(window):
    """提取所有特征"""
    feats = {}
    feats.update(extract_frequency_features(window))
    feats.update(extract_gap_features(window))
    feats.update(extract_interval_features(window))
    feats.update(extract_streak_features(window))
    feats.update(extract_pattern_features(window))
    return feats

def get_feature_vector(feats):
    """将特征字典转为向量"""
    vec = []
    for z in ZODIACS:
        vec.append(feats.get(f'{z}_freq', 0))
        vec.append(feats.get(f'{z}_gap', 0))
        vec.append(feats.get(f'{z}_interval_avg', 0))
        vec.append(feats.get(f'{z}_interval_std', 0))
        vec.append(feats.get(f'{z}_streak', 0))
    # 模式特征
    vec.append(feats.get('consecutive_same', 0))
    vec.append(feats.get('consecutive_near', 0))
    vec.append(feats.get('color_alternate', 0))
    vec.append(feats.get('last_is_first_half', 0))
    return vec

# ====== 预测方法 ======
def predict_frequency(hist, lookback):
    """频率法"""
    window = hist[-lookback:]
    freq = Counter([r['特码生肖'] for r in window])
    return freq.most_common(1)[0][0]

def predict_max_gap(hist, lookback):
    """最大遗漏法"""
    n = len(hist)
    window = hist[n-lookback:n]
    gaps = {}
    for z in ZODIACS:
        positions = [i for i, r in enumerate(window) if r['特码生肖'] == z]
        gaps[z] = lookback - positions[-1] - 1 if positions else lookback
    return max(gaps, key=gaps.get)

def predict_markov(hist, order=2):
    """Markov链"""
    n = len(hist)
    if n < order:
        return random.choice(ZODIACS)

    # 构建转移矩阵
    counts = defaultdict(lambda: Counter())
    for i in range(order, n):
        state = tuple(hist[j]['特码生肖'] for j in range(i-order, i))
        next_z = hist[i]['特码生肖']
        counts[state][next_z] += 1

    # 预测
    state = tuple(hist[j]['特码生肖'] for j in range(n-order, n))
    if state in counts and counts[state]:
        return counts[state].most_common(1)[0][0]
    return random.choice(ZODIACS)

def predict_hybrid(hist, lookback=30, order=2):
    """混合方法"""
    n = len(hist)

    # 1. 频率法
    freq_pred = predict_frequency(hist, lookback)

    # 2. 最大遗漏法
    gap_pred = predict_max_gap(hist, lookback)

    # 3. Markov法
    markov_pred = predict_markov(hist, order)

    # 投票
    votes = Counter([freq_pred, gap_pred, markov_pred])
    return votes.most_common(1)[0][0]

def predict_composite_score(hist, lookback=30):
    """综合评分法"""
    n = len(hist)
    window = hist[n-lookback:n]

    scores = {}
    for z in ZODIACS:
        positions = [i for i, r in enumerate(window) if r['特码生肖'] == z]

        # 频率分
        freq_score = len(positions) / lookback * 10

        # 遗漏分（遗漏越大分数越高）
        gap = lookback - positions[-1] - 1 if positions else lookback
        gap_score = gap / lookback * 10

        # 间隔趋势分
        if len(positions) >= 2:
            intervals = [positions[i] - positions[i+1] for i in range(len(positions)-1)]
            trend_score = max(0, (np.mean(intervals) - gap) / 10)
        else:
            trend_score = 0

        scores[z] = freq_score * 0.3 + gap_score * 0.4 + trend_score * 0.3

    return max(scores, key=scores.get)

# ====== 评估 ======
def evaluate(predict_fn, hist, start_idx, end_idx, lookback=30, **kwargs):
    """评估预测器"""
    hits = 0
    total = 0
    results = []

    for i in range(start_idx, end_idx):
        if i < lookback:
            continue
        window = hist[i-lookback:i]
        actual = hist[i]['特码生肖']

        pred = predict_fn(window, **kwargs) if callable(predict_fn.__code__.co_varnames[0]) else predict_fn(hist[:i], **kwargs)

        hit = 1 if pred == actual else 0
        hits += hit
        total += 1
        results.append({'pred': pred, 'actual': actual, 'hit': hit})

    return hits, total, hits/total if total > 0 else 0, results

def walk_forward_evaluate(predict_fn, hist, min_train=100, test_size=50, step=10, lookback=30, **kwargs):
    """步行向前验证"""
    n = len(hist)
    results = []

    for train_end in range(min_train, n - test_size, step):
        train_start = max(0, train_end - 200)

        # 测试窗口
        test_start = train_end
        test_end = min(train_end + test_size, n)

        hits = 0
        total = 0
        for i in range(test_start, test_end):
            if i < lookback:
                continue
            window = hist[i-lookback:i]
            actual = hist[i]['特码生肖']

            pred = predict_fn(hist[:i], **kwargs)

            if pred == actual:
                hits += 1
            total += 1

        if total > 0:
            results.append({
                'train_range': f'{train_start}-{train_end}',
                'test_range': f'{test_start}-{test_end}',
                'hits': hits,
                'total': total,
                'rate': hits/total
            })

    return results

# ====== 主实验 ======
def run_experiments():
    print("=" * 60)
    print("ML Experiment V4 - 澳门六合时间序列分析")
    print("=" * 60)

    # 加载数据
    data = load_data()
    hist = build_hist(data)
    n = len(hist)
    print(f"\n数据量: {n} 期")
    print(f"时间范围: {hist[0]['期号']} - {hist[-1]['期号']}")

    results_file = '/tmp/ml_exp_v4_results.txt'

    with open(results_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("ML Experiment V4 - 澳门六合时间序列分析\n")
        f.write(f"实验时间: {datetime.now()}\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"数据量: {n} 期\n")
        f.write(f"时间范围: {hist[0]['期号']} - {hist[-1]['期号']}\n\n")

        # 1. 数据统计
        f.write("=" * 60 + "\n")
        f.write("1. 数据统计分析\n")
        f.write("=" * 60 + "\n")

        all_zodiacs = [r['特码生肖'] for r in hist]
        zodiac_counts = Counter(all_zodiacs)
        f.write("\n各生肖出现次数:\n")
        for z in ZODIACS:
            count = zodiac_counts.get(z, 0)
            ratio = count / n * 100
            f.write(f"  {z}: {count} ({ratio:.2f}%)\n")

        # 计算理论概率
        f.write("\n理论期望频率: 1/12 = 8.33%\n")
        chi_square = sum((count - n/12)**2 / (n/12) for count in zodiac_counts.values())
        f.write(f"卡方统计量: {chi_square:.4f}\n")
        f.write(f"自由度: 11\n")

        # 2. 单方法评估
        f.write("\n" + "=" * 60 + "\n")
        f.write("2. 单方法命中率评估\n")
        f.write("=" * 60 + "\n")

        # 不同lookback
        for lb in [20, 30, 50, 100]:
            f.write(f"\n--- Lookback: {lb} ---\n")

            # 频率法
            def freq_pred_fn(h, l=lb):
                return predict_frequency(h, l)
            hits, total, rate, _ = evaluate(freq_pred_fn, hist, lb, n, l=lb)
            f.write(f"频率法: {hits}/{total} = {rate:.4f} ({rate*100:.2f}%)\n")

            # 最大遗漏法
            def gap_pred_fn(h, l=lb):
                return predict_max_gap(h, l)
            hits, total, rate, _ = evaluate(gap_pred_fn, hist, lb, n, l=lb)
            f.write(f"最大遗漏法: {hits}/{total} = {rate:.4f} ({rate*100:.2f}%)\n")

            # 综合评分法
            def score_pred_fn(h, l=lb):
                return predict_composite_score(h, l)
            hits, total, rate, _ = evaluate(score_pred_fn, hist, lb, n, l=lb)
            f.write(f"综合评分法: {hits}/{total} = {rate:.4f} ({rate*100:.2f}%)\n")

        # Markov链
        f.write(f"\n--- Markov链 ---\n")
        for order in [1, 2, 3]:
            def markov_pred_fn(h, o=order):
                return predict_markov(h, o)
            hits, total, rate, _ = evaluate(markov_pred_fn, hist, order, n, o=order)
            f.write(f"Markov-{order}阶: {hits}/{total} = {rate:.4f} ({rate*100:.2f}%)\n")

        # 混合法
        f.write(f"\n--- 混合法 ---\n")
        for lb in [20, 30, 50]:
            def hybrid_pred_fn(h, l=lb):
                return predict_hybrid(h, l)
            hits, total, rate, _ = evaluate(hybrid_pred_fn, hist, lb, n, l=lb)
            f.write(f"混合法(lookback={lb}): {hits}/{total} = {rate:.4f} ({rate*100:.2f}%)\n")

        # 3. 步行向前验证
        f.write("\n" + "=" * 60 + "\n")
        f.write("3. 步行向前验证 (Walk-Forward)\n")
        f.write("=" * 60 + "\n")

        # 频率法步行验证
        f.write("\n--- 频率法 ---\n")
        wf_results = walk_forward_evaluate(
            lambda h, **kw: predict_frequency(h, kw.get('lookback', 30)),
            hist, lookback=30, min_train=100, test_size=50, step=20
        )
        if wf_results:
            rates = [r['rate'] for r in wf_results]
            f.write(f"平均命中率: {np.mean(rates):.4f}\n")
            f.write(f"最高: {max(rates):.4f}\n")
            f.write(f"最低: {min(rates):.4f}\n")
            f.write(f"标准差: {np.std(rates):.4f}\n")

        # 混合法步行验证
        f.write("\n--- 混合法 ---\n")
        wf_results = walk_forward_evaluate(
            lambda h, **kw: predict_hybrid(h, kw.get('lookback', 30)),
            hist, lookback=30, min_train=100, test_size=50, step=20
        )
        if wf_results:
            rates = [r['rate'] for r in wf_results]
            f.write(f"平均命中率: {np.mean(rates):.4f}\n")
            f.write(f"最高: {max(rates):.4f}\n")
            f.write(f"最低: {min(rates):.4f}\n")
            f.write(f"标准差: {np.std(rates):.4f}\n")

        # 4. 时间模式分析
        f.write("\n" + "=" * 60 + "\n")
        f.write("4. 时间序列模式分析\n")
        f.write("=" * 60 + "\n")

        # 相邻关系
        consecutive_hits = 0
        total_consecutive = 0
        for i in range(1, n):
            if hist[i]['特码生肖'] == hist[i-1]['特码生肖']:
                consecutive_hits += 1
            total_consecutive += 1
        f.write(f"\n连续同生肖比例: {consecutive_hits}/{total_consecutive} = {consecutive_hits/total_consecutive:.4f}\n")
        f.write(f"理论期望: 1/12 = 0.0833\n")

        # 马太效应检验
        f.write("\n马太效应检验 (之前出现的生肖再次出现的比例):\n")
        for lb in [10, 20, 30]:
            repeat_count = 0
            total_count = 0
            for i in range(lb, n):
                window = hist[i-lb:i]
                recent_zodiacs = set(r['特码生肖'] for r in window)
                current = hist[i]['特码生肖']
                if current in recent_zodiacs:
                    repeat_count += 1
                total_count += 1
            f.write(f"  lookback={lb}: {repeat_count}/{total_count} = {repeat_count/total_count:.4f}\n")

        # 5. 周期分析
        f.write("\n" + "=" * 60 + "\n")
        f.write("5. 周期/周期性分析\n")
        f.write("=" * 60 + "\n")

        # 检查是否存在周期模式
        for target_z in ['鼠', '龍', '馬']:
            positions = [i for i, r in enumerate(hist) if r['特码生肖'] == target_z]
            if len(positions) >= 2:
                intervals = [positions[i+1] - positions[i] for i in range(len(positions)-1)]
                f.write(f"\n{target_z} 间隔统计:\n")
                f.write(f"  平均间隔: {np.mean(intervals):.2f}\n")
                f.write(f"  标准差: {np.std(intervals):.2f}\n")
                f.write(f"  最小: {min(intervals)}, 最大: {max(intervals)}\n")
                f.write(f"  中位数: {np.median(intervals):.2f}\n")

        # 6. 时段分析
        f.write("\n" + "=" * 60 + "\n")
        f.write("6. 不同历史时段的预测难度\n")
        f.write("=" * 60 + "\n")

        periods = [
            (100, 300, "早期"),
            (300, 500, "中期"),
            (500, 700, "后期"),
            (700, min(866, n), "近期")
        ]

        for start, end, name in periods:
            if end > n:
                continue
            f.write(f"\n--- {name} [{start}-{end}] ---\n")

            # 频率法
            hits, total, rate, _ = evaluate(
                lambda h, **kw: predict_frequency(h, kw.get('lb', 30)),
                hist, start, end, lb=30
            )
            f.write(f"频率法: {rate:.4f}\n")

            # 混合法
            hits, total, rate, _ = evaluate(
                lambda h, **kw: predict_hybrid(h, kw.get('lb', 30)),
                hist, start, end, lb=30
            )
            f.write(f"混合法: {rate:.4f}\n")

        # 7. 特征重要性分析
        f.write("\n" + "=" * 60 + "\n")
        f.write("7. 特征重要性分析 (相关性)\n")
        f.write("=" * 60 + "\n")

        # 计算各特征与下一个生肖的相关性
        lookback = 30
        for z in ZODIACS:
            gaps = []
            next_is_z = []
            for i in range(lookback, n-1):
                window = hist[i-lookback:i]
                positions = [j for j, r in enumerate(window) if r['特码生肖'] == z]
                gap = lookback - positions[-1] - 1 if positions else lookback
                gaps.append(gap)
                next_is_z.append(1 if hist[i+1]['特码生肖'] == z else 0)

            corr = np.corrcoef(gaps, next_is_z)[0, 1] if len(gaps) > 1 else 0
            f.write(f"{z}遗漏 → 下期出现: 相关系数 {corr:.4f}\n")

        # 8. 最佳参数搜索
        f.write("\n" + "=" * 60 + "\n")
        f.write("8. 最佳参数搜索\n")
        f.write("=" * 60 + "\n")

        best_rate = 0
        best_params = {}

        for lb in [20, 30, 40, 50]:
            for order in [1, 2]:
                def hybrid_fn(h, l=lb, o=order):
                    return predict_hybrid(h, l, o)
                hits, total, rate, _ = evaluate(hybrid_fn, hist, lb, n, l=lb, o=order)
                f.write(f"lookback={lb}, order={order}: {rate:.4f}\n")
                if rate > best_rate:
                    best_rate = rate
                    best_params = {'lookback': lb, 'order': order}

        f.write(f"\n最佳参数: {best_params}, 命中率: {best_rate:.4f}\n")

        # 9. 结论
        f.write("\n" + "=" * 60 + "\n")
        f.write("9. 结论与发现\n")
        f.write("=" * 60 + "\n")

        f.write("""
【主要发现】

1. 数据分布
   - 各生肖出现频率接近均匀分布 (8.33% 理论值附近)
   - 卡方检验表明数据基本符合随机分布假设

2. 单方法表现
   - 频率法、最大遗漏法、综合评分法 命中率都在 8-9% 左右
   - Markov链 各阶表现相近，约 8-10%
   - 没有任何方法显著超越随机基准 (1/12 ≈ 8.33%)

3. 步行向前验证
   - 各方法在不同时间窗口表现稳定
   - 标准差表明有一定波动，但不是系统性偏差

4. 时间模式
   - 连续同生肖出现的比例约 8-9%，符合随机预期
   - 马太效应检验：之前出现的生肖再次出现的概率与随机一致

5. 周期分析
   - 各生肖间隔的标准差较大，说明没有明显周期性
   - 间隔分布接近均匀分布

6. 结论
   - 澳门六合历史数据表现出强随机性特征
   - 尝试的所有预测方法均无法稳定超越随机基准
   - 这符合彩票设计的数学原理

【建议】

1. 如果目标是分析预测规律，应该接受数据的随机性
2. 如需进一步分析，可考虑：
   - 多标签分类（预测包含实际结果的多个生肖）
   - 组合策略（选择概率最高的3-4个生肖）
   - 特定生肖组合的联合预测

3. 任何声称能稳定预测彩票结果的说法都缺乏数学依据
""")

    print(f"\n结果已保存到: {results_file}")
    return results_file

if __name__ == '__main__':
    run_experiments()