"""能耗智能管理优化平台 — 应用入口

初始化 FastAPI 应用、注册路由、启动后台模拟线程、配置 CORS。
"""

import threading
import time
import os
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, SessionLocal
from models import Base, ReportSubscription, AgentReport
from services.data_simulator import simulator
from init_db import init_database
from utils.logger import setup_logger
from config import settings

logger = setup_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时建表 + 初始化管理员 + 启动模拟器，关闭时停止模拟器"""
    # 启动前：确保数据库表存在并初始化默认管理员
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表已就绪")

    # 创建 RAG 数据目录
    _ensure_data_dirs()

    # 初始化默认管理员账户
    init_database()

    # 启动数据模拟器
    simulator.start()

    # 记录服务端口配置
    logger.info(f"服务配置: host={settings.SERVER_HOST}, port={settings.SERVER_PORT}")

    # 启动定时分析任务（每分钟检查一次订阅是否需要执行）
    def scheduled_analysis():
        # 延迟10秒等应用完全启动
        time.sleep(10)
        while True:
            try:
                db = SessionLocal()
                now = datetime.now()
                current_time = now.strftime("%H:%M")
                # 查找当前分钟应执行且未在最近一分钟执行过的活跃订阅
                subs = (
                    db.query(ReportSubscription)
                    .filter(
                        ReportSubscription.is_active == True,
                        ReportSubscription.cron_time == current_time,
                    )
                    .all()
                )
                for sub in subs:
                    # 防重复：1分钟内不重复执行
                    if sub.last_run_at and (now - sub.last_run_at).total_seconds() < 60:
                        continue
                    try:
                        _execute_subscription(db, sub)
                    except Exception as e:
                        logger.error(f"执行订阅 {sub.name} 失败: {e}")
                db.close()
            except Exception as e:
                logger.error(f"调度循环异常: {e}")
            time.sleep(60)

    def _execute_subscription(db, sub):
        """同步执行单个订阅任务"""
        from routers.agent import analyze_energy
        import asyncio

        device_ids = None
        if sub.device_ids:
            ids = [int(x.strip()) for x in sub.device_ids.split(",") if x.strip()]
            device_ids = ids[0] if len(ids) == 1 else ids

        start_time = datetime.now().strftime("%Y-%m-%dT00:00:00")
        end_time = datetime.now().strftime("%Y-%m-%dT23:59:59")

        # 在新事件循环中运行异步 analyze_energy
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            analyze_energy(
                device_id=device_ids if isinstance(device_ids, int) else None,
                start_time=start_time,
                end_time=end_time,
                db=db,
            )
        )
        loop.close()

        report = AgentReport(
            report_type="analysis",
            trigger_time=datetime.now(),
            input_summary=f"scheduled: subscription_id={sub.id}, name={sub.name}",
            input_payload={
                "device_id": device_ids if isinstance(device_ids, int) else None,
                "start_time": start_time,
                "end_time": end_time,
                "via": "subscription_scheduled",
            },
            output_json=result,
        )
        db.add(report)
        db.flush()

        # 定时执行也生成通知
        from models import Notification
        n = Notification(
            title=f"定时报告「{sub.name}」已生成",
            content=f"{'日报' if sub.report_type == 'daily' else '周报' if sub.report_type == 'weekly' else '分析报告'}"
                     f"已按计划生成，请前往「智能报告」页面查看详情",
            category="report",
            source_type="agent_report",
            source_id=report.id,
        )
        db.add(n)

        # 发送外部通知（邮件/钉钉）
        if sub.notify_method and sub.notify_method != "system":
            from services.notification_dispatcher import dispatch_notification
            report_data = {
                "report_name": sub.name,
                "report_summary": result.get("summary", "能耗分析报告"),
                "report_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "device_count": result.get("analyzed_devices", 0),
                "report_id": report.id,
            }
            dispatch_result = dispatch_notification(sub, report_data)
            if dispatch_result.get("success"):
                logger.info(f"外部通知已发送 [{sub.notify_method}]: {sub.name}")
            else:
                logger.warning(f"外部通知发送失败 [{sub.notify_method}]: {dispatch_result.get('error')}")

        sub.last_run_at = datetime.now()
        db.commit()
        logger.info(f"已执行订阅: {sub.name} ({sub.cron_time})")

    analysis_thread = threading.Thread(target=scheduled_analysis, daemon=True)
    analysis_thread.start()

    yield

    # 关闭时
    simulator.stop()
    logger.info("应用已关闭")


def _ensure_data_dirs():
    """确保 RAG 相关数据目录存在"""
    dirs = [
        os.getenv("DOCUMENT_UPLOAD_DIR", "./data/documents"),
        os.getenv("CHROMA_PERSIST_DIR", "./data/chromadb"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    logger.info("RAG 数据目录已就绪")


app = FastAPI(
    title="能耗智能管理优化平台",
    description="工业能耗监控与优化系统 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由模块
from routers import devices, telemetry, tariffs, alerts, agent, reports, dashboard, auth, report_center, cost_allocation, chat, ai_config, workflows, notifications, knowledge_base, rag_chat, llm_config

app.include_router(devices.router)
app.include_router(telemetry.router)
app.include_router(tariffs.router)
app.include_router(alerts.router)
app.include_router(agent.router)
app.include_router(reports.router)
app.include_router(dashboard.router)
app.include_router(auth.router)
app.include_router(report_center.router)
app.include_router(cost_allocation.router)
app.include_router(chat.router)
app.include_router(ai_config.router)
app.include_router(workflows.router)
app.include_router(notifications.router)
app.include_router(knowledge_base.router)
app.include_router(rag_chat.router)
app.include_router(llm_config.router)


@app.get("/")
def root():
    """API 根路径"""
    return {
        "code": 200,
        "data": {
            "name": "能耗智能管理优化平台",
            "version": "1.0.0",
            "docs": "/docs",
        },
        "message": "success",
    }


if __name__ == "__main__":
    import uvicorn
    port = settings.SERVER_PORT
    logger.info(f"启动服务: host={settings.SERVER_HOST}, port={port}")
    uvicorn.run("main:app", host=settings.SERVER_HOST, port=port, reload=True)
