"""工具调用处理器 — 处理智能体发出的工具调用指令"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from sqlalchemy.orm import Session
from services.device_matcher import DeviceMatcher
from models import Device

logger = logging.getLogger(__name__)

# 全量分析关键字（智能体可能返回这些词表示分析所有设备）
ALL_DEVICES_KEYWORDS = {"全部", "所有", "全部设备", "所有设备", "all", "全"}


class ToolResult:
    """工具执行结果"""

    def __init__(self, success: bool = False, result: dict = None, error: str = None,
                 match_status: dict = None):
        self.success = success
        self.result = result or {}
        self.error = error
        self.match_status = match_status or {}

    def to_dict(self):
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "match_status": self.match_status,
        }


class ToolHandler:
    """处理智能体发出的工具调用指令

    支持工具：
      - analyze_energy: 调用能耗分析工作流
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.device_matcher = DeviceMatcher(db_session)

    async def execute(self, tool_type: str, params: dict, db: Session = None) -> ToolResult:
        """执行工具调用"""
        if tool_type not in ("analyze_energy",):
            return ToolResult(
                success=False,
                error=f"不支持的工具类型: {tool_type}",
            )

        try:
            return await self._handle_analyze_energy(params, db or self.db)
        except Exception as e:
            logger.error(f"[tool_handler] 工具执行异常: {e}")
            return ToolResult(success=False, error=str(e))

    async def _handle_analyze_energy(self, params: dict, db: Session) -> ToolResult:
        """处理能耗分析请求

        流程：
          1. 提取 device_names 列表（归一化：string → list）
          2. 检测是否为全量分析请求（["全部"] 等关键字）
          3. 是 → 查询全部设备直接分析；否 → DeviceMatcher 匹配后分析
          4. 返回分析结果 + 匹配状态
        """
        raw_device_names = params.get("device_names", [])
        time_range = params.get("time_range", "today")

        # ── Bugfix: 归一化 device_names（Bar → 字符串 → "全部" 会迭代字符而非列表元素）
        device_names = self._normalize_device_names(raw_device_names)
        logger.info(f"[tool_handler] 收到能耗分析请求: raw={raw_device_names}, normalized={device_names}, time_range={time_range}")

        # ── 1. 检测是否为全量分析请求 ──
        if self._is_all_devices_request(device_names):
            logger.info("[tool_handler] 检测到全量分析请求，跳过设备匹配，查询所有设备")
            all_devices = db.query(Device).all()
            if not all_devices:
                return ToolResult(
                    success=False,
                    error="系统中暂无设备数据。",
                    match_status={"total": len(device_names), "matched": {}, "can_proceed": False},
                )
            device_ids = [d.id for d in all_devices]
            matched_names = [d.name for d in all_devices]
            logger.info(f"[tool_handler] 全量设备查询结果: device_ids={device_ids}, names={matched_names}, count={len(all_devices)}")
            match_dict = {
                "total": len(device_names),
                "matched": {name: did for name, did in zip(matched_names, device_ids)},
                "fuzzy_matched": {},
                "unmatched": [],
                "needs_confirmation": False,
                "confirmation_message": None,
                "can_proceed": True,
            }
            match_requested = len(device_names)
        else:
            # ── 2. 设备名称匹配 ──
            match_result = self.device_matcher.match(device_names)
            match_dict = match_result.to_dict()

            if not match_result.can_proceed:
                return ToolResult(
                    success=False,
                    error=match_result.confirmation_message or "设备名称匹配失败，请确认后重试。",
                    match_status=match_dict,
                )

            device_ids = list(match_result.matched.values())
            matched_names = list(match_result.matched.keys())
            match_requested = match_result.total

        # ── 3. 解析时间范围 ──
        start_time, end_time = self._parse_time_range(time_range)

        # ── 4. 调用能耗分析工作流 ──
        try:
            from services.agent_adapter import analyze_energy
            analysis_result = await analyze_energy(
                device_id=device_ids[0] if len(device_ids) == 1 else device_ids,
                start_time=start_time,
                end_time=end_time,
                db=db,
            )

            # 验证：分析结果应包含所有设备的数据
            analyzed_count = analysis_result.get("analyzed_devices", 0) if analysis_result else 0
            if analyzed_count != len(device_ids):
                logger.warning(f"[tool_handler] 全量分析结果设备数({analyzed_count})与请求数({len(device_ids)})不匹配，可能未完整执行")

            formatted = self._format_analysis_for_agent(analysis_result, device_ids)
            logger.info(f"[tool_handler] 能耗分析完成: device_count={len(device_ids)}, analyzed_devices={analyzed_count}, mode={formatted.get('mode')}")

            return ToolResult(
                success=True,
                result={
                    "status": "success",
                    "device_ids": device_ids,
                    "device_count": len(device_ids),
                    "match_result": {
                        "matched_names": matched_names,
                        "total_requested": match_requested,
                    },
                    "time_range": time_range,
                    "analysis_result": formatted,
                    "generated_at": datetime.now().isoformat(),
                },
                match_status=match_dict,
            )

        except Exception as e:
            logger.error(f"[tool_handler] 工作流调用失败: {e}")
            return ToolResult(
                success=False,
                error=f"能耗分析工作流执行失败: {e}",
                match_status=match_dict,
            )

    @staticmethod
    def _normalize_device_names(names: List) -> List[str]:
        """归一化 device_names 为字符串列表

        修复 Bug #1: Coze Bot 可能返回 string("全部") 而非 Array(["全部"])
        """
        if not names:
            return []
        if isinstance(names, str):
            # 字符串 → 单元素列表
            return [names]
        if isinstance(names, (list, tuple)):
            return [str(n) for n in names if n]
        return [str(names)]

    @staticmethod
    def _is_all_devices_request(device_names: List[str]) -> bool:
        """检测 device_names 是否全部为全量分析关键字（如 "全部"）

        修复 Bug #1: 已通过 _normalize_device_names 归一化输入，
        此处确保 ALL_DEVICES_KEYWORDS 的匹配健壮性。
        """
        if not device_names:
            return False
        for name in device_names:
            stripped = name.strip().lower()
            if stripped not in ALL_DEVICES_KEYWORDS:
                logger.debug(f"[tool_handler] 非全量关键字: '{stripped}' (不在 {ALL_DEVICES_KEYWORDS})")
                return False
        logger.info(f"[tool_handler] 全量分析请求确认: {device_names}")
        return True

    def _parse_time_range(self, time_range: str) -> tuple:
        """解析时间范围字符串"""
        now = datetime.now()
        if time_range == "today":
            return (now.replace(hour=0, minute=0, second=0).isoformat(),
                    now.isoformat())
        elif time_range == "yesterday":
            from datetime import timedelta
            yesterday = now - timedelta(days=1)
            return (yesterday.replace(hour=0, minute=0, second=0).isoformat(),
                    yesterday.replace(hour=23, minute=59, second=59).isoformat())
        elif time_range == "this_week":
            from datetime import timedelta
            monday = now - timedelta(days=now.weekday())
            return (monday.replace(hour=0, minute=0, second=0).isoformat(),
                    now.isoformat())
        else:
            return (None, None)

    def _format_analysis_for_agent(self, analysis_result: dict, device_ids: list) -> dict:
        """格式化分析结果为智能体可读的摘要"""
        if not analysis_result:
            return {"error": "分析结果为空"}

        return {
            "summary": analysis_result.get("summary", "无摘要"),
            "anomalies": analysis_result.get("anomalies", []),
            "suggestions": analysis_result.get("suggestions", []),
            "total_power_avg": analysis_result.get("total_power_avg", 0),
            "analyzed_devices": len(device_ids),
            "mode": analysis_result.get("_mode", "unknown"),
        }
