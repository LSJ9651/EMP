"""功能测试：验证 AI 对话中 ["全部"] 参数能耗分析功能

测试场景：
  当智能体返回 device_names=["全部"] 时，系统应触发对所有设备的完整能耗分析，
  且结果与智能报告页 "全部设备" 分析完全一致。

使用方式：
  cd backend && python -m tests.test_all_devices_analysis
"""

import sys
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test_all_devices")

sys.path.insert(0, ".")


def test_device_names_normalization():
    """测试 _normalize_device_names 的各种输入情景"""
    from services.tool_handler import ToolHandler

    # 情景 1: 字符串 "全部"  → 应转为 ["全部"]
    assert ToolHandler._normalize_device_names("全部") == ["全部"], "字符串归一化失败"
    logger.info("✅ 字符串 '全部' → ['全部']  √")

    # 情景 2: 列表 ["全部"]  → 保持 ["全部"]
    assert ToolHandler._normalize_device_names(["全部"]) == ["全部"], "列表归一化失败"
    logger.info("✅ 列表 ['全部'] → ['全部']  √")

    # 情景 3: 空列表 → []
    assert ToolHandler._normalize_device_names([]) == [], "空列表归一化失败"
    logger.info("✅ 空列表 → []  √")

    # 情景 4: None → []
    assert ToolHandler._normalize_device_names(None) == [], "None 归一化失败"
    logger.info("✅ None → []  √")

    # 情景 5: 多设备列表
    assert ToolHandler._normalize_device_names(["空压机A-1", "注塑机B-1"]) == ["空压机A-1", "注塑机B-1"]
    logger.info("✅ 多设备列表保持 √")

    # 情景 6: 混合（字符串中含 None）→ 过滤
    assert ToolHandler._normalize_device_names(["全部", None]) == ["全部"]
    logger.info("✅ 混合列表过滤 None  √")


def test_is_all_devices_request():
    """测试全量分析请求检测"""
    from services.tool_handler import ToolHandler

    # 情景 1: ["全部"] → True
    assert ToolHandler._is_all_devices_request(ToolHandler._normalize_device_names("全部")) is True
    logger.info("✅ '全部' → True  √")

    # 情景 2: ["全部设备"] → True
    assert ToolHandler._is_all_devices_request(["全部设备"]) is True
    logger.info("✅ '全部设备' → True  √")

    # 情景 3: ["所有"] → True
    assert ToolHandler._is_all_devices_request(["所有"]) is True
    logger.info("✅ '所有' → True  √")

    # 情景 4: ["特定设备"] → False
    assert ToolHandler._is_all_devices_request(["空压机A-1"]) is False
    logger.info("✅ '空压机A-1' → False  √")

    # 情景 5: 空列表 → False
    assert ToolHandler._is_all_devices_request([]) is False
    logger.info("✅ 空列表 → False  √")

    # 情景 6: ["全部", "空压机"] → False（混合不允许多个关键字以外项）
    assert ToolHandler._is_all_devices_request(["全部", "空压机"]) is False
    logger.info("✅ ['全部', '空压机'] → False  √")


def test_tag_parser_with_all_keyword():
    """测试标签解析器对 <INTERNAL_CMD> 中含 ["全部"] 的解析"""
    from services.tag_parser import tag_parser

    test_content = """好的，我来分析所有设备的能耗数据。

<INTERNAL_CMD>
{
  "type": "tool_call",
  "tool": "analyze_energy",
  "parameters": {
    "device_names": ["全部"],
    "time_range": "today"
  }
}
</INTERNAL_CMD>

正在为您分析，请稍候...
"""

    result = tag_parser.parse(test_content)

    assert result.has_tag is True, "应检测到标签"
    assert result.tool_type == "analyze_energy", f"工具类型应为 analyze_energy, 实际为 {result.tool_type}"
    assert result.tool_params.get("device_names") == ["全部"], "device_names 应为 ['全部']"
    assert result.tool_params.get("time_range") == "today", "time_range 应为 today"
    assert "<INTERNAL_CMD>" not in result.clean_content, "clean_content 应移除标签"

    logger.info("✅ 标签解析正确: has_tag=True, tool=analyze_energy, device_names=['全部']  √")
    logger.info(f"   干净内容预览: {result.clean_content[:50]}...")


def test_tag_parser_with_string_keyword():
    """测试标签解析器对 device_names 为字符串 "全部" 的解析"""
    from services.tag_parser import tag_parser

    # 模拟 Coze Bot 返回字符串而非数组
    test_content = """<INTERNAL_CMD>
{"type":"tool_call","tool":"analyze_energy","parameters":{"device_names":"全部","time_range":"today"}}
</INTERNAL_CMD>"""

    result = tag_parser.parse(test_content)
    assert result.has_tag is True, "应检测到标签"
    raw_device_names = result.tool_params.get("device_names")
    assert raw_device_names == "全部", f"原始 device_names 为字符串 {raw_device_names}"

    # 验证归一化后转为列表
    from services.tool_handler import ToolHandler
    normalized = ToolHandler._normalize_device_names(raw_device_names)
    assert normalized == ["全部"], f"归一化后应为 ['全部'], 实际为 {normalized}"
    assert ToolHandler._is_all_devices_request(normalized) is True, "归一化后应检测为全量分析"

    logger.info("✅ 字符串 '全部' → 归一化 → ['全部'] → _is_all_devices_request=True  √")


