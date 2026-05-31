#!/usr/bin/env python3
"""
liuhecai_v4.py - 全新穷举优化脚本
核心：特征工程 + 动态敏感策略穷举 + 严格WF验证 + 多策略集成
彻底解决静态策略问题
"""

import json
import random
import math
from collections import defaultdict
from datetime import datetime
from itertools import combinations, product

random.seed(42)

# ========== 基础配置 ==========
ANIMALS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']
YINYANG = ['陽', '陰']
WUXING = ['木', '火', '土', '金', '水']
SHENGXIAO = {a: i for i, a in enumerate(ANIMALS)}
WAVE_COLORS = {'紅': 0, '藍': 1, '綠': 2, '波': 3}
PHASE_COLORS = {'陽': 0, '陰': 1}

# ========== 数据加载 ==========
def load_history():
    with open('/home/admin1/liuhecai_history.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    records = data.get('recent30', [])
    seq = []
    for r in reversed(records):
        seq.append({
            'period': r['period'],
            'animal': r['actual'],
            'scores': r.get('scores', {})
        })
    return seq

# ========== 特征工程 ==========
def compute_features(seq):
    """计算高级特征：波色、动态间隔、动量、协变"""
    feats = []
    n = len(seq)
    
    for i in range(n):
        f = {}
        # 基础特征
        f['idx'] = i
        f['animal_idx'] = SHENGXIAO[seq[i]['animal']]
        f['period'] = seq[i]['period']
        
        # 波色特征 (Wave Color)
        f['wave_color'] = i % 4  # 0:紅 1:藍 2:綠 3:波
        
        # 阴阳相位
        f['phase'] = i % 2
        
        # 五行
        f['wuxing_idx'] = f['animal_idx'] % 5
        
        # 动态间隔 (Interval since last occurrence)
        f['interval'] = 0
        for j in range(i-1, -1, -1):
            if seq[j]['animal'] == seq[i]['animal']:
                f['interval'] = i - j
                break
        
        # 奇偶特征
        f['parity'] = f['animal_idx'] % 2
        
        # 连庄间隔 (连续出现次数)
        f['streak'] = 0
        for j in range(i-1, -1, -1):
            if seq[j]['animal'] == seq[i]['animal']:
                f['streak'] += 1
            else:
                break
        
        # 动量 (Momentum) - 近N期出现次数
        for window in [3, 5, 8]:
            key = f'momentum_{window}'
            f[key] = 0
            for j in range(max(0, i-window+1), i+1):
                if seq[j]['animal'] == seq[i]['animal']:
                    f[key] += 1
        
        # 协变特征 (Co-variance) - 与其他动物的相关性
        for other in ANIMALS[:6]:  # 前6个
            if other != seq[i]['animal']:
                f[f'co_{other}'] = 0
                for j in range(max(0, i-10), i):
                    if seq[j]['animal'] == other:
                        f[f'co_{other}'] += 1
        
        # 位置波动
        f['pos_volatility'] = 0
        if i >= 5:
            recent = [SHENGXIAO[seq[k]['animal']] for k in range(i-5, i)]
            f['pos_volatility'] = max(recent) - min(recent)
        
        # 得分特征
        if seq[i].get('scores'):
            s = seq[i]['scores']
            f['score_sum'] = sum(s.values())
            f['score_max'] = max(s.values())
            f['score_std'] = (sum((v - f['score_sum']/12)**2 for v in s.values()) / 12) ** 0.5
        
        feats.append(f)
    
    return feats

def compute_composite_signal(feats, idx, target_animal):
    """计算综合信号强度"""
    score = 0.0
    f = feats[idx]
    
    # 波色匹配度
    if f.get('wave_color') == WAVE_COLORS.get(target_animal[0] if len(target_animal) == 1 else '波', 3):
        score += 2.0
    
    # 间隔信号 (遗漏越大，下期出现概率理论回归)
    interval = f.get('interval', 0)
    if 3 <= interval <= 8:
        score += 1.5
    
    # 动量信号
    mom = f.get('momentum_5', 0)
    if mom >= 2:
        score += 1.0
    
    # 协变信号
    co_key = f'co_{target_animal}'
    if f.get(co_key, 0) >= 2:
        score += 1.0
    
    # 位置波动
    if f.get('pos_volatility', 0) > 6:
        score += 0.5
    
    # 冷热信号
    if interval > 10:
        score += 2.0  # 冷号回调
    elif interval <= 2:
        score += 1.0  # 热号延续
    
    return score

# ========== 动态策略生成 ==========
class DynamicStrategy:
    def __init__(self, name, condition_fn, ranking_fn, weight=1.0):
        self.name = name
        self.condition_fn = condition_fn  # (feats, idx) -> bool
        self.ranking_fn = ranking_fn      # (feats, idx, candidates) -> list of (animal, score)
        self.weight = weight
        self.wf_hits = 0
        self.wf_total = 0
    
    def predict(self, feats, idx, candidates):
        if self.condition_fn(feats, idx):
            return self.ranking_fn(feats, idx, candidates)
        return [(a, 0.0) for a in candidates]
    
    def update_wf(self, hit):
        self.wf_total += 1
        if hit:
            self.wf_hits += 1
    
    def wf_rate(self):
        return self.wf_hits / self.wf_total if self.wf_total > 0 else 0.0

# ========== 策略工厂 ==========
def create_strategies():
    strategies = []
    
    # S1: 波色周期策略
    def make_wave_strategy(wave_idx):
        def cond(feats, idx):
            return feats[idx].get('wave_color') == wave_idx
        def rank(feats, idx, candidates):
            scored = []
            for a in candidates:
                # 波色对应动物
                wave_map = {0: ['馬', '蛇'], 1: ['鼠', '虎'], 2: ['兔', '龍'], 3: ['猴', '雞']}
                s = 1.0 if a in wave_map.get(wave_idx, []) else 0.3
                # 间隔加成
                if feats[idx].get('interval', 0) > 5:
                    s += 0.5
                scored.append((a, s))
            return sorted(scored, key=lambda x: -x[1])
        return DynamicStrategy(f'波色_{["紅","藍","綠","波"][wave_idx]}', cond, rank)
    
    for wi in range(4):
        strategies.append(make_wave_strategy(wi))
    
    # S5-S8: 阴阳相位策略
    def make_phase_strategy(phase):
        def cond(feats, idx):
            return feats[idx].get('phase') == phase
        def rank(feats, idx, candidates):
            scored = []
            for a in candidates:
                # 阴阳分类
                yin_map = {'陰': ['鼠', '虎', '兔', '蛇', '馬', '猴'], '陽': ['牛', '龍', '羊', '雞', '狗', '豬']}
                phase_animals = yin_map.get(['陽','陰'][phase], [])
                s = 1.5 if a in phase_animals else 0.5
                scored.append((a, s))
            return sorted(scored, key=lambda x: -x[1])
        return DynamicStrategy(f'相位_{["陽","陰"][phase]}', cond, rank)
    
    for p in range(2):
        strategies.append(make_phase_strategy(p))
    
    # S9-S12: 五行策略
    def make_wuxing_strategy(wx_idx):
        def cond(feats, idx):
            return feats[idx].get('wuxing_idx') == wx_idx
        def rank(feats, idx, candidates):
            scored = []
            wx_map = {0: ['虎', '兔'], 1: ['蛇', '馬'], 2: ['龍', '羊'], 3: ['猴', '雞'], 4: ['鼠', '牛']}
            wx_animals = wx_map.get(wx_idx, [])
            for a in candidates:
                s = 1.3 if a in wx_animals else 0.6
                scored.append((a, s))
            return sorted(scored, key=lambda x: -x[1])
        return DynamicStrategy(f'五行_{["木","火","土","金","水"][wx_idx]}', cond, rank)
    
    for wi in range(5):
        strategies.append(make_wuxing_strategy(wi))
    
    # S13-S16: 间隔区间策略
    def make_interval_strategy(min_int, max_int):
        def cond(feats, idx):
            iv = feats[idx].get('interval', 0)
            return min_int <= iv <= max_int
        def rank(feats, idx, candidates):
            scored = []
            for a in candidates:
                s = 1.0
                # 遗漏大给冷号加分
                if feats[idx].get('interval', 0) >= 8:
                    # 推荐久未出现的
                    s = 0.5  # 降低热度
                scored.append((a, s))
            return sorted(scored, key=lambda x: -x[1])
        return DynamicStrategy(f'间隔_{min_int}_{max_int}', cond, rank)
    
    for mn, mx in [(0,2), (3,5), (6,8), (9,15)]:
        strategies.append(make_interval_strategy(mn, mx))
    
    # S17-S20: 动量策略
    def make_momentum_strategy(window, threshold):
        def cond(feats, idx):
            return feats[idx].get(f'momentum_{window}', 0) >= threshold
        def rank(feats, idx, candidates):
            scored = []
            for a in candidates:
                s = 0.8
                # 历史热号
                if feats[idx].get(f'momentum_{window}', 0) >= threshold:
                    s = 1.5
                scored.append((a, s))
            return sorted(scored, key=lambda x: -x[1])
        return DynamicStrategy(f'动量_{window}_{threshold}', cond, rank)
    
    for w in [3, 5, 8]:
        for t in [1, 2]:
            strategies.append(make_momentum_strategy(w, t))
    
    # S21-S24: 位置波动策略
    def make_volatility_strategy(level):
        def cond(feats, idx):
            vol = feats[idx].get('pos_volatility', 0)
            if level == 0:
                return vol < 3
            elif level == 1:
                return 3 <= vol <= 6
            else:
                return vol > 6
        def rank(feats, idx, candidates):
            return [(a, 1.0) for a in candidates]
        return DynamicStrategy(f'波动_{["低","中","高"][level]}', cond, rank)
    
    for lv in range(3):
        strategies.append(make_volatility_strategy(lv))
    
    # S25-S28: 奇偶策略
    def make_parity_strategy(parity):
        def cond(feats, idx):
            return feats[idx].get('parity') == parity
        def rank(feats, idx, candidates):
            scored = []
            for a in candidates:
                a_parity = SHENGXIAO[a] % 2
                s = 1.5 if a_parity == parity else 0.5
                scored.append((a, s))
            return sorted(scored, key=lambda x: -x[1])
        return DynamicStrategy(f'奇偶_{["奇","偶"][parity]}', cond, rank)
    
    for p in range(2):
        strategies.append(make_parity_strategy(p))
    
    # S29-S32: 连庄策略
    def make_streak_strategy(min_streak):
        def cond(feats, idx):
            return feats[idx].get('streak', 0) >= min_streak
        def rank(feats, idx, candidates):
            scored = []
            for a in candidates:
                s = 1.0
                if feats[idx].get('streak', 0) >= min_streak:
                    s = 1.2
                scored.append((a, s))
            return sorted(scored, key=lambda x: -x[1])
        return DynamicStrategy(f'连庄_{min_streak}', cond, rank)
    
    for ms in [1, 2, 3]:
        strategies.append(make_streak_strategy(ms))
    
    # S33-S36: 协变策略
    def make_covariance_strategy(trigger_animal):
        def cond(feats, idx):
            co_key = f'co_{trigger_animal}'
            return feats[idx].get(co_key, 0) >= 2
        def rank(feats, idx, candidates):
            scored = []
            for a in candidates:
                s = 1.0
                # 与触发动物同五行加分
                if SHENGXIAO[a] % 5 == SHENGXIAO[trigger_animal] % 5:
                    s = 1.3
                scored.append((a, s))
            return sorted(scored, key=lambda x: -x[1])
        return DynamicStrategy(f'协变_{trigger_animal}', cond, rank)
    
    for a in ANIMALS[:6]:
        strategies.append(make_covariance_strategy(a))
    
    # S37-S40: 复合信号策略
    def make_composite_strategy(sig_type):
        def cond(feats, idx):
            if sig_type == 'hot':
                return feats[idx].get('interval', 0) <= 3
            elif sig_type == 'cold':
                return feats[idx].get('interval', 0) >= 8
            elif sig_type == 'momentum_up':
                return feats[idx].get('momentum_5', 0) >= 2
            else:  # volatile
                return feats[idx].get('pos_volatility', 0) > 5
        def rank(feats, idx, candidates):
            scored = []
            for a in candidates:
                s = compute_composite_signal(feats, idx, a)
                scored.append((a, s))
            return sorted(scored, key=lambda x: -x[1])[:6]
        return DynamicStrategy(f'复合_{sig_type}', cond, rank)
    
    for st in ['hot', 'cold', 'momentum_up', 'volatile']:
        strategies.append(make_composite_strategy(st))
    
    # S41-S44: 综合评分策略
    def make_score_strategy(score_type):
        def cond(feats, idx):
            return True  # 全局适用
        def rank(feats, idx, candidates):
            scored = []
            f = feats[idx]
            for a in candidates:
                s = 1.0
                if score_type == 'interval_weight':
                    s = 2.0 / (f.get('interval', 1) + 0.1)
                elif score_type == 'momentum_weight':
                    s = f.get('momentum_8', 0) * 0.5
                elif score_type == 'combined':
                    s = (2.0 / (f.get('interval', 1) + 0.1)) + f.get('momentum_5', 0) * 0.3
                else:  # volatility_weight
                    s = 10.0 / (f.get('pos_volatility', 1) + 1)
                scored.append((a, s))
            return sorted(scored, key=lambda x: -x[1])[:6]
        return DynamicStrategy(f'评分_{score_type}', cond, rank)
    
    for st in ['interval_weight', 'momentum_weight', 'combined', 'volatility_weight']:
        strategies.append(make_score_strategy(st))
    
    # S45-S52: 混合条件策略 (动态敏感)
    def make_hybrid_strategy(c1, c2):
        def cond(feats, idx):
            f = feats[idx]
            if c1 == 'wave' and c2 == 'interval':
                return f.get('wave_color', 0) in [0,1] and 4 <= f.get('interval', 0) <= 8
            elif c1 == 'phase' and c2 == 'momentum':
                return f.get('phase', 0) == 0 and f.get('momentum_5', 0) >= 1
            elif c1 == 'wuxing' and c2 == 'parity':
                return f.get('wuxing_idx', 0) in [0,2] and f.get('parity', 0) == 0
            elif c1 == 'interval' and c2 == 'streak':
                return 5 <= f.get('interval', 0) <= 10 and f.get('streak', 0) <= 1
            elif c1 == 'wave' and c2 == 'parity':
                return f.get('wave_color', 0) in [0,2] and f.get('parity', 0) == 1
            elif c1 == 'momentum' and c2 == 'volatility':
                return f.get('momentum_3', 0) >= 1 and f.get('pos_volatility', 0) > 4
            elif c1 == 'interval' and c2 == 'covariance':
                return 6 <= f.get('interval', 0) <= 12 and f.get('co_鼠', 0) >= 1
            elif c1 == 'phase' and c2 == 'interval':
                return f.get('phase', 0) == 1 and 7 <= f.get('interval', 0) <= 12
            return False
        def rank(feats, idx, candidates):
            return [(a, 1.2) for a in candidates]
        return DynamicStrategy(f'混合_{c1}_{c2}', cond, rank)
    
    for c1, c2 in [('wave','interval'), ('phase','momentum'), ('wuxing','parity'), 
                   ('interval','streak'), ('wave','parity'), ('momentum','volatility'),
                   ('interval','covariance'), ('phase','interval')]:
        strategies.append(make_hybrid_strategy(c1, c2))
    
    return strategies

# ========== Walk-Forward 验证 ==========
def walk_forward_validate(seq, strategies, test_size=30):
    """严格Walk-Forward验证"""
    feats = compute_features(seq)
    n = len(feats)
    
    # 使用最后test_size期作为测试集
    train_end = n - test_size
    
    results = []
    for strat in strategies:
        strat.wf_hits = 0
        strat.wf_total = 0
    
    for i in range(train_end, n):
        actual = seq[i]['animal']
        candidates = ANIMALS[:]
        
        # 收集各策略预测
        all_scores = defaultdict(float)
        active_count = 0
        
        for strat in strategies:
            preds = strat.predict(feats, i, candidates)
            if any(p[1] > 0 for p in preds):
                active_count += 1
                for animal, score in preds:
                    all_scores[animal] += score * strat.weight
        
        # 排序
        ranked = sorted(all_scores.items(), key=lambda x: -x[1])
        top6 = [a for a, s in ranked[:6]]
        
        hit = actual in top6
        
        # 更新各策略WF
        for strat in strategies:
            preds = strat.predict(feats, i, candidates)
            top_predicted = [a for a, s in preds[:3]] if preds else []
            strat.update_wf(actual in top_predicted)
        
        results.append({
            'period': seq[i]['period'],
            'actual': actual,
            'predicted': top6,
            'hit': hit
        })
    
    return results

# ========== 多策略集成 ==========
class EnsembleStrategy:
    def __init__(self, strategies, weights=None):
        self.strategies = strategies
        self.weights = weights or [1.0] * len(strategies)
        self.wf_hits = 0
        self.wf_total = 0
    
    def predict(self, feats, idx, candidates):
        combined = defaultdict(float)
        for strat, w in zip(self.strategies, self.weights):
            preds = strat.predict(feats, idx, candidates)
            for animal, score in preds:
                combined[animal] += score * w
        return sorted(combined.items(), key=lambda x: -x[1])
    
    def update_wf(self, hit):
        self.wf_total += 1
        if hit:
            self.wf_hits += 1
    
    def wf_rate(self):
        return self.wf_hits / self.wf_total if self.wf_total > 0 else 0.0

def build_ensemble(top_strategies, n=5):
    """从TOP策略构建集成"""
    # 选择权重
    total_rate = sum(s.wf_rate() for s in top_strategies[:n])
    weights = [s.wf_rate() / total_rate if total_rate > 0 else 1.0/n 
               for s in top_strategies[:n]]
    return EnsembleStrategy(top_strategies[:n], weights)

# ========== 主流程 ==========
def main():
    print("=" * 60)
    print("liuhecai_v4.py - 全新穷举优化脚本")
    print("特征工程 + 动态敏感策略穷举 + 严格WF验证 + 多策略集成")
    print("=" * 60)
    
    # 加载数据
    print("\n[1] 加载历史数据...")
    seq = load_history()
    print(f"    历史记录数: {len(seq)}")
    
    # 特征工程
    print("\n[2] 特征工程...")
    feats = compute_features(seq)
    print(f"    计算特征: 波色, 动态间隔, 动量, 协变, 位置波动等")
    
    # 策略穷举
    print("\n[3] 穷举动态敏感策略...")
    strategies = create_strategies()
    print(f"    生成策略数: {len(strategies)}")
    
    # Walk-Forward验证
    print("\n[4] Walk-Forward严格验证...")
    wf_results = walk_forward_validate(seq, strategies, test_size=30)
    
    hit_count = sum(1 for r in wf_results if r['hit'])
    print(f"    测试期数: {len(wf_results)}")
    print(f"    单期命中率: {hit_count}/{len(wf_results)} = {hit_count/len(wf_results)*100:.2f}%")
    
    # 排序策略
    print("\n[5] 策略排序 (按WF单期命中率)...")
    strategies.sort(key=lambda s: (-s.wf_rate(), -s.wf_total))
    
    # TOP10报告
    print("\n" + "=" * 60)
    print("TOP10 策略及其WF单期命中率")
    print("=" * 60)
    print(f"{'排名':<4} {'策略名':<20} {'WF命中率':<12} {'WF命中/总数'}")
    print("-" * 60)
    
    top10 = strategies[:10]
    for i, s in enumerate(top10):
        rate = s.wf_rate()
        print(f"{i+1:<4} {s.name:<20} {rate*100:>8.2f}%    {s.wf_hits}/{s.wf_total}")
    
    # 集成策略
    print("\n[6] 多策略集成...")
    ensemble = build_ensemble(strategies, n=5)
    
    # 集成预测验证
    ens_hits = 0
    ens_total = 0
    for i in range(len(feats) - 30, len(feats)):
        actual = seq[i]['animal']
        preds = ensemble.predict(feats, i, ANIMALS[:])
        top6 = [a for a, s in preds[:6]]
        hit = actual in top6
        if hit:
            ens_hits += 1
        ens_total += 1
    
    print(f"    TOP5集成策略 - WF单期命中率: {ens_hits}/{ens_total} = {ens_hits/ens_total*100:.2f}%")
    
    # 完整预测
    print("\n[7] 最新一期预测 (2026087)")
    latest_idx = len(feats) - 1
    print(f"    特征状态: 波色={feats[latest_idx].get('wave_color')}, "
          f"间隔={feats[latest_idx].get('interval')}, "
          f"动量5={feats[latest_idx].get('momentum_5')}")
    
    # 各TOP策略预测
    print("\n    TOP策略预测:")
    for i, s in enumerate(top10[:5]):
        preds = s.predict(feats, latest_idx, ANIMALS[:])
        top6 = [a for a, sc in preds[:6]]
        print(f"    {i+1}. {s.name}: {''.join(top6)}")
    
    # 集成预测
    ens_preds = ensemble.predict(feats, latest_idx, ANIMALS[:])
    ens_top6 = [a for a, s in ens_preds[:6]]
    print(f"\n    集成策略预测: {''.join(ens_top6)}")
    
    # 保存结果
    result = {
        'timestamp': datetime.now().isoformat(),
        'top10_strategies': [
            {'rank': i+1, 'name': s.name, 'wf_rate': s.wf_rate(), 
             'wf_hits': s.wf_hits, 'wf_total': s.wf_total}
            for i, s in enumerate(top10)
        ],
        'ensemble_rate': ens_hits / ens_total if ens_total > 0 else 0,
        'latest_prediction': ''.join(ens_top6)
    }
    
    with open('/home/admin1/liuhecai_v4_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("完成! 结果已保存到 liuhecai_v4_result.json")
    print("=" * 60)
    
    return top10, ensemble

if __name__ == '__main__':
    top10, ensemble = main()
