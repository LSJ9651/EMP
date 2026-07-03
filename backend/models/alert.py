"""告警相关模型 — AlertThreshold, AlertRecord"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import Base


class AlertThreshold(Base):
    """告警阈值配置表"""
    __tablename__ = "alert_thresholds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, comment="设备ID")
    param_type = Column(String(50), nullable=False, comment="参数类型：power/temperature/voltage/current")
    upper_limit = Column(Float, comment="上限值")
    lower_limit = Column(Float, comment="下限值")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    device = relationship("Device", back_populates="alert_thresholds")


class AlertRecord(Base):
    """告警历史记录表"""
    __tablename__ = "alert_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, comment="设备ID")
    alert_time = Column(DateTime, nullable=False, default=datetime.now, comment="告警时间")
    param_type = Column(String(50), nullable=False, comment="参数类型")
    value = Column(Float, nullable=False, comment="触发值")
    threshold_value = Column(Float, nullable=False, comment="阈值")
    message = Column(String(500), comment="告警信息")
    severity = Column(String(20), default="warning", comment="严重程度：info/warning/critical")
    is_resolved = Column(Boolean, default=False, comment="是否已处理")
    handler = Column(String(50), comment="处理人")
    measure = Column(Text, comment="处理措施")
    resolved_at = Column(DateTime, comment="处理时间")

    # 关联
    device = relationship("Device", back_populates="alert_records")
