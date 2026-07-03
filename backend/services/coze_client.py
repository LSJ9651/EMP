"""Coze SDK 封装 — 统一管理工作流和对话智能体调用

严格遵循 Coze 官方 Python SDK 示例规范：
https://github.com/coze-dev/coze-py
"""

import json
import time
import logging
from typing import Optional
from sqlalchemy.orm import Session

from cozepy import Coze, TokenAuth, COZE_CN_BASE_URL, Message, ChatStatus, MessageContentType, ChatEventType
from cozepy.request import SyncHTTPClient
from cozepy.exception import CozeAPIError
from services.ai_config_service import ai_config_service

logger = logging.getLogger(__name__)


class CozeClient:
    """Coze SDK 客户端，每次根据数据库配置动态创建"""

    @staticmethod
    def _build(db: Session) -> Optional[Coze]:
        """根据数据库配置构建 Coze 客户端，无有效 API Key 则返回 None"""
        api_key = ai_config_service.get_api_key(db)
        api_base = ai_config_service.get_api_base(db)

        if not api_key:
            logger.warning("[coze] API Key 未配置")
            return None

        return Coze(
            auth=TokenAuth(token=api_key),
            base_url=api_base or COZE_CN_BASE_URL,
            http_client=SyncHTTPClient(
                headers={"X-Coze-Client-Header": "energy-optimizer-platform"}
            ),
        )

    @staticmethod
    async def run_workflow(
        db: Session,
        service_type: str,
        parameters: dict,
    ) -> Optional[dict]:
        """执行 Coze 工作流（analyze / optimize）

        Args:
            db: 数据库会话
            service_type: analyze / optimize
            parameters: 工作流入参

        Returns:
            工作流执行结果 dict，失败返回 None
        """
        coze = CozeClient._build(db)
        if not coze:
            return None

        workflow_id = ai_config_service.get_service_id(db, service_type)
        if not workflow_id:
            logger.warning(f"[coze] {service_type} workflow_id 未配置")
            return None

        timeout = ai_config_service.get_service_timeout(db, service_type)

        start_ts = time.time()
        logger.warning(f"[coze] 调用工作流 {service_type}: workflow_id={workflow_id}, 超时={timeout}s")

        # 打印完整的请求参数（仅参数名称和顶层结构，避免日志过长）
        param_keys = list(parameters.keys())
        param_shapes = {}
        for k, v in parameters.items():
            if isinstance(v, list):
                param_shapes[k] = f"Array[{len(v)}]"
                if v and isinstance(v[0], dict):
                    param_shapes[k] = f"Array[Object] x{len(v)}, fields={list(v[0].keys())}"
            elif isinstance(v, dict):
                param_shapes[k] = f"Object, fields={list(v.keys())}"
            elif isinstance(v, str) and len(v) > 50:
                param_shapes[k] = f'String(truncated, len={len(v)})'
            else:
                param_shapes[k] = f"{type(v).__name__}={v}"
        logger.warning(f"[coze] 工作流 {service_type} 入参结构: {param_shapes}")
        logger.warning(f"[coze] 工作流 {service_type} 完整入参 JSON: {json.dumps(parameters, ensure_ascii=False, default=str)[:2000]}")

        try:
            workflow_run = coze.workflows.runs.create(
                workflow_id=workflow_id,
                parameters=parameters,
            )
            elapsed = round(time.time() - start_ts, 2)
            logger.info(f"[coze] 工作流 {service_type} 执行成功, 耗时: {elapsed}s")
            return {"data": workflow_run.data, "execute_id": workflow_run.execute_id}
        except CozeAPIError as e:
            elapsed = round(time.time() - start_ts, 2)
            logger.error(
                f"[coze] 工作流 {service_type} 执行失败 (耗时{elapsed}s): code={e.code}, msg={e.msg}, logid={e.logid}"
            )
            if e.debug_url:
                logger.error(
                    f"[coze] 调试链接: {e.debug_url}\n"
                    f"[coze] 请在浏览器中打开上述链接，检查 Coze 工作流 Start 节点的实际参数名称是否与发送的键名一致：{param_keys}"
                )
            raise
        except Exception as e:
            elapsed = round(time.time() - start_ts, 2)
            logger.error(f"[coze] 工作流 {service_type} 执行失败 (耗时{elapsed}s): {e}")
            raise

    @staticmethod
    async def chat(
        db: Session,
        message: str,
        session_id: str,
    ) -> Optional[str]:
        """调用 Coze 对话智能体（轮询模式，保留兼容）

        Args:
            db: 数据库会话
            message: 用户消息
            session_id: 会话ID

        Returns:
            智能体回复文本，失败返回 None
        """
        coze = CozeClient._build(db)
        if not coze:
            return None

        bot_id = ai_config_service.get_service_id(db, "chat")
        if not bot_id:
            logger.warning("[coze] chat bot_id 未配置")
            return None

        timeout = ai_config_service.get_service_timeout(db, "chat")

        start_ts = time.time()
        logger.info(f"[coze] 调用对话智能体: bot_id={bot_id}, 超时={timeout}s")

        try:
            chat_result = coze.chat.create_and_poll(
                bot_id=bot_id,
                user_id=session_id,
                additional_messages=[
                    Message.build_user_question_text(message),
                ],
            )
            elapsed = round(time.time() - start_ts, 2)
            logger.info(f"[coze] 对话智能体响应成功, 耗时: {elapsed}s")

            if chat_result and chat_result.messages:
                for msg in chat_result.messages:
                    if msg.role == "assistant" and msg.content:
                        return msg.content
            return str(chat_result) if chat_result else None
        except Exception as e:
            elapsed = round(time.time() - start_ts, 2)
            logger.error(f"[coze] 对话智能体失败 (耗时{elapsed}s): {e}")
            raise

    @staticmethod
    def chat_stream(
        db: Session,
        message: str,
        session_id: str,
    ):
        """流式对话 — 按 Coze 官方 streaming 接口

        使用 coze.chat.stream() 迭代事件，处理 DELTA/COMPLETED/FAILED

        Yields:
            dict: {"type": "delta", "content": "..."}
                  {"type": "done", "token_count": N, "elapsed": S}
                  {"type": "error", "message": "..."}
        """
        coze = CozeClient._build(db)
        if not coze:
            yield {"type": "error", "message": "Coze 客户端初始化失败"}
            return

        bot_id = ai_config_service.get_service_id(db, "chat")
        if not bot_id:
            logger.warning("[coze] chat bot_id 未配置")
            yield {"type": "error", "message": "对话智能体 Bot ID 未配置"}
            return

        start_ts = time.time()
        logger.info(f"[coze] 流式对话: bot_id={bot_id}")

        try:
            for event in coze.chat.stream(
                bot_id=bot_id,
                user_id=session_id,
                additional_messages=[
                    Message.build_user_question_text(message),
                ],
            ):
                # 官方示例：event.message.content 直接作为字符串使用
                # print(event.message.content, end="", flush=True)
                if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
                    content = event.message.content if event.message else ""
                    if content:
                        yield {"type": "delta", "content": content}

                # 官方示例：event.chat.usage.token_count 获取 token 用量
                if event.event == ChatEventType.CONVERSATION_CHAT_COMPLETED:
                    elapsed = round(time.time() - start_ts, 2)
                    token_count = event.chat.usage.token_count if event.chat and event.chat.usage else 0
                    logger.info(f"[coze] 流式对话完成, 耗时: {elapsed}s, tokens: {token_count}")
                    yield {"type": "done", "token_count": token_count, "elapsed": elapsed}
                    return

                if event.event == ChatEventType.CONVERSATION_CHAT_FAILED:
                    logger.error(f"[coze] 流式对话失败, status: {event.chat.status if event.chat else 'unknown'}")
                    yield {"type": "error", "message": f"对话失败, 状态: {event.chat.status if event.chat else 'unknown'}"}
                    return

        except Exception as e:
            elapsed = round(time.time() - start_ts, 2)
            logger.error(f"[coze] 流式对话异常 (耗时{elapsed}s): {e}")
            yield {"type": "error", "message": str(e)}

    @staticmethod
    async def test_connection(
        db: Session,
        service_type: str,
    ) -> dict:
        """测试连接：使用 Coze SDK 验证 API Key + workflow_id/bot_id 连通性

        使用 Coze SDK 的轻量检索 API（bots.retrieve / workflows.retrieve）
        验证 ID 的有效性，无需创建实际对话或运行工作流。

        Args:
            db: 数据库会话
            service_type: analyze / optimize / chat

        Returns:
            dict: {"status": "connected"|"failed"|"unknown",
                   "response_time_ms": int,
                   "status_code": int|None,
                   "error_message": str|None}
        """
        import asyncio

        coze = CozeClient._build(db)
        if not coze:
            return {
                "status": "unknown",
                "response_time_ms": None,
                "status_code": None,
                "error_message": "API Key 未配置",
            }

        service_id = ai_config_service.get_service_id(db, service_type)
        if not service_id:
            return {
                "status": "unknown",
                "response_time_ms": None,
                "status_code": None,
                "error_message": "工作流/Bot ID 未配置",
            }

        start_ts = time.time()

        try:
            if service_type == "chat":
                # 使用 bots.retrieve 轻量验证 bot_id 是否存在
                # 比 create_and_poll 更快速，避免创建实际对话
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    lambda: coze.bots.retrieve(
                        bot_id=service_id,
                    ),
                )
            else:
                # 使用 workflows.retrieve 轻量验证 workflow_id
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    lambda: coze.workflows.retrieve(
                        workflow_id=service_id,
                    ),
                )

            elapsed_ms = int((time.time() - start_ts) * 1000)
            return {
                "status": "connected",
                "response_time_ms": elapsed_ms,
                "status_code": 200,
                "error_message": None,
            }

        except CozeAPIError as e:
            elapsed_ms = int((time.time() - start_ts) * 1000)
            error_msg = e.msg or str(e)
            logid = getattr(e, 'logid', None)
            logger.warning(
                f"[coze] test_connection CozeAPIError: code={e.code}, msg={error_msg}, logid={logid}"
            )
            # 根据 Coze SDK 错误信息判断具体原因
            if any(word in error_msg.lower() for word in ["not found", "invalid", "not exist"]):
                return {
                    "status": "failed",
                    "response_time_ms": elapsed_ms,
                    "status_code": e.code,
                    "error_message": "工作流/Bot ID 不存在",
                }
            # 401/403 表示 API Key 问题
            if e.code in (401, 403):
                return {
                    "status": "failed",
                    "response_time_ms": elapsed_ms,
                    "status_code": e.code,
                    "error_message": "API Key 无效或未授权",
                }
            return {
                "status": "failed",
                "response_time_ms": elapsed_ms,
                "status_code": e.code,
                "error_message": f"Coze API 错误: {error_msg}",
            }

        except Exception as e:
            elapsed_ms = int((time.time() - start_ts) * 1000)
            logger.error(f"[coze] test_connection 异常: {e}")
            return {
                "status": "failed",
                "response_time_ms": elapsed_ms,
                "status_code": None,
                "error_message": str(e),
            }
