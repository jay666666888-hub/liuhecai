#!/usr/bin/env python3
"""
V26 平特一肖 - 多策略并行搜索
同时尝试：纯频率、纯遗漏、贝叶斯、马尔可夫等方法
"""
import sys, os
sys.path.insert(0, '.')
from predictor.data_fetcher import get_all_records, build_standard_records
import random
from collections import defaultdict

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

def get_history():
    records = get_all_records([2024,2025,2026])
    return build_standard_records(records)

# 方法1: 纯频率优先
def method_freq_only(hist, lb):
    h = t = 0
    for i in range(lb, len(hist)):
        w = hist[max(0,i-lb):i]
        cur = hist[i]
        # 找出现最多的生肖
        freq = defaultdict(int)
        for r in w:
            freq[r['特码生肖']] += 1
        if not freq:
            continue
        p = max(freq, key=freq.get)
        if p in (cur.get('开奖生肖') or []):
            h += 1
        t += 1
    return h/t if t>0 else 0, t

# 方法2: 纯遗漏优先
def method_gap_only(hist, lb):
    h = t = 0
    for i in range(lb, len(hist)):
        w = hist[max(0,i-lb):i]
        cur = hist[i]
        # 找遗漏最久的生肖
        last_seen = {z: lb+1 for z in ZODIACS}
        for idx, r in enumerate(w):
            last_seen[r['特码生肖']] = idx
        gap = {z: len(w) - last_seen[z] - 1 for z in ZODIACS}
        p = max(gap, key=gap.get)
        if p in (cur.get('开奖生肖') or []):
            h += 1
        t += 1
    return h/t if t>0 else 0, t

# 方法3: 遗漏+频率混合
def method_gap_freq(hist, lb, gw, fw):
    h = t = 0
    for i in range(lb, len(hist)):
        w = hist[max(0,i-lb):i]
        cur = hist[i]
        last_seen = {z: lb+1 for z in ZODIACS}
        freq = defaultdict(int)
        for idx, r in enumerate(w):
            z = r['特码生肖']
            last_seen[z] = idx
            freq[z] += 1
        scores = {}
        for z in ZODIACS:
            gap = len(w) - last_seen[z] - 1
            g_s = min(gap, 50) / 50
            f_s = freq[z] / lb
            scores[z] = g_s * gw + f_s * fw
        p = max(scores, key=scores.get)
        if p in (cur.get('开奖生肖') or []):
            h += 1
        t += 1
    return h/t if t>0 else 0, t

# 方法4: 马尔可夫转移概率
def method_markov(hist, lb):
    h = t = 0
    # 先收集转移概率
    for start_i in range(lb, len(hist)-1):
        w = hist[max(0,start_i-lb):start_i]
        cur = hist[start_i]
        next_z = hist[start_i+1]['特码生肖']
        # 计算每个生肖的得分
        scores = {}
        for z in ZODIACS:
            cnt = sum(1 for r in w if r['特码生肖'] == z)
            scores[z] = cnt
        p = max(scores, key=scores.get)
        if p in (cur.get('开奖生肖') or []):
            h += 1
        t += 1
    return h/t if t>0 else 0, t

# 方法5: 冷热混合
def method_cold_hot(hist, lb, cold_w, hot_w):
    h = t = 0
    for i in range(lb, len(hist)):
        w = hist[max(0,i-lb):i]
        cur = hist[i]
        last_seen = {z: lb+1 for z in ZODIACS}
        freq = defaultdict(int)
        for idx, r in enumerate(w):
            z = r['特码生肖']
            last_seen[z] = idx
            freq[z] += 1
        # 冷门（久未出现）+ 热门（频繁出现）
        scores = {}
        for z in ZODIACS:
            gap = len(w) - last_seen[z] - 1
            cold = min(gap, 50) / 50  # 遗漏大=冷
            hot = freq[z] / lb  # 频率高=热
            scores[z] = cold * cold_w + hot * hot_w
        p = max(scores, key=scores.get)
        if p in (cur.get('开奖生肖') or []):
            h += 1
        t += 1
    return h/t if t>0 else 0, t

