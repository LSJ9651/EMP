"""设备相关模型 — Device, DeviceSynonym"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Device(Base):
    """耗能设备主数据表"""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="设备名称")
    type = Column(String(50), nullable=False, comment="设备类型：空压机/注塑机/冷水机组/照明/其他")
    rated_power = Column(Float, nullable=False, comment="额定功率(kW)")
    status = Column(String(20), default="offline", comment="设备状态：online/offline/alert")
    line_no = Column(String(50), comment="产线编号")
    workshop = Column(String(100), default="一车间", comment="所属车间")
    location = Column(String(200), comment="安装位置")
    install_date = Column(DateTime, default=datetime.now, comment="安装日期")
    efficiency = Column(Float, default=1.0, comment="当前效率系数(0-1)")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    telemetry_records = relationship("Telemetry", back_populates="device", cascade="all, delete-orphan")
    alert_thresholds = relationship("AlertThreshold", back_populates="device", cascade="all, delete-orphan")
    alert_records = relationship("AlertRecord", back_populates="device", cascade="all, delete-orphan")
    schedule_tasks = relationship("ScheduleTask", back_populates="device", cascade="all, delete-orphan")


class DeviceSynonym(Base):
    """设备同义词映射表 — 支持设备和常见别名的关联"""
    __tablename__ = "device_synonyms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, comment="设备ID")
    synonym = Column(String(100), nullable=False, comment="同义词/别名")
    created_at = Column(DateTime, default=datetime.now)

    device = relationship("Device")
