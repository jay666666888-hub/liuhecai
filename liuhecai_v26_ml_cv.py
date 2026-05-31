#!/usr/bin/env python3
"""
V26 平特一肖 - ML交叉验证
"""
import sys, random, math, json
from pathlib import Path
sys.path.insert(0, str(Path('.').resolve()))

from predictor.data_fetcher import get_all_records, build_standard_records
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']

records = get_all_records([2024,2025,2026])
hist = build_standard_records(records)
print(f"数据: {len(hist)}期")

# 特征提取
def extract_features(window):
    n = len(window)
    features = {}
    
    for z in ZODIACS:
        positions = [i for i,r in enumerate(window) if r['特码生肖']==z]
        if positions:
            features[f'{z}_freq'] = len(positions)
            features[f'{z}_gap'] = n - positions[-1] - 1
            features[f'{z}_recent'] = positions[-1]
            ints = [positions[i]-positions[i+1] for i in range(len(positions)-1)]
            features[f'{z}_interval_avg'] = np.mean(ints) if ints else n
            features[f'{z}_interval_std'] = np.std(ints) if len(ints) > 1 else 0
        else:
            features[f'{z}_freq'] = 0
            features[f'{z}_gap'] = n
            features[f'{z}_recent'] = n
            features[f'{z}_interval_avg'] = n
            features[f'{z}_interval_std'] = n
    
    return features

# 构建数据集
def build_dataset(hist, lookback, start, end):
    X, y = [], []
    for i in range(start, end):
        if i < lookback:
            continue
        window = hist[max(0,i-lookback):i]
        cur = hist[i]
        actual_list = cur.get('开奖生肖', [])
        
        feats = extract_features(window)
        feat_vec = []
        for z in ZODIACS:
            feat_vec.append(feats.get(f'{z}_freq', 0))
            feat_vec.append(feats.get(f'{z}_gap', 0))
            feat_vec.append(feats.get(f'{z}_interval_avg', 0))
            feat_vec.append(feats.get(f'{z}_interval_std', 0))
        
        labels = [1 if z in actual_list else 0 for z in ZODIACS]
        X.append(feat_vec)
        y.append(labels)
    
    return np.array(X), np.array(y)

# 交叉验证测试
print("=== 交叉验证 ===")
lookback = 30

# 分成多个时间段测试
test_periods = [
    (100, 300, "早期"),
    (300, 500, "中期"),
    (500, 700, "后期"),
    (700, 877, "近期"),
]

for train_start, train_end, name in test_periods:
    if train_end - train_start < 50:
        continue
    
    # 训练
    X_train, y_train = build_dataset(hist, lookback, train_start, train_end)
    
    # 测试
    test_end = min(train_end + 50, len(hist))
    X_test, y_test = build_dataset(hist, lookback, train_end, test_end)
    
    if len(X_test) < 10:
        continue
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    hits = 0
    total = 0
    for z_idx, z in enumerate(ZODIACS):
        model = LogisticRegression(max_iter=500, C=0.1)
        model.fit(X_train_scaled, y_train[:, z_idx])
        proba = model.predict_proba(X_test_scaled)[:, 1]
        
        for i in range(len(X_test)):
            pred = 1 if proba[i] > 0.5 else 0
            if pred == y_test[i, z_idx]:
                hits += 1
            total += 1
    
    print(f"{name} [{train_start}-{test_end}]: {hits}/{total} = {hits/total:.4f}")

# 全量步行验证
print("\n=== 步行验证 ===")
all_preds = []
all_actual = []

for i in range(30, len(hist) - 50):
    train_end = i
    train_start = max(0, train_end - 200)
    
    X_train, y_train = build_dataset(hist, lookback, train_start, train_end)
    X_test, y_test = build_dataset(hist, lookback, train_end, train_end + 1)
    
    if len(X_train) < 50 or len(X_test) < 1:
        continue
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    pred_probs = []
    for z_idx, z in enumerate(ZODIACS):
        model = LogisticRegression(max_iter=500, C=0.1)
        model.fit(X_train_scaled, y_train[:, z_idx])
        proba = model.predict_proba(X_test_scaled)[:, 1]
        pred_probs.append(proba[0])
    
    pred_z = ZODIACS[np.argmax(pred_probs)]
    actual_list = hist[train_end].get('开奖生肖', [])
    
    all_preds.append(pred_z)
    all_actual.append(actual_list)

hits = sum(1 for p, a in zip(all_preds, all_actual) if p in a)
print(f"步行验证: {hits}/{len(all_preds)} = {hits/len(all_preds):.4f}")