# 方法6: 间隔周期预测
def method_interval_cycle(hist, lb):
    """预测下一个可能出现的生肖基于历史间隔"""
    h = t = 0
    for i in range(lb+1, len(hist)):
        w = hist[max(0,i-lb):i]
        cur = hist[i]
        scores = {}
        for z in ZODIACS:
            positions = [idx for idx, r in enumerate(w) if r['特码生肖'] == z]
            if len(positions) < 2:
                scores[z] = 0.5
                continue
            # 计算平均间隔
            intervals = [positions[j] - positions[j+1] for j in range(len(positions)-1)]
            avg_int = sum(intervals) / len(intervals)
            # 预测下次出现位置 = 最后位置 + 平均间隔
            last_pos = positions[-1]
            predicted_pos = len(w) + int(avg_int)
            # 得分：预测位置越接近window末尾越高
            # 如果predicted_pos刚好在window外，说明快出现了
            if predicted_pos >= len(w):
                scores[z] = min(avg_int / 20, 1.0)  # 间隔适中
            else:
                scores[z] = 0.3  # 预测还在window内
        p = max(scores, key=scores.get)
        if p in (cur.get('开奖生肖') or []):
            h += 1
        t += 1
    return h/t if t>0 else 0, t

# 方法7: 回归预测
def method_regression(hist, lb):
    """使用简单的线性回归预测"""
    h = t = 0
    for i in range(lb+5, len(hist)):
        w = hist[max(0,i-lb):i]
        cur = hist[i]
        scores = {}
        for z in ZODIACS:
            positions = [idx for idx, r in enumerate(w) if r['特码生肖'] == z]
            if len(positions) < 3:
                scores[z] = 0.5
                continue
            # 用最近几次间隔做简单线性回归
            intervals = [positions[j] - positions[j+1] for j in range(len(positions)-1)]
            # 预测下一个间隔
            if len(intervals) >= 2:
                # 简单平均
                pred_gap = sum(intervals[:3]) / min(3, len(intervals))
            else:
                pred_gap = 12  # 默认12期
            gap_now = len(w) - positions[-1] - 1
            # gap越小=越可能近期出现
            scores[z] = 1 / (1 + gap_now)
        p = max(scores, key=scores.get)
        if p in (cur.get('开奖生肖') or []):
            h += 1
        t += 1
    return h/t if t>0 else 0, t


def main():
    hist = get_history()
    print(f'总数据: {len(hist)}期')

    results = []

    # 方法1-2: 简单方法
    for lb in [20, 25, 30, 35, 40, 50]:
        r, _ = method_freq_only(hist, lb)
        results.append(('freq_only', lb, 0, 0, r))
        r, _ = method_gap_only(hist, lb)
        results.append(('gap_only', lb, 0, 0, r))

    # 方法3: 遗漏+频率网格搜索
    print('搜索 gap+freq...')
    for lb in [20, 25, 30, 35, 40, 50]:
        for gw in [0.3, 0.4, 0.5, 0.6, 0.7]:
            for fw in [0.3, 0.4, 0.5, 0.6, 0.7]:
                r, _ = method_gap_freq(hist, lb, gw, fw)
                results.append(('gap_freq', lb, gw, fw, r))

    # 方法5: 冷热混合
    print('搜索 cold+hot...')
    for lb in [20, 25, 30, 35, 40, 50]:
        for cw in [0.3, 0.4, 0.5, 0.6, 0.7]:
            for hw in [0.3, 0.4, 0.5, 0.6, 0.7]:
                r, _ = method_cold_hot(hist, lb, cw, hw)
                results.append(('cold_hot', lb, cw, hw, r))

    # 方法4,6,7: 其他方法
    for lb in [20, 25, 30, 35, 40]:
        r, _ = method_markov(hist, lb)
        results.append(('markov', lb, 0, 0, r))
        r, _ = method_interval_cycle(hist, lb)
        results.append(('interval_cycle', lb, 0, 0, r))
        r, _ = method_regression(hist, lb)
        results.append(('regression', lb, 0, 0, r))

    # 排序
    results.sort(key=lambda x: x[4], reverse=True)

    print('\n=== Top 30 结果 ===')
    for i, r in enumerate(results[:30]):
        method, lb, w1, w2, rate = r
        if w1 != 0 or w2 != 0:
            print(f'{i+1}. {method}: lb={lb}, w1={w1}, w2={w2} -> {rate:.4f}')
        else:
            print(f'{i+1}. {method}: lb={lb} -> {rate:.4f}')

    print(f'\n最佳: {results[0]}')

if __name__ == '__main__':
    main()
