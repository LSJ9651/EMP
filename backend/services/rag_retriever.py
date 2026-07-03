"""RAG 检索器 — 向量检索 + 结果合并"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from models import LLMConfig
from services.llm_factory import create_embeddings
from services.document_processor import CHROMA_PERSIST_DIR, get_collection_name

logger = logging.getLogger(__name__)


class ChunkResult:
    """检索结果块"""
    def __init__(self, doc_id: int, chunk_index: int, text: str, score: float, filename: str = ""):
        self.doc_id = doc_id
        self.chunk_index = chunk_index
        self.text = text
        self.score = score
        self.filename = filename

    def to_dict(self):
        return {
            "doc_id": self.doc_id,
            "chunk_index": self.chunk_index,
            "text_preview": self.text[:200],
            "score": round(self.score, 4),
            "filename": self.filename,
        }


def retrieve(query: str, kb_ids: list[int], db: Session, top_k: int = 5) -> list[ChunkResult]:
    """从指定的知识库中检索相关文档块

    Args:
        query: 用户查询文本
        kb_ids: 要检索的知识库 ID 列表
        db: 数据库会话
        top_k: 每个知识库返回的最相关结果数

    Returns:
        按 score 降序排列的 ChunkResult 列表
    """
    if not kb_ids:
        logger.warning("No knowledge base IDs provided for retrieval")
        return []

    # 获取 LLM 配置并创建 Embeddings
    llm_config = db.query(LLMConfig).filter(LLMConfig.id == 1).first()
    if not llm_config or not llm_config.is_active:
        logger.warning("LLM config not active, cannot perform retrieval")
        return []

    embeddings = create_embeddings(llm_config)
    if not embeddings:
        logger.error("Failed to create embeddings for retrieval")
        return []

    from chromadb.config import Settings
    from langchain_chroma import Chroma

    all_results: list[ChunkResult] = []

    for kb_id in kb_ids:
        try:
            collection_name = get_collection_name(kb_id)
            vector_store = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=CHROMA_PERSIST_DIR,
                client_settings=Settings(anonymized_telemetry=False),
            )

            docs_with_scores = vector_store.similarity_search_with_score(query, k=top_k)

            for doc, score in docs_with_scores:
                metadata = doc.metadata or {}
                all_results.append(ChunkResult(
                    doc_id=metadata.get("doc_id", 0),
                    chunk_index=metadata.get("chunk_index", 0),
                    text=doc.page_content,
                    score=score,
                    filename=metadata.get("filename", ""),
                ))

        except Exception as e:
            logger.warning("Failed to search knowledge base %s: %s", kb_id, e)
            continue

    # 按 score 升序排列（ChromaDB 的 score 越小越相似）
    all_results.sort(key=lambda r: r.score)
    return all_results[:top_k]


def format_context(results: list[ChunkResult]) -> str:
    """将检索结果格式化为上下文文本"""
    if not results:
        return ""

    parts = []
    for i, r in enumerate(results, 1):
        source = f"来源: {r.filename}" if r.filename else f"文档ID: {r.doc_id}"
        parts.append(f"[{i}] ({source})\n{r.text}")

    return "\n\n".join(parts)
