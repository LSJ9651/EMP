"""LLM 配置服务 — 读写 llm_config 表"""
import logging
from typing import Optional
from sqlalchemy.orm import Session

from models import LLMConfig
from config import settings

logger = logging.getLogger(__name__)

PLACEHOLDER = settings.KEY_PLACEHOLDER  # "********"

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


def _resolve_key(db_key: str, env_key: str) -> str:
    """解析 API Key：优先使用 .env 环境变量中的值，否则使用数据库值
    Args:
        db_key: 数据库 llm_config 表中存储的 Key
        env_key: .env 文件中配置的环境变量值
    Returns:
        真实的 API Key（非占位符）
    """
    if env_key:
        return env_key
    return db_key or ""


def save_llm_config(db: Session, data: dict) -> LLMConfig:
    """保存 LLM 配置（全量覆盖）

    安全保护：
    - 如果 API Key 传入的是占位符 "********"，则跳过该字段，保留数据库原值
    - 非占位符、非空的 Key 才会写入数据库
    """
    config = get_llm_config(db)

    allowed_fields = {
        "provider", "api_base", "api_key", "model_name",
        "embedding_provider", "embedding_api_base", "embedding_api_key",
        "embedding_model", "temperature", "max_tokens", "is_active",
    }

    for key, value in data.items():
        if key not in allowed_fields or value is None:
            continue

        # ── 关键保护：占位符不覆盖真实 Key ──
        if key in ("api_key", "embedding_api_key") and value == PLACEHOLDER:
            continue

        setattr(config, key, value)

    db.commit()
    db.refresh(config)
    return config


def to_dict(config: LLMConfig) -> dict:
    """将 LLMConfig 转为前端友好的字典（API Key 始终返回占位符，不回传真实值）

    前端无论怎么保存这个 Key 回来，后端都会丢弃它。
    真实 Key 只保存在 .env（优先）或数据库中（降级）。
    """
    return {
        "provider": config.provider,
        "api_base": config.api_base,
        "api_key": _api_key_display(config.api_key),
        "model_name": config.model_name,
        "embedding_provider": config.embedding_provider,
        "embedding_api_base": config.embedding_api_base,
        "embedding_api_key": _api_key_display(config.embedding_api_key),
        "embedding_model": config.embedding_model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "is_active": config.is_active,
    }


def get_resolved_config(db: Session) -> LLMConfig:
    """获取 LLM 配置，并将 API Key 解析为真实值（供内部服务使用）

    - 对话 api_key: 优先 .env LLM_API_KEY，降级数据库
    - 嵌入 api_key: 优先 .env LLM_EMBEDDING_API_KEY，降级数据库
    """
    config = get_llm_config(db)
    # 覆盖为真实 Key（不动数据库，只在内存中生效）
    config.api_key = _resolve_key(config.api_key, settings.LLM_API_KEY)
    config.embedding_api_key = _resolve_key(config.embedding_api_key, settings.LLM_EMBEDDING_API_KEY)
    return config


def _api_key_display(db_key: str) -> str:
    """返回给前端展示的 Key 值

    数据库中有真实 Key（无论是否在 .env 也配置了）→ 返回占位符
    数据库为空且 .env 也未配置 → 返回空字符串
    """
    if not db_key and not settings.LLM_API_KEY:
        return ""
    # 有 Key（无论是 DB 还是 .env），前端看到占位符
    return PLACEHOLDER


def mask_api_key(key: str) -> str:
    """脱敏 API Key：只显示前6位和后4位（仅用于日志等场景）"""
    if len(key) <= 10:
        return key[:3] + "***"
    return key[:6] + "****" + key[-4:]
