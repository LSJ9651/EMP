"""成本分摊路由 — SQL聚合版本，支持多规则、校验、导出、设备级钻取"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models import AIConfigEntry
from services.cost_allocation_service import CostAllocationService

router = APIRouter(prefix="/api/cost-allocation", tags=["成本分摊"])


# ═══════════════════════════════════════════════════════════
# 分摊查询端点
# ═══════════════════════════════════════════════════════════

@router.get("/workshop-summary")
def workshop_summary(
    start: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    rule_type: Optional[str] = Query(None, description="分摊规则: ratio/by_device_type"),
    db: Session = Depends(get_db),
):
    """按车间统计电费，返回各车间电费及峰/平/谷分级明细（SQL聚合版）"""
    # 读取保存的规则配置
    if not rule_type:
        rule_entry = db.query(AIConfigEntry).filter(
            AIConfigEntry.config_key == "cost_allocation_rule"
        ).first()
        rule_type = rule_entry.config_value if rule_entry else "ratio"

    result = CostAllocationService.get_workshop_summary(db, start, end, rule_type)
    return {"code": 200, "message": "success", "data": result}


@router.get("/workshop-detail/{workshop}")
def workshop_detail(
    workshop: str,
    days: int = 30,
    db: Session = Depends(get_db),
):
    """单个车间的每日电费明细"""
    data = CostAllocationService.get_workshop_detail(db, workshop, days)
    return {"code": 200, "data": data, "message": "success"}


@router.get("/device-cost")
def device_cost_detail(
    start: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """按设备维度汇总成本（设备级分摊明细）"""
    data = CostAllocationService.get_device_cost_detail(db, start, end)
    return {"code": 200, "data": data, "message": "success"}


# ═══════════════════════════════════════════════════════════
# 分摊规则配置端点
# ═══════════════════════════════════════════════════════════

@router.get("/rules")
def get_rules(db: Session = Depends(get_db)):
    """获取当前分摊规则配置"""
    entry = db.query(AIConfigEntry).filter(
        AIConfigEntry.config_key == "cost_allocation_rule"
    ).first()
    return {
        "code": 200,
        "data": {
            "rule_type": entry.config_value if entry else "ratio",
            "available_rules": ["ratio", "by_device_type"],
            "description": {
                "ratio": "按实际用电比例分摊（默认）",
                "by_device_type": "按设备类型细分成本分布",
            },
        },
    }


@router.put("/rules")
def update_rule(
    rule_type: str = Query(..., description="分摊规则: ratio / by_device_type"),
    db: Session = Depends(get_db),
):
    """更新分摊规则配置"""
    if rule_type not in ("ratio", "by_device_type"):
        return {"code": 400, "message": f"不支持的规则类型: {rule_type}，支持: ratio, by_device_type"}

    entry = db.query(AIConfigEntry).filter(
        AIConfigEntry.config_key == "cost_allocation_rule"
    ).first()
    if entry:
        entry.config_value = rule_type
        entry.updated_at = datetime.now()
    else:
        db.add(AIConfigEntry(config_key="cost_allocation_rule", config_value=rule_type))
    db.commit()

    return {"code": 200, "message": "规则已更新", "data": {"rule_type": rule_type}}


# ═══════════════════════════════════════════════════════════
# 导出端点
# ═══════════════════════════════════════════════════════════

@router.get("/export")
def export_csv(
    start: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    export_type: str = Query("workshop", description="导出类型: workshop/device/detail"),
    db: Session = Depends(get_db),
):
    """导出分摊结果为CSV文件"""
    if export_type not in ("workshop", "device", "detail"):
        return {"code": 400, "message": f"不支持导出类型: {export_type}，支持: workshop, device, detail"}

    csv_io = CostAllocationService.export_csv(db, start, end, export_type)
    filename = f"cost_allocation_{export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([csv_io.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
