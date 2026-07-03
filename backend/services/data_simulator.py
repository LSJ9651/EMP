"""能耗智能管理优化平台 — 数据模拟引擎

后台线程持续模拟设备能耗数据，写入 telemetry 表。
支持设备状态机、正弦波 + 随机噪声、故障注入。
"""

import math
import random
import time
import threading
from datetime import datetime, timedelta
from database import get_db_session
from models import Device, Telemetry
from services.alert_evaluator import evaluate_alerts
from utils.logger import setup_logger

logger = setup_logger("DataSimulator")


class DataSimulator:
    """数据模拟引擎 — 后台线程每5秒为每个在线设备生成能耗数据"""

    def __init__(self, interval: int = 5):
        self.interval = interval
        self._running = False
        self._thread = None
        self._base_time = datetime.now()

    def start(self):
        """启动模拟线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"已启动，采集间隔 {self.interval}s")

    def stop(self):
        """停止模拟线程"""
        self._running = False
        logger.info("已停止")

    def _run_loop(self):
        while self._running:
            try:
                self._generate_cycle()
            except Exception as e:
                logger.error(f"错误: {e}")
            time.sleep(self.interval)

    def _generate_cycle(self):
        """生成一轮模拟数据"""
        db = get_db_session()
        try:
            devices = db.query(Device).all()
            now = datetime.now()

            for device in devices:
                # 随机决定设备在线状态（大部分时间在线）
                if random.random() < 0.08:
                    device.status = "offline"
                    db.commit()
                    continue
                else:
                    device.status = "online"

                # 基于正弦波 + 随机噪声生成功率值
                elapsed = (now - self._base_time).total_seconds()
                base_sine = math.sin(elapsed * 0.05 + device.id * 1.5)

                # 根据设备类型设置基准功率比例
                type_ratios = {
                    "空压机": (0.5, 0.9),
                    "注塑机": (0.3, 0.85),
                    "冷水机组": (0.4, 0.8),
                    "照明": (0.6, 0.95),
                    "其他": (0.2, 0.7),
                }
                low, high = type_ratios.get(device.type, (0.2, 0.7))
                ratio = low + (high - low) * (base_sine + 1) / 2

                # 效率衰减模拟（设备老化）
                ratio *= device.efficiency

                # 随机噪声 ±8%
                noise = 1 + random.uniform(-0.08, 0.08)
                power = round(device.rated_power * ratio * noise, 2)
                power = max(0, power)

                # 计算电流和电度
                voltage = 380 + random.uniform(-5, 5)
                current = round(power * 1000 / (voltage * math.sqrt(3) * 0.95), 2) if power > 0 else 0
                energy_kwh = round(power * self.interval / 3600, 6)

                # 温度模拟
                temperature = round(25 + power / device.rated_power * 30 + random.uniform(-2, 2), 1)

                # 状态码：基于是否超额定功率
                status_code = 0
                if power > device.rated_power * 1.05:
                    status_code = 1
                if power > device.rated_power * 1.15:
                    status_code = 2

                telemetry = Telemetry(
                    device_id=device.id,
                    timestamp=now,
                    voltage=round(voltage, 1),
                    current=current,
                    power=power,
                    energy_kwh=energy_kwh,
                    power_factor=random.uniform(0.88, 0.99),
                    status_code=status_code,
                    temperature=temperature,
                )
                db.add(telemetry)

            db.commit()

            # 评估告警
            evaluate_alerts(db)

        finally:
            db.close()


# 全局模拟器实例
simulator = DataSimulator(interval=5)
