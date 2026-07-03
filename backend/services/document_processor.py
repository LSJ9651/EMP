"""文档处理后台任务 — 解析 -> 分块 -> 嵌入 -> 存入 ChromaDB"""
import os
import logging
from typing import Optional

from sqlalchemy.orm import Session

from models import Document, DocumentChunk, KnowledgeBase
from services.llm_factory import create_embeddings
from services.llm_config_service import get_resolved_config

logger = logging.getLogger(__name__)

# ChromaDB 持久化目录
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chromadb")

# 支持的文档类型与加载器映射
SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".txt": "text",
    ".md": "text",
    ".docx": "docx",
}


def get_collection_name(kb_id: int) -> str:
    """根据知识库 ID 生成 ChromaDB Collection 名称"""
    return f"kb_{kb_id}"


def process_document(doc_id: int, db: Session):
    """文档处理主逻辑：解析 -> 分块 -> 嵌入 -> 存储

    后台异步调用，执行完成后更新 Document 状态
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        logger.error("Document %s not found", doc_id)
        return

    # 更新状态为 processing
    doc.doc_status = "processing"
    db.commit()

    try:
        # 1. 检查文件是否存在
        if not os.path.exists(doc.file_path):
            raise FileNotFoundError(f"文件不存在: {doc.file_path}")

        # 2. 根据文档类型选择加载器并加载文本
        texts = load_document(doc.file_path, doc.mime_type)

        if not texts:
            raise ValueError("文档内容为空，无法处理")

        # 3. 文本分块
        chunks = split_texts(texts)

        # 4. 获取 LLM 配置并创建 Embeddings（get_resolved_config 会解析 .env 中的真实 Key）
        llm_config = get_resolved_config(db)
        embeddings = create_embeddings(llm_config)
        if not embeddings:
            raise RuntimeError("无法创建 Embeddings 实例，请检查 LLM 配置")

        # 5. 存入 DocumentChunk 表
        chunk_records = []
        for i, chunk_text in enumerate(chunks):
            chunk_records.append(DocumentChunk(
                doc_id=doc.id,
                chunk_index=i,
                chunk_text=chunk_text,
                token_count=len(chunk_text) // 4,  # 粗略估算 token 数
            ))
        for cr in chunk_records:
            db.add(cr)
        db.flush()

        # 6. 生成嵌入并存入 ChromaDB
        from chromadb.config import Settings
        from langchain_chroma import Chroma

        collection_name = get_collection_name(doc.kb_id)

        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR,
            client_settings=Settings(anonymized_telemetry=False),
        )

        metadatas = [
            {
                "kb_id": doc.kb_id,
                "doc_id": doc.id,
                "chunk_index": i,
                "filename": doc.filename,
            }
            for i in range(len(chunks))
        ]

        vector_store.add_texts(texts=chunks, metadatas=metadatas)

        # 7. 更新文档状态
        doc.doc_status = "ready"
        doc.chunk_count = len(chunks)
        doc.error_message = None
        db.commit()

        logger.info("Document %s processed: %d chunks", doc.filename, len(chunks))

    except Exception as e:
        logger.error("Failed to process document %s: %s", doc.filename, e)
        doc.doc_status = "failed"
        doc.error_message = str(e)[:500]
        db.commit()


def load_document(file_path: str, mime_type: Optional[str] = None) -> list[str]:
    """根据文件类型加载文档，返回文本列表

    支持格式：PDF、TXT、Markdown
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        return [doc.page_content for doc in documents]

    elif ext in (".txt", ".md"):
        from langchain_community.document_loaders import TextLoader
        loader = TextLoader(file_path, encoding="utf-8")
        documents = loader.load()
        return [doc.page_content for doc in documents]

    else:
        raise ValueError(f"不支持的文档格式: {ext}")


def split_texts(texts: list[str], chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
    """将文本列表递归分割为文本块

    使用 RecursiveCharacterTextSplitter，适合中英文混合内容
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )

    all_chunks = []
    for text in texts:
        if text.strip():
            chunks = splitter.split_text(text)
            all_chunks.extend(chunks)

    return all_chunks


def delete_document_vectors(doc_id: int, kb_id: int, db: Session):
    """删除指定文档在 ChromaDB 中的向量数据"""
    try:
        from chromadb.config import Settings
        import chromadb

        client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )

        collection_name = get_collection_name(kb_id)
        try:
            collection = client.get_collection(collection_name)
            collection.delete(where={"doc_id": doc_id})
            logger.info("Deleted vectors for doc %s from collection %s", doc_id, collection_name)
        except ValueError:
            # 集合不存在，忽略
            pass
    except Exception as e:
        logger.error("Failed to delete vectors for doc %s: %s", doc_id, e)


def delete_knowledge_base_vectors(kb_id: int):
    """删除整个知识库的 ChromaDB Collection"""
    try:
        from chromadb.config import Settings
        import chromadb

        client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )

        collection_name = get_collection_name(kb_id)
        try:
            client.delete_collection(collection_name)
            logger.info("Deleted collection %s", collection_name)
        except ValueError:
            pass
    except Exception as e:
        logger.error("Failed to delete collection for kb %s: %s", kb_id, e)