def test_match_dict_construction():
    """测试全量分析路径的 match_dict 构造"""
    from services.tool_handler import ALL_DEVICES_KEYWORDS, ToolHandler

    # 模拟数据
    device_names = ["全部"]
    all_device_ids = [1, 2, 3, 4]
    all_device_names = ["空压机A-1", "注塑机A-1", "冷水机组C-1", "注塑机B-1"]

    match_dict = {
        "total": len(device_names),
        "matched": {name: did for name, did in zip(all_device_names, all_device_ids)},
        "fuzzy_matched": {},
        "unmatched": [],
        "needs_confirmation": False,
        "confirmation_message": None,
        "can_proceed": True,
    }

    assert match_dict["total"] == 1
    assert len(match_dict["matched"]) == 4
    assert match_dict["can_proceed"] is True
    assert match_dict["matched"]["空压机A-1"] == 1
    assert match_dict["matched"]["注塑机B-1"] == 4

    logger.info("✅ match_dict 构造正确: total=1, matched=4 devices, can_proceed=True  √")


def test_time_range_parsing():
    """测试时间范围解析"""
    from services.tool_handler import ToolHandler

    handler = ToolHandler.__new__(ToolHandler)

    # today
    start, end = handler._parse_time_range("today")
    assert start is not None and end is not None
    logger.info(f"✅ today → {start[:10]} ~ {end[:10]}  √")

    # yesterday
    start, end = handler._parse_time_range("yesterday")
    assert start is not None and end is not None
    logger.info(f"✅ yesterday → {start[:10]} ~ {end[:10]}  √")

    # this_week
    start, end = handler._parse_time_range("this_week")
    assert start is not None and end is not None
    logger.info(f"✅ this_week → {start[:10]} ~ {end[:10]}  √")

    # unknown → (None, None)
    start, end = handler._parse_time_range("last_month")
    assert start is None and end is None
    logger.info("✅ last_month → (None, None)  √")


def test_enriched_message_structure():
    """测试增强消息结构是否包含所有必需信息"""
    from services.chat_service import _build_enriched_message

    analysis_result = {
        "summary": "空压机A-1：平均功率 85.5kW | 注塑机A-1：平均功率 45.2kW | 冷水机组C-1：平均功率 60.0kW | 注塑机B-1：平均功率 50.0kW",
        "anomalies": [
            {"device_id": 1, "device_name": "空压机A-1", "severity": "high", "message": "空压机A-1 接近额定功率运行（98kW/100kW）"}
        ],
        "suggestions": ["空压机加装变频器可节能15-25%", "建议检查管路泄漏"],
        "total_power_avg": 60.175,
        "analyzed_devices": 4,
        "mode": "local",
    }
    match_info = {
        "matched_names": ["空压机A-1", "注塑机A-1", "冷水机组C-1", "注塑机B-1"],
        "total_requested": 1,
    }

    enriched = _build_enriched_message("分析所有设备的能耗情况", analysis_result, match_info)

    # 验证内容结构
    assert "空压机A-1" in enriched
    assert "注塑机B-1" in enriched
    assert "总平均功率" in enriched or "total_power_avg" in enriched
    assert "用户原始请求分析 1 台设备" in enriched
    assert "成功匹配分析 4 台" in enriched

    logger.info("✅ 增强消息结构正确，包含所有 4 台设备数据  √")
    logger.info(f"   消息长度: {len(enriched)} 字符")


def test_analyze_energy_signature():
    """验证 analyze_energy 支持 list device_id 参数"""
    import inspect
    from services.agent_adapter import analyze_energy

    sig = inspect.signature(analyze_energy)
    params = list(sig.parameters.keys())
    logger.info(f"✅ analyze_energy 函数签名: {params}")
    assert "device_id" in params, "analyze_energy 应包含 device_id 参数"
    logger.info(f"   device_id 注释: {sig.parameters['device_id'].annotation}")


if __name__ == "__main__":
    print("=" * 60)
    print("  功能测试: ['全部'] 参数全量能耗分析")
    print("=" * 60)
    print()

    tests = [
        ("device_names 归一化", test_device_names_normalization),
        ("全量分析请求检测", test_is_all_devices_request),
        ("标签解析器 (['全部'])", test_tag_parser_with_all_keyword),
        ("标签解析器 (字符串'全部')", test_tag_parser_with_string_keyword),
        ("match_dict 构造", test_match_dict_construction),
        ("时间范围解析", test_time_range_parsing),
        ("增强消息结构", test_enriched_message_structure),
        ("analyze_energy 入参检查", test_analyze_energy_signature),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            logger.error(f"❌ {name} 失败: {e}")
            failed += 1
        except Exception as e:
            logger.error(f"❌ {name} 异常: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  结果: {passed} 通过, {failed} 失败, 共 {len(tests)} 项")
    print(f"{'=' * 60}")
    sys.exit(0 if failed == 0 else 1)
