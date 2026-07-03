"""能耗智能管理优化平台 — 调度算法辅助函数

提供调度优化的核心计算逻辑，包括成本估算、时段划分等。
"""

from datetime import datetime, timedelta
from typing import Optional


def estimate_energy_cost(
    power_kw: float,
    duration_hours: float,
    price_per_kwh: float,
) -> float:
    """估算单次运行能耗成本

    Args:
        power_kw: 功率 (kW)
        duration_hours: 运行时长 (小时)
        price_per_kwh: 电价 (元/kWh)

    Returns:
        估算成本 (元)
    """
    return round(power_kw * duration_hours * price_per_kwh, 2)


def estimate_carbon_emission(energy_kwh: float, emission_factor: float = 0.5703) -> float:
    """估算碳排放量

    Args:
        energy_kwh: 电能消耗 (kWh)
        emission_factor: 排放因子 (kgCO2/kWh)，默认中国电网平均值

    Returns:
        碳排放量 (kgCO2)
    """
    return round(energy_kwh * emission_factor, 2)


def get_current_tariff_period(current_time: Optional[datetime] = None, tariffs: list = None) -> dict:
    """获取当前电价时段

    Args:
        current_time: 当前时间
        tariffs: 电价策略列表

    Returns:
        当前时段信息 dict
    """
    if current_time is None:
        current_time = datetime.now()

    current_str = current_time.strftime("%H:%M")

    for tariff in tariffs:
        start = tariff.start_time
        end = tariff.end_time

        # 处理跨天时段 (如 22:00-06:00)
        if start <= end:
            in_period = start <= current_str <= end
        else:
            in_period = current_str >= start or current_str <= end

        if in_period:
            return {
                "period_name": tariff.period_name,
                "price_per_kwh": tariff.price_per_kwh,
            }

    return {"period_name": "未知", "price_per_kwh": 0.8}


def calculate_power_statistics(telemetry_records: list) -> dict:
    """计算功率统计信息

    Args:
        telemetry_records: 能耗记录列表

    Returns:
        统计信息 dict
    """
    if not telemetry_records:
        return {
            "avg_power": 0,
            "max_power": 0,
            "min_power": 0,
            "total_energy": 0,
            "record_count": 0,
        }

    powers = [r.power for r in telemetry_records]
    return {
        "avg_power": round(sum(powers) / len(powers), 2),
        "max_power": round(max(powers), 2),
        "min_power": round(min(powers), 2),
        "total_energy": round(sum(r.energy_kwh for r in telemetry_records), 4),
        "record_count": len(telemetry_records),
    }
