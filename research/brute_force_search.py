#!/usr/bin/env python3
"""
穷举法搜索最优预测方案
遍历不同的特征组合和权重，找到命中率最高的方案
"""

import json
from collections import Counter

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']  # 繁體

def load_data():
    """加载历史开奖数据"""
    with open('/mnt/c/Users/Admin/liuhecai/liuhecai_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = [{'issue': item['期号'], 'zodiac': item['特码生肖']} for item in data]
    return sorted(records, key=lambda x: x['issue'])

def predict_frequency(recs, window, top_k=6):
    """按近期频率预测"""
    recent = recs[-window:]
    freq = Counter(r['zodiac'] for r in recent)
    return [z for z, c in freq.most_common(top_k)]

def predict_gap(recs, top_k=6):
    """按遗漏间隔预测"""
    last_appear = {}
    for i, r in enumerate(recs):
        last_appear[r['zodiac']] = i

    gaps = {z: len(recs) - last_appear.get(z, -1) - 1 for z in ZODIACS}
    sorted_gaps = sorted(gaps.items(), key=lambda x: -x[1])
    return [z for z, g in sorted_gaps[:top_k]]

def predict_combined(recs, n_recent, n_gap_weight, top_k=6):
    """综合评分预测"""
    # 近期频率
    recent = recs[-n_recent:]
    freq = Counter(r['zodiac'] for r in recent)

    # 遗漏值
    last_appear = {}
    for i, r in enumerate(recs):
        last_appear[r['zodiac']] = i
    gaps = {z: len(recs) - last_appear.get(z, -1) - 1 for z in ZODIACS}

    # 标准化
    max_freq = max(freq.values()) if freq else 1
    max_gap = max(gaps.values()) if gaps else 1

    # 综合得分
    scores = {}
    for z in ZODIACS:
        freq_score = freq.get(z, 0) / max_freq
        gap_score = gaps[z] / max_gap
        scores[z] = freq_score * 0.5 + gap_score * 0.5

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]

def predict_reversed_gap(recs, window, top_k=6):
    """反向遗漏 - 近期出过的生肖权重降低"""
    recent = recs[-window:]
    recent_z = set(r['zodiac'] for r in recent)

    last_appear = {}
    for i, r in enumerate(recs):
        last_appear[r['zodiac']] = i

    gaps = {z: len(recs) - last_appear.get(z, -1) - 1 for z in ZODIACS}

    # 近期出过的，gap 要打折
    adjusted_gaps = {}
    for z in ZODIACS:
        gap = gaps[z]
        if z in recent_z:
            gap = gap * 0.3  # 近期出过，大幅降低
        adjusted_gaps[z] = gap

    sorted_gaps = sorted(adjusted_gaps.items(), key=lambda x: -x[1])
    return [z for z, g in sorted_gaps[:top_k]]

def predict_weighted_gap(recs, decay_factor, top_k=6):
    """带衰减的遗漏预测"""
    scores = {z: 0 for z in ZODIACS}

    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay_factor ** (len(recs) - i - 1)
        scores[z] += weight

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]

def test_strategy(records, predict_func, train_start=100, train_end=800):
    """测试策略命中率"""
    hits = 0
    total = 0

    for i in range(train_end, len(records)):
        if i <= train_start:
            continue

        recs = records[:i]
        actual = records[i]['zodiac']

        prediction = predict_func(recs)

        if actual in prediction:
            hits += 1
        total += 1

    return hits / total if total > 0 else 0


