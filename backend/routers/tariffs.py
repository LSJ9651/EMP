"""电价策略路由 — 分时电价配置"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from database import get_db
from models import TariffPolicy
from middleware.permission import require_permission

router = APIRouter(prefix="/api/tariffs", tags=["电价策略"])


class TariffCreate(BaseModel):
    period_name: str = Field(..., description="时段名称")
    start_time: str = Field(..., description="开始时间 HH:MM")
    end_time: str = Field(..., description="结束时间 HH:MM")
    price_per_kwh: float = Field(..., gt=0, description="电价(元/kWh)")
    is_active: bool = True
    description: Optional[str] = None


class TariffUpdate(BaseModel):
    period_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    price_per_kwh: Optional[float] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


@router.get("/")
def list_tariffs(db: Session = Depends(get_db)):
    """获取所有电价策略"""
    tariffs = db.query(TariffPolicy).order_by(TariffPolicy.start_time).all()
    return {
        "code": 200,
        "data": [
            {
                "id": t.id,
                "period_name": t.period_name,
                "start_time": t.start_time,
                "end_time": t.end_time,
                "price_per_kwh": t.price_per_kwh,
                "is_active": t.is_active,
                "description": t.description,
            }
            for t in tariffs
        ],
        "message": "success",
    }


@router.post("/")
def create_tariff(data: TariffCreate, db: Session = Depends(get_db),
                  _perm=Depends(require_permission("manage_tariffs"))):
    """创建电价策略"""
    tariff = TariffPolicy(**data.model_dump())
    db.add(tariff)
    db.commit()
    db.refresh(tariff)
    return {"code": 200, "data": {"id": tariff.id}, "message": "电价策略创建成功"}


@router.put("/{tariff_id}")
def update_tariff(tariff_id: int, data: TariffUpdate, db: Session = Depends(get_db),
                  _perm=Depends(require_permission("manage_tariffs"))):
    """更新电价策略"""
    tariff = db.query(TariffPolicy).filter(TariffPolicy.id == tariff_id).first()
    if not tariff:
        raise HTTPException(status_code=404, detail="电价策略不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tariff, key, value)
    db.commit()
    return {"code": 200, "data": None, "message": "电价策略更新成功"}


@router.get("/current")
def get_current_tariff(db: Session = Depends(get_db)):
    """获取当前时段电价"""
    from datetime import datetime
    now = datetime.now()
    current_str = now.strftime("%H:%M")

    tariffs = db.query(TariffPolicy).filter(TariffPolicy.is_active == True).all()

    for t in tariffs:
        start = t.start_time
        end = t.end_time
        if start <= end:
            in_period = start <= current_str <= end
        else:
            in_period = current_str >= start or current_str <= end

        if in_period:
            return {
                "code": 200,
                "data": {
                    "period_name": t.period_name,
                    "price_per_kwh": t.price_per_kwh,
                    "start_time": t.start_time,
                    "end_time": t.end_time,
                },
                "message": "success",
            }

    return {
        "code": 200,
        "data": {"period_name": "未知", "price_per_kwh": 0.8},
        "message": "success",
    }
