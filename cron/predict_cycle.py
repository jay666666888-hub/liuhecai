#!/usr/bin/env python3
"""
澳门六合 - 预测流程

✅ 已重构：使用 Orchestrator 统一入口
- 验证上期预测（所有活跃版本）
- 生成下期预测并写入账本
- 自动聚合到 storage/aggregated_live.jsonl

🛡️ P0 修复：进程互斥 + 崩溃保护
- PID 文件检查
- flock 文件锁
- 重复运行检测
- 崩溃自动释放锁
"""

import sys
import os
import fcntl
import time
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.orchestrator import run_live_cycle
from predictor.index_generator import write_index

LOCK_FILE = Path("/tmp/liuhe_pipeline.lock")
PID_FILE = Path("/tmp/liuhe_pipeline.pid")

# 持久化状态目录
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RUNTIME_DIR = DATA_DIR / "runtime"
PROCESSED_ISSUE_FILE = RUNTIME_DIR / "processed_issue.json"
PROCESSED_ISSUE_BACKUP = RUNTIME_DIR / "processed_issue.json._backup"

RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


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
            # 崩溃后残留锁文件由下次启动清理
        except (IOError, OSError):
            pass


def is_running():
    """检测是否有其他实例在运行"""
    if not PID_FILE.exists():
        return False

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())

        # 检查进程是否存在
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            # 进程不存在，说明残留，清除
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
                # 进程存在，锁是有效的
            except OSError:
                # 进程不存在，残留锁
                LOCK_FILE.unlink()
                print(f"[清理] 移除残留锁文件 (pid={pid})")
        except (ValueError, IOError):
            # 残留锁文件格式错误，直接删除
            LOCK_FILE.unlink()
            print(f"[清理] 移除格式错误的锁文件")


def load_last_processed_issue():
    """加载上次处理的开奖期号（带 backup 恢复）"""
    # 优先尝试主文件
    if PROCESSED_ISSUE_FILE.exists():
        try:
            with open(PROCESSED_ISSUE_FILE, 'r') as f:
                data = json.load(f)
            return data.get('last_processed_result_issue')
        except (json.JSONDecodeError, IOError):
            pass

    # 主文件损坏，尝试 backup
    if PROCESSED_ISSUE_BACKUP.exists():
        try:
            with open(PROCESSED_ISSUE_BACKUP, 'r') as f:
                data = json.load(f)
            shutil.copy2(PROCESSED_ISSUE_BACKUP, PROCESSED_ISSUE_FILE)
            print(f"  [恢复] 已从 backup 恢复 processed_issue.json")
            return data.get('last_processed_result_issue')
        except (json.JSONDecodeError, IOError):
            pass

    return None


def save_last_processed_issue(issue, source="predict_cycle", duration_ms=None):
    """保存最后处理的开奖期号（原子写入 + backup）"""
    data = {
        'last_processed_result_issue': issue,
        'processed_at': datetime.now().isoformat(),
        'source': source,
    }
    if duration_ms is not None:
        data['duration_ms'] = duration_ms

    # 原子写入：先写 backup，再 rename 到主文件
    temp_fd, temp_path = tempfile.mkstemp(dir=RUNTIME_DIR, prefix='.tmp_', suffix='.json')
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if PROCESSED_ISSUE_FILE.exists():
            shutil.copy2(PROCESSED_ISSUE_FILE, PROCESSED_ISSUE_BACKUP)
        os.replace(temp_path, PROCESSED_ISSUE_FILE)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def verify_and_predict():
    """验证上期预测，生成下期预测（使用 Orchestrator）"""
    start_time = time.time()

    result = run_live_cycle()

    # 计算耗时并保存处理状态
    if result and result.get('issue'):
        cycle_elapsed_ms = int((time.time() - start_time) * 1000)
        save_last_processed_issue(
            issue=result['issue'],
            source="predict_cycle",
            duration_ms=cycle_elapsed_ms
        )
        print(f"[{datetime.now().isoformat()}] [RESULT_CONSUMED] issue={result['issue']} source=predict_cycle duration_ms={cycle_elapsed_ms}")

    write_index()
    return result


if __name__ == "__main__":
    # P0: 进程互斥保护
    cleanup_stale_lock()

    if is_running():
        print(f"[{datetime.now().isoformat()}] 已有实例运行中，跳过此次执行")
        sys.exit(0)

    lock_file = get_lock()
    if not lock_file:
        print(f"[{datetime.now().isoformat()}] 无法获取锁，可能有其他实例在运行")
        sys.exit(1)

    try:
        print(f"[{datetime.now().isoformat()}] Pipeline 启动 (pid={os.getpid()})")
        verify_and_predict()
        print(f"[{datetime.now().isoformat()}] Pipeline 完成")
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Pipeline 异常: {e}")
        raise
    finally:
        release_lock(lock_file)
        # 正常完成后删除 PID 文件（锁文件由 cleanup 处理）
        if PID_FILE.exists():
            PID_FILE.unlink()