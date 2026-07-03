"""能耗智能管理优化平台 — 后端单元测试

测试模型层、服务层、路由层的核心功能。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from database import get_db
from models import Base, Device, Telemetry, TariffPolicy, AlertThreshold, AlertRecord, AgentReport, ScheduleTask
from services.scheduling_core import (
    estimate_energy_cost,
    estimate_carbon_emission,
    calculate_power_statistics,
    get_current_tariff_period,
)

# 测试数据库
TEST_DATABASE_URL = "sqlite:///./test_energy.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# 创建测试用 app
from main import app
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前重建数据库"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    # 插入测试设备
    device = Device(name="测试空压机", type="空压机", rated_power=75, status="online", workshop="一车间")
    db.add(device)
    db.commit()
    db.refresh(device)

    # 插入遥测数据
    for i in range(10):
        telemetry = Telemetry(
            device_id=device.id,
            timestamp=datetime.now() - timedelta(minutes=10 - i),
            voltage=380.0,
            current=100.0,
            power=50.0 + i * 2,
            energy_kwh=0.1,
        )
        db.add(telemetry)

    # 插入电价策略
    tariff = TariffPolicy(
        period_name="高峰", start_time="08:00", end_time="11:00",
        price_per_kwh=1.2, is_active=True,
    )
    db.add(tariff)

    # 插入告警阈值
    threshold = AlertThreshold(
        device_id=device.id, param_type="power",
        upper_limit=80.0, lower_limit=20.0, is_enabled=True,
    )
    db.add(threshold)

    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


# ========== 模型层测试 ==========

class TestModels:
    """测试数据模型"""

    def test_create_device(self):
        db = TestingSessionLocal()
        device = Device(name="测试注塑机", type="注塑机", rated_power=55, workshop="二车间")
        db.add(device)
        db.commit()
        db.refresh(device)
        assert device.id is not None
        assert device.name == "测试注塑机"
        assert device.rated_power == 55
        db.close()

    def test_create_telemetry(self):
        db = TestingSessionLocal()
        device = db.query(Device).first()
        telemetry = Telemetry(
            device_id=device.id,
            timestamp=datetime.now(),
            power=50.0,
            voltage=380.0,
            current=100.0,
        )
        db.add(telemetry)
        db.commit()
        assert telemetry.id is not None
        assert telemetry.power == 50.0
        db.close()

    def test_device_relationships(self):
        db = TestingSessionLocal()
        device = db.query(Device).first()
        assert len(device.telemetry_records) == 10
        assert len(device.alert_thresholds) == 1
        db.close()


# ========== 服务层测试 ==========

class TestSchedulingCore:
    """测试调度核心算法"""

    def test_estimate_energy_cost(self):
        cost = estimate_energy_cost(power_kw=50, duration_hours=2, price_per_kwh=1.2)
        assert cost == 120.0

    def test_estimate_carbon_emission(self):
        co2 = estimate_carbon_emission(energy_kwh=1000)
        assert co2 == 570.3

    def test_calculate_power_statistics(self):
        db = TestingSessionLocal()
        records = db.query(Telemetry).all()
        stats = calculate_power_statistics(records)
        assert stats["record_count"] == 10
        assert stats["avg_power"] > 0
        assert stats["max_power"] > stats["min_power"]
        db.close()

    def test_calculate_power_statistics_empty(self):
        stats = calculate_power_statistics([])
        assert stats["record_count"] == 0
        assert stats["avg_power"] == 0

    def test_get_current_tariff_period(self):
        db = TestingSessionLocal()
        tariffs = db.query(TariffPolicy).all()
        # 测试高峰时段
        test_time = datetime(2026, 6, 16, 9, 0, 0)  # 9:00 在高峰时段内
        result = get_current_tariff_period(test_time, tariffs)
        assert result["period_name"] == "高峰"
        assert result["price_per_kwh"] == 1.2
        db.close()


# ========== API 接口测试 ==========

class TestAPI:
    """测试 REST API"""

    def test_root(self):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200

    def test_list_devices(self):
        resp = client.get("/api/devices/list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "测试空压机"

    def test_get_device(self):
        resp = client.get("/api/devices/1")
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "测试空压机"

    def test_get_device_not_found(self):
        resp = client.get("/api/devices/999")
        assert resp.status_code == 404

    def test_create_device(self):
        resp = client.post("/api/devices/", json={
            "name": "新空压机", "type": "空压机", "rated_power": 100,
            "workshop": "二车间",
        })
        assert resp.status_code == 200
        assert resp.json()["message"] == "设备创建成功"

    def test_update_device(self):
        resp = client.put("/api/devices/1", json={"name": "改名空压机"})
        assert resp.status_code == 200
        # 验证
        resp2 = client.get("/api/devices/1")
        assert resp2.json()["data"]["name"] == "改名空压机"

    def test_delete_device(self):
        # 先创建
        resp = client.post("/api/devices/", json={
            "name": "待删除", "type": "其他", "rated_power": 10,
        })
        dev_id = resp.json()["data"]["id"]
        # 删除
        resp2 = client.delete(f"/api/devices/{dev_id}")
        assert resp2.status_code == 200

    def test_get_latest_telemetry(self):
        resp = client.get("/api/telemetry/latest")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) > 0

    def test_get_current_power(self):
        resp = client.get("/api/telemetry/current")
        assert resp.status_code == 200
        assert "total_power_kw" in resp.json()["data"]

    def test_get_telemetry_range(self):
        resp = client.get("/api/telemetry/range?device_id=1")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 10

    def test_list_tariffs(self):
        resp = client.get("/api/tariffs/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_get_current_tariff(self):
        resp = client.get("/api/tariffs/current")
        assert resp.status_code == 200

    def test_list_thresholds(self):
        resp = client.get("/api/alerts/thresholds")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_list_alert_records(self):
        resp = client.get("/api/alerts/records")
        assert resp.status_code == 200

    def test_dashboard_overview(self):
        resp = client.get("/api/dashboard/overview")
        assert resp.status_code == 200
        assert "total_power_kw" in resp.json()["data"]

    def test_dashboard_energyflow(self):
        resp = client.get("/api/dashboard/energyflow")
        assert resp.status_code == 200
        assert "nodes" in resp.json()["data"]

    def test_dashboard_trend(self):
        resp = client.get("/api/dashboard/trend?minutes=5")
        assert resp.status_code == 200

    def test_dashboard_alerts_bar(self):
        resp = client.get("/api/dashboard/alerts-bar")
        assert resp.status_code == 200

    def test_agent_analyze(self):
        resp = client.post("/api/agent/analyze", json={
            "device_id": 1,
        })
        assert resp.status_code == 200
        assert "summary" in resp.json()["data"]

    def test_agent_optimize(self):
        resp = client.post("/api/agent/optimize", json={
            "production_goal": 1000,
            "devices": [1],
        })
        assert resp.status_code == 200
        assert "schedule" in resp.json()["data"]
        assert "estimated_cost_saved" in resp.json()["data"]

    def test_agent_reports(self):
        resp = client.get("/api/agent/reports")
        assert resp.status_code == 200

    def test_report_summary(self):
        resp = client.get("/api/reports/summary")
        assert resp.status_code == 200
