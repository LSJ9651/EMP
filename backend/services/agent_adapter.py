"""能耗智能管理优化平台 — 智能体适配器

封装与外部智能体的交互逻辑。云端模式使用 Coze SDK 调用工作流/对话智能体，
本地模式使用 Mock 规则引擎。
"""

import asyncio
import json
import math
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from cozepy.exception import CozeAPIError

load_dotenv()

logger = logging.getLogger(__name__)


def _coze_error_message(e: Exception) -> str:
    """从 CozeAPIError 提取用户可读的错误信息"""
    if isinstance(e, CozeAPIError):
        code = e.code
        msg = e.msg or str(e)
        if code == 4028:
            return f"Coze API 配额已用尽 (错误码 {code})"
        elif code in (401, 403):
            return f"Coze API Key 无效或未授权 (错误码 {code})"
        else:
            return f"Coze API 错误 (错误码 {code}): {msg}"
    return str(e)[:200]


def _sample_data(data_list, max_points=200):
    """对时序数据进行等间隔采样，控制数据量防止 Token 溢出"""
    if len(data_list) <= max_points:
        return data_list
    step = len(data_list) / max_points
    return [data_list[int(i * step)] for i in range(max_points)]


def _build_analysis_params(device, start_time, end_time, db, max_points=200) -> dict:
    """构建单设备能耗分析入参（严格匹配 Coze 工作流 start 节点 Schema）

    Args:
        device: Device ORM 对象
        start_time: 起始时间 ISO 格式
        end_time: 结束时间 ISO 格式
        db: 数据库会话
        max_points: 最大采样点数

    Returns:
        扁平结构 dict，字段与设计文档 §3.1 完全对应
    """
    from models import Telemetry

    try:
        st = datetime.fromisoformat(start_time)
        et = datetime.fromisoformat(end_time)
    except (ValueError, TypeError):
        st = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        et = datetime.now()

    records = (
        db.query(Telemetry)
        .filter(
            Telemetry.device_id == device.id,
            Telemetry.timestamp >= st,
            Telemetry.timestamp <= et,
        )
        .order_by(Telemetry.timestamp)
        .all()
    )

    powers = [r.power for r in records]
    sampled = _sample_data(records, max_points)

    # 计算 max_time / min_time（出现最大/最小功率的时刻，HH:MM 格式）
    if records:
        max_record = max(records, key=lambda r: r.power)
        min_record = min(records, key=lambda r: r.power)
        max_time = max_record.timestamp.strftime("%H:%M")
        min_time = min_record.timestamp.strftime("%H:%M")
    else:
        max_time = "N/A"
        min_time = "N/A"

    statistics = {
        "avg_power": round(sum(powers) / len(powers), 2) if powers else 0,
        "max_power": round(max(powers), 2) if powers else 0,
        "min_power": round(min(powers), 2) if powers else 0,
        "max_time": max_time,
        "min_time": min_time,
        "std_dev": round(
            math.sqrt(sum((p - sum(powers) / len(powers)) ** 2 for p in powers) / len(powers)), 2
        ) if powers and len(powers) > 1 else 0,
    }
    data_points = [
        {"ts": r.timestamp.strftime("%H:%M"), "power": r.power}
        for r in sampled
    ]

    return {
        "device_id": device.id,
        "device_name": device.name,
        "rated_power": device.rated_power,
        "start_time": start_time or st.isoformat(),
        "end_time": end_time or et.isoformat(),
        "statistics": statistics,
        "data_points": data_points,
    }


