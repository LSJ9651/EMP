"""报告与导出路由 — 报表导出（Excel）"""
from datetime import datetime, timedelta
from io import BytesIO
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Telemetry, Device, AlertRecord, AgentReport

router = APIRouter(prefix="/api/reports", tags=["报告导出"])


@router.get("/export/excel")
def export_excel(
    device_id: int = Query(None),
    start: str = Query(None, description="开始时间"),
    end: str = Query(None, description="结束时间"),
    db: Session = Depends(get_db),
):
    """导出能耗数据为 Excel"""
    try:
        import openpyxl
    except ImportError:
        return {"code": 500, "data": None, "message": "openpyxl 未安装"}

    try:
        st = datetime.fromisoformat(start) if start else datetime.now() - timedelta(days=7)
        et = datetime.fromisoformat(end) if end else datetime.now()
    except ValueError:
        return {"code": 400, "data": None, "message": "时间格式错误"}

    # 查询数据
    query = db.query(Telemetry).filter(
        Telemetry.timestamp >= st,
        Telemetry.timestamp <= et,
    )
    if device_id:
        query = query.filter(Telemetry.device_id == device_id)
    records = query.order_by(Telemetry.timestamp.asc()).all()

    # 创建设备名称映射
    devices = {d.id: d.name for d in db.query(Device).all()}

    # 创建 Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "能耗数据"

    headers = ["序号", "设备名称", "时间", "电压(V)", "电流(A)", "功率(kW)",
               "电度(kWh)", "功率因数", "温度(°C)", "状态码"]
    ws.append(headers)

    for i, r in enumerate(records, 1):
        ws.append([
            i,
            devices.get(r.device_id, f"设备{r.device_id}"),
            r.timestamp.strftime("%Y-%m-%d %H:%M:%S") if r.timestamp else "",
            r.voltage,
            r.current,
            r.power,
            r.energy_kwh,
            r.power_factor,
            r.temperature,
            r.status_code,
        ])

    # 调整列宽
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 30)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"energy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/summary")
def report_summary(db: Session = Depends(get_db)):
    """获取报告摘要数据"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)

    # 今日能耗
    today_records = db.query(Telemetry).filter(Telemetry.timestamp >= today).all()
    today_energy = round(sum(r.energy_kwh for r in today_records), 2)
    today_avg_power = round(
        sum(r.power for r in today_records) / len(today_records) if today_records else 0, 2
    )

    # 告警统计
    alert_count = db.query(AlertRecord).filter(
        AlertRecord.alert_time >= today,
        AlertRecord.is_resolved == False,
    ).count()

    # 设备统计
    devices = db.query(Device).all()
    online = sum(1 for d in devices if d.status == "online")
    offline = sum(1 for d in devices if d.status == "offline")
    alert = sum(1 for d in devices if d.status == "alert")

    return {
        "code": 200,
        "data": {
            "today_energy_kwh": today_energy,
            "today_avg_power_kw": today_avg_power,
            "co2_estimate_kg": round(today_energy * 0.5703, 2),
            "alert_count": alert_count,
            "device_stats": {
                "total": len(devices),
                "online": online,
                "offline": offline,
                "alert": alert,
            },
        },
        "message": "success",
    }
