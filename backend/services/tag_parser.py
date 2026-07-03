"""标签解析器 — 解析智能体回复中的 <INTERNAL_CMD> 标签"""

import json
import re
import logging

logger = logging.getLogger(__name__)

# 标签正则：匹配 <INTERNAL_CMD>...</INTERNAL_CMD>
_TAG_RE = re.compile(r"<INTERNAL_CMD>\s*([\s\S]*?)\s*</INTERNAL_CMD>", re.IGNORECASE)

# 工具类型白名单
SUPPORTED_TOOLS = {"analyze_energy"}


class ParseResult:
    """标签解析结果"""

    def __init__(self):
        self.has_tag = False
        self.clean_content = ""  # 移除标签后的纯净文本
        self.tag_content = None  # 标签 JSON 内容
        self.tool_type = None    # 工具类型
        self.tool_params = None  # 工具参数
        self.request_id = None   # 请求ID


class TagParser:
    """解析智能体回复中的特殊标签"""

    def parse(self, content: str) -> ParseResult:
        """
        解析文本中的 <INTERNAL_CMD> 标签

        返回 ParseResult：
          - has_tag: bool 是否包含标签
          - clean_content: str 移除标签后的纯净文本
          - tag_content: dict 标签内的 JSON
          - tool_type: str 工具类型
          - tool_params: dict 工具参数
        """
        result = ParseResult()

        if not content:
            result.clean_content = content or ""
            return result

        match = _TAG_RE.search(content)
        if not match:
            result.clean_content = content
            return result

        result.has_tag = True
        result.clean_content = _TAG_RE.sub("", content).strip()

        tag_str = match.group(1).strip()
        try:
            tag_json = json.loads(tag_str)
            result.tag_content = tag_json
            result.tool_type = tag_json.get("tool", "")
            result.tool_params = tag_json.get("parameters", {})
            result.request_id = tag_json.get("request_id", "")

            if result.tool_type not in SUPPORTED_TOOLS:
                logger.warning(f"[tag_parser] 不支持的工具类型: {result.tool_type}，将忽略标签")
                result.has_tag = False
                result.clean_content = content  # 保留原文

        except json.JSONDecodeError as e:
            logger.warning(f"[tag_parser] 标签内容 JSON 解析失败: {e}")
            result.has_tag = False
            result.clean_content = content  # 解析失败，保留原文展示

        return result

    def clean_response(self, content: str) -> str:
        """移除所有内部标签，仅保留展示内容"""
        return _TAG_RE.sub("", content).strip()

    @staticmethod
    def has_internal_tag(content: str) -> bool:
        """快速检查文本是否包含标签（不解析内容）"""
        return bool(_TAG_RE.search(content or ""))


# 单例
tag_parser = TagParser()
