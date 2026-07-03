"""生成历史模拟数据 — 过去24小时逐分钟能耗数据

为演示和测试提供历史数据，便于前端趋势图展示。
"""

import math
import random
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Device, Telemetry


def generate_mock_data():
    """生成过去24小时逐分钟模拟数据"""
    print("=" * 50)
    print("能耗智能管理优化平台 — 模拟数据生成")
    print("=" * 50)

    db = SessionLocal()
    try:
        devices = db.query(Device).all()
        if not devices:
            print("[ERROR] 数据库中没有设备，请先运行 init_db.py")
            return

        # 检查是否已有模拟数据
        existing = db.query(Telemetry).count()
        if existing > 100:
            print(f"[SKIP] 数据库已有 {existing} 条遥测数据，跳过模拟数据生成")
            return

        now = datetime.now()
        total = 0

        # 过去24小时，每分钟一条
        for i in range(24 * 60):
            ts = now - timedelta(minutes=24 * 60 - i)

            for device in devices:
                # 正弦波模拟功率变化
                base_ratio = math.sin(i * 0.02 + device.id * 2.0) * 0.3 + 0.6

                type_ratios = {
                    "空压机": (0.5, 0.9),
                    "注塑机": (0.3, 0.85),
                    "冷水机组": (0.4, 0.8),
                    "照明": (0.6, 0.95),
                    "其他": (0.2, 0.7),
                }
                low, high = type_ratios.get(device.type, (0.2, 0.7))
                ratio = low + (high - low) * base_ratio

                noise = 1 + random.uniform(-0.1, 0.1)
                power = round(device.rated_power * ratio * noise, 2)
                power = max(0, power)

                voltage = 380 + random.uniform(-5, 5)
                current = round(power * 1000 / (voltage * math.sqrt(3) * 0.95), 2) if power > 0 else 0
                energy_kwh = round(power / 60, 6)
                temperature = round(25 + power / device.rated_power * 30 + random.uniform(-2, 2), 1)

                telemetry = Telemetry(
                    device_id=device.id,
                    timestamp=ts,
                    voltage=round(voltage, 1),
                    current=current,
                    power=power,
                    energy_kwh=energy_kwh,
                    power_factor=random.uniform(0.88, 0.99),
                    temperature=temperature,
                )
                db.add(telemetry)
                total += 1

            # 每100条提交一次
            if total % 500 == 0:
                db.commit()
                print(f"  已生成 {total} 条记录...")

        db.commit()
        print(f"\n[OK] 模拟数据生成完成！共 {total} 条记录")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    generate_mock_data()