def predict_markov_state(recs, state_size, window, state_weight, decay, top_k=6):
    """马尔可夫链状态转移预测（扩展state size）"""
    # 收集状态
    recent = recs[-window:]
    recent_z = [r['zodiac'] for r in recent]

    # 构建状态转移计数
    trans_counts = {}
    for i in range(len(recent_z) - state_size):
        state = tuple(recent_z[i:i+state_size])
        next_z = recent_z[i+state_size] if i+state_size < len(recent_z) else None
        if next_z:
            if state not in trans_counts:
                trans_counts[state] = Counter()
            trans_counts[state][next_z] += 1

    # 衰减加权频率
    scores = {z: 0 for z in ZODIACS}
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    # 基于状态转移预测
    if len(recent_z) >= state_size:
        current_state = tuple(recent_z[-state_size:])
        if current_state in trans_counts:
            for z, count in trans_counts[current_state].items():
                scores[z] += count * state_weight * 10

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_ngram_simple(recs, n, decay, top_k=6):
    """N-gram简单预测"""
    recent_z = [r['zodiac'] for r in recs[-50:]]  # 固定窗口50，取zodiac字符串

    # 构建N-gram计数
    ngram_counts = {}
    for i in range(len(recent_z) - n):
        key = tuple(recent_z[i:i+n])
        next_z = recent_z[i+n] if i+n < len(recent_z) else None
        if next_z:
            if key not in ngram_counts:
                ngram_counts[key] = Counter()
            ngram_counts[key][next_z] += 1

    # 衰减频率
    scores = {z: 0 for z in ZODIACS}
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    # 基于N-gram加分
    if len(recent_z) >= n:
        current_ngram = tuple(recent_z[-n:])
        if current_ngram in ngram_counts:
            for z, count in ngram_counts[current_ngram].items():
                scores[z] += count * 2.0

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_hot_streak(recs, window, streak_weight, decay, top_k=6):
    """热门连出预测 - 近期高频且连出的生肖加权"""
    recent = recs[-window:]

    # 计算连出次数
    streak_counts = Counter()
    current_streak = {}
    for r in recent:
        z = r['zodiac']
        if z in current_streak:
            current_streak[z] += 1
        else:
            current_streak[z] = 1
        streak_counts[z] = max(streak_counts[z], current_streak.get(z, 0))

    # 衰减频率
    scores = {z: 0 for z in ZODIACS}
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    # 连出加权
    for z, streak in streak_counts.items():
        scores[z] += streak * streak_weight

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_recent_momentum(recs, window, momentum_weight, decay, top_k=6):
    """近期动量预测 - 最近N期出现次数二次加权"""
    recent = recs[-window:]

    # 计算每个生肖近期出现次数
    recent_counts = Counter(r['zodiac'] for r in recent)

    # 衰减频率
    scores = {z: 0 for z in ZODIACS}
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    # 近期动量加权（次数越多加权越高）
    for z, count in recent_counts.items():
        scores[z] += count * momentum_weight * 0.5

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_position_weighted(recs, decay, top_k=6):
    """位置加权预测 - 更近期的位置权重更高"""
    scores = {z: 0 for z in ZODIACS}
    for i, r in enumerate(recs):
        z = r['zodiac']
        # 位置加权：使用 (len - i) 作为权重基数，配合衰减
        position_weight = (len(recs) - i) / len(recs)
        weight = decay ** (len(recs) - i - 1) * position_weight
        scores[z] += weight
    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_alternating(recs, window, decay, top_k=6):
    """交替模式检测 - 检测交替出现的生肖"""
    recent = recs[-window:]
    recent_z = [r['zodiac'] for r in recent]

    # 检测交替模式：A-B-A-B 这种
    alternating_scores = Counter()
    for i in range(len(recent_z) - 2):
        if recent_z[i] == recent_z[i+2] and recent_z[i] != recent_z[i+1]:
            # 这是一个交替模式：z, x, z
            alternating_scores[recent_z[i]] += 1

    # 衰减频率
    scores = {z: 0 for z in ZODIACS}
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    # 交替模式加权
    for z, count in alternating_scores.items():
        scores[z] += count * 2.0

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_triplet(recs, window, decay, top_k=6):
    """三元组模式 - 检测连续出现的三个生肖的下一个"""
    recent = recs[-window:]
    recent_z = [r['zodiac'] for r in recent]

    # 构建三元组计数
    triplet_counts = {}
    for i in range(len(recent_z) - 3):
        triplet = tuple(recent_z[i:i+3])
        next_z = recent_z[i+3]
        if triplet not in triplet_counts:
            triplet_counts[triplet] = Counter()
        triplet_counts[triplet][next_z] += 1

    # 衰减频率
    scores = {z: 0 for z in ZODIACS}
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    # 三元组预测加权
    if len(recent_z) >= 3:
        current_triplet = tuple(recent_z[-3:])
        if current_triplet in triplet_counts:
            for z, count in triplet_counts[current_triplet].items():
                scores[z] += count * 3.0

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_odd_even(recs, decay, top_k=6):
    """奇偶模式 - 根据历史奇偶期出现频率"""
    # 分奇偶期统计
    odd_zodiacs = Counter()
    even_zodiacs = Counter()

    for i, r in enumerate(recs):
        z = r['zodiac']
        if i % 2 == 0:
            odd_zodiacs[z] += 1
        else:
            even_zodiacs[z] += 1

    # 衰减频率
    scores = {z: 0 for z in ZODIACS}
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    # 奇偶模式加权
    current_is_odd = len(recs) % 2 == 0
    target_counter = odd_zodiacs if current_is_odd else even_zodiacs
    total = sum(target_counter.values()) or 1
    for z in ZODIACS:
        scores[z] += (target_counter[z] / total) * 1.5

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_recent_distribution(recs, decay, top_k=6):
    """近期分布匹配 - 匹配历史中出现率接近的生肖"""
    # 整体分布
    total_counts = Counter(r['zodiac'] for r in recs)
    total = sum(total_counts.values()) or 1

    # 近期分布
    recent = recs[-30:]
    recent_counts = Counter(r['zodiac'] for r in recent)
    recent_total = sum(recent_counts.values()) or 1

    # 衰减频率
    scores = {z: 0 for z in ZODIACS}
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    # 分布差异加权：近期出现多的但历史上少的，加分
    for z in ZODIACS:
        recent_ratio = recent_counts[z] / recent_total
        total_ratio = total_counts[z] / total
        if recent_ratio > total_ratio:
            scores[z] += (recent_ratio - total_ratio) * 2.0

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def run_experiments():
    print("穷举法搜索最优方案...")
    records = load_data()
    print(f"共 {len(records)} 条记录\n")

    best_results = []

    # ====== 方案1: 近期频率法 ======
    print("--- 方案1: 近期频率法 ---")
    for window in [5, 8, 10, 12, 15, 18, 20, 25, 30, 40, 50]:
        for train_end in [300, 400, 450]:
            if train_end >= len(records) - 20:
                continue

            def make_pred(w):
                def pred(recs):
                    return predict_frequency(recs, w, 6)
                return pred

            hit_rate = test_strategy(records, make_pred(window), train_end=train_end)
            print(f"  窗口{window:2d}期, 训练到{train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.52:
                best_results.append(('freq', window, train_end, hit_rate))

    # ====== 方案2: 反向遗漏法 ======
    print("\n--- 方案2: 反向遗漏法 ---")
    for window in [5, 8, 10, 12, 15, 20, 25, 30]:
        for train_end in [300, 400, 450]:
            if train_end >= len(records) - 20:
                continue

            def make_pred(w):
                def pred(recs):
                    return predict_reversed_gap(recs, w, 6)
                return pred

            hit_rate = test_strategy(records, make_pred(window), train_end=train_end)
            print(f"  窗口{window:2d}期, 训练到{train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.52:
                best_results.append(('rev_gap', window, train_end, hit_rate))

    # ====== 方案3: 衰减加权法 ======
    print("\n--- 方案3: 衰减加权法 ---")
    for decay in [0.85, 0.88, 0.90, 0.92, 0.94, 0.96, 0.98]:
        for train_end in [300, 400, 450]:
            if train_end >= len(records) - 20:
                continue

            def make_pred(dp):
                def pred(recs):
                    return predict_weighted_gap(recs, dp, 6)
                return pred

            hit_rate = test_strategy(records, make_pred(decay), train_end=train_end)
            print(f"  衰减{decay:.2f}, 训练到{train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.52:
                best_results.append(('decay', decay, train_end, hit_rate))

    # ====== 方案4: 综合评分法 ======
    print("\n--- 方案4: 综合评分法 ---")
    for n_recent in [5, 8, 10, 12, 15, 20]:
        for gap_weight in [0.3, 0.5, 0.7]:
            for train_end in [300, 400, 450]:
                if train_end >= len(records) - 20:
                    continue

                def make_pred(nr, gw):
                    def pred(recs):
                        return predict_combined(recs, nr, gw, 6)
                    return pred

                hit_rate = test_strategy(records, make_pred(n_recent, gap_weight), train_end=train_end)
                print(f"  recent={n_recent}, gap_weight={gap_weight}, 训练到{train_end}: {hit_rate*100:.2f}%")
                if hit_rate > 0.52:
                    best_results.append(('combined', (n_recent, gap_weight), train_end, hit_rate))

    # ====== 方案5: 版本投票法 ======
    print("\n--- 方案5: 版本投票法 ---")
    def version_voting(recs):
        # v12 style
        pred1 = predict_combined(recs, 20, 0.5, 6)
        # frequency
        pred2 = predict_frequency(recs, 10, 6)
        # decay
        pred3 = predict_weighted_gap(recs, 0.90, 6)

        # 投票
        all_preds = pred1 + pred2 + pred3
        counter = Counter(all_preds)
        return [z for z, c in counter.most_common(6)]

    for train_end in [400, 450]:
        if train_end >= len(records) - 20:
            continue
        hit_rate = test_strategy(records, version_voting, train_end=train_end)
        print(f"  版本投票, 训练到{train_end}: {hit_rate*100:.2f}%")
        if hit_rate > 0.52:
            best_results.append(('voting', None, train_end, hit_rate))

    # ====== 结果汇总 ======
    print("\n" + "="*60)
    print("最佳结果 TOP 10:")
    best_results.sort(key=lambda x: -x[3])
    for i, r in enumerate(best_results[:10]):
        print(f"  {i+1}. {r[3]*100:.2f}% - {r[0]} {r[1]} 训练到{r[2]}")

    return best_results


def run_extended_search():
    """扩展搜索 - 尝试更多参数"""
    print("扩展搜索...")
    records = load_data()
    print(f"共 {len(records)} 条记录\n")

    best_results = []

    # ====== 马尔可夫扩展state size ======
    print("--- 马尔可夫扩展state size ---")
    for state_size in [3, 4, 5, 6]:
        for window in [30, 50, 80]:
            for state_weight in [0.3, 0.5, 0.7]:
                for decay in [0.95, 0.98, 0.99]:
                    for train_end in [300, 400, 450]:
                        if len(records) - train_end < 20:
                            continue

                        def make_pred(ss, w, sw, d):
                            def pred(recs):
                                return predict_markov_state(recs, ss, w, sw, d, 6)
                            return pred

                        hit_rate = test_strategy(records, make_pred(state_size, window, state_weight, decay), train_end=train_end)
                        if hit_rate > 0.50:
                            print(f"  state={state_size}, window={window}, sw={state_weight}, decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
                        if hit_rate > 0.55:
                            best_results.append(('markov_ext', (state_size, window, state_weight, decay), train_end, hit_rate))

    # ====== N-gram预测 ======
    print("\n--- N-gram预测 ---")
    for n in [2, 3, 4, 5]:
        for decay in [0.90, 0.95, 0.98, 0.99]:
            for train_end in [300, 400, 450]:
                if len(records) - train_end < 20:
                    continue

                def make_pred_ngram(n_, d):
                    def pred(recs):
                        return predict_ngram_simple(recs, n_, d, 6)
                    return pred

                hit_rate = test_strategy(records, make_pred_ngram(n, decay), train_end=train_end)
                if hit_rate > 0.50:
                    print(f"  n={n}, decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
                if hit_rate > 0.55:
                    best_results.append(('ngram', (n, decay), train_end, hit_rate))

    # ====== 热门连出 ======
    print("\n--- 热门连出 ---")
    for window in [10, 15, 20, 30]:
        for streak_weight in [0.5, 1.0, 1.5, 2.0]:
            for decay in [0.90, 0.95, 0.98]:
                for train_end in [300, 400, 450]:
                    if len(records) - train_end < 20:
                        continue

                    def make_pred_sw(w, sw, d):
                        def pred(recs):
                            return predict_hot_streak(recs, w, sw, d, 6)
                        return pred

                    hit_rate = test_strategy(records, make_pred_sw(window, streak_weight, decay), train_end=train_end)
                    if hit_rate > 0.50:
                        print(f"  window={window}, sw={streak_weight}, decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
                    if hit_rate > 0.55:
                        best_results.append(('hotstreak', (window, streak_weight, decay), train_end, hit_rate))

    # ====== 近期动量 ======
    print("\n--- 近期动量 ---")
    for window in [10, 15, 20, 30]:
        for momentum_weight in [0.5, 1.0, 1.5, 2.0]:
            for decay in [0.90, 0.95, 0.98]:
                for train_end in [300, 400, 450]:
                    if len(records) - train_end < 20:
                        continue

                    def make_pred_mw(w, mw, d):
                        def pred(recs):
                            return predict_recent_momentum(recs, w, mw, d, 6)
                        return pred

                    hit_rate = test_strategy(records, make_pred_mw(window, momentum_weight, decay), train_end=train_end)
                    if hit_rate > 0.50:
                        print(f"  window={window}, mw={momentum_weight}, decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
                    if hit_rate > 0.55:
                        best_results.append(('momentum', (window, momentum_weight, decay), train_end, hit_rate))

    # ====== 位置加权搜索 ======
    print("\n--- 位置加权搜索 ---")
    for decay in [0.85, 0.90, 0.92, 0.95, 0.98, 0.99]:
        for train_end in [300, 400, 450]:
            if len(records) - train_end < 20:
                continue

            def make_pred_pw(d):
                def pred(recs):
                    return predict_position_weighted(recs, d, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_pw(decay), train_end=train_end)
            if hit_rate > 0.50:
                print(f"  decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.55:
                best_results.append(('pos_weight', (decay,), train_end, hit_rate))

    # ====== 交替模式搜索 ======
    print("\n--- 交替模式搜索 ---")
    for window in [15, 20, 30, 50]:
        for decay in [0.90, 0.95, 0.98]:
            for train_end in [300, 400, 450]:
                if len(records) - train_end < 20:
                    continue

                def make_pred_alt(w, d):
                    def pred(recs):
                        return predict_alternating(recs, w, d, 6)
                    return pred

                hit_rate = test_strategy(records, make_pred_alt(window, decay), train_end=train_end)
                if hit_rate > 0.50:
                    print(f"  window={window}, decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
                if hit_rate > 0.55:
                    best_results.append(('alternating', (window, decay), train_end, hit_rate))

    # ====== 三元组模式搜索 ======
    print("\n--- 三元组模式搜索 ---")
    for window in [30, 50, 80, 100]:
        for decay in [0.90, 0.95, 0.98]:
            for train_end in [300, 400, 450]:
                if len(records) - train_end < 20:
                    continue

                def make_pred_triplet(w, d):
                    def pred(recs):
                        return predict_triplet(recs, w, d, 6)
                    return pred

                hit_rate = test_strategy(records, make_pred_triplet(window, decay), train_end=train_end)
                if hit_rate > 0.50:
                    print(f"  window={window}, decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
                if hit_rate > 0.55:
                    best_results.append(('triplet', (window, decay), train_end, hit_rate))

    # ====== 奇偶模式搜索 ======
    print("\n--- 奇偶模式搜索 ---")
    for decay in [0.90, 0.95, 0.98]:
        for train_end in [300, 400, 450]:
            if len(records) - train_end < 20:
                continue

            def make_pred_oe(d):
                def pred(recs):
                    return predict_odd_even(recs, d, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_oe(decay), train_end=train_end)
            if hit_rate > 0.50:
                print(f"  decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.55:
                best_results.append(('odd_even', (decay,), train_end, hit_rate))

    # ====== 近期分布匹配搜索 ======
    print("\n--- 近期分布匹配搜索 ---")
    for decay in [0.90, 0.95, 0.98]:
        for train_end in [300, 400, 450]:
            if len(records) - train_end < 20:
                continue

            def make_pred_rd(d):
                def pred(recs):
                    return predict_recent_distribution(recs, d, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_rd(decay), train_end=train_end)
            if hit_rate > 0.50:
                print(f"  decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.55:
                best_results.append(('recent_dist', (decay,), train_end, hit_rate))

    # ====== 综合混合策略搜索 ======
    print("\n--- 综合混合策略搜索 ---")
    def predict_hybrid(recs, window1, window2, decay1, decay2, top_k=6):
        """混合策略：频率 + 遗漏 + 位置加权"""
        recent = recs[-window1:]
        freq = Counter(r['zodiac'] for r in recent)

        last_appear = {}
        for i, r in enumerate(recs):
            last_appear[r['zodiac']] = i
        gaps = {z: len(recs) - last_appear.get(z, -1) - 1 for z in ZODIACS}

        scores = {z: 0 for z in ZODIACS}
        for i, r in enumerate(recs):
            z = r['zodiac']
            position_weight = (len(recs) - i) / len(recs)
            weight = (decay1 ** (len(recs) - i - 1)) * position_weight
            scores[z] += weight * 0.5

        max_gap = max(gaps.values()) if gaps else 1
        for z in ZODIACS:
            scores[z] += (gaps[z] / max_gap) * decay2

        max_freq = max(freq.values()) if freq else 1
        for z in ZODIACS:
            scores[z] += (freq.get(z, 0) / max_freq) * 1.5

        return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]

    for window1 in [15, 20, 25]:
        for window2 in [20, 30, 50]:
            for decay1 in [0.95, 0.98]:
                for decay2 in [0.90, 0.95]:
                    for train_end in [300, 400, 450]:
                        if len(records) - train_end < 20:
                            continue

                        def make_pred_h(w1, w2, d1, d2):
                            def pred(recs):
                                return predict_hybrid(recs, w1, w2, d1, d2, 6)
                            return pred

                        hit_rate = test_strategy(records, make_pred_h(window1, window2, decay1, decay2), train_end=train_end)
                        if hit_rate > 0.50:
                            print(f"  w1={window1}, w2={window2}, d1={decay1}, d2={decay2}, train={train_end}: {hit_rate*100:.2f}%")
                        if hit_rate > 0.55:
                            best_results.append(('hybrid', (window1, window2, decay1, decay2), train_end, hit_rate))

    print("\n" + "="*60)
    print("扩展搜索最佳结果 TOP 20:")
    best_results.sort(key=lambda x: -x[3])
    for i, r in enumerate(best_results[:20]):
        print(f"  {i+1}. {r[3]*100:.2f}% - {r[0]} {r[1]}")

    return best_results


def predict_aggressive_hybrid(recs, w1, w2, w3, decay, top_k=6):
    """激进的混合策略 - 三种特征加权"""
    # 近期高频
    recent = recs[-w1:]
    freq = Counter(r['zodiac'] for r in recent)

    # 遗漏值
    last_appear = {}
    for i, r in enumerate(recs):
        last_appear[r['zodiac']] = i
    gaps = {z: len(recs) - last_appear.get(z, -1) - 1 for z in ZODIACS}

    # 连出检测
    recent_z = [r['zodiac'] for r in recs[-w2:]]
    streak_counts = Counter()
    current_streak = {}
    for z in recent_z:
        if z in current_streak:
            current_streak[z] += 1
        else:
            current_streak[z] = 1
        streak_counts[z] = max(streak_counts[z], current_streak.get(z, 0))

    # 综合评分
    scores = {z: 0 for z in ZODIACS}
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    max_gap = max(gaps.values()) if gaps else 1
    for z in ZODIACS:
        scores[z] += (gaps[z] / max_gap) * 1.2

    max_freq = max(freq.values()) if freq else 1
    for z in ZODIACS:
        scores[z] += (freq.get(z, 0) / max_freq) * 2.0

    for z, streak in streak_counts.items():
        scores[z] += streak * 0.8

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_adaptive_window(recs, decay, top_k=6):
    """自适应窗口 - 同时考虑多个窗口的加权平均"""
    all_scores = {z: 0 for z in ZODIACS}

    for window in [10, 20, 30, 50]:
        recent = recs[-window:]
        freq = Counter(r['zodiac'] for r in recent)

        scores = {z: 0 for z in ZODIACS}
        for i, r in enumerate(recs):
            z = r['zodiac']
            weight = decay ** (len(recs) - i - 1)
            scores[z] += weight

        max_freq = max(freq.values()) if freq else 1
        for z in ZODIACS:
            all_scores[z] += (freq.get(z, 0) / max_freq) * (50 - window) / 100

    return [z for z, s in sorted(all_scores.items(), key=lambda x: -x[1])][:top_k]


def predict_cycle_detection(recs, cycle_len, decay, top_k=6):
    """周期检测 - 检测固定周期内重复出现的生肖"""
    # 检测是否存在周期性模式
    scores = {z: 0 for z in ZODIACS}

    # 衰减基础分
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    # 周期加成：如果某个生肖在cycle_len位置之前出现过，加分
    if len(recs) >= cycle_len:
        check_idx = len(recs) - cycle_len
        target_z = recs[check_idx]['zodiac']
        scores[target_z] += 3.0

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_weighted_voting(recs, top_k=6):
    """加权投票 - 多种策略投票"""
    pred1 = predict_frequency(recs, 20, 6)
    pred2 = predict_reversed_gap(recs, 5, 6)
    pred3 = predict_weighted_gap(recs, 0.96, 6)
    pred4 = predict_hot_streak(recs, 20, 1.0, 0.9, 6)

    all_preds = []
    all_preds.extend(pred1)
    all_preds.extend(pred2)
    all_preds.extend(pred3)
    all_preds.extend(pred4)
    counter = Counter(all_preds)
    return [z for z, c in counter.most_common(6)]


def run_extreme_search():
    """极限搜索 - 尝试更极端的参数组合"""
    print("\n\n========== 极限搜索 ==========")
    records = load_data()
    print(f"共 {len(records)} 条记录\n")

    best_results = []

    # ====== 激进混合策略 ======
    print("--- 激进混合策略 ---")
    for w1 in [15, 20, 25, 30]:
        for w2 in [15, 20, 30, 50]:
            for w3 in [10, 20, 30]:
                for decay in [0.92, 0.95, 0.98]:
                    for train_end in [280, 300, 350, 400]:
                        if len(records) - train_end < 20:
                            continue

                        def make_pred_ah(w1_, w2_, w3_, d):
                            def pred(recs):
                                return predict_aggressive_hybrid(recs, w1_, w2_, w3_, d, 6)
                            return pred

                        hit_rate = test_strategy(records, make_pred_ah(w1, w2, w3, decay), train_end=train_end)
                        if hit_rate > 0.55:
                            print(f"  w1={w1}, w2={w2}, w3={w3}, d={decay}, train={train_end}: {hit_rate*100:.2f}%")
                        if hit_rate > 0.58:
                            best_results.append(('aggressive', (w1, w2, w3, decay), train_end, hit_rate))

    # ====== 自适应窗口 ======
    print("\n--- 自适应窗口 ---")
    for decay in [0.92, 0.95, 0.98]:
        for train_end in [280, 300, 350, 400]:
            if len(records) - train_end < 20:
                continue

            def make_pred_aw(d):
                def pred(recs):
                    return predict_adaptive_window(recs, d, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_aw(decay), train_end=train_end)
            if hit_rate > 0.55:
                print(f"  decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.58:
                best_results.append(('adaptive', (decay,), train_end, hit_rate))

    # ====== 周期检测 ======
    print("\n--- 周期检测 ---")
    for cycle_len in [5, 6, 7, 8, 9, 10, 11, 12]:
        for decay in [0.92, 0.95, 0.98]:
            for train_end in [280, 300, 350, 400]:
                if len(records) - train_end < 20:
                    continue

                def make_pred_cycle(c, d):
                    def pred(recs):
                        return predict_cycle_detection(recs, c, d, 6)
                    return pred

                hit_rate = test_strategy(records, make_pred_cycle(cycle_len, decay), train_end=train_end)
                if hit_rate > 0.55:
                    print(f"  cycle={cycle_len}, decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
                if hit_rate > 0.58:
                    best_results.append(('cycle', (cycle_len, decay), train_end, hit_rate))

    # ====== 超大窗口频率法 ======
    print("\n--- 超大窗口频率法 ---")
    for window in [60, 80, 100, 150, 200]:
        for train_end in [280, 300, 350, 400, 450]:
            if len(records) - train_end < 20:
                continue

            def make_pred_large_w(w):
                def pred(recs):
                    return predict_frequency(recs, w, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_large_w(window), train_end=train_end)
            if hit_rate > 0.55:
                print(f"  window={window}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.58:
                best_results.append(('large_freq', (window,), train_end, hit_rate))

    # ====== 极限衰减参数 ======
    print("\n--- 极限衰减参数 ---")
    for decay in [0.80, 0.82, 0.85, 0.87, 0.88, 0.89]:
        for train_end in [280, 300, 350, 400]:
            if len(records) - train_end < 20:
                continue

            def make_pred_extreme_decay(d):
                def pred(recs):
                    return predict_weighted_gap(recs, d, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_extreme_decay(decay), train_end=train_end)
            if hit_rate > 0.55:
                print(f"  decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.58:
                best_results.append(('extreme_decay', (decay,), train_end, hit_rate))

    # ====== 极小窗口反向遗漏 ======
    print("\n--- 极小窗口反向遗漏 ---")
    for window in [3, 4, 5, 6]:
        for train_end in [280, 300, 350, 400, 450]:
            if len(records) - train_end < 20:
                continue

            def make_pred_small_rg(w):
                def pred(recs):
                    return predict_reversed_gap(recs, w, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_small_rg(window), train_end=train_end)
            if hit_rate > 0.55:
                print(f"  window={window}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.58:
                best_results.append(('small_rev', (window,), train_end, hit_rate))

    print("\n" + "="*60)
    print("极限搜索最佳结果 TOP 20:")
    best_results.sort(key=lambda x: -x[3])
    for i, r in enumerate(best_results[:20]):
        print(f"  {i+1}. {r[3]*100:.2f}% - {r[0]} {r[1]} train={r[2]}")

    return best_results


def predict_consecutive_pairs(recs, decay, top_k=6):
    """连续对预测 - 检测历史上连续出现的生肖对"""
    scores = {z: 0 for z in ZODIACS}

    # 统计连续对出现的次数
    pair_counts = Counter()
    for i in range(len(recs) - 1):
        z1 = recs[i]['zodiac']
        z2 = recs[i+1]['zodiac']
        pair_counts[(z1, z2)] += 1

    # 如果最后一个是某个对的第一元素，强烈推荐第二个
    if len(recs) >= 1:
        last_z = recs[-1]['zodiac']
        for (z1, z2), count in pair_counts.items():
            if z1 == last_z:
                scores[z2] += count * 2.0

    # 衰减频率
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_recent_first(recs, decay, top_k=6):
    """近期首次出现加权 - 近期未出现的生肖但总体常见"""
    scores = {z: 0 for z in ZODIACS}

    # 近期出现统计
    recent = recs[-30:]
    recent_set = set(r['zodiac'] for r in recent)

    # 总体频率
    total_counts = Counter(r['zodiac'] for r in recs)

    # 衰减频率
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    # 近期未出现但总体常见 = 遗漏反弹信号
    for z in ZODIACS:
        if z not in recent_set:
            total_ratio = total_counts[z] / sum(total_counts.values())
            scores[z] += total_ratio * 3.0

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_interval_analysis(recs, decay, top_k=6):
    """间隔分析 - 分析每个生肖的平均出现间隔"""
    scores = {z: 0 for z in ZODIACS}

    # 计算每个生肖的出现位置
    positions = {z: [] for z in ZODIACS}
    for i, r in enumerate(recs):
        positions[r['zodiac']].append(i)

    # 计算平均间隔
    avg_intervals = {}
    for z in ZODIACS:
        if len(positions[z]) > 1:
            intervals = [positions[z][i+1] - positions[z][i] for i in range(len(positions[z])-1)]
            avg_intervals[z] = sum(intervals) / len(intervals)
        else:
            avg_intervals[z] = len(recs)  # 从未出现，假设初始间隔为总长度

    # 当前已过去多少期
    last_appear = {}
    for i, r in enumerate(recs):
        last_appear[r['zodiac']] = i
    current_gaps = {z: len(recs) - last_appear.get(z, -1) - 1 for z in ZODIACS}

    # 衰减频率
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    # 当前间隔接近平均间隔的加分
    for z in ZODIACS:
        ratio = current_gaps[z] / avg_intervals[z] if avg_intervals[z] > 0 else 0
        if ratio >= 0.8 and ratio <= 1.2:
            scores[z] += 2.0

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_top_half(recs, decay, top_k=6):
    """历史上半区加权 - 只使用历史上出现次数最多的生肖"""
    scores = {z: 0 for z in ZODIACS}

    # 总体频率排序
    total_counts = Counter(r['zodiac'] for r in recs)
    top_half = [z for z, c in total_counts.most_common(6)]

    # 衰减频率
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    # 历史高频加权
    for i, z in enumerate(top_half):
        scores[z] += (6 - i) * 0.5

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_zodiac_group(recs, decay, top_k=6):
    """生肖分组预测 - 将生肖分成两组，轮流出现"""
    scores = {z: 0 for z in ZODIACS}

    # 检测轮换模式
    group_a = ZODIACS[:6]  # 鼠牛虎兔龍蛇
    group_b = ZODIACS[6:]  # 馬羊猴雞狗豬

    recent = recs[-10:]
    recent_groups = ['A' if r['zodiac'] in group_a else 'B' for r in recent]

    # 衰减频率
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight

    # 如果最近都是A组，下期更可能是B组
    if recent_groups[-1] == 'A':
        for z in group_b:
            scores[z] += 1.5
    else:
        for z in group_a:
            scores[z] += 1.5

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_fibonacci_weight(recs, decay, top_k=6):
    """斐波那契加权 - 使用斐波那契数列作为权重"""
    scores = {z: 0 for z in ZODIACS}

    # 斐波那契权重
    fib = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
    for i, r in enumerate(recs[-10:]):
        z = r['zodiac']
        idx = min(i, len(fib) - 1)
        scores[z] += fib[idx] * (decay ** (len(recs) - i - 1))

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def predict_ml_style(recs, decay, top_k=6):
    """类机器学习风格 - 多特征融合"""
    scores = {z: 0 for z in ZODIACS}

    # 特征1: 衰减频率
    for i, r in enumerate(recs):
        z = r['zodiac']
        weight = decay ** (len(recs) - i - 1)
        scores[z] += weight * 0.4

    # 特征2: 近期频率 (10期)
    recent_10 = Counter(r['zodiac'] for r in recs[-10:])
    max_10 = max(recent_10.values()) if recent_10 else 1
    for z in ZODIACS:
        scores[z] += (recent_10.get(z, 0) / max_10) * 2.0

    # 特征3: 反向遗漏
    last_appear = {}
    for i, r in enumerate(recs):
        last_appear[r['zodiac']] = i
    gaps = {z: len(recs) - last_appear.get(z, -1) - 1 for z in ZODIACS}
    max_gap = max(gaps.values()) if gaps else 1
    for z in ZODIACS:
        scores[z] += (gaps[z] / max_gap) * 1.5

    # 特征4: 连出检测
    recent_z = [r['zodiac'] for r in recs[-5:]]
    for z in recent_z:
        if recent_z.count(z) >= 2:
            scores[z] += 1.0

    return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]


def run_final_search():
    """最终搜索 - 尝试所有能想到的方法"""
    print("\n\n========== 最终搜索 ==========")
    records = load_data()
    print(f"共 {len(records)} 条记录\n")

    best_results = []

    # ====== 连续对预测 ======
    print("--- 连续对预测 ---")
    for decay in [0.90, 0.95, 0.98]:
        for train_end in [280, 300, 350, 400, 450]:
            if len(records) - train_end < 20:
                continue

            def make_pred_cp(d):
                def pred(recs):
                    return predict_consecutive_pairs(recs, d, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_cp(decay), train_end=train_end)
            if hit_rate > 0.55:
                print(f"  decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.58:
                best_results.append(('consec_pair', (decay,), train_end, hit_rate))

    # ====== 近期首次出现 ======
    print("\n--- 近期首次出现 ---")
    for decay in [0.90, 0.95, 0.98]:
        for train_end in [280, 300, 350, 400, 450]:
            if len(records) - train_end < 20:
                continue

            def make_pred_rf(d):
                def pred(recs):
                    return predict_recent_first(recs, d, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_rf(decay), train_end=train_end)
            if hit_rate > 0.55:
                print(f"  decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.58:
                best_results.append(('recent_first', (decay,), train_end, hit_rate))

    # ====== 间隔分析 ======
    print("\n--- 间隔分析 ---")
    for decay in [0.90, 0.95, 0.98]:
        for train_end in [280, 300, 350, 400, 450]:
            if len(records) - train_end < 20:
                continue

            def make_pred_ia(d):
                def pred(recs):
                    return predict_interval_analysis(recs, d, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_ia(decay), train_end=train_end)
            if hit_rate > 0.55:
                print(f"  decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.58:
                best_results.append(('interval', (decay,), train_end, hit_rate))

    # ====== 历史高频 ======
    print("\n--- 历史高频 ---")
    for decay in [0.90, 0.95, 0.98]:
        for train_end in [280, 300, 350, 400, 450]:
            if len(records) - train_end < 20:
                continue

            def make_pred_th(d):
                def pred(recs):
                    return predict_top_half(recs, d, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_th(decay), train_end=train_end)
            if hit_rate > 0.55:
                print(f"  decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.58:
                best_results.append(('top_half', (decay,), train_end, hit_rate))

    # ====== 生肖分组 ======
    print("\n--- 生肖分组 ---")
    for decay in [0.90, 0.95, 0.98]:
        for train_end in [280, 300, 350, 400, 450]:
            if len(records) - train_end < 20:
                continue

            def make_pred_zg(d):
                def pred(recs):
                    return predict_zodiac_group(recs, d, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_zg(decay), train_end=train_end)
            if hit_rate > 0.55:
                print(f"  decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.58:
                best_results.append(('zodiac_group', (decay,), train_end, hit_rate))

    # ====== 斐波那契加权 ======
    print("\n--- 斐波那契加权 ---")
    for decay in [0.90, 0.95, 0.98]:
        for train_end in [280, 300, 350, 400, 450]:
            if len(records) - train_end < 20:
                continue

            def make_pred_fib(d):
                def pred(recs):
                    return predict_fibonacci_weight(recs, d, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_fib(decay), train_end=train_end)
            if hit_rate > 0.55:
                print(f"  decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.58:
                best_results.append(('fibonacci', (decay,), train_end, hit_rate))

    # ====== 类机器学习风格 ======
    print("\n--- 类机器学习风格 ---")
    for decay in [0.90, 0.95, 0.98]:
        for train_end in [280, 300, 350, 400, 450]:
            if len(records) - train_end < 20:
                continue

            def make_pred_ml(d):
                def pred(recs):
                    return predict_ml_style(recs, d, 6)
                return pred

            hit_rate = test_strategy(records, make_pred_ml(decay), train_end=train_end)
            if hit_rate > 0.55:
                print(f"  decay={decay}, train={train_end}: {hit_rate*100:.2f}%")
            if hit_rate > 0.58:
                best_results.append(('ml_style', (decay,), train_end, hit_rate))

    # ====== 超多特征融合 ======
    print("\n--- 超多特征融合 ---")
    def predict_full_fusion(recs, w1, w2, w3, w4, d1, d2, d3, top_k=6):
        """全特征融合 - 结合所有特征"""
        scores = {z: 0 for z in ZODIACS}

        # w1: 近期频率
        recent_10 = Counter(r['zodiac'] for r in recs[-w1:])
        max_10 = max(recent_10.values()) if recent_10 else 1

        # w2: 衰减频率
        for i, r in enumerate(recs):
            z = r['zodiac']
            weight = d1 ** (len(recs) - i - 1)
            scores[z] += weight

        # w3: 反向遗漏
        last_appear = {}
        for i, r in enumerate(recs):
            last_appear[r['zodiac']] = i
        gaps = {z: len(recs) - last_appear.get(z, -1) - 1 for z in ZODIACS}
        max_gap = max(gaps.values()) if gaps else 1

        # w4: 位置加权
        max_pos = len(recs)

        for z in ZODIACS:
            scores[z] += (recent_10.get(z, 0) / max_10) * w2
            scores[z] += (gaps[z] / max_gap) * w3
            position_weight = (max_pos - last_appear.get(z, 0)) / max_pos
            scores[z] += position_weight * w4 * 0.5

        return [z for z, s in sorted(scores.items(), key=lambda x: -x[1])][:top_k]

    for w1 in [10, 15, 20]:
        for w2 in [1.5, 2.0, 2.5]:
            for w3 in [1.0, 1.5, 2.0]:
                for w4 in [1.0, 1.5, 2.0]:
                    for d1 in [0.95, 0.98]:
                        for train_end in [280, 300, 350, 400]:
                            if len(records) - train_end < 20:
                                continue

                            def make_pred_ff(w1_, w2_, w3_, w4_, d1_):
                                def pred(recs):
                                    return predict_full_fusion(recs, w1_, w2_, w3_, w4_, d1_, 0.95, 0.95, 6)
                                return pred

                            hit_rate = test_strategy(records, make_pred_ff(w1, w2, w3, w4, d1), train_end=train_end)
                            if hit_rate > 0.56:
                                print(f"  w1={w1}, w2={w2}, w3={w3}, w4={w4}, d1={d1}, train={train_end}: {hit_rate*100:.2f}%")
                            if hit_rate > 0.58:
                                best_results.append(('full_fusion', (w1, w2, w3, w4, d1), train_end, hit_rate))

    print("\n" + "="*60)
    print("最终搜索最佳结果 TOP 20:")
    best_results.sort(key=lambda x: -x[3])
    for i, r in enumerate(best_results[:20]):
        print(f"  {i+1}. {r[3]*100:.2f}% - {r[0]} {r[1]} train={r[2]}")

    return best_results


if __name__ == '__main__':
    run_experiments()
    print("\n\n")
    run_extended_search()
    print("\n\n")
    run_extreme_search()
    print("\n\n")
    run_final_search()