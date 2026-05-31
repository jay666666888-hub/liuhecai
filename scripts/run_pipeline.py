#!/usr/bin/env python3
"""
Cron 调用脚本 - 每日 21:35 运行
Usage: python3 scripts/run_pipeline.py

🛡️ P0 修复：进程互斥保护（与 cron/predict_cycle.py 共用锁）
- PID 文件检查
- flock 文件锁
- 重复运行检测
- 崩溃自动释放锁

统一入口：使用 Orchestrator 作为唯一数据源
"""

import sys
import os
import fcntl
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.orchestrator import run_live_cycle
from predictor.notification import send_notification

LOCK_FILE = Path("/tmp/liuhe_pipeline.lock")
PID_FILE = Path("/tmp/liuhe_pipeline.pid")


def get_lock():
    """获取进程锁"""
    lock_file = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        return lock_file
    except (IOError, OSError):
        lock_file.close()
        return None


def release_lock(lock_file):
    """释放锁"""
    if lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
        except (IOError, OSError):
            pass


def is_running():
    """检测是否有其他实例在运行"""
    if not PID_FILE.exists():
        return False
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            PID_FILE.unlink()
            return False
    except (ValueError, IOError):
        return False


def cleanup_stale_lock():
    """清理残留的锁文件"""
    if LOCK_FILE.exists():
        try:
            with open(LOCK_FILE, 'r') as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 0)
            except OSError:
                LOCK_FILE.unlink()
                print(f"[清理] 移除残留锁文件 (pid={pid})")
        except (ValueError, IOError):
            LOCK_FILE.unlink()
            print(f"[清理] 移除格式错误的锁文件")


if __name__ == "__main__":
    # P0: 进程互斥保护
    cleanup_stale_lock()

    if is_running():
        print(f"[{datetime.now().isoformat()}] 已有实例运行中 (pid={PID_FILE.read_text().strip()})，跳过")
        sys.exit(0)

    lock_file = get_lock()
    if not lock_file:
        print(f"[{datetime.now().isoformat()}] 无法获取锁，可能有其他实例在运行")
        sys.exit(1)

    try:
        print(f"[{datetime.now().isoformat()}] Pipeline 启动 (pid={os.getpid()})")
        result = run_live_cycle()
        if result:
            notification_data = {
                "pending_period": result.get("issue"),
                "pending_top6": [],
                "versions": {}
            }
            for v, r in result.get("results", {}).items():
                pred = r.get("prediction", [])
                notification_data["versions"][v] = {
                    "prediction": pred,
                    "strategy": r.get("metadata", {}).get("strategy", "")
                }
                if not notification_data["pending_top6"]:
                    notification_data["pending_top6"] = pred
            send_notification(notification_data)
            print("通知已发送" if notification_data else "无待发送通知")
        print(f"[{datetime.now().isoformat()}] Pipeline 完成")
    finally:
        release_lock(lock_file)
        if PID_FILE.exists():
            PID_FILE.unlink()