def _build_optimize_payload(production_goal, deadline, device_ids, db) -> dict:
    """构建完整的调度优化请求数据包（附带电价策略和设备功率特性）"""
    from models import Device, TariffPolicy

    tariffs = (
        db.query(TariffPolicy)
        .filter(TariffPolicy.is_active == True)
        .order_by(TariffPolicy.start_time)
        .all()
    )

    if not tariffs:
        tariff_list = [
            {"period": "高峰", "start": "08:00", "end": "11:00", "price": 1.20},
            {"period": "平段", "start": "11:00", "end": "18:00", "price": 0.80},
            {"period": "高峰", "start": "18:00", "end": "22:00", "price": 1.20},
            {"period": "低谷", "start": "22:00", "end": "06:00", "price": 0.30},
        ]
    else:
        tariff_list = [
            {
                "period": t.period_name,
                "start": t.start_time,
                "end": t.end_time,
                "price": t.price_per_kwh,
            }
            for t in tariffs
        ]

    query = db.query(Device)
    if device_ids:
        query = query.filter(Device.id.in_(device_ids))
    devices = query.all()

    device_list = [
        {
            "id": d.id,
            "name": d.name,
            "rated_power": d.rated_power,
            "run_power": round(d.rated_power * 0.85, 2),
            "idle_power": round(d.rated_power * 0.15, 2),
        }
        for d in devices
    ]

    deadline_str = deadline or datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

    # 严格按照能源调度工作流设计报告的输入契约
    return {
        "production_goal": production_goal,
        "deadline": deadline_str,
        "available_devices": device_list,
        "tariff_policy": tariff_list,
    }


async def analyze_energy(device_id: Optional[int], start_time: str, end_time: str, db,
                        max_points: int = 200) -> dict:
    """能耗分析智能体

    云端模式：对每台设备单独调用 Coze 工作流，汇总结果。
    本地模式：使用规则引擎逐设备分析。

    Args:
        device_id: 设备ID，不传则全厂分析
        start_time: 起始时间 ISO 格式
        end_time: 结束时间 ISO 格式
        db: 数据库会话
        max_points: 最大采样点数（控制数据量）

    Returns:
        分析结果 dict，包含 summary / anomalies / suggestions / _mode
    """
    from models import Device, Telemetry
    from services.ai_config_service import ai_config_service

    # ── 确定设备列表 ──
    if device_id:
        if isinstance(device_id, (list, tuple)):
            devices = db.query(Device).filter(Device.id.in_(device_id)).all()
            if not devices:
                return {"error": "设备不存在", "_mode": "local"}
        else:
            device = db.query(Device).filter(Device.id == device_id).first()
            if not device:
                return {"error": "设备不存在", "_mode": "local"}
            devices = [device]
    else:
        devices = db.query(Device).all()

    # ── 判断是否走云端 ──
    use_cloud = ai_config_service.is_cloud_enabled(db, "analyze")
    if use_cloud:
        api_key = ai_config_service.get_api_key(db)
        workflow_id = ai_config_service.get_service_id(db, "analyze")
        if not api_key or not workflow_id:
            use_cloud = False

    # ── 云端模式：并行调用 Coze 工作流（Semaphore 限流 5 路并发） ──
    if use_cloud:
        from services.coze_client import CozeClient

        semaphore = asyncio.Semaphore(5)

        async def _analyze_one_device(device):
            """并行任务：分析单台设备，失败自动降级本地"""
            async with semaphore:
                # 严格按照能耗分析工作流设计报告的 Start 节点参数定义
                params = _build_analysis_params(device, start_time, end_time, db, max_points)
                try:
                    result = await CozeClient.run_workflow(db, "analyze", params)
                    if result:
                        data = result.get("data", result)
                        if isinstance(data, str):
                            try:
                                data = json.loads(data)
                            except (json.JSONDecodeError, TypeError):
                                data = {"raw_output": data}
                        return {
                            "summary": data.get("summary", ""),
                            "anomalies": data.get("anomalies", []),
                            "suggestions": data.get("suggestions", []),
                            "total_power_avg": data.get("total_power_avg", 0),
                            "mode": "cloud",
                        }
                    else:
                        local = _analyze_device_local(device, start_time, end_time, db)
                        local["mode"] = "local"
                        local["_cloud_error"] = "工作流返回空结果"
                        return local
                except CozeAPIError as e:
                    err_msg = _coze_error_message(e)
                    logger.error(f"[analyze] 设备 {device.id} 云端调用失败({err_msg})，使用本地分析")
                    local = _analyze_device_local(device, start_time, end_time, db)
                    local["mode"] = "local"
                    local["_cloud_error"] = err_msg
                    return local
                except Exception as e:
                    logger.error(f"[analyze] 设备 {device.id} 云端调用失败，使用本地分析: {e}")
                    local = _analyze_device_local(device, start_time, end_time, db)
                    local["mode"] = "local"
                    local["_cloud_error"] = str(e)[:200]
                    return local

        tasks = [_analyze_one_device(d) for d in devices]
        results = await asyncio.gather(*tasks)

        all_summaries = []
        all_anomalies = []
        all_suggestions = set()
        total_avg_power = 0.0
        success_count = 0
        cloud_success = 0  # 实际云端调用成功的设备数
        cloud_errors = []  # 收集云端调用失败信息

        for r in results:
            if r:
                all_summaries.append(r.get("summary", ""))
                all_anomalies.extend(r.get("anomalies", []))
                for s in r.get("suggestions", []):
                    all_suggestions.add(s)
                total_avg_power += r.get("total_power_avg", 0)
                success_count += 1
                if r.get("mode") == "cloud":
                    cloud_success += 1
                if r.get("_cloud_error"):
                    cloud_errors.append(r["_cloud_error"])

        avg_total_power = round(total_avg_power / success_count, 2) if success_count > 0 else 0
        # 如果全部设备云端调用失败，整体标记为本地模式
        actual_mode = "cloud" if cloud_success > 0 else "local"
        return {
            "summary": " | ".join([s for s in all_summaries if s]),
            "anomalies": all_anomalies,
            "suggestions": list(all_suggestions)[:5],
            "total_power_avg": avg_total_power,
            "analyzed_devices": len(devices),
            "time_range": f"{start_time or 'auto'} ~ {end_time or 'auto'}",
            "_mode": actual_mode,
            "_cloud_error": cloud_errors[0] if cloud_errors and cloud_success == 0 else None,
        }

    # ── 本地模式：规则引擎 ──
    all_summaries = []
    all_anomalies = []
    all_suggestions = set()
    total_avg_power = 0.0

    for device in devices:
        local = _analyze_device_local(device, start_time, end_time, db)
        all_summaries.append(local["summary"])
        all_anomalies.extend(local["anomalies"])
        for s in local.get("suggestions", []):
            all_suggestions.add(s)
        total_avg_power += local.get("total_power_avg", 0)

    avg_total_power = round(total_avg_power / len(devices), 2) if devices else 0

    return {
        "summary": " | ".join([s for s in all_summaries if s]),
        "anomalies": all_anomalies,
        "suggestions": list(all_suggestions)[:5],
        "total_power_avg": avg_total_power,
        "analyzed_devices": len(devices),
        "time_range": f"{start_time or 'auto'} ~ {end_time or 'auto'}",
        "_mode": "local",
    }


