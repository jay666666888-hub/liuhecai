#!/usr/bin/env python3
"""
Cron 调用脚本 - 每日 21:35 运行
Usage: python3 scripts/run_pipeline.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.main import main

if __name__ == "__main__":
    main()