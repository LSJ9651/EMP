"""初始化数据库脚本 — 建表 + 写入基础数据

幂等设计：使用 CREATE TABLE IF NOT EXISTS，可重复执行。
"""

import sys
import os

# 确保脚本可以从 backend/ 目录运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from models import Base, Device, TariffPolicy, AlertThreshold


def init_database():
    """建表并初始化基础数据"""
    print("=" * 50)
    print("能耗智能管理优化平台 — 数据库初始化")
    print("=" * 50)

    # 建表
    Base.metadata.create_all(bind=engine)
    print("[OK] 数据库表创建完成")

    db = SessionLocal()
    try:
        # 检查是否已有数据
        existing_devices = db.query(Device).count()
        if existing_devices > 0:
            print(f"[SKIP] 数据库中已有 {existing_devices} 台设备，跳过初始化")
            return

        # ========== 1. 初始化设备 ==========
        devices_data = [
            {"name": "空压机 A-1", "type": "空压机", "rated_power": 75, "status": "online",
             "line_no": "L01", "workshop": "一车间", "location": "A区-空压站", "efficiency": 0.92},
            {"name": "注塑机 B-1", "type": "注塑机", "rated_power": 55, "status": "online",
             "line_no": "L02", "workshop": "一车间", "location": "B区-注塑区", "efficiency": 0.95},
            {"name": "冷水机组 C-1", "type": "冷水机组", "rated_power": 120, "status": "online",
             "line_no": "L03", "workshop": "一车间", "location": "C区-制冷站", "efficiency": 0.88},
            {"name": "照明系统 D-1", "type": "照明", "rated_power": 30, "status": "online",
             "line_no": "L04", "workshop": "一车间", "location": "全车间", "efficiency": 1.0},
            {"name": "注塑机 B-2", "type": "注塑机", "rated_power": 45, "status": "offline",
             "line_no": "L05", "workshop": "一车间", "location": "B区-注塑区", "efficiency": 0.90},
        ]

        for dd in devices_data:
            device = Device(**dd)
            db.add(device)

        db.flush()
        print(f"[OK] 已创建 {len(devices_data)} 台设备")

        # ========== 2. 初始化电价策略 ==========
        tariffs_data = [
            {"period_name": "高峰", "start_time": "08:00", "end_time": "11:00",
             "price_per_kwh": 1.2, "description": "上午高峰时段"},
            {"period_name": "平段", "start_time": "11:00", "end_time": "18:00",
             "price_per_kwh": 0.8, "description": "白天平段"},
            {"period_name": "高峰", "start_time": "18:00", "end_time": "22:00",
             "price_per_kwh": 1.2, "description": "晚高峰时段"},
            {"period_name": "低谷", "start_time": "22:00", "end_time": "06:00",
             "price_per_kwh": 0.3, "description": "夜间谷电时段"},
        ]

        for td in tariffs_data:
            tariff = TariffPolicy(**td)
            db.add(tariff)

        print(f"[OK] 已创建 {len(tariffs_data)} 条电价策略")

        # ========== 3. 初始化告警阈值 ==========
        for dd in devices_data:
            name = dd["name"]
            rated = dd["rated_power"]

            # 根据设备名称确定设备ID（从数据库查询）
            device = db.query(Device).filter(Device.name == name).first()
            if not device:
                continue

            # 功率阈值：上限=额定*1.1，下限=额定*0.3
            thresholds = [
                AlertThreshold(
                    device_id=device.id,
                    param_type="power",
                    upper_limit=round(rated * 1.1, 2),
                    lower_limit=round(rated * 0.3, 2),
                ),
                AlertThreshold(
                    device_id=device.id,
                    param_type="temperature",
                    upper_limit=85.0,
                    lower_limit=0,
                ),
                AlertThreshold(
                    device_id=device.id,
                    param_type="voltage",
                    upper_limit=420.0,
                    lower_limit=340.0,
                ),
            ]
            for t in thresholds:
                db.add(t)

        print(f"[OK] 已为设备创建告警阈值配置")

        db.commit()
        print("\n[OK] 数据库初始化完成！")
        print(f"  - 设备: {len(devices_data)} 台")
        print(f"  - 电价策略: {len(tariffs_data)} 条")
        print(f"  - 告警阈值: {len(devices_data) * 3} 条")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
