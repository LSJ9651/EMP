"""API 验证脚本 — 快速验证所有接口是否正常

启动后端服务后运行此脚本，验证各模块接口响应。
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, engine
from models import Base
from database import get_db_session


def verify_database():
    """验证数据库连接和表结构"""
    print("=" * 50)
    print("1. 验证数据库连接")
    print("=" * 50)
    try:
        db = get_db_session()
        from models import Device, Telemetry, TariffPolicy
        device_count = db.query(Device).count()
        telemetry_count = db.query(Telemetry).count()
        tariff_count = db.query(TariffPolicy).count()
        db.close()

        print(f"  [OK] 设备数量: {device_count}")
        print(f"  [OK] 遥测数据: {telemetry_count}")
        print(f"  [OK] 电价策略: {tariff_count}")

        if device_count == 0:
            print("  [WARN] 无设备数据，请运行 init_db.py")
        if telemetry_count == 0:
            print("  [WARN] 无遥测数据，请运行 init_mock_data.py")

        return device_count > 0 and telemetry_count > 0 and tariff_count > 0
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def verify_api_endpoints():
    """通过 HTTP 验证 API 响应"""
    print("\n" + "=" * 50)
    print("2. 验证 API 端点")
    print("=" * 50)
    print("  (需要后端服务运行在 http://localhost:8080)")

    try:
        import urllib.request
        import urllib.error

        base_url = "http://localhost:8080"

        endpoints = [
            ("GET", "/"),
            ("GET", "/api/devices/list"),
            ("GET", "/api/telemetry/current"),
            ("GET", "/api/telemetry/latest"),
            ("GET", "/api/tariffs/"),
            ("GET", "/api/tariffs/current"),
            ("GET", "/api/alerts/records"),
            ("GET", "/api/alerts/thresholds"),
            ("GET", "/api/dashboard/overview"),
            ("GET", "/api/dashboard/energyflow"),
            ("GET", "/api/dashboard/trend?minutes=5"),
            ("GET", "/api/dashboard/alerts-bar"),
            ("GET", "/api/agent/reports"),
            ("GET", "/api/reports/summary"),
        ]

        results = []
        for method, path in endpoints:
            try:
                url = f"{base_url}{path}"
                req = urllib.request.Request(url, method=method)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())
                    status = "OK" if data.get("code") == 200 else f"CODE:{data.get('code')}"
                    print(f"  [{status}] {method:4s} {path}")
                    results.append(True)
            except urllib.error.URLError as e:
                print(f"  [FAIL] {method:4s} {path} — 连接失败 (后端未启动?)")
                results.append(False)
            except Exception as e:
                print(f"  [FAIL] {method:4s} {path} — {e}")
                results.append(False)

        success = all(results)
        if success:
            print(f"\n  [OK] 所有 {len(results)} 个端点验证通过！")
        else:
            failed = results.count(False)
            print(f"\n  [WARN] {failed}/{len(results)} 个端点验证失败")
        return success

    except ImportError:
        print("  [WARN] 无法导入 urllib，跳过 HTTP 验证")
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


if __name__ == "__main__":
    print("能耗智能管理优化平台 — API 验证")
    print("=" * 50)

    db_ok = verify_database()
    print()

    if db_ok:
        api_ok = verify_api_endpoints()
    else:
        print("  数据库验证未通过，请先运行:")
        print("    python scripts/init_db.py")
        print("    python scripts/init_mock_data.py")
        api_ok = False

    print()
    if db_ok and api_ok:
        print("验证通过！系统已就绪。")
    else:
        print("验证未完全通过，请检查上述错误。")
