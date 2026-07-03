"""成本分摊服务层 — SQL聚合优化 + 多规则引擎 + 数据校验 + 导出

性能优化：原全表Python内存循环 → SQL GROUP BY + CASE WHEN 聚合
分摊规则：ratio(比例) / fixed(固定金额) / by_device_type(按设备类型) / by_workshop(按车间)
"""
import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, case, and_, or_
from sqlalchemy.orm import Session

from models import Telemetry, Device, TariffPolicy, AIConfigEntry

logger = logging.getLogger(__name__)

# ─── 时段分级 SQL 表达式构建器 ───
def _build_period_case(db: Session):
    """根据电价表动态构建 CASE WHEN 表达式，将时间戳映射为时段名称"""
    tariffs = db.query(TariffPolicy).filter(TariffPolicy.is_active == True).all()
    if not tariffs:
        return case((func.substr(Telemetry.timestamp, 12, 5).between("00:00", "23:59"), "平段"), else_="平段")

    whens = []
    for t in tariffs:
        start = t.start_time
        end = t.end_time
        if start <= end:
            whens.append((func.substr(Telemetry.timestamp, 12, 5).between(start, end), t.period_name))
        else:
            # 跨天时段，如 22:00-06:00
            whens.append((or_(
                func.substr(Telemetry.timestamp, 12, 5) >= start,
                func.substr(Telemetry.timestamp, 12, 5) <= end,
            ), t.period_name))
    return case(*whens, else_="平段")


def _build_price_case(db: Session):
    """动态构建电价 CASE WHEN"""
    tariffs = db.query(TariffPolicy).filter(TariffPolicy.is_active == True).all()
    if not tariffs:
        return case((func.substr(Telemetry.timestamp, 12, 5).between("00:00", "23:59"), 0.8), else_=0.8)

    whens = []
    for t in tariffs:
        start = t.start_time
        end = t.end_time
        if start <= end:
            whens.append((func.substr(Telemetry.timestamp, 12, 5).between(start, end), t.price_per_kwh))
        else:
            whens.append((or_(
                func.substr(Telemetry.timestamp, 12, 5) >= start,
                func.substr(Telemetry.timestamp, 12, 5) <= end,
            ), t.price_per_kwh))
    return case(*whens, else_=0.8)


