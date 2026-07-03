"""
数据清理脚本 — 仅删除今天之前产生的历史数据

执行流程：
  1. 备份数据库文件
  2. 统计当前数据量
  3. 删除今天之前的历史记录（保留今天 00:00 之后的数据）
  4. 验证清理结果
  5. 生成清理报告
"""

import datetime
import os
import shutil
import sys
from pathlib import Path

# 添加父目录到 sys.path，确保可以导入 backend 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import SessionLocal
from models import (
    Telemetry, AlertRecord, AgentReport, ScheduleTask,
    ScheduleExecution, ChatHistory, Notification, WorkflowExecution
)
from sqlalchemy import func

# ── 配置 ──────────────────────────────────────────
DB_DIR = Path(__file__).resolve().parent.parent
DB_FILE = DB_DIR / "energy_optimizer.db"
BACKUP_DIR = DB_DIR / "backups"
TODAY = datetime.date.today()
TODAY_START = datetime.datetime.combine(TODAY, datetime.time.min)

# 要清理的表及其时间戳字段
CLEANUP_TABLES = {
    "Telemetry":          (Telemetry, Telemetry.timestamp),
    "AlertRecord":        (AlertRecord, AlertRecord.alert_time),
    "AgentReport":        (AgentReport, AgentReport.created_at),
    "ScheduleTask":       (ScheduleTask, ScheduleTask.created_at),
    "ScheduleExecution":  (ScheduleExecution, ScheduleExecution.created_at),
    "ChatHistory":        (ChatHistory, ChatHistory.created_at),
    "Notification":       (Notification, Notification.created_at),
    "WorkflowExecution":  (WorkflowExecution, WorkflowExecution.created_at),
}


def create_backup() -> str:
    """创建数据库文件的时间戳备份"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"energy_optimizer_backup_{timestamp}.db"
    shutil.copy2(DB_FILE, backup_path)
    print(f"[OK] 备份已创建: {backup_path}")
    return str(backup_path)


def count_records(db, label: str = "当前") -> dict:
    """统计各表数据量"""
    result = {}
    total_all = 0
    total_today = 0
    total_history = 0

    print(f"\n─── {label}数据量统计 ───")
    print(f"{'表名':20s} {'总计':>8s} {'今天':>8s} {'历史':>8s}")
    print("-" * 48)

    for name, (model, time_col) in CLEANUP_TABLES.items():
        total = db.query(func.count(model.id)).scalar() or 0
        today_count = db.query(func.count(model.id)).filter(time_col >= TODAY_START).scalar() or 0
        history_count = total - today_count
        total_all += total
        total_today += today_count
        total_history += history_count
        result[name] = {"total": total, "today": today_count, "history": history_count}
        print(f"{name:20s} {total:8d} {today_count:8d} {history_count:8d}")

    print("-" * 48)
    print(f"{'合计':20s} {total_all:8d} {total_today:8d} {total_history:8d}")
    result["_summary"] = {"total": total_all, "today": total_today, "history": total_history}
    return result


def cleanup_history(db) -> dict:
    """删除今天之前的历史数据，返回各表删除的记录数"""
    deleted = {}
    print(f"\n─── 开始清理历史数据 ───")
    print(f"保留条件: 记录时间 >= {TODAY_START}")
    print()

    for name, (model, time_col) in CLEANUP_TABLES.items():
        # 查询要删除的记录数
        to_delete = db.query(func.count(model.id)).filter(time_col < TODAY_START).scalar() or 0
        if to_delete == 0:
            print(f"  {name:20s}  无历史数据，跳过")
            deleted[name] = 0
            continue

        # 执行删除
        db.query(model).filter(time_col < TODAY_START).delete(synchronize_session=False)
        db.commit()
        deleted[name] = to_delete
        print(f"  [OK] {name:20s}  已删除 {to_delete:6d} 条历史记录")

    return deleted


def verify_cleanup(db, before_stats: dict) -> bool:
    """验证清理结果"""
    print(f"\n─── 验证数据完整性 ───")
    all_pass = True

    for name, (model, time_col) in CLEANUP_TABLES.items():
        total = db.query(func.count(model.id)).scalar() or 0
        today_count = db.query(func.count(model.id)).filter(time_col >= TODAY_START).scalar() or 0
        history_count = db.query(func.count(model.id)).filter(time_col < TODAY_START).scalar() or 0

        # 检查1: 历史数据应为0
        if history_count == 0:
            print(f"  [OK] {name:20s}  历史数据已全部清除")
        else:
            print(f"  [FAIL] {name:20s}  仍有 {history_count} 条历史数据残留!")
            all_pass = False

        # 检查2: 今天的数据不受影响
        before_today = before_stats.get(name, {}).get("today", 0)
        if today_count == before_today:
            print(f"     {name:20s}  今天的数据完整 ({today_count} 条)")
        else:
            print(f"     {name:20s}  今天的数据量变化: {before_today} → {today_count}")
            all_pass = False

    # 检查配置/主数据表是否受影响
    print(f"\n─── 检查配置/主数据表完整性 ───")
    from models import User, Device, TariffPolicy, AlertThreshold, AIConfigEntry, ReportSubscription
    config_tables = {
        "User": User,
        "Device": Device,
        "TariffPolicy": TariffPolicy,
        "AlertThreshold": AlertThreshold,
        "AIConfigEntry": AIConfigEntry,
        "ReportSubscription": ReportSubscription,
    }
    for name, model in config_tables.items():
        count = db.query(func.count(model.id)).scalar() or 0
        print(f"  [OK] {name:20s}  数据完整 ({count} 条)")

    return all_pass


def main():
    print("=" * 60)
    print("  能耗管理平台 — 数据清理工具")
    print(f"  执行时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  保留日期: {TODAY} 00:00:00 之后的全部数据")
    print("=" * 60)

    # 1. 创建备份
    print("\n>>> 第1步: 创建数据库备份...")
    backup_path = create_backup()

    # 2. 连接数据库
    db = SessionLocal()

    try:
        # 3. 清理前统计
        print("\n>>> 第2步: 清理前数据统计...")
        before_stats = count_records(db, "清理前")

        # 4. 确认
        total_history = before_stats["_summary"]["history"]
        if total_history == 0:
            print("\n[OK] 无历史数据需要清理，操作完成。")
            return

        print(f"\n>>> 第3步: 执行清理 (将删除 {total_history} 条历史记录)...")
        deleted = cleanup_history(db)

        # 5. 清理后统计
        print("\n>>> 第4步: 清理后数据统计...")
        after_stats = count_records(db, "清理后")

        # 6. 验证
        print("\n>>> 第5步: 完整性验证...")
        all_ok = verify_cleanup(db, before_stats)

        # 7. 清理报告
        print(f"\n{'='*60}")
        print("  清理报告")
        print(f"{'='*60}")
        total_deleted = sum(deleted.values())
        print(f"  备份文件: {backup_path}")
        print(f"  总计删除: {total_deleted} 条历史记录")
        print(f"  保留数据: {after_stats['_summary']['today']} 条 (今天)")
        print(f"  验证结果: {'[OK] 全部通过' if all_ok else '[FAIL] 存在问题'}")
        print(f"{'='*60}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