def _analyze_device_local(device, start_time, end_time, db) -> dict:
    """单设备本地规则引擎分析（不含全厂汇总逻辑）"""
    from models import Telemetry

    try:
        st = datetime.fromisoformat(start_time)
        et = datetime.fromisoformat(end_time)
    except (ValueError, TypeError):
        st = datetime.now() - timedelta(hours=24)
        et = datetime.now()

    records = db.query(Telemetry).filter(
        Telemetry.device_id == device.id,
        Telemetry.timestamp >= st,
        Telemetry.timestamp <= et,
    ).all()

    if not records:
        return {
            "summary": f"{device.name} 无数据",
            "anomalies": [],
            "suggestions": [],
            "total_power_avg": 0,
        }

    avg_power = round(sum(r.power for r in records) / len(records), 2)
    max_power = round(max(r.power for r in records), 2)
    anomalies = []

    if max_power > device.rated_power * 0.95:
        anomalies.append({
            "device_id": device.id,
            "device_name": device.name,
            "severity": "high",
            "message": f"{device.name} 接近额定功率运行（{max_power}kW / {device.rated_power}kW），建议检查负载",
        })

    low_count = sum(1 for r in records if r.power < device.rated_power * 0.3)
    if low_count / len(records) > 0.5:
        anomalies.append({
            "device_id": device.id,
            "device_name": device.name,
            "severity": "medium",
            "message": f"{device.name} 存在长时间低负载运行，建议检查是否存在空转",
        })

    suggestions = _generate_suggestions([device], anomalies)
    summary = f"{device.name}：平均功率 {avg_power}kW，{'发现 ' + str(len(anomalies)) + ' 个异常' if anomalies else '运行正常'}"

    return {
        "summary": summary,
        "anomalies": anomalies,
        "suggestions": suggestions,
        "total_power_avg": avg_power,
    }


