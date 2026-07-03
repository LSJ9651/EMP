"""工作流统一服务层 — 参数标准化、执行日志、错误处理"""

import logging
import time
from datetime import datetime
from typing import Optional, Literal

from sqlalchemy.orm import Session
from models import WorkflowExecution, AgentReport
from services.agent_adapter import analyze_energy, optimize_schedule

logger = logging.getLogger(__name__)

WorkflowType = Literal["analyze", "optimize"]


def _validate_analyze_params(params: dict) -> Optional[str]:
    """校验analyze参数，返回错误消息或None"""
    if params.get("start_time"):
        try:
            datetime.fromisoformat(params["start_time"])
        except (ValueError, TypeError):
            return "start_time 格式错误，需为 ISO 格式（如 2026-06-17T00:00:00）"
    if params.get("end_time"):
        try:
            datetime.fromisoformat(params["end_time"])
        except (ValueError, TypeError):
            return "end_time 格式错误，需为 ISO 格式（如 2026-06-17T23:59:59）"
    return None


def _validate_optimize_params(params: dict) -> Optional[str]:
    """校验optimize参数，返回错误消息或None"""
    goal = params.get("production_goal")
    if not goal or not isinstance(goal, (int, float)) or goal <= 0:
        return "production_goal 必须为正整数"
    if params.get("deadline"):
        try:
            datetime.fromisoformat(params["deadline"])
        except (ValueError, TypeError):
            return "deadline 格式错误，需为 ISO 格式"
    return None


class WorkflowService:
    """工作流统一服务 — 单例无状态"""

    @staticmethod
    async def execute(
        workflow_type: WorkflowType,
        params: dict,
        db: Session,
        user_id: Optional[int] = None,
    ) -> dict:
        """统一执行入口

        Args:
            workflow_type: "analyze" | "optimize"
            params: 标准化参数字典
            db: 数据库会话
            user_id: 触发用户ID

        Returns:
            {"success": bool, "execution_id": int, "data": dict, "elapsed_ms": int}
        """
        # 1. 参数校验
        err = (
            _validate_analyze_params(params)
            if workflow_type == "analyze"
            else _validate_optimize_params(params)
        )
        if err:
            raise ValueError(err)

        # 2. 创建执行记录
        execution = WorkflowExecution(
            workflow_type=workflow_type,
            user_id=user_id,
            params_json=params,
            status="running",
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        start = time.time()

        try:
            # 3. 调用适配器（自动云端/本地选择）
            if workflow_type == "analyze":
                result = await analyze_energy(
                    device_id=params.get("device_id"),
                    start_time=params.get("start_time"),
                    end_time=params.get("end_time"),
                    db=db,
                    max_points=params.get("max_points", 200),
                )
            else:
                result = await optimize_schedule(
                    production_goal=params["production_goal"],
                    deadline=params.get("deadline"),
                    device_ids=params.get("device_ids", []),
                    db=db,
                )

            elapsed = int((time.time() - start) * 1000)

            # 判断实际使用的模式
            mode = _detect_mode(result, workflow_type)

            clean_result = dict(result)  # 保留 _mode 字段使前端能正确展示分析模式（云端/本地）

            # 4. 同步创建 AgentReport（使执行追踪 / 报告列表可关联）
            report_id = _ensure_agent_report(db, workflow_type, params, clean_result)

            # 5. 更新执行记录
            execution.status = "completed"
            execution.result_json = clean_result
            execution.mode_used = mode
            execution.elapsed_ms = elapsed
            db.commit()

            logger.info(f"[workflow] {workflow_type} #{execution.id} 完成, mode={mode}, {elapsed}ms")

            return {
                "success": True,
                "execution_id": execution.id,
                "report_id": report_id,
                "data": clean_result,
                "mode_used": mode,
                "elapsed_ms": elapsed,
            }

        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            execution.status = "failed"
            execution.error_message = str(e)
            execution.elapsed_ms = elapsed
            db.commit()
            logger.error(f"[workflow] {workflow_type} #{execution.id} 失败 ({elapsed}ms): {e}")
            raise

    @staticmethod
    def get_history(
        db: Session,
        workflow_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[WorkflowExecution]:
        """查询执行历史"""
        query = db.query(WorkflowExecution)
        if workflow_type:
            query = query.filter(WorkflowExecution.workflow_type == workflow_type)
        if status:
            query = query.filter(WorkflowExecution.status == status)
        return query.order_by(WorkflowExecution.created_at.desc()).limit(limit).all()


def _detect_mode(result: dict, workflow_type: str) -> str:
    """根据适配器返回的 _mode 字段判断实际使用的模式（云端/本地）"""
    return result.get("_mode", "unknown")


def _ensure_agent_report(db: Session, workflow_type: str, params: dict, result: dict) -> int:
    """同步创建 AgentReport，确保工作流结果在报告列表可检索"""
    report = AgentReport(
        report_type="analysis" if workflow_type == "analyze" else "schedule",
        trigger_time=datetime.now(),
        input_summary=(
            f"device_id={params.get('device_id')}, range={params.get('start_time')}~{params.get('end_time')}"
            if workflow_type == "analyze"
            else f"production_goal={params.get('production_goal')}, deadline={params.get('deadline')}"
        ),
        input_payload=params,
        output_json=result,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report.id
