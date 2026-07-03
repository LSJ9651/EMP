"""告警管理路由 — 告警阈值配置与告警记录查询"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from database import get_db
from models import AlertThreshold, AlertRecord, Device
from middleware.permission import require_permission

router = APIRouter(prefix="/api/alerts", tags=["告警管理"])


class ThresholdCreate(BaseModel):
    device_id: int
    param_type: str = Field(..., description="参数类型：power/temperature/voltage/current")
    upper_limit: Optional[float] = None
    lower_limit: Optional[float] = None
    is_enabled: bool = True


class ThresholdUpdate(BaseModel):
    upper_limit: Optional[float] = None
    lower_limit: Optional[float] = None
    is_enabled: Optional[bool] = None


class ResolveRequest(BaseModel):
    handler: str = Field(..., description="处理人")
    measure: str = Field(..., description="处理措施")


@router.get("/thresholds")
def list_thresholds(device_id: int = None, db: Session = Depends(get_db)):
    """获取告警阈值配置"""
    query = db.query(AlertThreshold)
    if device_id:
        query = query.filter(AlertThreshold.device_id == device_id)
    thresholds = query.order_by(AlertThreshold.device_id, AlertThreshold.param_type).all()
    return {
        "code": 200,
        "data": [
            {
                "id": t.id,
                "device_id": t.device_id,
                "param_type": t.param_type,
                "upper_limit": t.upper_limit,
                "lower_limit": t.lower_limit,
                "is_enabled": t.is_enabled,
            }
            for t in thresholds
        ],
        "message": "success",
    }


@router.put("/thresholds/{threshold_id}")
def update_threshold(threshold_id: int, data: ThresholdUpdate, db: Session = Depends(get_db),
                     _perm=Depends(require_permission("manage_alerts"))):
    """更新告警阈值"""
    threshold = db.query(AlertThreshold).filter(AlertThreshold.id == threshold_id).first()
    if not threshold:
        raise HTTPException(status_code=404, detail="阈值配置不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(threshold, key, value)
    db.commit()
    return {"code": 200, "data": None, "message": "阈值更新成功"}


@router.post("/thresholds")
def create_threshold(data: ThresholdCreate, db: Session = Depends(get_db),
                     _perm=Depends(require_permission("manage_alerts"))):
    """创建告警阈值"""
    threshold = AlertThreshold(**data.model_dump())
    db.add(threshold)
    db.commit()
    db.refresh(threshold)
    return {"code": 200, "data": {"id": threshold.id}, "message": "阈值创建成功"}


@router.get("/records")
def list_records(
    device_id: int = None,
    limit: int = 50,
    only_unresolved: bool = False,
    db: Session = Depends(get_db),
):
    """获取告警记录列表"""
    query = db.query(AlertRecord, Device.name).join(
        Device, AlertRecord.device_id == Device.id
    )
    if device_id:
        query = query.filter(AlertRecord.device_id == device_id)
    if only_unresolved:
        query = query.filter(AlertRecord.is_resolved == False)
    results = query.order_by(AlertRecord.alert_time.desc()).limit(limit).all()
    return {
        "code": 200,
        "data": [
            {
                "id": r.id,
                "device_id": r.device_id,
                "device_name": name,
                "alert_time": r.alert_time.isoformat() if r.alert_time else None,
                "param_type": r.param_type,
                "value": r.value,
                "threshold_value": r.threshold_value,
                "message": r.message,
                "severity": r.severity,
                "is_resolved": r.is_resolved,
            }
            for r, name in results
        ],
        "message": "success",
    }


@router.put("/records/{record_id}/resolve")
def resolve_alert(record_id: int, data: ResolveRequest, db: Session = Depends(get_db),
                  _perm=Depends(require_permission("manage_alerts"))):
    """标记告警为已处理"""
    record = db.query(AlertRecord).filter(AlertRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="告警记录不存在")
    record.is_resolved = True
    record.handler = data.handler
    record.measure = data.measure
    record.resolved_at = datetime.now()
    db.commit()
    return {"code": 200, "data": None, "message": "告警已处理"}


@router.get("/stats")
def get_alert_stats(db: Session = Depends(get_db)):
    """获取告警统计分析"""
    from datetime import datetime, timedelta
    from sqlalchemy import func

    total_alerts = db.query(AlertRecord).count()
    unresolved = db.query(AlertRecord).filter(AlertRecord.is_resolved == False).count()

    # 告警类型分布
    type_distribution = (
        db.query(AlertRecord.param_type, func.count(AlertRecord.id))
        .group_by(AlertRecord.param_type)
        .all()
    )

    # 严重程度分布
    severity_distribution = (
        db.query(AlertRecord.severity, func.count(AlertRecord.id))
        .group_by(AlertRecord.severity)
        .all()
    )

    # 平均响应时长（已处理的告警）
    resolved_records = (
        db.query(AlertRecord)
        .filter(AlertRecord.is_resolved == True, AlertRecord.resolved_at != None)
        .all()
    )

    avg_response_minutes = 0
    if resolved_records:
        total_seconds = sum(
            (r.resolved_at - r.alert_time).total_seconds()
            for r in resolved_records
            if r.resolved_at and r.alert_time
        )
        avg_response_minutes = round(total_seconds / len(resolved_records) / 60, 1)

    # 最近7天趋势
    seven_days_ago = datetime.now() - timedelta(days=7)
    daily_trend = (
        db.query(func.date(AlertRecord.alert_time), func.count(AlertRecord.id))
        .filter(AlertRecord.alert_time >= seven_days_ago)
        .group_by(func.date(AlertRecord.alert_time))
        .order_by(func.date(AlertRecord.alert_time))
        .all()
    )

    return {
        "code": 200,
        "data": {
            "total_alerts": total_alerts,
            "unresolved": unresolved,
            "avg_response_minutes": avg_response_minutes,
            "type_distribution": [
                {"type": t, "count": c, "label": {"power": "功率", "temperature": "温度", "voltage": "电压", "current": "电流"}.get(t, t)}
                for t, c in type_distribution
            ],
            "severity_distribution": [
                {"severity": s, "count": c, "label": {"critical": "严重", "warning": "警告", "info": "提示"}.get(s, s)}
                for s, c in severity_distribution
            ],
            "daily_trend": [
                {"date": str(d), "count": c}
                for d, c in daily_trend
            ],
        },
        "message": "success",
    }


@router.get("/suggestions")
def get_resolution_suggestions(device_id: int = None, param_type: str = None, db: Session = Depends(get_db)):
    """获取历史处理建议（知识库匹配）"""
    query = db.query(AlertRecord).filter(
        AlertRecord.is_resolved == True,
        AlertRecord.measure != None,
        AlertRecord.measure != ""
    )
    if device_id:
        query = query.filter(AlertRecord.device_id == device_id)
    if param_type:
        query = query.filter(AlertRecord.param_type == param_type)

    records = query.order_by(AlertRecord.resolved_at.desc()).limit(10).all()

    suggestions = []
    for r in records:
        suggestions.append({
            "device_id": r.device_id,
            "param_type": r.param_type,
            "handler": r.handler,
            "measure": r.measure,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        })

    return {"code": 200, "data": suggestions, "message": "success"}
