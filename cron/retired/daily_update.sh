#!/bin/bash
# ============================================================
# DEPRECATED (2026-05-27)
# Replaced by: cron/predict_cycle.py
# Reason: duplicate wrapper - daily_update.sh merely calls
#         predict_cycle.py, adding no unique functionality
# ============================================================
# This file is kept for rollback purposes only.
# Do not use in cron - use cron/predict_cycle.py instead.
# ============================================================

#!/bin/bash
# 每日开奖后自动更新预测流程
cd /mnt/c/Users/Admin/liuhecai
python3 cron/predict_cycle.py >> /tmp/liuhecai_update.log 2>&1
