"""RAG 知识库相关模型 — KnowledgeBase, Document, DocumentChunk, RAGChatSession, RAGChatMessage, LLMConfig"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .base import Base


class KnowledgeBase(Base):
    """知识库"""
    __tablename__ = "knowledge_bases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="知识库名称")
    description = Column(Text, comment="知识库描述")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan",
                             passive_deletes=True)


class Document(Base):
    """文档"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kb_id = Column(Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(500), nullable=False, comment="原始文件名")
    file_path = Column(String(1000), comment="存储路径")
    file_size = Column(Integer, comment="文件大小(bytes)")
    mime_type = Column(String(100), comment="MIME类型")
    doc_status = Column(String(20), default="pending", comment="pending/processing/ready/failed")
    chunk_count = Column(Integer, default=0, comment="分块数")
    error_message = Column(Text, comment="处理失败原因")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan",
                          passive_deletes=False)


class DocumentChunk(Base):
    """文档分块"""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False, comment="块序号")
    chunk_text = Column(Text, nullable=False, comment="文本内容")
    token_count = Column(Integer, comment="估算token数")
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    document = relationship("Document", back_populates="chunks")


class RAGChatSession(Base):
    """RAG对话会话"""
    __tablename__ = "rag_chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, unique=True, index=True)
    kb_ids = Column(JSON, comment="关联的知识库ID列表")
    title = Column(String(200), default="新对话", comment="会话标题")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    messages = relationship("RAGChatMessage", back_populates="session", cascade="all, delete-orphan",
                            passive_deletes=True, order_by="RAGChatMessage.created_at")


class RAGChatMessage(Base):
    """RAG对话消息"""
    __tablename__ = "rag_chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), ForeignKey("rag_chat_sessions.session_id", ondelete="CASCADE"),
                        nullable=False, index=True)
    role = Column(String(20), nullable=False, comment="user/assistant")
    content = Column(Text, nullable=False)
    sources = Column(JSON, comment="引用来源: [{doc_id, chunk_index, score, text_preview}]")
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    session = relationship("RAGChatSession", back_populates="messages")


class LLMConfig(Base):
    """LLM配置表（单行模式，始终 id=1）

    对话模型与嵌入模型可独立配置 Provider，支持混合模式：
    - 对话用云端（OpenAI兼容），嵌入用本地（Ollama）
    - 或两者都用同一 Provider
    """
    __tablename__ = "llm_config"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 对话模型配置 ──
    provider = Column(String(50), default="openai_compatible",
                      comment="对话模型: openai_compatible / ollama")
    api_base = Column(String(500), default="", comment="对话模型API地址")
    api_key = Column(String(500), default="", comment="对话模型API密钥")
    model_name = Column(String(200), default="gpt-4o-mini", comment="对话模型名")

    # ── 嵌入模型配置（独立于对话模型） ──
    embedding_provider = Column(String(50), default="openai_compatible",
                                comment="嵌入模型: openai_compatible / ollama")
    embedding_api_base = Column(String(500), default="", comment="嵌入模型API地址")
    embedding_api_key = Column(String(500), default="", comment="嵌入模型API密钥")
    embedding_model = Column(String(200), default="text-embedding-3-small", comment="嵌入模型名")

    # ── 公共参数 ──
    temperature = Column(Float, default=0.7, comment="生成温度")
    max_tokens = Column(Integer, default=2048, comment="最大生成token数")
    is_active = Column(Boolean, default=True, comment="是否启用")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