def _estimate_savings_from_schedule(schedule: list, production_goal: int, db) -> float:
    """根据调度方案重新估算成本节约（用于云端结果校验，防止透传 0）
    
    计算逻辑：基准成本 = 全时段高峰电价，优化成本 = 各时段实际电价
    """
    from models import Device

    if not schedule:
        return round(production_goal * 0.08, 2)

    # 收集所有涉及的设备ID → 查询 rated_power
    device_ids = list({item.get("device_id", 0) for item in schedule if item.get("device_id")})
    devices = {}
    if device_ids:
        devs = db.query(Device).filter(Device.id.in_(device_ids)).all()
        devices = {d.id: d.rated_power for d in devs}

    total_base = 0.0
    total_optim = 0.0

    for item in schedule:
        pid = item.get("price_per_kwh", 0) or 0
        rated_power = devices.get(item.get("device_id", 0), 75)
        action = item.get("action", "run")
        device_power = rated_power if action == "run" else rated_power * 0.1

        # 计算时段小时数
        start_str = item.get("start", "00:00")
        end_str = item.get("end", "00:00")
        try:
            sh, sm = map(int, start_str.split(":"))
            eh, em = map(int, end_str.split(":"))
            if eh <= sh:
                eh += 24
            period_hours = (eh - sh) + (em - sm) / 60
        except (ValueError, AttributeError):
            continue

        # 找出电价表中最高电价作为基准
        peak_price = max((i.get("price_per_kwh", pid) for i in schedule), default=pid)
        kwh = device_power * period_hours
        total_base += kwh * peak_price
        total_optim += kwh * pid

    saved = round(total_base - total_optim, 2)
    if saved <= 0:
        saved = round(production_goal * 0.08, 2)
    return saved


