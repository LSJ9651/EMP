"""AI相关模型 — AIConfigEntry, ChatHistory, WorkflowExecution, AgentReport, ScheduleTask, ScheduleExecution"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .base import Base


class AgentReport(Base):
    """智能体分析/调度结果表"""
    __tablename__ = "agent_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(50), nullable=False, comment="报告类型：analysis/schedule")
    trigger_time = Column(DateTime, default=datetime.now, comment="触发时间")
    input_summary = Column(Text, comment="输入摘要")
    input_payload = Column(JSON, comment="完整的入参JSON，便于追溯")
    output_json = Column(JSON, comment="输出结果JSON")
    created_at = Column(DateTime, default=datetime.now)


class ScheduleTask(Base):
    """调度优化任务表"""
    __tablename__ = "schedule_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, comment="设备ID")
    start_time = Column(String(5), nullable=False, comment="开始时间 HH:MM")
    end_time = Column(String(5), nullable=False, comment="结束时间 HH:MM")
    action_type = Column(String(20), nullable=False, comment="动作类型：run/idle/off")
    source = Column(String(20), default="agent", comment="来源：agent/manual")
    priority = Column(Integer, default=0, comment="优先级")
    created_at = Column(DateTime, default=datetime.now)

    # 关联
    device = relationship("Device", back_populates="schedule_tasks")


class ScheduleExecution(Base):
    """调度执行追踪表"""
    __tablename__ = "schedule_executions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("agent_reports.id"), comment="关联的报告ID")
    status = Column(String(20), default="pending", comment="执行状态：pending/running/completed")
    baseline_cost = Column(Float, default=0.0, comment="基线成本(元)")
    actual_cost = Column(Float, default=0.0, comment="实际成本(元)")
    saved_cost = Column(Float, default=0.0, comment="实际节省成本(元)")
    started_at = Column(DateTime, comment="开始执行时间")
    completed_at = Column(DateTime, comment="完成时间")
    created_at = Column(DateTime, default=datetime.now)


class ChatHistory(Base):
    """对话记录表"""
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, index=True, comment="会话ID")
    role = Column(String(20), nullable=False, comment="角色：user/assistant")
    content = Column(Text, nullable=False, comment="消息内容")
    intent = Column(String(50), comment="识别意图（仅assistant记录有值）")
    workflow_type = Column(String(50), comment="调用的工作流类型")
    parent_id = Column(Integer, comment="关联父消息ID，工具调用前后关联")
    tool_type = Column(String(50), comment="调用的工具类型")
    tool_params = Column(JSON, comment="工具调用参数")
    tool_result = Column(JSON, comment="工具执行结果")
    match_status = Column(JSON, comment="设备匹配状态")
    is_final = Column(Boolean, default=True, comment="是否为最终回答")
    needs_user_input = Column(Boolean, default=False, comment="是否需要用户进一步输入")
    created_at = Column(DateTime, default=datetime.now)


class AIConfigEntry(Base):
    """AI配置键值对表"""
    __tablename__ = "ai_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), nullable=False, unique=True, comment="配置键")
    config_value = Column(Text, nullable=False, comment="配置值")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class WorkflowExecution(Base):
    """工作流执行记录表 — 记录每次 analyze/optimize 调用的输入输出"""
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_type = Column(String(20), nullable=False, comment="analyze | optimize")
    user_id = Column(Integer, nullable=True, comment="触发用户ID")
    params_json = Column(JSON, nullable=True, comment="入参快照")
    result_json = Column(JSON, nullable=True, comment="输出结果")
    mode_used = Column(String(20), default="unknown", comment="cloud | local | unknown")
    status = Column(String(20), default="pending", comment="pending | running | completed | failed")
    elapsed_ms = Column(Integer, nullable=True, comment="执行耗时(毫秒)")
    error_message = Column(Text, nullable=True, comment="失败原因")
    created_at = Column(DateTime, default=datetime.now)
