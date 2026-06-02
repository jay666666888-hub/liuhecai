#!/usr/bin/env python3
"""
澳门六合 - 开奖监控进程

功能：
- 21:34 启动（主 cron 前 1 分钟）
- 每 2 秒轮询 API 检查新期号
- 发现新数据立即写入缓存并执行预测流程
- 超时 120 秒自动退出监控模式

使用方式：
  python3 cron/lottery_monitor.py

Crontab 配置：
  34 21 * * * flock -n /tmp/liuhe_monitor.lock -c "cd /mnt/c/Users/Admin/liuhecai && python3 cron/lottery_monitor.py >> /tmp/liuhecai_monitor.log 2>&1"
"""

import sys
import os
import fcntl
import time
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from predictor.data_fetcher import fetch_year_data, get_all_records, build_standard_records
from predictor.orchestrator import sync_latest_results, run_live_cycle
from predictor.ledger_writer import read_live_predictions
from predictor.index_generator import generate_index

LOCK_FILE = Path("/tmp/liuhe_monitor.lock")
PID_FILE = Path("/tmp/liuhe_monitor.pid")

# 监控配置
POLL_INTERVAL = 2  # 秒
MAX_MONITOR_TIME = 120  # 秒
CURRENT_YEAR = datetime.now().year

# 持久化状态目录
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RUNTIME_DIR = DATA_DIR / "runtime"
PROCESSED_ISSUE_FILE = RUNTIME_DIR / "processed_issue.json"
PROCESSED_ISSUE_BACKUP = RUNTIME_DIR / "processed_issue.json._backup"

# 确保目录存在
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


def is_running():
    """检测是否有其他实例在运行"""
    if not PID_FILE.exists():
        return False
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except OSError:
        PID_FILE.unlink()
        return False


def get_latest_cached_issue():
    """获取缓存中的最新期号"""
    cache_path = BASE_DIR / "predictor" / ".cache" / f"liuhecai_{CURRENT_YEAR}.json"
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            if data:
                issues = [r['expect'] for r in data]
                return max(issues) if issues else None
        except:
            pass
    return None


def poll_latest_issue():
    """轮询获取最新期号（仅检查不停顿）"""
    try:
        url = f"https://history.macaumarksix.com/history/macaujc2/y/{CURRENT_YEAR}"
        import requests
        resp = requests.get(url, timeout=(3, 5))
        resp.raise_for_status()
        data = resp.json()
        if data.get('result') and data['data']:
            records = data['data']
            latest = max(records, key=lambda x: x['expect'])
            return latest['expect']
    except:
        pass
    return None


def load_last_processed_issue():
    """
    加载上次处理的开奖期号（持久化存储，带 backup 恢复）

    加载顺序：
    1. 尝试主文件
    2. 主文件损坏 → 尝试 backup
    3. 均有损坏 → 返回 None

    Returns:
        str: 上次处理的开奖期号，或 None
    """
    # 优先尝试主文件
    if PROCESSED_ISSUE_FILE.exists():
        try:
            with open(PROCESSED_ISSUE_FILE, 'r') as f:
                data = json.load(f)
            return data.get('last_processed_result_issue')
        except (json.JSONDecodeError, IOError):
            # 主文件损坏，尝试 backup
            pass

    # 主文件损坏或不存在，尝试 backup
    if PROCESSED_ISSUE_BACKUP.exists():
        try:
            with open(PROCESSED_ISSUE_BACKUP, 'r') as f:
                data = json.load(f)
            # 恢复 backup 到主文件
            import shutil
            shutil.copy2(PROCESSED_ISSUE_BACKUP, PROCESSED_ISSUE_FILE)
            print(f"  [恢复] 已从 backup 恢复 processed_issue.json")
            return data.get('last_processed_result_issue')
        except (json.JSONDecodeError, IOError):
            pass

    return None


def save_last_processed_issue(issue, source="lottery_monitor", duration_ms=None):
    """
    保存最后处理的开奖期号（持久化存储，原子写入 + backup）

    写入顺序：
    1. 先写入 backup（临时）
    2. 再写入主文件
    3. 写入失败 → backup 保留供恢复

    Args:
        issue: 处理的开奖期号
        source: 来源（lottery_monitor / predict_cycle）
        duration_ms: 处理耗时（毫秒）
    """
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
        # backup 当前主文件（如果存在）
        if PROCESSED_ISSUE_FILE.exists():
            import shutil
            shutil.copy2(PROCESSED_ISSUE_FILE, PROCESSED_ISSUE_BACKUP)
        # 原子 rename
        os.replace(temp_path, PROCESSED_ISSUE_FILE)
    except Exception:
        # 写入失败，temp 文件会被清理
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def all_versions_have_prediction(next_issue):
    """
    检查所有活跃版本是否都具备下一期预测（幂等判断）

    Args:
        next_issue: 下一期期号

    Returns:
        True = 所有活跃版本都有下一期预测
        False = 至少有一个版本缺少下一期预测
    """
    try:
        index = generate_index()
        active_versions = index.get("active", [])

        for version in active_versions:
            predictions = read_live_predictions(version, limit=10)
            if not any(p.get('issue') == next_issue for p in predictions):
                return False
        return True
    except Exception as e:
        print(f"  [警告] 检查版本预测失败: {e}")
        return False


