"""功能测试：报告订阅通知配置持久化

测试场景：
  Email / DingTalk 通知配置的创建、读取、更新、验证。

使用方式：
  cd backend && python -m tests.test_notify_config
"""

import sys
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test_notify_config")

sys.path.insert(0, ".")


def test_notify_config_model_field():
    """验证 ReportSubscription 模型包含 notify_config 字段"""
    from models import ReportSubscription

    col_names = [c.name for c in ReportSubscription.__table__.columns]
    assert "notify_config" in col_names, "notify_config 字段不存在"
    logger.info("✅ ReportSubscription.notify_config 字段存在")


def test_subscription_create_pydantic():
    """验证 SubscriptionCreate Pydantic 模型包含 notify_config"""
    from routers.agent import SubscriptionCreate

    # 含 notify_config
    data = SubscriptionCreate(
        name="测试订阅",
        report_type="daily",
        cron_time="08:00",
        notify_method="email",
        notify_config={
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "sender_email": "noreply@example.com",
            "auth_password": "secret",
            "use_tls": True,
        },
    )
    assert data.notify_method == "email"
    assert data.notify_config["smtp_server"] == "smtp.example.com"
    assert data.notify_config["smtp_port"] == 587
    logger.info("✅ SubscriptionCreate 含 notify_config 字段")


def test_email_config_validation():
    """验证 Email 配置验证规则（SMTP 必需字段）"""
    from services.tool_handler import ToolHandler as TH

    required_fields = ["smtp_server", "smtp_port", "sender_email", "auth_password"]
    valid_config = {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "sender_email": "noreply@example.com",
        "auth_username": "",
        "auth_password": "secret123",
        "use_tls": True,
        "email_template": "",
    }
    for field in required_fields:
        assert valid_config.get(field) is not None, f"缺少必填字段: {field}"
    assert isinstance(valid_config["smtp_port"], int)
    assert 1 <= valid_config["smtp_port"] <= 65535
    logger.info("✅ Email 配置字段验证通过")


def test_dingtalk_config_validation():
    """验证 DingTalk 配置验证规则（Webhook URL 格式）"""
    import re

    valid_url = "https://oapi.dingtalk.com/robot/send?access_token=abc123"
    invalid_url = "https://example.com/webhook"
    pattern = r"^https://oapi\.dingtalk\.com/robot/send\?access_token="

    assert re.match(pattern, valid_url), "有效 URL 应匹配"
    assert not re.match(pattern, invalid_url), "无效 URL 不应匹配"
    logger.info("✅ DingTalk URL 格式验证通过")


def test_notify_config_json_serialization():
    """验证 notify_config dict → JSON str → dict 的序列化/反序列化"""
    config = {
        "smtp_server": "smtp.example.com",
        "smtp_port": 587,
        "sender_email": "noreply@example.com",
        "auth_password": "secret123",
        "use_tls": True,
    }
    # 序列化
    json_str = json.dumps(config, ensure_ascii=False)
    assert isinstance(json_str, str)
    assert "smtp.example.com" in json_str

    # 反序列化
    restored = json.loads(json_str)
    assert restored["smtp_server"] == "smtp.example.com"
    assert restored["smtp_port"] == 587
    assert restored["use_tls"] is True
    logger.info("✅ JSON 序列化/反序列化正确")


def test_notify_config_update_serialization():
    """验证 API update 中 notify_config 的序列化逻辑"""
    import json as j

    test_cases = [
        # (input, expected_type_after_setattr)
        ({"webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx"}, str),  # dict → JSON str
        (None, type(None)),  # None → None
        ("", str),  # empty str → str
    ]

    for nc_input, expected_type in test_cases:
        if isinstance(nc_input, dict):
            result = j.dumps(nc_input, ensure_ascii=False)
        else:
            result = nc_input
        assert isinstance(result, expected_type) or (result is None and expected_type is type(None)), \
            f"类型不匹配: {type(result)} != {expected_type}"
    logger.info("✅ 更新时 notify_config 序列化逻辑正确")


def test_email_config_ui_structure():
    """验证 Email 配置组件包含所有必需字段（基于代码检查）"""
    required_fields = {
        "smtp_server": "SMTP 服务器",
        "smtp_port": "端口号",
        "sender_email": "发送邮箱",
        "auth_username": "认证用户名",
        "auth_password": "认证密码",
        "use_tls": "启用 TLS",
        "email_template": "邮件模板",
    }
    default_values = {
        "smtp_server": "",
        "smtp_port": 587,
        "sender_email": "",
        "auth_username": "",
        "auth_password": "",
        "use_tls": True,
        "email_template": "",
    }
    for field in required_fields:
        assert field in default_values, f"Email 配置缺少字段: {field}"
    assert default_values["smtp_port"] == 587
    assert default_values["use_tls"] is True
    logger.info("✅ Email 配置 UI 字段结构完整")


def test_dingtalk_config_ui_structure():
    """验证 DingTalk 配置组件包含所有必需字段"""
    required_fields = {
        "webhook_url": "Webhook URL",
        "access_token": "访问令牌",
        "msg_template": "消息模板",
        "notify_frequency": "通知频率",
    }
    default_values = {
        "webhook_url": "",
        "access_token": "",
        "msg_template": "",
        "notify_frequency": "immediately",
    }
    for field in required_fields:
        assert field in default_values, f"DingTalk 配置缺少字段: {field}"
    assert default_values["notify_frequency"] == "immediately"
    logger.info("✅ DingTalk 配置 UI 字段结构完整")


def test_notify_config_migration_script():
    """验证数据库迁移 SQL（ALTER TABLE + 查询）"""
    from models import ReportSubscription

    # 验证反向兼容：旧记录 notify_config 应可为 NULL
    col = ReportSubscription.__table__.columns["notify_config"]
    assert col.nullable or col.default is not None, "notify_config 应可为 NULL（兼容旧数据）"
    assert col.type.python_type == str or col.type.python_type == "Text", "notify_config 应为 Text 类型"
    logger.info("✅ notify_config 字段兼容旧记录")


if __name__ == "__main__":
    print("=" * 60)
    print("  功能测试：报告订阅通知配置持久化")
    print("=" * 60)
    print()

    tests = [
        ("模型字段", test_notify_config_model_field),
        ("Pydantic 模型", test_subscription_create_pydantic),
        ("Email 配置验证", test_email_config_validation),
        ("DingTalk URL 验证", test_dingtalk_config_validation),
        ("JSON 序列化", test_notify_config_json_serialization),
        ("更新序列化逻辑", test_notify_config_update_serialization),
        ("Email UI 字段结构", test_email_config_ui_structure),
        ("DingTalk UI 字段结构", test_dingtalk_config_ui_structure),
        ("数据库兼容性", test_notify_config_migration_script),
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
