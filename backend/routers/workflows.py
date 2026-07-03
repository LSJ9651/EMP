"""工作流路由 — 项目级可复用工作流调用 API"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from database import get_db
from services.workflow_service import WorkflowService

router = APIRouter(prefix="/api/workflows", tags=["工作流"])


# ========== 请求模型 ==========

class AnalyzeRunRequest(BaseModel):
    device_id: Optional[int] = Field(None, description="设备ID，不传则全厂分析")
    start_time: Optional[str] = Field(None, description="开始时间 ISO格式，默认今天00:00")
    end_time: Optional[str] = Field(None, description="结束时间 ISO格式，默认今天23:59")
    max_points: Optional[int] = Field(200, ge=10, le=500, description="最大数据点数")


class OptimizeRunRequest(BaseModel):
    production_goal: int = Field(..., gt=0, description="生产目标数量")
    deadline: Optional[str] = Field(None, description="截止时间 ISO格式")
    device_ids: Optional[list[int]] = Field(None, description="可用设备ID列表，不传则全厂")


# ========== 路由端点 ==========

@router.post("/analyze")
async def run_analyze(req: AnalyzeRunRequest, db: Session = Depends(get_db)):
    """执行能耗分析工作流"""
    try:
        result = await WorkflowService.execute(
            workflow_type="analyze",
            params={
                "device_id": req.device_id,
                "start_time": req.start_time,
                "end_time": req.end_time,
                "max_points": req.max_points,
            },
            db=db,
        )
        return {"code": 200, "message": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")


@router.post("/optimize")
async def run_optimize(req: OptimizeRunRequest, db: Session = Depends(get_db)):
    """执行调度优化工作流"""
    try:
        result = await WorkflowService.execute(
            workflow_type="optimize",
            params={
                "production_goal": req.production_goal,
                "deadline": req.deadline,
                "device_ids": req.device_ids or [],
            },
            db=db,
        )
        return {"code": 200, "message": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")


@router.get("/history")
def get_history(
    workflow_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """获取工作流执行历史"""
    records = WorkflowService.get_history(
        db=db,
        workflow_type=workflow_type,
        status=status,
        limit=min(limit, 200),
    )
    return {
        "code": 200,
        "message": "success",
        "data": [
            {
                "id": r.id,
                "workflow_type": r.workflow_type,
                "status": r.status,
                "mode_used": r.mode_used,
                "elapsed_ms": r.elapsed_ms,
                "error_message": r.error_message,
                "params_json": r.params_json,
                "result_json": r.result_json,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
    }


@router.get("/history/{execution_id}")
def get_execution_detail(execution_id: int, db: Session = Depends(get_db)):
    """获取单次执行详情"""
    from models import WorkflowExecution
    r = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return {
        "code": 200,
        "message": "success",
        "data": {
            "id": r.id,
            "workflow_type": r.workflow_type,
            "status": r.status,
            "mode_used": r.mode_used,
            "elapsed_ms": r.elapsed_ms,
            "params_json": r.params_json,
            "result_json": r.result_json,
            "error_message": r.error_message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        },
    }
