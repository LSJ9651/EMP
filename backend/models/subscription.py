"""订阅与通知模型 — ReportSubscription, Notification"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from .base import Base


class ReportSubscription(Base):
    """报告订阅配置表"""
    __tablename__ = "report_subscriptions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="订阅名称")
    report_type = Column(String(20), nullable=False, comment="报告类型：daily/weekly/analysis")
    cron_time = Column(String(5), nullable=False, comment="定时执行时间 HH:MM")
    device_ids = Column(String(500), comment="目标设备ID列表，逗号分隔")
    is_active = Column(Boolean, default=True, comment="是否启用")
    notify_method = Column(String(20), default="system", comment="通知方式：system/email/dingtalk")
    notify_config = Column(Text, comment="通知配置 JSON")
    last_run_at = Column(DateTime, comment="上次执行时间")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Notification(Base):
    """系统通知表 — 消息中心数据源"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False, comment="通知标题")
    content = Column(Text, default="", comment="通知内容")
    category = Column(String(20), default="system", comment="分类：subscription/alert/report/system")
    source_type = Column(String(20), comment="来源类型：subscription/alert_report")
    source_id = Column(Integer, comment="关联的业务记录ID")
    is_read = Column(Boolean, default=False, comment="是否已读")
    created_at = Column(DateTime, default=datetime.now, index=True)
