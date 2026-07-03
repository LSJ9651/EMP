"""通知消息路由 — 消息中心 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Notification

router = APIRouter(prefix="/api/notifications", tags=["通知消息"])


@router.get("/list")
def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """获取通知列表（按时间倒序）"""
    total = db.query(Notification).count()
    items = (
        db.query(Notification)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "code": 200,
        "data": {
            "total": total,
            "items": [
                {
                    "id": n.id,
                    "title": n.title,
                    "content": n.content,
                    "category": n.category,
                    "source_type": n.source_type,
                    "source_id": n.source_id,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in items
            ],
        },
        "message": "success",
    }


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db)):
    """获取未读通知数量"""
    count = db.query(Notification).filter(Notification.is_read == False).count()
    return {"code": 200, "data": {"count": count}, "message": "success"}


@router.put("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db)):
    """标记单条通知为已读"""
    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if n:
        n.is_read = True
        db.commit()
    return {"code": 200, "data": None, "message": "success"}


@router.put("/read-all")
def mark_all_read(db: Session = Depends(get_db)):
    """标记全部通知为已读"""
    db.query(Notification).filter(Notification.is_read == False).update(
        {"is_read": True}
    )
    db.commit()
    return {"code": 200, "data": None, "message": "success"}