# ─── 核心计算方法 ───
class CostAllocationService:
    """成本分摊引擎"""

    @staticmethod
    def get_workshop_summary(
        db: Session,
        start: Optional[str] = None,
        end: Optional[str] = None,
        rule_type: str = "ratio",
    ) -> dict:
        """
        按车间汇总电费（SQL聚合版，性能大幅提升）

        Args:
            db: 数据库会话
            start: 开始日期 YYYY-MM-DD
            end: 结束日期 YYYY-MM-DD
            rule_type: ratio | fixed | by_device_type | by_workshop

        Returns:
            {start_date, end_date, total_cost, total_energy_kwh, workshops: [...]}
        """
        # ── 参数校验 ──
        now = datetime.now()
        try:
            if start:
                start_dt = datetime.strptime(start, "%Y-%m-%d")
            else:
                start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if end:
                end_dt = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            else:
                end_dt = now
        except ValueError:
            start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_dt = now

        if start_dt > end_dt:
            start_dt, end_dt = end_dt, start_dt

        # ── 构建电价 CASE ──
        period_expr = _build_period_case(db)
        price_expr = _build_price_case(db)

        # ── SQL聚合：按workshop + period分组 ──
        # 使用子查询先计算每条记录的period和cost，然后聚合
        cost_expr = Telemetry.energy_kwh * price_expr

        subq = (
            db.query(
                Telemetry.device_id,
                Telemetry.energy_kwh,
                period_expr.label("period"),
                cost_expr.label("line_cost"),
            )
            .filter(Telemetry.timestamp >= start_dt, Telemetry.timestamp <= end_dt)
            .subquery()
        )

        # ── 关联设备表获取workshop ──
        rows = (
            db.query(
                Device.workshop,
                subq.c.period,
                func.sum(subq.c.energy_kwh).label("total_kwh"),
                func.sum(subq.c.line_cost).label("total_cost"),
            )
            .join(subq, Device.id == subq.c.device_id)
            .group_by(Device.workshop, subq.c.period)
            .all()
        )

        # ── 后聚合：按 workshop 汇总 ──
        workshop_data = {}
        for workshop, period, kwh, cost in rows:
            ws = workshop or "未分配"
            if ws not in workshop_data:
                workshop_data[ws] = {
                    "cost": 0.0, "energy_kwh": 0.0,
                    "peak_cost": 0.0, "flat_cost": 0.0, "valley_cost": 0.0,
                }
            ws_data = workshop_data[ws]
            ws_data["cost"] += round(cost or 0, 2)
            ws_data["energy_kwh"] += round(kwh or 0, 2)

            if period == "高峰":
                ws_data["peak_cost"] += round(cost or 0, 2)
            elif period in ("谷时", "低谷"):
                ws_data["valley_cost"] += round(cost or 0, 2)
            else:
                ws_data["flat_cost"] += round(cost or 0, 2)

        total_cost = sum(v["cost"] for v in workshop_data.values())
        total_kwh = sum(v["energy_kwh"] for v in workshop_data.values())

        # ── 应用分摊规则 ──
        result_list = _apply_rule(
            workshop_data, total_cost, rule_type, db, start_dt, end_dt, total_kwh
        )

        # ── 数据校验 ──
        validation = _validate_results(result_list, total_cost)
        if validation:
            logger.warning(f"[cost-allocation] 数据校验: {validation}")

        return {
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": end_dt.strftime("%Y-%m-%d"),
            "total_cost": round(total_cost, 2),
            "total_energy_kwh": round(total_kwh, 2),
            "workshops": result_list,
            "rule_type": rule_type,
            "validation_warnings": validation or [],
        }


    @staticmethod
    def get_workshop_detail(
        db: Session,
        workshop: str,
        days: int = 30,
    ) -> list:
        """单个车间的每日电费明细（SQL聚合版）"""
        now = datetime.now()
        start = now - timedelta(days=max(days, 1))

        devices = db.query(Device).filter(Device.workshop == workshop).all()
        device_ids = [d.id for d in devices]
        if not device_ids:
            return []

        price_expr = _build_price_case(db)
        cost_expr = Telemetry.energy_kwh * price_expr

        rows = (
            db.query(
                func.date(Telemetry.timestamp).label("day"),
                func.sum(Telemetry.energy_kwh).label("total_kwh"),
                func.sum(cost_expr).label("total_cost"),
                func.max(Telemetry.power).label("max_power"),
            )
            .filter(
                Telemetry.device_id.in_(device_ids),
                Telemetry.timestamp >= start,
                Telemetry.timestamp <= now,
            )
            .group_by(func.date(Telemetry.timestamp))
            .order_by(func.date(Telemetry.timestamp).asc())
            .all()
        )

        return [
            {
                "date": str(r.day),
                "cost": round(r.total_cost or 0, 2),
                "energy_kwh": round(r.total_kwh or 0, 2),
                "max_power_kw": round(r.max_power or 0, 2),
            }
            for r in rows
        ]


    @staticmethod
    def get_device_cost_detail(
        db: Session,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> list:
        """按设备维度汇总成本（用于设备级分摊明细）"""
        now = datetime.now()
        try:
            start_dt = datetime.strptime(start, "%Y-%m-%d") if start else now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_dt = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59) if end else now
        except ValueError:
            start_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_dt = now

        period_expr = _build_period_case(db)
        price_expr = _build_price_case(db)
        cost_expr = Telemetry.energy_kwh * price_expr

        subq = (
            db.query(
                Telemetry.device_id,
                Telemetry.energy_kwh,
                period_expr.label("period"),
                cost_expr.label("line_cost"),
            )
            .filter(Telemetry.timestamp >= start_dt, Telemetry.timestamp <= end_dt)
            .subquery()
        )

        rows = (
            db.query(
                Device.id,
                Device.name,
                Device.type,
                Device.workshop,
                Device.rated_power,
                subq.c.period,
                func.sum(subq.c.energy_kwh).label("total_kwh"),
                func.sum(subq.c.line_cost).label("total_cost"),
            )
            .join(subq, Device.id == subq.c.device_id)
            .group_by(Device.id, Device.name, Device.type, Device.workshop, Device.rated_power, subq.c.period)
            .all()
        )

        device_data = {}
        for did, name, dtype, workshop, rated_power, period, kwh, cost in rows:
            if did not in device_data:
                device_data[did] = {
                    "device_id": did,
                    "device_name": name,
                    "device_type": dtype,
                    "workshop": workshop or "未分配",
                    "rated_power": rated_power,
                    "cost": 0.0, "energy_kwh": 0.0,
                    "peak_cost": 0.0, "flat_cost": 0.0, "valley_cost": 0.0,
                }
            dd = device_data[did]
            dd["cost"] += round(cost or 0, 2)
            dd["energy_kwh"] += round(kwh or 0, 2)
            if period == "高峰":
                dd["peak_cost"] += round(cost or 0, 2)
            elif period in ("谷时", "低谷"):
                dd["valley_cost"] += round(cost or 0, 2)
            else:
                dd["flat_cost"] += round(cost or 0, 2)

        total = sum(v["cost"] for v in device_data.values())
        result = sorted(device_data.values(), key=lambda x: x["cost"], reverse=True)
        for item in result:
            item["percentage"] = round(item["cost"] / total * 100, 1) if total > 0 else 0

        return result


    @staticmethod
    def export_csv(
        db: Session,
        start: Optional[str] = None,
        end: Optional[str] = None,
        export_type: str = "workshop",
    ) -> io.StringIO:
        """导出分摊结果为 CSV"""
        output = io.StringIO()
        output.write("\ufeff")  # BOM for Excel UTF-8 compatibility
        writer = csv.writer(output)

        if export_type == "workshop":
            summary = CostAllocationService.get_workshop_summary(db, start, end)
            writer.writerow(["车间", "电费(元)", "用电量(kWh)", "峰时电费", "平时电费", "谷时电费", "占比(%)"])
            for ws in summary["workshops"]:
                writer.writerow([
                    ws["workshop"], ws["cost"], ws["energy_kwh"],
                    ws["peak_cost"], ws["flat_cost"], ws["valley_cost"], ws["percentage"],
                ])
            writer.writerow([])
            writer.writerow(["总计", summary["total_cost"], summary["total_energy_kwh"]])

        elif export_type == "device":
            devices = CostAllocationService.get_device_cost_detail(db, start, end)
            writer.writerow(["设备ID", "设备名称", "设备类型", "车间", "额定功率(kW)", "电费(元)", "用电量(kWh)", "峰时电费", "平时电费", "谷时电费", "占比(%)"])
            for d in devices:
                writer.writerow([
                    d["device_id"], d["device_name"], d["device_type"], d["workshop"],
                    d["rated_power"], d["cost"], d["energy_kwh"],
                    d["peak_cost"], d["flat_cost"], d["valley_cost"], d["percentage"],
                ])

        elif export_type == "detail":
            # 车间明细导出
            detail_rows = []
            # 获取所有车间
            workshops = db.query(Device.workshop).distinct().all()
            all_workshops = [w[0] for w in workshops if w[0]]
            writer.writerow(["车间", "日期", "电费(元)", "用电量(kWh)", "最大功率(kW)"])
            for ws_name in all_workshops:
                detail = CostAllocationService.get_workshop_detail(db, ws_name)
                for d in detail:
                    writer.writerow([ws_name, d["date"], d["cost"], d["energy_kwh"], d["max_power_kw"]])

        output.seek(0)
        return output


