"""LLM 配置服务 — 读写 llm_config 表"""
import logging
from typing import Optional
from sqlalchemy.orm import Session

from models import LLMConfig

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "provider": "openai_compatible",
    "api_base": "",
    "api_key": "",
    "model_name": "gpt-4o-mini",
    "embedding_provider": "openai_compatible",
    "embedding_api_base": "",
    "embedding_api_key": "",
    "embedding_model": "text-embedding-3-small",
    "temperature": 0.7,
    "max_tokens": 2048,
    "is_active": True,
}


def get_llm_config(db: Session) -> LLMConfig:
    """获取 LLM 配置，不存在则创建默认配置

    始终使用 id=1 的单行模式
    """
    config = db.query(LLMConfig).filter(LLMConfig.id == 1).first()
    if not config:
        config = LLMConfig(**DEFAULT_CONFIG)
        config.id = 1
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def save_llm_config(db: Session, data: dict) -> LLMConfig:
    """保存 LLM 配置（全量覆盖）"""
    config = get_llm_config(db)

    allowed_fields = {
        "provider", "api_base", "api_key", "model_name",
        "embedding_provider", "embedding_api_base", "embedding_api_key",
        "embedding_model", "temperature", "max_tokens", "is_active",
    }

    for key, value in data.items():
        if key in allowed_fields and value is not None:
            setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return config


def to_dict(config: LLMConfig) -> dict:
    """将 LLMConfig 转为前端友好的字典（隐藏 api_key 完整值）"""
    return {
        "provider": config.provider,
        "api_base": config.api_base,
        "api_key": mask_api_key(config.api_key) if config.api_key else "",
        "model_name": config.model_name,
        "embedding_provider": config.embedding_provider,
        "embedding_api_base": config.embedding_api_base,
        "embedding_api_key": mask_api_key(config.embedding_api_key) if config.embedding_api_key else "",
        "embedding_model": config.embedding_model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "is_active": config.is_active,
    }


def mask_api_key(key: str) -> str:
    """脱敏 API Key：只显示前6位和后4位"""
    if len(key) <= 10:
        return key[:3] + "***"
    return key[:6] + "****" + key[-4:]
