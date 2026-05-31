#!/usr/bin/env python3
"""
V26 平特一肖 - ML+特征组合搜索
"""
import sys, random, math
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from predictor.data_fetcher import get_all_records, build_standard_records
import numpy as np

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f"数据: {len(hist)}期")

# 特征提取
def extract_features(window):
    """提取所有可用特征"""
    n = len(window)
    features = {}
    
    # 基础：每个生肖的出现次数、遗漏、间隔
    for z in ZODIACS:
        positions = [i for i,r in enumerate(window) if r['特码生肖']==z]
        if positions:
            features[f'{z}_freq'] = len(positions)
            features[f'{z}_gap'] = n - positions[-1] - 1
            features[f'{z}_recent'] = positions[-1] if positions else n
            if len(positions) >= 2:
                features[f'{z}_interval_avg'] = np.mean([positions[i]-positions[i+1] for i in range(len(positions)-1)])
                features[f'{z}_interval_std'] = np.std([positions[i]-positions[i+1] for i in range(len(positions)-1)])
            else:
                features[f'{z}_interval_avg'] = n
                features[f'{z}_interval_std'] = n
        else:
            features[f'{z}_freq'] = 0
            features[f'{z}_gap'] = n
            features[f'{z}_recent'] = n
            features[f'{z}_interval_avg'] = n
            features[f'{z}_interval_std'] = n
    
    # 全局特征
    all_zodiacs = [r['特码生肖'] for r in window]
    features['total_appearances'] = len(all_zodiacs)
    
    # 号码特征
    numbers = [int(r['特码号码']) for r in window if r.get('特码号码')]
    if numbers:
        features['num_avg'] = np.mean(numbers)
        features['num_std'] = np.std(numbers) if len(numbers) > 1 else 0
        features['num_max'] = max(numbers)
        features['num_min'] = min(numbers)
    
    # 波色特征
    colors = [r.get('波色') for r in window]
    features['red_count'] = colors.count('red')
    features['blue_count'] = colors.count('blue')
    features['green_count'] = colors.count('green')
    
    return features

# 构建训练数据
def build_dataset(hist, lookback, train_end):
    X, y = [], []
    for i in range(lookback, train_end):
        window = hist[max(0,i-lookback):i]
        cur = hist[i]
        actual_list = cur.get('开奖生肖', [])
        
        # 标签：哪个生肖命中
        labels = []
        for z_idx, z in enumerate(ZODIACS):
            labels.append(1 if z in actual_list else 0)
        
        feats = extract_features(window)
        feat_vec = [feats.get(f'{z}_freq', 0) for z in ZODIACS] + \
                   [feats.get(f'{z}_gap', 0) for z in ZODIACS] + \
                   [feats.get(f'{z}_interval_avg', 0) for z in ZODIACS] + \
                   [feats.get(f'{z}_interval_std', 0) for z in ZODIACS]
        
        X.append(feat_vec)
        y.append(labels)
    
    return np.array(X), np.array(y)

# 简单ML：梯度提升
try:
    import lightgbm as lgb
    HAS_LGB = True
except:
    HAS_LGB = False

try:
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    HAS_SK = True
except:
    HAS_SK = False

print(f"LightGBM: {HAS_LGB}, Sklearn: {HAS_SK}")

if HAS_LGB or HAS_SK:
    train_end = 700
    X_train, y_train = build_dataset(hist, 30, train_end)
    
    # 多标签分类
    predictions = {}
    for z_idx, z in enumerate(ZODIACS):
        y_z = y_train[:, z_idx]
        if HAS_LGB:
            model = lgb.LGBMClassifier(n_estimators=50, max_depth=3, learning_rate=0.1, verbose=-1)
        else:
            model = LogisticRegression(max_iter=200)
        model.fit(X_train, y_z)
        
        # 全量预测
        X_all, _ = build_dataset(hist, 30, len(hist))
        proba = model.predict_proba(X_all)[:, 1] if hasattr(model, 'predict_proba') else model.predict(X_all)
        predictions[z] = proba
    
    # 综合评分
    scores = np.zeros(len(hist) - 30)
    for z_idx, z in enumerate(ZODIACS):
        scores += predictions.get(z, np.zeros(len(scores)))
    
    # 评估
    hits = 0
    total = 0
    for i in range(30, len(hist)):
        pred_zodiac = ZODIACS[np.argmax([predictions[z][i-30] if i-30 < len(predictions[z]) else 0 for z in ZODIACS])]
        actual_list = hist[i].get('开奖生肖', [])
        if pred_zodiac in actual_list:
            hits += 1
        total += 1
    
    print(f"ML方法命中率: {hits}/{total} = {hits/total:.4f}")
else:
    print("无可用ML库")
