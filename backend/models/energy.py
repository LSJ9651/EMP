"""能耗数据模型 — Telemetry, TariffPolicy"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class Telemetry(Base):
    """实时能耗时序数据表"""
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True, comment="设备ID")
    timestamp = Column(DateTime, nullable=False, index=True, comment="采集时间戳")
    voltage = Column(Float, default=380.0, comment="电压(V)")
    current = Column(Float, default=0.0, comment="电流(A)")
    power = Column(Float, nullable=False, comment="有功功率(kW)")
    energy_kwh = Column(Float, default=0.0, comment="累计电度(kWh)")
    power_factor = Column(Float, default=0.95, comment="功率因数")
    status_code = Column(Integer, default=0, comment="状态码：0-正常,1-警告,2-故障")
    temperature = Column(Float, comment="设备温度(°C)")

    # 关联
    device = relationship("Device", back_populates="telemetry_records")


class TariffPolicy(Base):
    """分时电价策略表"""
    __tablename__ = "tariff_policy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period_name = Column(String(50), nullable=False, comment="时段名称：高峰/平段/低谷")
    start_time = Column(String(5), nullable=False, comment="开始时间 HH:MM")
    end_time = Column(String(5), nullable=False, comment="结束时间 HH:MM")
    price_per_kwh = Column(Float, nullable=False, comment="电价(元/kWh)")
    is_active = Column(Boolean, default=True, comment="是否启用")
    description = Column(String(200), comment="说明")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
