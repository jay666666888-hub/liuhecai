#!/bin/bash
# pre-commit hook - 提交前自动运行生肖映射测试
# 安装: ln -sf predictor/run_tests.py .git/hooks/pre-commit

echo "Running pre-commit tests..."

cd "$(dirname "$0")/.." || exit 1

python3 predictor/run_tests.py test_zodiac_mapping
RESULT=$?

if [ $RESULT -ne 0 ]; then
    echo ""
    echo "============================================================"
    echo "ERROR: 生肖映射测试失败!"
    echo "请修复上述问题后再提交。"
    echo "============================================================"
    exit 1
fi

echo "✓ 生肖映射测试通过"
exit 0