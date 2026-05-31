#!/usr/bin/env python3
"""
五行算法检查
"""
import json

# 当前五行映射（固定表）
WUXING_MAP = {
    '金': [17, 18, 21, 22, 29, 30, 37, 38],
    '木': [13, 14, 21, 22, 27, 28, 35, 36],
    '水': [11, 12, 19, 20, 27, 28, 33, 34],
    '火': [5, 6, 13, 14, 23, 24, 31, 32],
    '土': [49, 1, 2, 9, 10, 41, 42, 49]
}

print("=" * 60)
print("五行算法检查")
print("=" * 60)

print("\n[1] 当前五行规则:")
print("  - 类型: 固定映射表")
print("  - 来源: 传统六合五行对应")
print("  - 规则: 号码 -> 五行")
print()
for wx, nums in WUXING_MAP.items():
    print(f"  {wx}: {nums}")

print("\n[2] 覆盖率验证:")
all_nums = set(range(1, 50))
mapped_nums = set()
for nums in WUXING_MAP.values():
    mapped_nums.update(nums)

missing = all_nums - mapped_nums
duplicates = []
for i in range(1, 50):
    count = sum(1 for nums in WUXING_MAP.values() if i in nums)
    if count > 1:
        duplicates.append((i, count))

print(f"  总号码: 1-49 ({len(all_nums)}个)")
print(f"  已映射: {len(mapped_nums)}个")
print(f"  缺失: {len(missing)}个 - {sorted(missing)}")
print(f"  重复: {len(duplicates)}个")

# 检查五行分布
print("\n[3] 五行分布:")
for wx, nums in WUXING_MAP.items():
    print(f"  {wx}: {len(nums)}个 {sorted(nums)}")

# 验证
print("\n[4] 完整性检查:")
is_complete = len(missing) == 0 and len(duplicates) == 0
print(f"  覆盖率: {len(mapped_nums)}/49 = {len(mapped_nums)/49:.0%}")
print(f"  缺失号码: {'无' if not missing else sorted(missing)}")
print(f"  重复映射: {'无' if not duplicates else duplicates}")
print(f"  状态: {'✓ 完整' if is_complete else '✗ 不完整'}")

# 输出wuxing_algorithm.txt
with open('/home/admin1/liuhecai_strategy_search/wuxing_algorithm.txt', 'w', encoding='utf-8') as f:
    f.write("五行算法说明\n")
    f.write("=" * 50 + "\n\n")
    f.write("1. 算法类型: 固定映射表\n")
    f.write("2. 来源: 传统六合五行对应\n")
    f.write("3. 规则: 号码 -> 五行 (不可更改)\n")
    f.write("4. 覆盖: 49号码中只有部分有映射\n\n")
    f.write("当前映射:\n")
    for wx, nums in WUXING_MAP.items():
        f.write(f"  {wx}: {sorted(nums)}\n")
    f.write(f"\n缺失号码: {sorted(missing)}\n")
    f.write(f"重复映射: {duplicates}\n")

print("\n已保存: wuxing_algorithm.txt")

# 输出wuxing_mapping.json
wuxing_mapping = {}
for i in range(1, 50):
    for wx, nums in WUXING_MAP.items():
        if i in nums:
            wuxing_mapping[f"{i:02d}"] = wx
            break

with open('/home/admin1/liuhecai_strategy_search/wuxing_mapping.json', 'w', encoding='utf-8') as f:
    json.dump(wuxing_mapping, f, ensure_ascii=False, indent=2)

print("已保存: wuxing_mapping.json")

# 输出wuxing_integrity.json
wuxing_integrity = {
    'total_numbers': 49,
    'mapped_numbers': len(mapped_nums),
    'missing_numbers': sorted(list(missing)),
    'duplicate_mappings': duplicates,
    'is_complete': is_complete
}

with open('/home/admin1/liuhecai_strategy_search/wuxing_integrity.json', 'w', encoding='utf-8') as f:
    json.dump(wuxing_integrity, f, ensure_ascii=False, indent=2)

print("已保存: wuxing_integrity.json")

print("\n" + "=" * 60)
if not is_complete:
    print("结论: 五行映射不完整，必须禁用五行特征")
    print("禁用: feature_engine.py -> disable_features: ['wuxing']")
else:
    print("结论: 五行映射完整")