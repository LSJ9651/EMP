"""设备管理路由 — 设备 CRUD"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from database import get_db
from models import Device
from middleware.permission import require_permission

router = APIRouter(prefix="/api/devices", tags=["设备管理"])


class DeviceCreate(BaseModel):
    name: str = Field(..., description="设备名称")
    type: str = Field(..., description="设备类型")
    rated_power: float = Field(..., gt=0, description="额定功率(kW)")
    status: str = Field(default="offline")
    line_no: Optional[str] = None
    workshop: Optional[str] = "一车间"
    location: Optional[str] = None
    efficiency: float = Field(default=1.0, ge=0, le=1)


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    rated_power: Optional[float] = None
    status: Optional[str] = None
    line_no: Optional[str] = None
    workshop: Optional[str] = None
    location: Optional[str] = None
    efficiency: Optional[float] = None


@router.get("/list")
def list_devices(db: Session = Depends(get_db)):
    """获取所有设备列表（含实时能耗数据）"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from models import Telemetry

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = datetime.now() - timedelta(days=7)

    devices = db.query(Device).order_by(Device.id).all()
    result = []

    for d in devices:
        # 今日能耗
        today_energy = (
            db.query(func.sum(Telemetry.energy_kwh))
            .filter(Telemetry.device_id == d.id, Telemetry.timestamp >= today_start)
            .scalar() or 0
        )

        # 近7日负载率
        recent_records = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == d.id, Telemetry.timestamp >= seven_days_ago)
            .all()
        )
        avg_load_rate = 0.0
        if recent_records and d.rated_power > 0:
            avg_power = sum(r.power for r in recent_records) / len(recent_records)
            avg_load_rate = round(avg_power / d.rated_power, 3)

        avg_pf = 0.0
        if recent_records:
            avg_pf = round(sum(r.power_factor for r in recent_records) / len(recent_records), 2)

        result.append({
            "id": d.id,
            "name": d.name,
            "type": d.type,
            "rated_power": d.rated_power,
            "status": d.status,
            "line_no": d.line_no,
            "workshop": d.workshop,
            "location": d.location,
            "efficiency": d.efficiency,
            "today_energy_kwh": round(today_energy, 2),
            "avg_load_rate": avg_load_rate,
            "avg_power_factor": avg_pf,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        })

    return {
        "code": 200,
        "data": result,
        "message": "success",
    }


@router.get("/ranking")
def device_ranking(db: Session = Depends(get_db)):
    """获取设备能效排行榜"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from models import Telemetry

    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = datetime.now() - timedelta(days=7)

    devices = db.query(Device).all()
    ranking = []

    for device in devices:
        # 今日能耗
        today_energy = (
            db.query(func.sum(Telemetry.energy_kwh))
            .filter(
                Telemetry.device_id == device.id,
                Telemetry.timestamp >= today_start,
            )
            .scalar() or 0
        )

        # 近7日负载率
        recent_records = (
            db.query(Telemetry)
            .filter(
                Telemetry.device_id == device.id,
                Telemetry.timestamp >= seven_days_ago,
            )
            .all()
        )

        avg_load_rate = 0.0
        if recent_records and device.rated_power > 0:
            avg_power = sum(r.power for r in recent_records) / len(recent_records)
            avg_load_rate = round(avg_power / device.rated_power, 3)

        # 运行时长（有数据的分钟数）
        runtime_minutes = 0
        if recent_records:
            runtime_minutes = len(recent_records)

        # 功率因数
        avg_pf = 0.0
        if recent_records:
            avg_pf = round(sum(r.power_factor for r in recent_records) / len(recent_records), 2)

        ranking.append({
            "device_id": device.id,
            "name": device.name,
            "type": device.type,
            "rated_power": device.rated_power,
            "efficiency": device.efficiency,
            "status": device.status,
            "today_energy_kwh": round(today_energy, 2),
            "avg_load_rate": avg_load_rate,
            "runtime_minutes": runtime_minutes,
            "avg_power_factor": avg_pf,
            "workshop": device.workshop,
        })

    # 按负载率降序排列
    ranking.sort(key=lambda x: x["avg_load_rate"], reverse=True)

    return {
        "code": 200,
        "data": {
            "ranking": ranking,
            "headers": [
                "name", "type", "rated_power", "efficiency", "today_energy_kwh",
                "avg_load_rate", "avg_power_factor", "runtime_minutes"
            ],
        },
        "message": "success",
    }


@router.get("/{device_id}")
def get_device(device_id: int, db: Session = Depends(get_db)):
    """获取单个设备详情"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    return {
        "code": 200,
        "data": {
            "id": device.id,
            "name": device.name,
            "type": device.type,
            "rated_power": device.rated_power,
            "status": device.status,
            "line_no": device.line_no,
            "workshop": device.workshop,
            "location": device.location,
            "efficiency": device.efficiency,
            "created_at": device.created_at.isoformat() if device.created_at else None,
            "updated_at": device.updated_at.isoformat() if device.updated_at else None,
        },
        "message": "success",
    }


@router.post("/")
def create_device(data: DeviceCreate, db: Session = Depends(get_db),
                  _perm=Depends(require_permission("manage_devices"))):
    """创建设备"""
    device = Device(**data.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return {
        "code": 200,
        "data": {"id": device.id, "name": device.name},
        "message": "设备创建成功",
    }


@router.put("/{device_id}")
def update_device(device_id: int, data: DeviceUpdate, db: Session = Depends(get_db),
                  _perm=Depends(require_permission("manage_devices"))):
    """更新设备信息"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(device, key, value)
    db.commit()
    return {"code": 200, "data": None, "message": "设备更新成功"}


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db),
                  _perm=Depends(require_permission("manage_devices"))):
    """删除设备"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    db.delete(device)
    db.commit()
    return {"code": 200, "data": None, "message": "设备删除成功"}

