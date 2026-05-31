#!/usr/bin/env python3
"""
启动检查 - 在 cron 或服务启动时运行
确保所有 metadata 配置正确
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    from scripts.validate_metadata import run_validation
    run_validation()