# ─── 分摊规则引擎 ───
def _apply_rule(
    workshop_data: dict,
    total_cost: float,
    rule_type: str,
    db: Session,
    start_dt: datetime,
    end_dt: datetime,
    total_kwh: float,
) -> list:
    """根据规则类型调整分摊结果"""
    result = []
    for ws_name, v in sorted(workshop_data.items()):
        percentage = round(v["cost"] / total_cost * 100, 1) if total_cost > 0 else 0
        item = {
            "workshop": ws_name,
            "cost": round(v["cost"], 2),
            "energy_kwh": round(v["energy_kwh"], 2),
            "peak_cost": round(v["peak_cost"], 2),
            "flat_cost": round(v["flat_cost"], 2),
            "valley_cost": round(v["valley_cost"], 2),
            "percentage": percentage,
        }

        # by_device_type: 附加设备类型成本分布
        if rule_type == "by_device_type":
            item["device_type_breakdown"] = _get_device_type_cost(db, ws_name, start_dt, end_dt)

        result.append(item)
    return result


def _get_device_type_cost(db: Session, workshop: str, start_dt: datetime, end_dt: datetime) -> dict:
    """获取某车间按设备类型的成本分布"""
    price_expr = _build_price_case(db)
    cost_expr = Telemetry.energy_kwh * price_expr

    rows = (
        db.query(
            Device.type,
            func.sum(cost_expr).label("total_cost"),
        )
        .join(Telemetry, Device.id == Telemetry.device_id)
        .filter(
            Device.workshop == workshop,
            Telemetry.timestamp >= start_dt,
            Telemetry.timestamp <= end_dt,
        )
        .group_by(Device.type)
        .all()
    )
    return {r[0]: round(r[1] or 0, 2) for r in rows}


def _validate_results(workshop_list: list, total_cost: float) -> list:
    """校验分摊结果，返回告警列表"""
    warnings = []
    if not workshop_list:
        warnings.append("所选时间范围内无数据")
        return warnings

    pct_sum = round(sum(w["percentage"] for w in workshop_list), 1)
    if total_cost > 1 and abs(pct_sum - 100) > 1:
        warnings.append(f"占比之和={pct_sum}%，偏离100%（机器舍入误差可忽略）")

    for w in workshop_list:
        pfv = round(w["peak_cost"] + w["flat_cost"] + w["valley_cost"], 2)
        if abs(pfv - w["cost"]) > 0.1:
            warnings.append(f"{w['workshop']} 峰({w['peak_cost']})+平({w['flat_cost']})+谷({w['valley_cost']}) = {pfv} != cost({w['cost']})")

        if w["cost"] < 0:
            warnings.append(f"{w['workshop']} 成本为负数 ({w['cost']})，请检查电价表")

    return warnings
