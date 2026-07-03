"""智能体接口路由 — 能耗分析 + 调度优化"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from database import get_db
from models import AgentReport, ReportSubscription
from services.agent_adapter import analyze_energy, optimize_schedule

router = APIRouter(prefix="/api/agent", tags=["智能体"])


class AnalyzeRequest(BaseModel):
    device_id: Optional[int] = Field(None, description="设备ID，不传则全厂分析")
    start_time: Optional[str] = Field(None, description="开始时间 ISO格式")
    end_time: Optional[str] = Field(None, description="结束时间 ISO格式")
    sample_interval: Optional[int] = Field(60, description="采样间隔（秒），默认60秒，控制数据密度")
    max_points: Optional[int] = Field(200, description="最大数据点数，防止Token溢出")


class OptimizeRequest(BaseModel):
    production_goal: int = Field(..., gt=0, description="生产目标数量")
    deadline: Optional[str] = Field(None, description="截止时间 ISO格式")
    devices: Optional[list] = Field(None, description="可用设备ID列表")


@router.post("/analyze")
async def analyze(data: AnalyzeRequest, db=Depends(get_db)):
    """能耗分析 — 检测异常并给出节能建议"""
    from datetime import datetime

    start_time = data.start_time or datetime.now().strftime("%Y-%m-%dT00:00:00")
    end_time = data.end_time or datetime.now().strftime("%Y-%m-%dT23:59:59")

    result = await analyze_energy(
        device_id=data.device_id,
        start_time=start_time,
        end_time=end_time,
        db=db,
        max_points=data.max_points or 200,
    )

    # 保存报告
    report = AgentReport(
        report_type="analysis",
        trigger_time=datetime.now(),
        input_summary=f"device_id={data.device_id}, range={start_time}~{end_time}",
        input_payload={  # 保存完整的入参快照，便于追溯和审计
            "device_id": data.device_id,
            "start_time": start_time,
            "end_time": end_time,
            "sample_interval": data.sample_interval,
            "max_points": data.max_points,
        },
        output_json=result,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "code": 200,
        "data": {**result, "report_id": report.id},
        "message": "success",
    }


@router.post("/optimize")
async def optimize(data: OptimizeRequest, db=Depends(get_db)):
    """调度优化 — 基于电价时段生成最优设备启停计划"""
    from datetime import datetime
    from models import Device

    # 确定设备范围
    if data.devices:
        device_ids = data.devices
    else:
        all_devices = db.query(Device).all()
        device_ids = [d.id for d in all_devices]

    deadline = data.deadline or datetime.now().strftime("%Y-%m-%dT23:59:59")

    result = await optimize_schedule(
        production_goal=data.production_goal,
        deadline=deadline,
        device_ids=device_ids,
        db=db,
    )

    clean_result = result

    # 保存报告
    report = AgentReport(
        report_type="schedule",
        trigger_time=datetime.now(),
        input_summary=f"goal={data.production_goal}, devices={device_ids}",
        input_payload={
            "production_goal": data.production_goal,
            "deadline": deadline,
            "devices": device_ids,
        },
        output_json=clean_result,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "code": 200,
        "data": {**clean_result, "report_id": report.id},
        "message": "success",
    }


@router.get("/reports")
def list_reports(
    report_type: str = None,
    device_id: int = None,
    device_name: str = None,
    subscription_id: int = None,
    start_time: str = None,
    end_time: str = None,
    page: int = 1,
    page_size: int = 20,
    limit: int = None,  # 保留兼容旧参数
    db: Session = Depends(get_db),
):
    """获取智能体报告列表（支持设备/时间/订阅筛选 + 分页）

    device_id:      精确匹配 input_payload 中的设备ID
    device_name:    模糊匹配 input_summary 或 input_payload 中的设备名称/ID
    subscription_id: 筛选指定订阅生成的报告
    start_time:     时间范围起始 (ISO格式)
    end_time:       时间范围结束 (ISO格式)
    page:           页码 (从1开始)
    page_size:      每页条数 (默认20, 最大100)
    """
    from sqlalchemy import or_, func
    from datetime import datetime

    query = db.query(AgentReport)

    # ── 报告类型筛选 ──
    if report_type:
        query = query.filter(AgentReport.report_type == report_type)

    # ── 设备ID精确筛选 ──
    if device_id is not None:
        query = query.filter(
            AgentReport.input_payload.isnot(None),
            or_(
                AgentReport.input_payload.like(f'%"device_id": {device_id},%'),
                AgentReport.input_payload.like(f'%"device_id": {device_id}' + '}%'),
            ),
        )

    # ── 设备名称模糊搜索 ──
    if device_name:
        query = query.filter(
            or_(
                AgentReport.input_summary.ilike(f"%{device_name}%"),
                AgentReport.input_payload.isnot(None) & AgentReport.input_payload.like(f"%{device_name}%"),
            )
        )

    # ── 订阅筛选 ──
    if subscription_id is not None:
        query = query.filter(
            AgentReport.input_summary.ilike(f"%subscription_id={subscription_id}%")
        )

    # ── 时间范围筛选 ──
    if start_time:
        try:
            st = datetime.fromisoformat(start_time)
            query = query.filter(AgentReport.created_at >= st)
        except ValueError:
            pass

    if end_time:
        try:
            et = datetime.fromisoformat(end_time)
            query = query.filter(AgentReport.created_at <= et)
        except ValueError:
            pass

    # ── 分页 ──
    page_size = min(max(page_size, 1), 100)
    page = max(page, 1)
    total = query.count()
    total_pages = max((total + page_size - 1) // page_size, 1)

    if limit is not None:
        # 旧参数兼容模式
        reports = query.order_by(AgentReport.created_at.desc()).limit(limit).all()
        page_size = limit
        page = 1
        total = len(reports)
        total_pages = 1
    else:
        reports = (
            query.order_by(AgentReport.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

    return {
        "code": 200,
        "data": {
            "items": [
                {
                    "id": r.id,
                    "report_type": r.report_type,
                    "trigger_time": r.trigger_time.isoformat() if r.trigger_time else None,
                    "input_summary": r.input_summary,
                    "input_payload": r.input_payload,
                    "output_json": r.output_json,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reports
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        },
        "message": "success",
    }


class ExecuteScheduleRequest(BaseModel):
    report_id: int = Field(..., description="调度报告ID")


@router.post("/execute")
def execute_schedule(data: ExecuteScheduleRequest, db: Session = Depends(get_db)):
    """下发/模拟执行调度方案"""
    from datetime import datetime
    from models import ScheduleExecution, Device

    report = db.query(AgentReport).filter(AgentReport.id == data.report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")

    output = report.output_json or {}
    schedule = output.get("schedule", [])

    # ── 计算基线成本（全部按峰电价格运行的假想成本）──
    peak_price = max((s.get("price_per_kwh", 1.2) for s in schedule), default=1.2)
    baseline_cost = 0.0
    for item in schedule:
        device = db.query(Device).filter(Device.id == item.get("device_id")).first()
        power = device.rated_power if device else 50  # kW
        start_h, start_m = (int(x) for x in item.get("start", "0:0").split(":"))
        end_h, end_m = (int(x) for x in item.get("end", "0:0").split(":"))
        if end_h <= start_h:
            end_h += 24
        hours = (end_h - start_h) + (end_m - start_m) / 60
        baseline_cost += power * hours * peak_price
    baseline_cost = round(baseline_cost, 2)

    # 创建执行记录
    execution = ScheduleExecution(
        report_id=data.report_id,
        status="running",
        baseline_cost=baseline_cost,
        started_at=datetime.now(),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    return {"code": 200, "data": {"execution_id": execution.id, "status": "running"}, "message": "调度方案已下发执行"}


@router.get("/executions")
def list_executions(db: Session = Depends(get_db)):
    """获取调度执行记录列表"""
    from models import ScheduleExecution
    executions = db.query(ScheduleExecution).order_by(ScheduleExecution.created_at.desc()).all()
    return {
        "code": 200,
        "data": [
            {
                "id": e.id,
                "report_id": e.report_id,
                "status": e.status,
                "baseline_cost": e.baseline_cost,
                "actual_cost": e.actual_cost,
                "saved_cost": e.saved_cost,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in executions
        ],
        "message": "success",
    }


@router.post("/executions/{execution_id}/complete")
def complete_execution(execution_id: int, db: Session = Depends(get_db)):
    """完成调度执行并核算实际节费"""
    from datetime import datetime
    from models import ScheduleExecution, AgentReport, Device
    import random

    execution = db.query(ScheduleExecution).filter(ScheduleExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    # ── 计算实际成本（基于调度方案的实际电价，加少许执行偏差）──
    report = db.query(AgentReport).filter(AgentReport.id == execution.report_id).first()
    schedule = (report.output_json or {}).get("schedule", []) if report else []
    actual_cost = 0.0
    for item in schedule:
        device = db.query(Device).filter(Device.id == item.get("device_id")).first()
        power = device.rated_power if device else 50
        start_h, start_m = (int(x) for x in item.get("start", "0:0").split(":"))
        end_h, end_m = (int(x) for x in item.get("end", "0:0").split(":"))
        if end_h <= start_h:
            end_h += 24
        hours = (end_h - start_h) + (end_m - start_m) / 60
        rate = item.get("price_per_kwh", 0.8)
        # 实际功率有 ±5% 偏差，模拟真实执行波动
        actual_power = power * random.uniform(0.95, 1.05)
        actual_cost += actual_power * hours * rate
    actual_cost = round(actual_cost, 2)

    execution.status = "completed"
    execution.actual_cost = actual_cost
    execution.saved_cost = round(execution.baseline_cost - actual_cost, 2)
    execution.completed_at = datetime.now()
    db.commit()

    return {
        "code": 200,
        "data": {
            "id": execution.id,
            "status": "completed",
            "baseline_cost": execution.baseline_cost,
            "actual_cost": execution.actual_cost,
            "saved_cost": execution.saved_cost,
        },
        "message": "执行完成",
    }


# ========== 报告订阅管理 ==========

class SubscriptionCreate(BaseModel):
    name: str = Field(..., description="订阅名称")
    report_type: str = Field(..., description="daily/weekly/analysis")
    cron_time: str = Field(..., description="执行时间 HH:MM")
    device_ids: Optional[str] = Field(None, description="设备ID列表，逗号分隔")
    notify_method: str = Field("system")
    notify_config: Optional[dict] = Field(None, description="通知配置 JSON")
    is_active: bool = Field(True)


class SubscriptionSearch(BaseModel):
    """订阅搜索参数"""
    keyword: Optional[str] = Field(None, description="搜索关键词（名称/类型）")
    report_type: Optional[str] = Field(None, description="报告类型筛选")
    is_active: Optional[bool] = Field(None, description="启用状态筛选")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


@router.get("/subscriptions")
def list_subscriptions(
    keyword: str = None,
    report_type: str = None,
    is_active: str = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    """获取报告订阅列表（支持搜索 + 分页）

    keyword:    搜索关键词（匹配订阅名称）
    report_type: 报告类型筛选
    is_active:  启用状态筛选 ("true"/"false")
    page:       页码
    page_size:  每页条数
    """
    query = db.query(ReportSubscription)

    if keyword:
        query = query.filter(ReportSubscription.name.ilike(f"%{keyword}%"))

    if report_type:
        query = query.filter(ReportSubscription.report_type == report_type)

    if is_active is not None:
        active_bool = is_active.lower() == "true"
        query = query.filter(ReportSubscription.is_active == active_bool)

    page_size = min(max(page_size, 1), 100)
    page = max(page, 1)
    total = query.count()
    total_pages = max((total + page_size - 1) // page_size, 1)

    subs = (
        query.order_by(ReportSubscription.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "code": 200,
        "data": {
            "items": [
                {"id": s.id, "name": s.name, "report_type": s.report_type,
                 "cron_time": s.cron_time, "device_ids": s.device_ids,
                 "is_active": s.is_active, "notify_method": s.notify_method,
                 "notify_config": json.loads(s.notify_config) if s.notify_config else None,
                 "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
                 "created_at": s.created_at.isoformat() if s.created_at else None}
                for s in subs
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        },
        "message": "success",
    }


@router.get("/subscriptions/{sub_id}/reports")
def get_subscription_reports(
    sub_id: int,
    start_time: str = None,
    end_time: str = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """获取指定订阅产生的报告列表（按时序排列 + 分页）

    报告通过 input_summary 中的 subscription_id 标记关联到订阅。
    """
    sub = db.query(ReportSubscription).filter(ReportSubscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")

    from datetime import datetime

    query = db.query(AgentReport).filter(
        AgentReport.input_summary.ilike(f"%subscription_id={sub_id}%")
    )

    if start_time:
        try:
            st = datetime.fromisoformat(start_time)
            query = query.filter(AgentReport.created_at >= st)
        except ValueError:
            pass

    if end_time:
        try:
            et = datetime.fromisoformat(end_time)
            query = query.filter(AgentReport.created_at <= et)
        except ValueError:
            pass

    page_size = min(max(page_size, 1), 100)
    page = max(page, 1)
    total = query.count()
    total_pages = max((total + page_size - 1) // page_size, 1)

    reports = (
        query.order_by(AgentReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "code": 200,
        "data": {
            "subscription": {
                "id": sub.id,
                "name": sub.name,
                "report_type": sub.report_type,
                "is_active": sub.is_active,
                "last_run_at": sub.last_run_at.isoformat() if sub.last_run_at else None,
            },
            "items": [
                {
                    "id": r.id,
                    "report_type": r.report_type,
                    "trigger_time": r.trigger_time.isoformat() if r.trigger_time else None,
                    "input_summary": r.input_summary,
                    "output_json": r.output_json,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reports
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        },
        "message": "success",
    }


@router.post("/subscriptions")
def create_subscription(data: SubscriptionCreate, db: Session = Depends(get_db)):
    """创建报告订阅"""
    sub_data = data.model_dump()
    # 将 dict 序列化为 JSON 字符串存储
    if sub_data.get("notify_config") and isinstance(sub_data["notify_config"], dict):
        sub_data["notify_config"] = json.dumps(sub_data["notify_config"], ensure_ascii=False)
    sub = ReportSubscription(**sub_data)
    db.add(sub)
    db.flush()

    # 生成订阅成功通知
    _create_notification(
        db,
        title=f"订阅「{sub.name}」创建成功",
        content=f"报告类型：{_report_type_label(sub.report_type)}，执行时间：每天 {sub.cron_time}，"
                 f"通知方式：{_notify_method_label(sub.notify_method)}",
        category="subscription",
        source_type="subscription",
        source_id=sub.id,
    )

    db.commit()
    db.refresh(sub)
    return {"code": 200, "data": {"id": sub.id}, "message": "订阅创建成功"}


@router.put("/subscriptions/{sub_id}")
def update_subscription(sub_id: int, data: dict, db: Session = Depends(get_db)):
    """更新订阅配置"""
    sub = db.query(ReportSubscription).filter(ReportSubscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    for key in ["name", "cron_time", "device_ids", "is_active", "notify_method", "report_type"]:
        if key in data:
            setattr(sub, key, data[key])
    # 处理 notify_config JSON 序列化
    if "notify_config" in data:
        nc = data["notify_config"]
        if isinstance(nc, dict):
            setattr(sub, "notify_config", json.dumps(nc, ensure_ascii=False))
        elif isinstance(nc, str) or nc is None:
            setattr(sub, "notify_config", nc)
    db.commit()
    return {"code": 200, "message": "订阅更新成功"}


@router.delete("/subscriptions/{sub_id}")
def delete_subscription(sub_id: int, db: Session = Depends(get_db)):
    """删除订阅"""
    sub = db.query(ReportSubscription).filter(ReportSubscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    db.delete(sub)
    db.commit()
    return {"code": 200, "message": "订阅已删除"}


@router.post("/subscriptions/{sub_id}/run")
async def run_subscription(sub_id: int, db=Depends(get_db)):
    """手动触发订阅任务执行"""
    from datetime import datetime

    sub = db.query(ReportSubscription).filter(ReportSubscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")

    device_ids = None
    if sub.device_ids:
        device_ids = [int(x.strip()) for x in sub.device_ids.split(",") if x.strip()]
        device_ids = device_ids[0] if len(device_ids) == 1 else device_ids

    start_time = (datetime.now()).strftime("%Y-%m-%dT00:00:00")
    end_time = datetime.now().strftime("%Y-%m-%dT23:59:59")

    result = await analyze_energy(
        device_id=device_ids if isinstance(device_ids, int) else None,
        start_time=start_time,
        end_time=end_time,
        db=db,
    )

    # 保存报告（input_payload 必须包含 device_id，供列表筛选使用）
    report = AgentReport(
        report_type="analysis",
        trigger_time=datetime.now(),
        input_summary=f"subscription_id={sub_id}, name={sub.name}",
        input_payload={
            "device_id": device_ids if isinstance(device_ids, int) else None,
            "start_time": start_time,
            "end_time": end_time,
            "via": "subscription_manual",
        },
        output_json=result,
    )
    db.add(report)

    # 更新最后执行时间
    sub.last_run_at = datetime.now()
    db.flush()

    # 生成报告完成通知（source_id 指向报告ID以便前端跳转）
    _create_notification(
        db,
        title=f"报告「{sub.name}」生成完成",
        content=f"{_report_type_label(sub.report_type)}已生成，请前往「智能报告」页面查看详情",
        category="report",
        source_type="agent_report",
        source_id=report.id,
    )

    db.commit()
    db.refresh(report)

    return {"code": 200, "data": {"report_id": report.id, **result}, "message": "订阅任务执行完成"}


# ──── 通知辅助函数 ────

def _create_notification(db, title: str, content: str, category: str,
                         source_type: str = "", source_id: int = None):
    """创建一条系统通知"""
    try:
        from models import Notification
        n = Notification(
            title=title,
            content=content,
            category=category,
            source_type=source_type,
            source_id=source_id,
        )
        db.add(n)
    except Exception as e:
        from utils.logger import setup_logger
        logger = setup_logger("agent")
        logger.error(f"创建通知失败: {e}")


def _report_type_label(t: str) -> str:
    return {"daily": "日报", "weekly": "周报", "analysis": "分析报告"}.get(t, t)


def _notify_method_label(m: str) -> str:
    return {"system": "系统通知", "email": "邮件", "dingtalk": "钉钉"}.get(m, m)
