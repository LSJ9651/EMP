"""知识库 + 文档管理 API 路由"""
import os
import uuid
import logging
import threading

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import KnowledgeBase, Document
from services.document_processor import (
    process_document,
    delete_document_vectors,
    delete_knowledge_base_vectors,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/knowledge-bases", tags=["知识库管理"])

# 文件存储根目录
UPLOAD_ROOT = os.getenv("DOCUMENT_UPLOAD_DIR", "./data/documents")

# 最大文件大小（50MB）
MAX_FILE_SIZE = 50 * 1024 * 1024

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


def ensure_upload_dir(kb_id: int, doc_id: int) -> str:
    """确保上传目录存在"""
    dir_path = os.path.join(UPLOAD_ROOT, str(kb_id), str(doc_id))
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


# ──── 知识库 CRUD ────


class KBCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="知识库名称")
    description: Optional[str] = Field("", description="知识库描述")


class KBUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None


@router.get("/")
def list_knowledge_bases(db: Session = Depends(get_db)):
    """获取知识库列表（含文档计数）"""
    kbs = db.query(KnowledgeBase).order_by(KnowledgeBase.updated_at.desc()).all()
    result = []
    for kb in kbs:
        doc_count = db.query(Document).filter(Document.kb_id == kb.id).count()
        result.append({
            "id": kb.id,
            "name": kb.name,
            "description": kb.description or "",
            "doc_count": doc_count,
            "created_at": kb.created_at.isoformat() if kb.created_at else None,
            "updated_at": kb.updated_at.isoformat() if kb.updated_at else None,
        })
    return {"code": 200, "data": result, "message": "success"}


@router.post("/")
def create_knowledge_base(data: KBCreateRequest, db: Session = Depends(get_db)):
    """创建知识库"""
    if db.query(KnowledgeBase).filter(KnowledgeBase.name == data.name).first():
        raise HTTPException(status_code=400, detail="知识库名称已存在")

    kb = KnowledgeBase(name=data.name, description=data.description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return {"code": 200, "data": {"id": kb.id}, "message": "知识库创建成功"}


@router.put("/{kb_id}")
def update_knowledge_base(kb_id: int, data: KBUpdateRequest, db: Session = Depends(get_db)):
    """更新知识库"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    if data.name is not None:
        existing = db.query(KnowledgeBase).filter(
            KnowledgeBase.name == data.name, KnowledgeBase.id != kb_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="知识库名称已存在")
        kb.name = data.name
    if data.description is not None:
        kb.description = data.description

    db.commit()
    return {"code": 200, "message": "知识库更新成功"}


@router.delete("/{kb_id}")
def delete_knowledge_base(kb_id: int, db: Session = Depends(get_db)):
    """删除知识库（级联删除文档 + 向量）"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 异步删除 ChromaDB 向量
    delete_knowledge_base_vectors(kb_id)

    # 删除数据库记录（ORM cascade 会自动删除关联的 Document 和 Chunk）
    db.delete(kb)
    db.commit()

    return {"code": 200, "message": "知识库删除成功"}


# ──── 文档管理 ────


@router.post("/{kb_id}/documents/upload")
def upload_document(kb_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传文档到知识库"""
    # 验证知识库存在
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 验证文件扩展名
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，支持的格式: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # 读取文件内容
    content = file.file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）")

    if file_size == 0:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 创建 Document 记录
    doc = Document(
        kb_id=kb_id,
        filename=file.filename or "unnamed",
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        doc_status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 保存文件到磁盘
    upload_dir = ensure_upload_dir(kb_id, doc.id)
    safe_filename = file.filename or f"doc_{doc.id}{ext}"
    file_path = os.path.join(upload_dir, safe_filename).replace("\\", "/")
    with open(file_path, "wb") as f:
        f.write(content)
    file.file.close()

    doc.file_path = file_path
    db.commit()

    # 后台异步处理文档（使用线程避免阻塞）
    def _process():
        from database import SessionLocal
        try:
            thread_db = SessionLocal()
            process_document(doc.id, thread_db)
        finally:
            thread_db.close()

    thread = threading.Thread(target=_process, daemon=True)
    thread.start()

    return {
        "code": 200,
        "data": {
            "id": doc.id,
            "filename": doc.filename,
            "file_size": file_size,
            "status": "pending",
            "message": "文件上传成功，正在后台处理...",
        },
        "message": "上传成功",
    }


@router.get("/{kb_id}/documents")
def list_documents(kb_id: int, db: Session = Depends(get_db)):
    """获取知识库下的文档列表"""
    if not db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first():
        raise HTTPException(status_code=404, detail="知识库不存在")

    docs = (
        db.query(Document)
        .filter(Document.kb_id == kb_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    result = [
        {
            "id": d.id,
            "filename": d.filename,
            "file_size": d.file_size,
            "mime_type": d.mime_type,
            "doc_status": d.doc_status,
            "chunk_count": d.chunk_count,
            "error_message": d.error_message,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in docs
    ]
    return {"code": 200, "data": result, "message": "success"}


@router.delete("/{kb_id}/documents/{doc_id}")
def delete_document(kb_id: int, doc_id: int, db: Session = Depends(get_db)):
    """删除文档（含向量数据）"""
    doc = db.query(Document).filter(
        Document.id == doc_id, Document.kb_id == kb_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除 ChromaDB 向量
    delete_document_vectors(doc_id, kb_id, db)

    # 删除文件（兼容正反斜杠路径）
    if doc.file_path:
        normalized_path = doc.file_path.replace("\\", "/")
        if os.path.exists(normalized_path):
            try:
                os.remove(normalized_path)
            except OSError as e:
                logger.warning("Failed to delete file %s: %s", normalized_path, e)

    # 删除数据库记录
    db.delete(doc)
    db.commit()

    return {"code": 200, "message": "文档删除成功"}


@router.post("/{kb_id}/documents/{doc_id}/reprocess")
def reprocess_document(kb_id: int, doc_id: int, db: Session = Depends(get_db)):
    """重新处理文档"""
    doc = db.query(Document).filter(
        Document.id == doc_id, Document.kb_id == kb_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=400, detail="文档文件不存在，无法重新处理")

    # 先清除旧向量
    delete_document_vectors(doc_id, kb_id, db)
    # 清除旧 chunk 记录
    doc.chunk_count = 0
    doc.doc_status = "pending"
    doc.error_message = None
    db.commit()

    # 后台异步处理
    def _process():
        from database import SessionLocal
        try:
            thread_db = SessionLocal()
            process_document(doc.id, thread_db)
        finally:
            thread_db.close()

    thread = threading.Thread(target=_process, daemon=True)
    thread.start()

    return {"code": 200, "data": {"id": doc.id, "status": "pending"}, "message": "已重新开始处理"}
