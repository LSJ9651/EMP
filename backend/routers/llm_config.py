"""LLM 配置 API 路由"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from services.llm_factory import create_llm, create_embeddings
from services.llm_config_service import get_llm_config, save_llm_config, to_dict

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/llm-config", tags=["LLM配置"])


class LLMConfigSaveRequest(BaseModel):
    provider: str = Field(default="openai_compatible", description="openai_compatible / ollama")
    api_base: str = Field(default="", description="API地址")
    api_key: Optional[str] = Field(default="", description="API密钥")
    model_name: Optional[str] = Field(default="gpt-4o-mini", description="对话模型名")
    embedding_provider: Optional[str] = Field(default=None, description="嵌入模型提供商，不传则跟随 provider")
    embedding_api_base: Optional[str] = Field(default=None, description="嵌入模型API地址")
    embedding_api_key: Optional[str] = Field(default=None, description="嵌入模型API密钥")
    embedding_model: Optional[str] = Field(default=None, description="嵌入模型名")
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2, description="生成温度")
    max_tokens: Optional[int] = Field(default=2048, ge=64, le=32768, description="最大生成token数")
    is_active: Optional[bool] = Field(default=True, description="是否启用")


class TestConnectionRequest(BaseModel):
    test_type: str = Field(default="all", description="测试类型: llm / embedding / all")
    provider: str = "openai_compatible"
    api_base: str = ""
    api_key: str = ""
    model_name: str = "gpt-4o-mini"
    embedding_provider: Optional[str] = None
    embedding_api_base: Optional[str] = None
    embedding_api_key: Optional[str] = None
    embedding_model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048


@router.get("/")
def get_config(db: Session = Depends(get_db)):
    """获取 LLM 配置"""
    config = get_llm_config(db)
    return {"code": 200, "data": to_dict(config), "message": "success"}


@router.post("/")
def save_config(data: LLMConfigSaveRequest, db: Session = Depends(get_db)):
    """保存 LLM 配置"""
    save_data = data.model_dump(exclude_none=True)

    # 对话 api_key 为空时保留旧值
    if not data.api_key:
        existing = get_llm_config(db)
        if existing and existing.api_key:
            save_data["api_key"] = existing.api_key

    # 嵌入 api_key 为空时保留旧值
    if not data.embedding_api_key:
        existing = get_llm_config(db)
        if existing and existing.embedding_api_key:
            save_data["embedding_api_key"] = existing.embedding_api_key

    config = save_llm_config(db, save_data)
    return {"code": 200, "data": to_dict(config), "message": "配置保存成功"}


@router.post("/test")
def test_connection(data: TestConnectionRequest, db: Session = Depends(get_db)):
    """测试 LLM / Embeddings 连接"""
    logger.info("Testing connection: type=%s, provider=%s, model=%s",
                data.test_type, data.provider, data.model_name)

    try:
        # 使用传入参数创建临时配置对象
        class TempConfig:
            pass

        test_config = TempConfig()
        test_config.is_active = True
        test_config.provider = data.provider
        test_config.api_base = data.api_base
        test_config.api_key = data.api_key
        test_config.model_name = data.model_name
        test_config.temperature = data.temperature
        test_config.max_tokens = data.max_tokens
        # 嵌入配置
        test_config.embedding_provider = data.embedding_provider or data.provider
        test_config.embedding_api_base = data.embedding_api_base or data.api_base
        test_config.embedding_api_key = data.embedding_api_key or data.api_key
        test_config.embedding_model = data.embedding_model or "nomic-embed-text"

        result = {"success": True, "details": {}}

        # ── 测试 Embeddings ──
        if data.test_type in ("embedding", "all"):
            embeddings = create_embeddings(test_config)
            if not embeddings:
                return {"code": 400, "message": "创建 Embeddings 失败，请检查配置",
                        "data": {"success": False, "error": "embeddings_init_failed"}}

            test_text = "test"
            emb_result = embeddings.embed_query(test_text)
            if not emb_result or len(emb_result) == 0:
                return {"code": 400, "message": "Embeddings 测试失败，返回空向量",
                        "data": {"success": False, "error": "empty_embedding"}}

            result["details"]["embedding"] = {
                "success": True,
                "model": test_config.embedding_model,
                "dimension": len(emb_result),
            }

        # ── 测试 LLM ──
        if data.test_type in ("llm", "all"):
            llm = create_llm(test_config)
            if not llm:
                return {"code": 400, "message": "创建 LLM 实例失败，请检查配置",
                        "data": {"success": False, "error": "llm_init_failed"}}

            reply = llm.invoke("请回复'连接成功'四个字")
            reply_text = reply.content if hasattr(reply, "content") else str(reply)

            result["details"]["llm"] = {
                "success": True,
                "model": data.model_name,
                "reply": reply_text,
            }

        return {"code": 200, "data": result, "message": "连接测试成功"}

    except Exception as e:
        logger.error("Connection test failed: %s", e)
        return {
            "code": 400,
            "data": {"success": False, "error": str(e)},
            "message": f"连接测试失败: {str(e)}",
        }
