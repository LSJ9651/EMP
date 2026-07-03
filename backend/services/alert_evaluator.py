"""能耗智能管理优化平台 — 告警评估服务

评估最新的能耗数据是否超过告警阈值，自动生成告警记录。

严重程度分级：
- critical (严重)：当前值超过上限阈值
- warning (警告)：当前值低于下限阈值
- info    (提示)：当前值接近阈值（达到阈值的 85%~100%），提前预警
"""

from datetime import datetime
from models import Device, Telemetry, AlertThreshold, AlertRecord


def evaluate_alerts(db):
    """评估所有设备的告警状态

    对每个设备的最近一条遥测数据，检查是否超过告警阈值，
    同时检测接近阈值的情况生成 info 级别预警。

    Args:
        db: 数据库会话
    """
    devices = db.query(Device).filter(Device.status == "online").all()

    for device in devices:
        # 获取最新一条遥测数据
        latest = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == device.id)
            .order_by(Telemetry.timestamp.desc())
            .first()
        )
        if not latest:
            continue

        # 获取该设备的告警阈值
        thresholds = (
            db.query(AlertThreshold)
            .filter(
                AlertThreshold.device_id == device.id,
                AlertThreshold.is_enabled == True,
            )
            .all()
        )

        for threshold in thresholds:
            value = None
            if threshold.param_type == "power":
                value = latest.power
            elif threshold.param_type == "temperature":
                value = latest.temperature
            elif threshold.param_type == "voltage":
                value = latest.voltage
            elif threshold.param_type == "current":
                value = latest.current

            if value is None:
                continue

            # 检查上限：实际值 > 阈值 → critical
            if threshold.upper_limit is not None and value > threshold.upper_limit:
                _create_alert(db, device.id, threshold.param_type, value,
                              threshold.upper_limit, "upper", "critical")

            # 检查下限：实际值 < 阈值 → warning
            elif threshold.lower_limit is not None and value < threshold.lower_limit:
                _create_alert(db, device.id, threshold.param_type, value,
                              threshold.lower_limit, "lower", "warning")

            # 接近上限阈值（85%~100%）→ info 预警
            elif threshold.upper_limit is not None and value >= threshold.upper_limit * 0.85:
                _create_alert(db, device.id, threshold.param_type, value,
                              threshold.upper_limit, "approaching-upper", "info")

            # 接近下限阈值（100%~115%）→ info 预警
            elif threshold.lower_limit is not None and value <= threshold.lower_limit * 1.15:
                _create_alert(db, device.id, threshold.param_type, value,
                              threshold.lower_limit, "approaching-lower", "info")

    db.commit()


def _create_alert(db, device_id: int, param_type: str, value: float,
                  threshold_value: float, direction: str, severity: str):
    """创建告警记录（防重复：5分钟内同参数不重复）"""
    from datetime import timedelta

    five_min_ago = datetime.now() - timedelta(minutes=5)

    existing = (
        db.query(AlertRecord)
        .filter(
            AlertRecord.device_id == device_id,
            AlertRecord.param_type == param_type,
            AlertRecord.alert_time >= five_min_ago,
            AlertRecord.is_resolved == False,
        )
        .first()
    )

    if existing:
        return

    direction_map = {
        "upper": "超过上限",
        "lower": "低于下限",
        "approaching-upper": "接近上限",
        "approaching-lower": "接近下限",
    }
    direction_text = direction_map.get(direction, direction)
    alert = AlertRecord(
        device_id=device_id,
        alert_time=datetime.now(),
        param_type=param_type,
        value=value,
        threshold_value=threshold_value,
        message=f"{param_type} {direction_text}：当前值 {value:.2f}，阈值 {threshold_value:.2f}",
        severity=severity,
    )
    db.add(alert)

    # 更新设备状态为 alert
    device = db.query(Device).filter(Device.id == device_id).first()
    if device:
        device.status = "alert"
