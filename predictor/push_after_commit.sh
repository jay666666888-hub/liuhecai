#!/bin/bash
# post-commit hook - 每次 commit 后自动 push
# 安装: ln -sf predictor/run_tests.sh .git/hooks/post-commit

echo "Auto-pushing to remote..."
cd /mnt/c/Users/Admin/liuhecai

git push
RESULT=$?

if [ $RESULT -ne 0 ]; then
    echo "WARNING: Auto-push failed. Please push manually."
else
    echo "✓ Auto-push successful"
fi

exit 0