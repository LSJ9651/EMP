"""LLM / Embeddings 工厂 — 根据配置动态创建实例"""
import logging
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


def create_llm(config) -> Optional[BaseChatModel]:
    """根据 LLM 配置动态创建 LLM 实例

    Args:
        config: LLMConfig ORM 对象（或任意有相同属性的对象）

    Returns:
        BaseChatModel 实例，配置无效时返回 None
    """
    if not config or not config.is_active:
        logger.warning("LLM config is not active or missing")
        return None

    try:
        if config.provider == "ollama":
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=config.model_name or "qwen2:7b",
                temperature=config.temperature or 0.7,
                num_predict=config.max_tokens or 2048,
                base_url=config.api_base or "http://localhost:11434",
            )
        else:
            # openai_compatible
            if not config.api_key:
                logger.warning("OpenAI-compatible LLM requires api_key")
                return None
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=config.model_name or "gpt-4o-mini",
                temperature=config.temperature or 0.7,
                max_tokens=config.max_tokens or 2048,
                api_key=config.api_key,
                base_url=config.api_base,
            )
    except Exception as e:
        logger.error("Failed to create LLM instance: %s", e)
        return None


def create_embeddings(config) -> Optional[Embeddings]:
    """根据 LLM 配置动态创建 Embeddings 实例

    使用独立的嵌入模型配置（embedding_provider/embedding_api_base/embedding_api_key/embedding_model），
    未设置时降级使用对话模型的配置。

    Args:
        config: LLMConfig ORM 对象

    Returns:
        Embeddings 实例，配置无效时返回 None
    """
    if not config or not config.is_active:
        logger.warning("LLM config is not active or missing")
        return None

    emb_provider = config.embedding_provider or config.provider
    emb_api_base = config.embedding_api_base or config.api_base
    emb_api_key = config.embedding_api_key or config.api_key
    emb_model = config.embedding_model or "nomic-embed-text"

    try:
        if emb_provider == "ollama":
            from langchain_ollama import OllamaEmbeddings
            return OllamaEmbeddings(
                model=emb_model,
                base_url=emb_api_base or "http://localhost:11434",
            )
        else:
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=emb_model,
                api_key=emb_api_key,
                base_url=emb_api_base,
            )
    except Exception as e:
        logger.error("Failed to create Embeddings instance: %s", e)
        return None
