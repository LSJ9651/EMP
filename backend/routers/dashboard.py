"""看板路由 — 聚合数据：概览、能流图、趋势"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Device, Telemetry, AlertRecord, TariffPolicy
from services.scheduling_core import estimate_carbon_emission

router = APIRouter(prefix="/api/dashboard", tags=["看板"])


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """获取看板概览数据"""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 总功率
    subq = (
        db.query(
            Telemetry.device_id,
            func.max(Telemetry.timestamp).label("max_ts")
        )
        .filter(Telemetry.timestamp >= today_start)
        .group_by(Telemetry.device_id)
    ).subquery()

    latest_records = (
        db.query(Telemetry)
        .join(subq, (Telemetry.device_id == subq.c.device_id) &
               (Telemetry.timestamp == subq.c.max_ts))
        .all()
    )

    total_power_kw = round(sum(r.power for r in latest_records), 2)

    # 今日总能耗
    today_telemetry = db.query(Telemetry).filter(
        Telemetry.timestamp >= today_start
    ).all()

    today_energy_kwh = round(sum(r.energy_kwh for r in today_telemetry), 2)
    co2_estimate_kg = estimate_carbon_emission(today_energy_kwh)

    # 告警数量
    alert_count = (
        db.query(AlertRecord)
        .filter(AlertRecord.is_resolved == False)
        .count()
    )

    # 设备状态
    devices = db.query(Device).all()
    online = sum(1 for d in devices if d.status == "online")
    offline = sum(1 for d in devices if d.status == "offline")
    alert_dev = sum(1 for d in devices if d.status == "alert")

    return {
        "code": 200,
        "data": {
            "total_power_kw": total_power_kw,
            "today_energy_kwh": today_energy_kwh,
            "co2_estimate_kg": co2_estimate_kg,
            "alert_count": alert_count,
            "device_stats": {
                "online": online,
                "offline": offline,
                "alert": alert_dev,
            },
        },
        "message": "success",
    }


@router.get("/energyflow")
def get_energyflow(db: Session = Depends(get_db)):
    """获取能流图数据（桑基图：变压器→车间→设备三级，nodes/links 格式兼容 ECharts sankey）"""
    devices = db.query(Device).all()

    # 构建节点：name 作为标识符，links 中的 source/target 必须匹配节点 name
    nodes = []
    # 变压器节点 (category=0)
    nodes.append({
        "name": "变压器",
        "value": 200,
        "category": 0,
    })

    # 车间节点（按 workshop 分组，category=1）
    workshops = {}
    for d in devices:
        if d.workshop not in workshops:
            workshops[d.workshop] = {
                "name": d.workshop,
                "value": 0,
                "category": 1,
            }
        workshops[d.workshop]["value"] += d.rated_power

    nodes.extend(workshops.values())

    # 设备节点（category=2）
    for d in devices:
        nodes.append({
            "name": d.name,
            "value": d.rated_power,
            "category": 2,
            "status": d.status,
        })

    # 构建边：source/target 使用节点 name 匹配
    links = []
    # 变压器→车间
    for ws_name, ws_data in workshops.items():
        links.append({
            "source": "变压器",
            "target": ws_data["name"],
            "value": round(ws_data["value"], 1),
        })

    # 车间→设备
    for d in devices:
        # 创建车间到设备的连接（仅当设备功率>0）
        links.append({
            "source": d.workshop,
            "target": d.name,
            "value": d.rated_power,
        })

    return {
        "code": 200,
        "data": {
            "nodes": nodes,
            "links": links,
        },
        "message": "success",
    }


@router.get("/trend")
def get_trend(
    device_ids: str = Query(None, description="设备ID列表，逗号分隔"),
    minutes: int = Query(60, description="查询最近N分钟"),
    db: Session = Depends(get_db),
):
    """获取多设备功率趋势数据"""
    since = datetime.now() - timedelta(minutes=minutes)

    # 解析设备ID
    if device_ids:
        ids = [int(x.strip()) for x in device_ids.split(",") if x.strip()]
    else:
        ids = [d.id for d in db.query(Device).all()]

    records = (
        db.query(Telemetry, Device.name)
        .join(Device, Telemetry.device_id == Device.id)
        .filter(
            Telemetry.device_id.in_(ids),
            Telemetry.timestamp >= since,
        )
        .order_by(Telemetry.timestamp.asc())
        .all()
    )

    # 按设备分组
    device_data = {}
    for r, name in records:
        if name not in device_data:
            device_data[name] = []
        device_data[name].append({
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "power": r.power,
        })

    return {
        "code": 200,
        "data": {
            "series": [
                {"name": name, "data": values}
                for name, values in device_data.items()
            ],
            "time_range": f"{since.isoformat()} ~ {datetime.now().isoformat()}",
        },
        "message": "success",
    }


@router.get("/alerts-bar")
def get_alerts_bar(limit: int = Query(10, description="返回条数"), db: Session = Depends(get_db)):
    """获取最新未处理告警（看板滚动条）"""
    alerts = (
        db.query(AlertRecord, Device.name)
        .join(Device, AlertRecord.device_id == Device.id)
        .filter(AlertRecord.is_resolved == False)
        .order_by(AlertRecord.alert_time.desc())
        .limit(limit)
        .all()
    )

    return {
        "code": 200,
        "data": [
            {
                "id": a.id,
                "device_name": name,
                "alert_time": a.alert_time.isoformat() if a.alert_time else None,
                "message": a.message,
                "severity": a.severity,
            }
            for a, name in alerts
        ],
        "message": "success",
    }
