"""通知调度服务 — 支持邮件和钉钉机器人通知发送

报告订阅生成后，根据订阅的 notify_method 和 notify_config 发送外部通知。
发送失败不影响主流程，仅记录日志。
"""

import json
import logging
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

# 确保通知日志能输出到控制台
logger = logging.getLogger("notification")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


def send_email(config: dict, report_data: dict) -> dict:
    """通过 SMTP 发送邮件通知

    Args:
        config: 邮件配置字典，包含 smtp_server, smtp_port, sender_email,
                auth_username, auth_password, use_tls, email_template
        report_data: 报告数据，包含 report_name, report_summary, report_time, device_count

    Returns:
        {"success": bool, "error": str or None}
    """
    smtp_server = config.get("smtp_server", "")
    smtp_port = config.get("smtp_port", 587)
    sender_email = config.get("sender_email", "")
    recipient_email = config.get("recipient_email", "")
    auth_username = config.get("auth_username", sender_email)
    auth_password = config.get("auth_password", "")
    use_tls = config.get("use_tls", True)
    email_template = config.get("email_template", "")

    if not smtp_server or not sender_email:
        return {"success": False, "error": "SMTP 配置不完整：缺少服务器地址或发送邮箱"}
    if not recipient_email:
        return {"success": False, "error": "未配置收件邮箱，请在订阅的邮件配置中填写收件邮箱"}

    report_name = report_data.get("report_name", "能耗分析报告")
    report_summary = report_data.get("report_summary", "")
    report_time = report_data.get("report_time", datetime.now().strftime("%Y-%m-%d %H:%M"))
    device_count = report_data.get("device_count", 0)
    report_id = report_data.get("report_id")

    # 构建邮件正文（使用模板或默认内容）
    if email_template:
        body = email_template.replace("{{report_name}}", report_name)
        body = body.replace("{{report_summary}}", report_summary)
        body = body.replace("{{report_time}}", report_time)
        body = body.replace("{{device_count}}", str(device_count))
    else:
        body = (
            f"尊敬的用户，您好：\n\n"
            f"报告「{report_name}」已生成完毕。\n"
            f"生成时间：{report_time}\n"
            f"报告摘要：{report_summary or '暂无摘要'}\n"
            f"分析设备数：{device_count} 台\n\n"
            f"请登录能耗智能管理优化平台查看详情。\n"
            f"—— 能耗智能管理优化平台"
        )

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = f"【能耗平台】报告「{report_name}」已生成"

        msg.attach(MIMEText(body, "plain", "utf-8"))

        # 连接 SMTP 服务器
        if use_tls:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)

        if auth_username and auth_password:
            server.login(auth_username, auth_password)

        # 发送邮件
        server.sendmail(sender_email, [recipient_email], msg.as_string())
        server.quit()

        logger.info(f"邮件发送成功: {report_name} -> {recipient_email}")
        return {"success": True, "error": None}

    except smtplib.SMTPAuthenticationError:
        err_msg = "SMTP 认证失败，请检查用户名和密码"
        logger.error(f"邮件发送失败: {err_msg}")
        return {"success": False, "error": err_msg}
    except smtplib.SMTPException as e:
        err_msg = f"SMTP 错误: {str(e)}"
        logger.error(f"邮件发送失败: {err_msg}")
        return {"success": False, "error": err_msg}
    except Exception as e:
        err_msg = f"邮件发送异常: {str(e)}"
        logger.error(f"邮件发送失败: {err_msg}")
        return {"success": False, "error": err_msg}


def send_dingtalk(config: dict, report_data: dict) -> dict:
    """通过钉钉机器人 Webhook 发送通知

    Args:
        config: 钉钉配置字典，包含 webhook_url, access_token, msg_template
        report_data: 报告数据，包含 report_name, report_summary, report_time, device_count

    Returns:
        {"success": bool, "error": str or None}
    """
    webhook_url = config.get("webhook_url", "")
    access_token = config.get("access_token", "")
    msg_template = config.get("msg_template", "")

    if not webhook_url:
        return {"success": False, "error": "钉钉 Webhook URL 未配置"}

    # 如果 access_token 存在但 URL 中未包含，追加到 URL
    if access_token and access_token not in webhook_url:
        separator = "&" if "?" in webhook_url else "?"
        webhook_url = f"{webhook_url}{separator}access_token={access_token}"

    report_name = report_data.get("report_name", "能耗分析报告")
    report_summary = report_data.get("report_summary", "")
    report_time = report_data.get("report_time", datetime.now().strftime("%Y-%m-%d %H:%M"))
    device_count = report_data.get("device_count", 0)

    # 构建消息文本
    if msg_template:
        text = msg_template.replace("{{report_name}}", report_name)
        text = text.replace("{{report_summary}}", report_summary)
        text = text.replace("{{report_time}}", report_time)
        text = text.replace("{{device_count}}", str(device_count))
    else:
        text = (
            f"### 📊 能耗分析报告\n\n"
            f"**报告名称**：{report_name}\n"
            f"**生成时间**：{report_time}\n"
            f"**报告摘要**：{report_summary or '暂无摘要'}\n"
            f"**分析设备数**：{device_count} 台\n\n"
            f"---\n"
            f"请登录平台查看详情。"
        )

    # 构建钉钉机器人消息体
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"能耗平台报告: {report_name}",
            "text": text,
        },
    }

    try:
        import httpx

        with httpx.Client(timeout=15) as client:
            resp = client.post(webhook_url, json=payload)
            result = resp.json()

        if resp.status_code == 200 and result.get("errcode") == 0:
            logger.info(f"钉钉通知发送成功: {report_name}")
            return {"success": True, "error": None}
        else:
            err_msg = result.get("errmsg", f"HTTP {resp.status_code}")
            logger.error(f"钉钉通知发送失败: {err_msg}")
            return {"success": False, "error": err_msg}

    except ImportError:
        err_msg = "httpx 未安装，无法发送钉钉通知"
        logger.error(err_msg)
        return {"success": False, "error": err_msg}
    except Exception as e:
        err_msg = f"钉钉通知发送异常: {str(e)}"
        logger.error(f"钉钉通知发送失败: {err_msg}")
        return {"success": False, "error": err_msg}


def dispatch_notification(subscription, report_data: dict) -> dict:
    """调度发送通知 — 根据订阅的 notify_method 选择合适的渠道

    Args:
        subscription: ReportSubscription ORM 对象
        report_data: 报告数据字典

    Returns:
        {"success": bool, "channel": str, "error": str or None}
    """
    method = subscription.notify_method or "system"

    if method == "system":
        # 系统通知已由调用方在数据库创建，无需额外操作
        return {"success": True, "channel": "system", "error": None}

    # 解析 notify_config JSON 字符串
    config_raw = subscription.notify_config
    if isinstance(config_raw, str):
        try:
            config = json.loads(config_raw)
        except json.JSONDecodeError as e:
            err_msg = f"通知配置 JSON 解析失败: {e}"
            logger.error(err_msg)
            return {"success": False, "channel": method, "error": err_msg}
    elif isinstance(config_raw, dict):
        config = config_raw
    else:
        config = {}

    if method == "email":
        result = send_email(config, report_data)
        return {**result, "channel": "email"}

    elif method == "dingtalk":
        result = send_dingtalk(config, report_data)
        return {**result, "channel": "dingtalk"}

    else:
        err_msg = f"未知的通知方式: {method}"
        logger.warning(err_msg)
        return {"success": False, "channel": method, "error": err_msg}
