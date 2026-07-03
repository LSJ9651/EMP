"""RAG 对话服务 — SSE 流式生成"""
import json
import logging
import uuid
from typing import AsyncGenerator

from sqlalchemy.orm import Session

from models import RAGChatSession, RAGChatMessage, LLMConfig
from services.llm_factory import create_llm
from services.llm_config_service import get_resolved_config
from services.rag_retriever import retrieve, format_context

logger = logging.getLogger(__name__)

# 对话历史保留轮数
MAX_HISTORY_ROUNDS = 10

# System Prompt 模板
SYSTEM_PROMPT_TEMPLATE = """你是一个智能知识库助手，基于用户提供的知识库文档回答用户的问题。

请遵循以下规则：
1. 仅根据以下提供的"上下文内容"回答问题。如果上下文中没有足够信息，如实说明"知识库中没有相关信息的"。
2. 回答时引用信息来源，格式为 [1]、[2] 等，并在文末列出"参考来源"。
3. 使用中文回答，语言简洁专业。
4. 不要编造信息，不要使用外部知识补充。

=== 上下文内容 ===

{context}

=== 上下文结束 ===
"""


def get_or_create_session(db: Session, session_id: str = None, kb_ids: list[int] = None) -> RAGChatSession:
    """获取或创建 RAG 对话会话"""
    if session_id:
        session = db.query(RAGChatSession).filter(
            RAGChatSession.session_id == session_id
        ).first()
        if session:
            return session

    # 创建新会话
    new_session = RAGChatSession(
        session_id=session_id or str(uuid.uuid4()),
        kb_ids=kb_ids or [],
        title="新对话",
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


def get_session_history(db: Session, session_id: str) -> list[dict]:
    """获取最近 N 轮对话历史"""
    messages = (
        db.query(RAGChatMessage)
        .filter(RAGChatMessage.session_id == session_id)
        .order_by(RAGChatMessage.created_at.desc())
        .limit(MAX_HISTORY_ROUNDS * 2)
        .all()
    )
    messages.reverse()
    return [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]


async def rag_chat_stream(
    db: Session,
    message: str,
    session_id: str,
    kb_ids: list[int],
) -> AsyncGenerator[str, None]:
    """RAG 对话 SSE 流式生成器

    流程：
    1. 获取/创建会话
    2. 保存用户消息
    3. 检索知识库
    4. 构建 prompt
    5. 调用 LLM 流式生成
    6. 保存 AI 回复
    7. 流式返回事件

    Yields:
        SSE 格式的事件字符串
    """
    # 1. 获取/创建会话
    session = get_or_create_session(db, session_id, kb_ids)
    current_session_id = session.session_id

    # 2. 保存用户消息
    db.add(RAGChatMessage(
        session_id=current_session_id,
        role="user",
        content=message,
    ))
    db.commit()

    # 3. 检索知识库
    results = retrieve(message, kb_ids or session.kb_ids or [], db, top_k=5)
    context = format_context(results)

    if not context:
        # 无检索结果：直接返回提示
        reply = "知识库中未找到相关内容，请上传相关文档后再试。"
        db.add(RAGChatMessage(
            session_id=current_session_id,
            role="assistant",
            content=reply,
        ))
        db.commit()
        yield f"data: {json.dumps({'type': 'delta', 'content': reply})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'reply': reply, 'session_id': current_session_id, 'sources': [], 'mode': 'local'})}\n\n"
        return

    # 4. 构建 prompt
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)
    history = get_session_history(db, current_session_id)

    # 5. 获取 LLM 配置并创建实例（get_resolved_config 会解析 .env 中的真实 Key）
    llm_config = get_resolved_config(db)
    llm = create_llm(llm_config)

    if not llm:
        error_msg = "LLM 配置不可用，请在「系统设置-AI管理-本地LLM」中配置并测试连接"
        db.add(RAGChatMessage(
            session_id=current_session_id,
            role="assistant",
            content=error_msg,
        ))
        db.commit()
        yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
        return

    # 构建消息列表（System + 历史 + 当前问题）
    messages_for_llm = [{"role": "system", "content": system_prompt}]
    for h in history:
        messages_for_llm.append(h)
    messages_for_llm.append({"role": "user", "content": message})

    # 6. 调用 LLM 流式生成
    full_reply = ""
    try:
        stream = llm.stream(messages_for_llm)
        for chunk in stream:
            if hasattr(chunk, "content") and chunk.content:
                full_reply += chunk.content
                yield f"data: {json.dumps({'type': 'delta', 'content': chunk.content})}\n\n"
    except Exception as e:
        logger.error("LLM stream error: %s", e)
        yield f"data: {json.dumps({'type': 'error', 'message': f'LLM 调用失败: {str(e)}'})}\n\n"
        return

    # 7. 保存 AI 回复
    sources_data = [r.to_dict() for r in results]
    db.add(RAGChatMessage(
        session_id=current_session_id,
        role="assistant",
        content=full_reply,
        sources=sources_data,
    ))
    db.commit()

    # 更新会话标题（第一轮对话后自动命名）
    if session.title == "新对话" and len(full_reply) > 5:
        session.title = message[:50] + ("..." if len(message) > 50 else "")
        db.commit()

    # 8. 返回完成事件
    mode = 'cloud' if (llm_config and llm_config.provider == 'openai_compatible') else 'local'
    yield f"data: {json.dumps({
        'type': 'done',
        'reply': full_reply,
        'session_id': current_session_id,
        'sources': sources_data,
        'mode': mode,
    })}\n\n"
