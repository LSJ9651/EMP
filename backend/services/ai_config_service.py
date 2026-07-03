"""AI配置服务 — 从数据库读写智能体配置，支持环境变量降级"""

import logging
from sqlalchemy.orm import Session
from models import AIConfigEntry

logger = logging.getLogger(__name__)

# 默认配置值
DEFAULT_CONFIGS = {
    "enable_cloud_agent": "false",
    "coze_api_key": "",
    "coze_api_base": "https://api.coze.cn",
    "analyze_enabled": "false",
    "analyze_workflow_id": "",
    "analyze_timeout": "120",
    "optimize_enabled": "false",
    "optimize_workflow_id": "",
    "optimize_timeout": "120",
    "chat_enabled": "false",
    "chat_bot_id": "",
    "chat_timeout": "30",
}


class AIConfigService:
    """AI 配置服务 — 单例模式，无缓存，每次调用实时读取数据库"""

    @staticmethod
    def init_defaults(db: Session):
        """初始化默认配置（仅当数据库为空时）"""
        existing = db.query(AIConfigEntry.config_key).all()
        existing_keys = {e[0] for e in existing}

        for key, value in DEFAULT_CONFIGS.items():
            if key not in existing_keys:
                db.add(AIConfigEntry(config_key=key, config_value=value))

        db.commit()
        logger.info("[ai_config] 默认配置初始化完成")

    @staticmethod
    def get_all(db: Session) -> dict:
        """获取所有 AI 配置，返回结构化字典"""
        AIConfigService.init_defaults(db)

        entries = db.query(AIConfigEntry).all()
        raw = {e.config_key: e.config_value for e in entries}

        return {
            "enable_cloud_agent": raw.get("enable_cloud_agent", "false") == "true",
            "coze_api_key": raw.get("coze_api_key", ""),
            "coze_api_base": raw.get("coze_api_base", "https://api.coze.cn"),
            "analyze": {
                "enabled": raw.get("analyze_enabled", "false") == "true",
                "workflow_id": raw.get("analyze_workflow_id", ""),
                "timeout": int(raw.get("analyze_timeout", "120")),
            },
            "optimize": {
                "enabled": raw.get("optimize_enabled", "false") == "true",
                "workflow_id": raw.get("optimize_workflow_id", ""),
                "timeout": int(raw.get("optimize_timeout", "120")),
            },
            "chat": {
                "enabled": raw.get("chat_enabled", "false") == "true",
                "bot_id": raw.get("chat_bot_id", ""),
                "timeout": int(raw.get("chat_timeout", "30")),
            },
        }

    @staticmethod
    def update_all(db: Session, config: dict) -> bool:
        """批量更新 AI 配置"""
        flat = {}
        for key, value in config.items():
            if isinstance(value, bool):
                flat[key] = "true" if value else "false"
            elif isinstance(value, (int, float)):
                flat[key] = str(value)
            elif isinstance(value, str):
                flat[key] = value

        try:
            for key, value in flat.items():
                if key not in DEFAULT_CONFIGS:
                    continue
                entry = db.query(AIConfigEntry).filter(AIConfigEntry.config_key == key).first()
                if entry:
                    entry.config_value = value
                else:
                    db.add(AIConfigEntry(config_key=key, config_value=value))

            db.commit()
            logger.info(f"[ai_config] 配置已更新: {list(flat.keys())}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"[ai_config] 配置更新失败: {e}")
            return False

    @staticmethod
    def is_cloud_enabled(db: Session, service_type: str) -> bool:
        """判断指定服务是否应使用云端模式

        返回 True 的条件：
        1. 总开关 enable_cloud_agent == "true"
        2. 服务开关 {service_type}_enabled == "true"
        3. API Key 已配置（非空）
        4. 服务 ID（workflow_id/bot_id）已配置（非空）

        注意：之前的实现只检查开关，不检查实际配置是否完整，导致状态显示与实际执行不一致。
        """
        AIConfigService.init_defaults(db)

        master = (
            db.query(AIConfigEntry).filter(AIConfigEntry.config_key == "enable_cloud_agent").first()
        )
        if not master or master.config_value != "true":
            return False

        service_key = f"{service_type}_enabled"
        entry = db.query(AIConfigEntry).filter(AIConfigEntry.config_key == service_key).first()
        if not entry or entry.config_value != "true":
            return False

        # 新增：检查 API Key 是否配置
        api_key = AIConfigService.get_api_key(db)
        if not api_key:
            logger.warning(f"[ai_config] {service_type} 云端模式未启用：API Key 未配置")
            return False

        # 新增：检查服务 ID 是否配置
        service_id = AIConfigService.get_service_id(db, service_type)
        if not service_id:
            logger.warning(f"[ai_config] {service_type} 云端模式未启用：服务 ID 未配置")
            return False

        return True

    @staticmethod
    def get_service_id(db: Session, service_type: str) -> str:
        """获取指定服务的工作流ID/BotID

        Args:
            db: 数据库会话
            service_type: analyze / optimize / chat
        Returns:
            workflow_id (analyze/optimize) 或 bot_id (chat)
        """
        import os

        AIConfigService.init_defaults(db)

        if service_type == "chat":
            id_key = f"{service_type}_bot_id"
            env_key = "COZE_CHAT_BOT_ID"
        else:
            id_key = f"{service_type}_workflow_id"
            env_key = f"COZE_{service_type.upper()}_WORKFLOW_ID"

        entry = db.query(AIConfigEntry).filter(AIConfigEntry.config_key == id_key).first()

        if entry and entry.config_value:
            return entry.config_value

        return os.getenv(env_key, "")

    @staticmethod
    def get_api_key(db: Session) -> str:
        """获取 Coze API Key（数据库优先，环境变量降级）"""
        import os

        AIConfigService.init_defaults(db)

        entry = db.query(AIConfigEntry).filter(AIConfigEntry.config_key == "coze_api_key").first()
        if entry and entry.config_value:
            return entry.config_value

        return os.getenv("COZE_API_KEY", "")

    @staticmethod
    def get_api_base(db: Session) -> str:
        """获取 Coze API Base URL"""
        import os

        AIConfigService.init_defaults(db)

        entry = db.query(AIConfigEntry).filter(AIConfigEntry.config_key == "coze_api_base").first()
        if entry and entry.config_value:
            return entry.config_value

        return os.getenv("COZE_API_BASE", "https://api.coze.cn")

    @staticmethod
    def get_service_timeout(db: Session, service_type: str) -> int:
        """获取指定服务的超时时间"""
        import os

        AIConfigService.init_defaults(db)

        timeout_key = f"{service_type}_timeout"
        entry = db.query(AIConfigEntry).filter(AIConfigEntry.config_key == timeout_key).first()

        if entry and entry.config_value:
            try:
                return int(entry.config_value)
            except ValueError:
                pass

        if service_type == "chat":
            return int(os.getenv("COZE_CHAT_TIMEOUT", 30))
        return int(os.getenv("COZE_AGENT_TIMEOUT", 120))



# 全局服务实例
ai_config_service = AIConfigService()
