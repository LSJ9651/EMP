"""对话业务服务 — 纯对话功能，直接调用 Coze Bot，失败降级本地
增强：支持标签指令检测 → 工具调用 → 二次对话
"""

import uuid
import json
import asyncio
import logging
from datetime import datetime

from sqlalchemy.orm import Session
from models import ChatHistory
from services.ai_config_service import ai_config_service
from services.tag_parser import tag_parser

logger = logging.getLogger(__name__)


def generate_session_id() -> str:
    """生成新的会话ID"""
    return f"sess_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"


def get_history(session_id: str, db: Session, limit: int = 50) -> list:
    """获取指定会话的聊天历史"""
    messages = (
        db.query(ChatHistory)
        .filter(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.created_at)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "timestamp": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


def _local_fallback(message: str) -> str:
    """本地兜底回复"""
    msg_lower = message.lower().strip()

    if any(w in msg_lower for w in ["你好", "hello", "hi", "嗨"]):
        return "你好！我是能耗智能管理助手，有什么可以帮你的吗？"

    if any(w in msg_lower for w in ["功能", "能做什么", "帮助", "help"]):
        return ("我可以回答你关于能源管理的各种问题，例如设备运行状态、能耗数据查询、"
                "节能建议等。你也可以直接在功能页面查看详细数据。")

    if any(w in msg_lower for w in ["谢谢", "感谢", "thanks"]):
        return "不客气！如有其他问题，随时问我。"

    return ("您好，我是能耗管理智能助手。当前运行在本地模式，您的消息已收到。"
            "如需更智能的对话体验，请在 AI 配置中启用云端智能体。")


def _sse_event(data: dict) -> str:
    """构建 SSE 事件字符串"""
    return f'data: {json.dumps(data, ensure_ascii=False)}\n\n'


def _build_enriched_message(user_message: str, analysis_result: dict, match_info: dict) -> str:
    """构建增强消息，将分析结果拼接用户问题后重新发给智能体"""
    matched_names = match_info.get("matched_names", [])
    total_requested = match_info.get("total_requested", 0)
    device_count = len(matched_names)

    return (
        f"用户问题：{user_message}\n\n"
        f"设备能耗分析结果（共 {device_count} 台设备）：\n"
        f"{json.dumps(analysis_result, ensure_ascii=False, indent=2)}\n\n"
        f"备注：用户原始请求分析 {total_requested} 台设备，成功匹配分析 {device_count} 台。\n"
        f"请根据以上分析数据，用中文向用户清晰地报告各设备的能耗状况、异常情况和节能建议。"
    )


def _save_message(db: Session, session_id: str, role: str, content: str, **kwargs):
    """保存消息到 chat_history"""
    msg = ChatHistory(
        session_id=session_id,
        role=role,
        content=content,
        **kwargs,
    )
    db.add(msg)
    db.commit()
    return msg


def stream_general_chat(message: str, session_id: str, db: Session):
    """流式对话 SSE 生成器（增强版 — 支持标签指令 → 工具调用 → 二次对话）

    流程：
    1. 保存用户消息
    2. 第一次调用 Coze（流式输出 delta + 累积完整内容）
    3. 解析累积内容中的 <INTERNAL_CMD> 标签
    4. 若存在标签：执行工具调用 → 第二次调用 Coze → 流式最终回答
    5. 若不存在标签：直接返回第一次回复
    6. 云端不可用时降级本地固定回复
    """

    # ── 1. 保存用户消息 ──
    _save_message(db, session_id, "user", message)

    full_reply = ""
    final_mode = "local"
    is_fallback = False
    tool_used = False

    # ── 2. 检查云端配置 ──
    cloud_enabled = ai_config_service.is_cloud_enabled(db, "chat")
    api_key = ai_config_service.get_api_key(db)
    bot_id = ai_config_service.get_service_id(db, "chat")

    logger.info(f"[chat] 对话请求开始: message_len={len(message)}, session_id={session_id}")
    logger.info(f"[chat] 云端配置: enabled={cloud_enabled}, api_key={bool(api_key)}, bot_id={bool(bot_id)}")

    first_error = None

    if cloud_enabled:
        logger.info(f"[chat] 云端对话模式，调用 Coze Bot, session_id={session_id}")
        try:
            from services.coze_client import CozeClient

            # ── Phase 1: 第一次 Coze 调用（流式输出 + 累积完整内容）──
            first_content = ""
            first_token = 0
            first_elapsed = 0

            for event in CozeClient.chat_stream(db, message, session_id):
                if event["type"] == "delta":
                    first_content += event["content"]
                    yield _sse_event({"type": "delta", "content": event["content"]})

                elif event["type"] == "done":
                    first_token = event.get("token_count", 0)
                    first_elapsed = event.get("elapsed", 0)

                elif event["type"] == "error":
                    first_error = event.get("message", "未知错误")
                    logger.warning(f"[chat] 第一次 Coze 调用出错: {first_error}")
                    break

            # 如果第一次调用就失败了，走降级
            if first_error and not first_content:
                raise Exception(first_error)

            # ── Phase 2: 解析标签 ──
            parse_result = tag_parser.parse(first_content)

            if parse_result.has_tag:
                logger.info(f"[chat] 检测到工具调用标签: tool={parse_result.tool_type}")
                tool_used = True

                # ── Phase 3: 执行工具调用 ──
                from services.tool_handler import ToolHandler
                tool_handler = ToolHandler(db)
                tool_result = asyncio.run(tool_handler.execute(
                    parse_result.tool_type,
                    parse_result.tool_params,
                    db,
                ))

                tool_result_dict = tool_result.to_dict()
                match_status = tool_result.match_status

                if not tool_result.success:
                    # 工具执行失败或需要用户澄清
                    clarification = tool_result.error or "工具执行异常，请稍后重试。"
                    full_reply = clarification
                    is_fallback = True

                    # 保存中间消息（含工具信息）
                    _save_message(
                        db, session_id, "assistant", full_reply,
                        intent="general_chat", workflow_type="chat",
                        tool_type=parse_result.tool_type,
                        tool_params=json.dumps(parse_result.tool_params, ensure_ascii=False),
                        tool_result=json.dumps(tool_result_dict, ensure_ascii=False),
                        match_status=json.dumps(match_status, ensure_ascii=False) if match_status else None,
                        is_final=True,
                        needs_user_input=not tool_result.success,
                    )

                    yield _sse_event({
                        "type": "done",
                        "reply": full_reply,
                        "session_id": session_id,
                        "intent": "general_chat",
                        "mode": "cloud",
                        "tool_used": True,
                        "tool_type": parse_result.tool_type,
                        "needs_user_input": True,
                    })
                    return

                # ── Phase 4: 工具成功 → 构建增强消息 → 第二次 Coze 调用 ──
                analysis_result = tool_result.result.get("analysis_result", {})
                match_info = tool_result.result.get("match_result", {})
                enriched = _build_enriched_message(message, analysis_result, match_info)

                logger.info(f"[chat] 工具执行成功，发送二次对话: enriched_len={len(enriched)}")

                # 通知前端：正在执行工具
                yield _sse_event({
                    "type": "tool_status",
                    "tool": parse_result.tool_type,
                    "phase": "analyzing",
                    "message": "正在分析设备能耗数据...",
                })

                # 第二次 Coze 调用（流式输出最终回答）
                second_content = ""
                second_token = 0
                second_elapsed = 0

                for event in CozeClient.chat_stream(db, enriched, session_id):
                    if event["type"] == "delta":
                        second_content += event["content"]
                        yield _sse_event({"type": "delta", "content": event["content"]})

                    elif event["type"] == "done":
                        second_token = event.get("token_count", 0)
                        second_elapsed = event.get("elapsed", 0)

                    elif event["type"] == "error":
                        logger.warning(f"[chat] 第二次 Coze 调用出错: {event.get('message')}")
                        break

                if second_content:
                    full_reply = second_content
                    final_mode = "cloud"
                else:
                    # 第二次调用无内容，使用第一次的清洁内容
                    full_reply = parse_result.clean_content or "分析完成，但智能体未能生成详细报告。"
                    is_fallback = True

                # 保存最终消息（含完整工具信息）
                _save_message(
                    db, session_id, "assistant", full_reply,
                    intent="general_chat", workflow_type="chat",
                    tool_type=parse_result.tool_type,
                    tool_params=json.dumps(parse_result.tool_params, ensure_ascii=False),
                    tool_result=json.dumps(tool_result_dict, ensure_ascii=False),
                    match_status=json.dumps(match_status, ensure_ascii=False) if match_status else None,
                    is_final=True,
                    needs_user_input=False,
                )

                yield _sse_event({
                    "type": "done",
                    "reply": full_reply,
                    "session_id": session_id,
                    "intent": "general_chat",
                    "mode": final_mode,
                    "tool_used": True,
                    "tool_type": parse_result.tool_type,
                    "fallback": is_fallback,
                    "token_count": first_token + second_token,
                    "elapsed": first_elapsed + second_elapsed,
                })
                return

            else:
                # ── Phase 2b: 无标签 → 直接返回第一次回复 ──
                full_reply = first_content
                final_mode = "cloud"

                _save_message(
                    db, session_id, "assistant", full_reply,
                    intent="general_chat", workflow_type="chat",
                    is_final=True,
                )

                yield _sse_event({
                    "type": "done",
                    "reply": full_reply,
                    "session_id": session_id,
                    "intent": "general_chat",
                    "mode": "cloud",
                    "token_count": first_token,
                    "elapsed": first_elapsed,
                })
                return

        except Exception as e:
            logger.error(f"[chat] 云端对话异常: {e}，降级到本地模式")

    # ── 云端未启用或异常 → 本地降级 ──
    logger.info("[chat] 使用本地兜底回复")
    full_reply = _local_fallback(message)
    _save_message(
        db, session_id, "assistant", full_reply,
        intent="general_chat", workflow_type="chat",
        is_final=True,
    )
    yield _sse_event({
        "type": "done",
        "reply": full_reply,
        "session_id": session_id,
        "intent": "general_chat",
        "mode": "local",
        "fallback": True,
    })