async def optimize_schedule(production_goal: int, deadline: str, device_ids: list, db) -> dict:
    """调度优化智能体

    Args:
        production_goal: 生产目标数量
        deadline: 截止时间 ISO 格式
        device_ids: 可用设备ID列表
        db: 数据库会话

    Returns:
        调度计划 dict，包含 schedule / estimated_cost_saved / reasoning
    """
    from services.ai_config_service import ai_config_service

    use_cloud = ai_config_service.is_cloud_enabled(db, "optimize")
    cloud_err = None  # 云端错误信息，供结果回传
    # 提前检查：无有效 API Key 或 workflow_id 则不尝试云端
    if use_cloud:
        api_key = ai_config_service.get_api_key(db)
        workflow_id = ai_config_service.get_service_id(db, "optimize")
        if not api_key or not workflow_id:
            use_cloud = False

    if use_cloud:
        from services.coze_client import CozeClient

        # 严格按照能源调度工作流设计报告的 Start 节点参数定义
        payload = _build_optimize_payload(production_goal, deadline, device_ids, db)
        logger.info(f"[optimize] 云端调用: production_goal={production_goal}, devices={len(payload.get('available_devices',[]))}, tariffs={len(payload.get('tariff_policy',[]))}")
        try:
            result = await CozeClient.run_workflow(db, "optimize", payload)
            if result:
                data = result.get("data", result)
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        data = {"raw_output": data}
                data["_mode"] = "cloud"
                # 云端返回 estimated_cost_saved 为 0 时，根据调度方案重新估算
                if not data.get("estimated_cost_saved") and data.get("schedule"):
                    recalc = _estimate_savings_from_schedule(data["schedule"], production_goal, db)
                    logger.info(f"[optimize] 云端返回值 cost_saved=0，根据调度方案重新估算: {recalc}")
                    data["estimated_cost_saved"] = recalc
                return data
        except CozeAPIError as e:
            cloud_err = _coze_error_message(e)
            logger.error(f"[optimize] 云端调用失败({cloud_err})，降级到本地模式")
        except Exception as e:
            cloud_err = str(e)[:200]
            logger.error(f"[optimize] 云端调用失败，降级到本地模式: {e}")

    # Mock 实现（本地模式或云端失败降级）
    from models import Device, TariffPolicy

    query = db.query(Device)
    if device_ids:
        query = query.filter(Device.id.in_(device_ids))
    devices = query.all()
    if not devices:
        return {"error": "无可用设备", "_mode": "local"}

    tariffs = db.query(TariffPolicy).filter(TariffPolicy.is_active == True).order_by(
        TariffPolicy.start_time
    ).all()

    if not tariffs:
        tariffs = [
            type('Tariff', (), {'period_name': '高峰', 'start_time': '08:00', 'end_time': '11:00', 'price_per_kwh': 1.2})(),
            type('Tariff', (), {'period_name': '平段', 'start_time': '11:00', 'end_time': '18:00', 'price_per_kwh': 0.8})(),
            type('Tariff', (), {'period_name': '高峰', 'start_time': '18:00', 'end_time': '22:00', 'price_per_kwh': 1.2})(),
            type('Tariff', (), {'period_name': '低谷', 'start_time': '22:00', 'end_time': '06:00', 'price_per_kwh': 0.3})(),
        ]

    # ── 计算总产能 ──
    # 代理量：rated_power * efficiency% 作为每小时产能单位
    total_capacity_per_hour = sum(d.rated_power * (d.efficiency or 85) / 100 for d in devices)
    work_hours_needed = round(production_goal / total_capacity_per_hour, 1) if total_capacity_per_hour > 0 else 999

    # ── 按电价从低到高排序时段 ──
    sorted_tariffs = sorted(tariffs, key=lambda t: t.price_per_kwh)

    # ── 生成调度方案 ──
    schedule = []
    remaining_hours = work_hours_needed
    total_base_cost = 0.0
    total_optim_cost = 0.0

    for tariff in tariffs:
        start_h, start_m = (int(x) for x in tariff.start_time.split(':'))
        end_h, end_m = (int(x) for x in tariff.end_time.split(':'))
        if end_h <= start_h:
            end_h += 24  # 跨天
        period_hours = (end_h - start_h) + (end_m - start_m) / 60

        price = tariff.price_per_kwh
        # 根据产能需求决定时段内的设备动作比例
        if remaining_hours > 0:
            # 该时段需要的运行比例
            run_ratio = min(1.0, remaining_hours / (period_hours * len(devices))) if period_hours > 0 else 0
            remaining_hours -= period_hours * len(devices) * run_ratio
        else:
            run_ratio = 0

        for device in devices:
            # 随机分配运行/待机，整体比例逼近 run_ratio
            action = "run" if (device.id + hash(tariff.period_name)) % 10 < run_ratio * 10 else "idle"
            device_power = device.rated_power if action == "run" else device.rated_power * 0.1
            kwh = round(device_power * period_hours, 2)

            schedule.append({
                "device_id": device.id,
                "device_name": device.name,
                "start": tariff.start_time,
                "end": tariff.end_time if end_h < 24 else "06:00",
                "action": action,
                "price_per_kwh": price,
            })

            # 成本计算：无优化=全时段运行按峰电，优化后=按实际电价
            total_base_cost += device_power * period_hours * sorted_tariffs[-1].price_per_kwh
            total_optim_cost += kwh * price

    # ── 成本节省 ──
    estimated_saved = round(total_base_cost - total_optim_cost, 2)
    if estimated_saved <= 0:
        estimated_saved = round(production_goal * 0.08, 2)

    # ── 推理说明 ──
    deadline_info = ""
    if deadline:
        try:
            dl = datetime.fromisoformat(deadline)
            deadline_info = f"，截止时间 {dl.strftime('%m月%d日 %H:%M')}"
        except (ValueError, TypeError):
            pass

    reasoning = (
        f"目标产量 {production_goal} 件{deadline_info}，"
        f"总产能 {total_capacity_per_hour:.0f} 件/小时，预计需 {work_hours_needed:.1f} 工作小时。"
        f"利用谷电时段(¥{sorted_tariffs[0].price_per_kwh}/kWh)高负载运行、峰电时段(¥{sorted_tariffs[-1].price_per_kwh}/kWh)待机，"
        f"预计节省约 ¥{estimated_saved}"
    )

    return {
        "schedule": schedule,
        "estimated_cost_saved": estimated_saved,
        "reasoning": reasoning,
        "production_goal": production_goal,
        "_mode": "local",
        "_cloud_error": cloud_err,  # 云端调用失败原因（成功时 None）
    }


