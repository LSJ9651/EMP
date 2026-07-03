"""对话路由 — 纯对话助手 API（直接调用 Coze Bot，不再进行意图识别和业务路由）"""

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.chat_service import (
    stream_general_chat, get_history, generate_session_id,
)
from services.ai_config_service import ai_config_service

router = APIRouter(prefix="/api/agent/chat", tags=["智能对话助手"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="用户输入的消息内容")
    session_id: Optional[str] = Field(None, description="会话ID，不传则自动生成新会话")


@router.post("")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """纯对话接口 — 所有消息直接转发给 Coze Bot（或本地降级），统一 SSE 流式返回"""
    session_id = request.session_id or generate_session_id()

    return StreamingResponse(
        stream_general_chat(request.message, session_id, db),
        media_type="text/event-stream",
    )


@router.get("/diagnostics")
async def chat_diagnostics(db: Session = Depends(get_db)):
    """对话功能诊断 — 返回当前配置状态"""
    config = ai_config_service.get_all(db)
    api_key = ai_config_service.get_api_key(db)

    return {
        "code": 200,
        "data": {
            "master_switch": config["enable_cloud_agent"],
            "chat_enabled": config["chat"]["enabled"],
            "bot_id_configured": bool(config["chat"]["bot_id"]),
            "bot_id_preview": config["chat"]["bot_id"][:8] + "..." if config["chat"]["bot_id"] else "",
            "api_key_configured": bool(api_key),
            "api_base": ai_config_service.get_api_base(db),
            "is_ready": all([
                config["enable_cloud_agent"],
                config["chat"]["enabled"],
                bool(config["chat"]["bot_id"]),
                bool(api_key),
            ]),
        },
    }


@router.get("/history")
async def chat_history(session_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """获取指定会话的对话历史"""
    history = get_history(session_id, db, limit)
    return {"code": 200, "message": "success", "data": history}
