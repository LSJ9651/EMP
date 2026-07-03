"""实时能耗数据路由 — 查询实时/历史能耗"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Telemetry, Device

router = APIRouter(prefix="/api/telemetry", tags=["实时数据"])


@router.get("/latest")
def get_latest_telemetry(device_id: int = Query(None), db: Session = Depends(get_db)):
    """获取设备最新能耗数据"""
    query = db.query(Telemetry)
    if device_id:
        query = query.filter(Telemetry.device_id == device_id)

    # 获取每个设备的最新数据
    from sqlalchemy import func
    subq = (
        db.query(
            Telemetry.device_id,
            func.max(Telemetry.timestamp).label("max_ts")
        )
        .group_by(Telemetry.device_id)
    )
    if device_id:
        subq = subq.filter(Telemetry.device_id == device_id)
    subq = subq.subquery()

    records = (
        db.query(Telemetry)
        .join(subq, (Telemetry.device_id == subq.c.device_id) &
               (Telemetry.timestamp == subq.c.max_ts))
        .all()
    )

    return {
        "code": 200,
        "data": [
            {
                "device_id": r.device_id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "voltage": r.voltage,
                "current": r.current,
                "power": r.power,
                "energy_kwh": r.energy_kwh,
                "power_factor": r.power_factor,
                "status_code": r.status_code,
                "temperature": r.temperature,
            }
            for r in records
        ],
        "message": "success",
    }


@router.get("/current")
def get_current_power(db: Session = Depends(get_db)):
    """获取所有设备当前实时功率（轻量接口）"""
    from sqlalchemy import func
    subq = (
        db.query(
            Telemetry.device_id,
            func.max(Telemetry.timestamp).label("max_ts")
        )
        .group_by(Telemetry.device_id)
    ).subquery()

    latest = (
        db.query(Telemetry, Device.name, Device.type)
        .join(Device, Telemetry.device_id == Device.id)
        .join(subq, (Telemetry.device_id == subq.c.device_id) &
               (Telemetry.timestamp == subq.c.max_ts))
        .all()
    )

    total_power = sum(t.power for t, _, _ in latest)

    return {
        "code": 200,
        "data": {
            "total_power_kw": round(total_power, 2),
            "devices": [
                {
                    "device_id": t.device_id,
                    "name": name,
                    "type": dtype,
                    "power_kw": round(t.power, 2),
                    "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                }
                for t, name, dtype in latest
            ],
        },
        "message": "success",
    }


@router.get("/range")
def get_telemetry_range(
    device_id: int = Query(..., description="设备ID"),
    start: str = Query(None, description="开始时间 ISO格式"),
    end: str = Query(None, description="结束时间 ISO格式"),
    interval_minutes: int = Query(5, description="采样间隔(分钟)"),
    db: Session = Depends(get_db),
):
    """查询时间段内能耗数据"""
    try:
        st = datetime.fromisoformat(start) if start else datetime.now() - timedelta(hours=24)
        et = datetime.fromisoformat(end) if end else datetime.now()
    except ValueError:
        return {"code": 400, "data": None, "message": "时间格式错误"}

    records = (
        db.query(Telemetry)
        .filter(
            Telemetry.device_id == device_id,
            Telemetry.timestamp >= st,
            Telemetry.timestamp <= et,
        )
        .order_by(Telemetry.timestamp.asc())
        .all()
    )

    return {
        "code": 200,
        "data": [
            {
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "power": r.power,
                "voltage": r.voltage,
                "current": r.current,
                "energy_kwh": r.energy_kwh,
                "temperature": r.temperature,
            }
            for r in records
        ],
        "message": "success",
    }
