"""AI配置路由 — 智能体配置管理与连接测试 API"""

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.ai_config_service import ai_config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-config", tags=["AI配置管理"])


# ========== Pydantic 模型 ==========

class AIConfigRequest(BaseModel):
    enable_cloud_agent: bool = False
    coze_api_key: str = ""
    coze_api_base: str = "https://api.coze.cn"
    analyze_enabled: bool = False
    analyze_workflow_id: str = ""
    analyze_timeout: int = Field(default=120, ge=1, le=300)
    optimize_enabled: bool = False
    optimize_workflow_id: str = ""
    optimize_timeout: int = Field(default=120, ge=1, le=300)
    chat_enabled: bool = False
    chat_bot_id: str = ""
    chat_timeout: int = Field(default=30, ge=1, le=300)


class TestRequest(BaseModel):
    type: str = Field(..., pattern="^(analyze|optimize|chat)$")


# ========== API 端点 ==========

@router.get("")
async def get_config(db: Session = Depends(get_db)):
    """获取 AI 配置"""
    config = ai_config_service.get_all(db)
    return {
        "code": 200,
        "message": "success",
        "data": config,
    }


@router.post("")
async def save_config(req: AIConfigRequest, db: Session = Depends(get_db)):
    """保存 AI 配置（批量更新所有配置项）"""
    flat = {
        "enable_cloud_agent": req.enable_cloud_agent,
        "coze_api_key": req.coze_api_key,
        "coze_api_base": req.coze_api_base,
        "analyze_enabled": req.analyze_enabled,
        "analyze_workflow_id": req.analyze_workflow_id,
        "analyze_timeout": req.analyze_timeout,
        "optimize_enabled": req.optimize_enabled,
        "optimize_workflow_id": req.optimize_workflow_id,
        "optimize_timeout": req.optimize_timeout,
        "chat_enabled": req.chat_enabled,
        "chat_bot_id": req.chat_bot_id,
        "chat_timeout": req.chat_timeout,
    }

    success = ai_config_service.update_all(db, flat)

    if success:
        return {"code": 200, "message": "配置保存成功", "data": None}
    else:
        return {"code": 500, "message": "配置保存失败", "data": None}


@router.post("/test")
async def test_connection(req: TestRequest, db: Session = Depends(get_db)):
    """测试指定服务的连接状态（使用 Coze SDK）"""
    from services.coze_client import CozeClient

    result = await CozeClient.test_connection(db, req.type)
    return {
        "code": 200,
        "message": "success",
        "data": result,
    }


@router.get("/status")
async def get_status(db: Session = Depends(get_db)):
    """获取各服务当前有效模式状态（供前端实时显示）"""
    master_on = ai_config_service.is_cloud_enabled(db, "analyze") or \
                ai_config_service.is_cloud_enabled(db, "optimize") or \
                ai_config_service.is_cloud_enabled(db, "chat")

    api_key = ai_config_service.get_api_key(db)

    def _service_status(service_type: str) -> dict:
        enabled = ai_config_service.is_cloud_enabled(db, service_type)
        service_id = ai_config_service.get_service_id(db, service_type)
        ready = bool(enabled and api_key and service_id)

        if not master_on:
            mode = "local"
            detail = "总开关关闭，使用本地模式"
        elif not enabled:
            mode = "local"
            detail = "服务未启用云端，使用本地模式"
        elif not api_key:
            mode = "local"
            detail = "API Key 未配置，使用本地模式"
        elif not service_id:
            mode = "local"
            detail = "工作流/Bot ID 未配置，使用本地模式"
        else:
            mode = "cloud"
            detail = "云端模式就绪"

        return {
            "mode": mode,
            "ready": ready,
            "detail": detail,
        }

    return {
        "code": 200,
        "message": "success",
        "data": {
            "analyze": _service_status("analyze"),
            "optimize": _service_status("optimize"),
            "chat": _service_status("chat"),
        },
    }