def log_result_consumed(issue, source, duration_ms=None):
    """记录开奖结果已处理日志"""
    msg = f"[RESULT_CONSUMED] issue={issue} source={source}"
    if duration_ms is not None:
        msg += f" duration_ms={duration_ms}"
    print(f"[{datetime.now().isoformat()}] {msg}")


def log_result_skipped(issue, reason):
    """记录开奖结果跳过日志"""
    print(f"[{datetime.now().isoformat()}] [RESULT_SKIPPED] issue={issue} reason={reason}")


def main():
    start_time = time.time()
    last_issue = get_latest_cached_issue()

    # 加载持久化的已处理期号
    last_processed = load_last_processed_issue()

    print(f"[{datetime.now().isoformat()}] 监控启动")
    print(f"  初始期号: {last_issue}")
    print(f"  已处理期号: {last_processed}")
    print(f"  轮询间隔: {POLL_INTERVAL}s")
    print(f"  最大监控: {MAX_MONITOR_TIME}s")

    while True:
        # 检查超时
        elapsed = time.time() - start_time
        if elapsed > MAX_MONITOR_TIME:
            print(f"[{datetime.now().isoformat()}] 超时退出 ({elapsed:.0f}s)")
            break

        # 轮询最新期号
        current_issue = poll_latest_issue()

        if not current_issue:
            time.sleep(POLL_INTERVAL)
            continue

        # ===== P0 修复：last_issue 未更新问题 =====
        # 发现新期号时更新 last_issue，防止 API 抖动导致重复处理
        if current_issue != last_issue:
            last_issue = current_issue

        # ===== 核心判断：processed_issue 机制 =====
        # 1. API 返回旧期号 → 跳过
        # 2. API 重复返回同一期号 → 跳过
        # 3. 已处理过的期号 → 跳过
        if last_processed and int(current_issue) <= int(last_processed):
            log_result_skipped(current_issue, "already_processed")
            time.sleep(POLL_INTERVAL)
            continue

        # 发现新期号
        print(f"[{datetime.now().isoformat()}] 发现新期号: {current_issue}")
        cycle_start = time.time()

        try:
            print(f"  正在运行完整预测周期...")

            # 获取完整数据并更新缓存
            records = get_all_records([CURRENT_YEAR], force_refresh=True)
            standard = build_standard_records(records)

            cache_dir = BASE_DIR / "predictor" / ".cache"
            cache_dir.mkdir(exist_ok=True)
            cache_path = cache_dir / f"liuhecai_{CURRENT_YEAR}.json"

            url = f"https://history.macaumarksix.com/history/macaujc2/y/{CURRENT_YEAR}"
            import requests
            resp = requests.get(url, timeout=(10, 30))
            resp.raise_for_status()
            api_data = resp.json().get('data', [])

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(api_data, f, ensure_ascii=False, indent=2)

            # 更新缓存元数据
            meta_path = cache_dir / "_cache_metadata.json"
            metadata = {
                "last_api_success": datetime.now().isoformat(),
                "last_cache_read": datetime.now().isoformat(),
                "source": "api"
            }
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            print(f"  缓存已更新: {cache_path}")

            # ===== P0 修复：多版本判断错误 =====
            # 计算下一期号
            next_issue = str(int(current_issue) + 1)

            # 检查所有活跃版本是否都有下一期预测（而非任意一个）
            if all_versions_have_prediction(next_issue):
                log_result_skipped(next_issue, "all_versions_have_prediction")
                print(f"  [跳过] 所有版本已有下一期预测: {next_issue}")
                print(f"[{datetime.now().isoformat()}] 监控完成，退出")
                return

            # 触发验证 + 预测下一期
            cycle_result = run_live_cycle()
            predicted_issue = cycle_result.get('issue', next_issue)

            # 计算耗时
            cycle_elapsed_ms = int((time.time() - cycle_start) * 1000)

            # ===== 保存已处理期号（持久化）=====
            save_last_processed_issue(
                issue=current_issue,
                source="lottery_monitor",
                duration_ms=cycle_elapsed_ms
            )
            last_processed = current_issue

            log_result_consumed(current_issue, "lottery_monitor", cycle_elapsed_ms)
            print(f"  预测周期结果: {predicted_issue}")
            print(f"  总耗时: {cycle_elapsed_ms}ms")
            print(f"[{datetime.now().isoformat()}] 监控完成，退出")
            return

        except Exception as e:
            print(f"  更新失败: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    if is_running():
        print(f"[{datetime.now().isoformat()}] 已有实例运行中，跳过")
        sys.exit(0)

    lock_file = get_lock()
    if not lock_file:
        print(f"[{datetime.now().isoformat()}] 无法获取锁")
        sys.exit(1)

    try:
        main()
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] 异常: {e}")
        raise
    finally:
        if lock_file:
            try:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
                lock_file.close()
            except:
                pass
        if PID_FILE.exists():
            PID_FILE.unlink()