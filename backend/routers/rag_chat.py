"""RAG 对话 API 路由 — SSE 流式对话 + 会话管理"""
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import RAGChatSession, RAGChatMessage
from services.rag_chat_service import rag_chat_stream, get_or_create_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["RAG智能问答"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000, description="用户问题")
    session_id: Optional[str] = Field(None, description="会话ID，新会话留空")
    kb_ids: list[int] = Field(default_factory=list, description="知识库ID列表")


class SessionCreateRequest(BaseModel):
    kb_ids: list[int] = Field(default_factory=list)
    title: Optional[str] = "新对话"


# ──── 对话 ────


@router.post("/chat")
def chat(data: ChatRequest, db: Session = Depends(get_db)):
    """RAG 对话 — SSE 流式响应"""
    return StreamingResponse(
        rag_chat_stream(db, data.message, data.session_id or str(uuid.uuid4()), data.kb_ids),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ──── 会话管理 ────


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
    """获取 RAG 会话列表"""
    sessions = db.query(RAGChatSession).order_by(RAGChatSession.updated_at.desc()).limit(50).all()
    result = []
    for s in sessions:
        msg_count = db.query(RAGChatMessage).filter(
            RAGChatMessage.session_id == s.session_id
        ).count()
        result.append({
            "session_id": s.session_id,
            "title": s.title or "新对话",
            "kb_ids": s.kb_ids or [],
            "msg_count": msg_count,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        })
    return {"code": 200, "data": result, "message": "success"}


@router.post("/sessions")
def create_session(data: SessionCreateRequest, db: Session = Depends(get_db)):
    """创建新会话"""
    session = get_or_create_session(db, kb_ids=data.kb_ids)
    session.title = data.title or "新对话"
    db.commit()
    return {
        "code": 200,
        "data": {
            "session_id": session.session_id,
            "title": session.title,
            "kb_ids": session.kb_ids or [],
        },
        "message": "会话创建成功",
    }


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """删除会话"""
    session = db.query(RAGChatSession).filter(
        RAGChatSession.session_id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.delete(session)
    db.commit()
    return {"code": 200, "message": "会话删除成功"}


@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    """获取会话消息历史"""
    session = db.query(RAGChatSession).filter(
        RAGChatSession.session_id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = (
        db.query(RAGChatMessage)
        .filter(RAGChatMessage.session_id == session_id)
        .order_by(RAGChatMessage.created_at)
        .all()
    )
    result = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": m.sources or [],
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]
    return {"code": 200, "data": result, "message": "success"}