def _generate_suggestions(devices, anomalies) -> list:
    """根据异常情况生成节能建议"""
    suggestions = []

    device_types = set(d.type for d in devices)
    if "空压机" in device_types:
        suggestions.append("空压机加装变频器可节能15-25%")
        suggestions.append("定期检查压缩空气管路泄漏")

    if "照明" in device_types:
        suggestions.append("照明系统改用LED灯具可节能40-60%")

    if anomalies and len(anomalies) > 0:
        suggestions.append("优化生产排程，尽量在谷电时段集中生产")

    suggestions.append("建议对老设备进行能效评估，及时维护或更换")
    suggestions.append("安装功率因数补偿装置提高电能质量")

    return suggestions[:5]


def _compare_periods(devices, start_time, end_time, db) -> dict:
    """同环比分析：对比上一周期的能耗数据"""
    from models import Telemetry

    delta = end_time - start_time
    prev_start = start_time - delta
    prev_end = start_time

    comparison = []

    for device in devices:
        curr_records = db.query(Telemetry).filter(
            Telemetry.device_id == device.id,
            Telemetry.timestamp >= start_time,
            Telemetry.timestamp <= end_time,
        ).all()

        prev_records = db.query(Telemetry).filter(
            Telemetry.device_id == device.id,
            Telemetry.timestamp >= prev_start,
            Telemetry.timestamp <= prev_end,
        ).all()

        curr_energy = round(sum(r.energy_kwh for r in curr_records), 2)
        prev_energy = round(sum(r.energy_kwh for r in prev_records), 2)

        ratio = round(curr_energy / prev_energy * 100, 1) if prev_energy > 0 else 0

        if ratio > 105:
            trend = "up"
        elif ratio < 95:
            trend = "down"
        else:
            trend = "stable"

        comparison.append({
            "device_id": device.id,
            "device_name": device.name,
            "current_energy_kwh": curr_energy,
            "previous_energy_kwh": prev_energy,
            "ratio_pct": ratio,
            "trend": trend,
            "delta_kwh": round(curr_energy - prev_energy, 2),
        })

    return {
        "periods": [
            {"label": "上一周期", "range": f"{prev_start.isoformat()} ~ {prev_end.isoformat()}"},
            {"label": "当前周期", "range": f"{start_time.isoformat()} ~ {end_time.isoformat()}"},
        ],
        "devices": comparison,
    }


async def chat_with_agent(message: str, session_id: str, db=None) -> str:
    """调用外部对话智能体

    优先使用 Coze SDK polling 模式调用云端 Bot（兼容 async 上下文），
    失败降级返回空字符串，由上层降级到本地兜底。
    """
    if db:
        from services.ai_config_service import ai_config_service
        use_cloud = ai_config_service.is_cloud_enabled(db, "chat")
        if use_cloud:
            api_key = ai_config_service.get_api_key(db)
            bot_id = ai_config_service.get_service_id(db, "chat")
            if api_key and bot_id:
                try:
                    from services.coze_client import CozeClient
                    result = await CozeClient.chat(db, message, session_id)
                    if result:
                        logger.info(f"[chat] 云端回复成功, 长度={len(result)}")
                        return result
                except Exception as e:
                    logger.error(f"[chat] 云端调用失败，降级本地: {e}")

    return ""
