"""应用配置 — 集中管理所有环境相关配置"""

import os
import socket
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── 服务端口 ──
    DEFAULT_PORT = 8000
    DEFAULT_HOST = "0.0.0.0"

    # ── LLM API Key 占位符 ──
    # 前端和 API 返回中用此值替代真实 Key，防止 Key 泄露或意外覆盖
    KEY_PLACEHOLDER = "********"

    @property
    def LLM_API_KEY(self) -> str:
        """LLM 对话模型真实 API Key，优先从 .env 读取"""
        return os.environ.get("LLM_API_KEY", "")

    @property
    def LLM_EMBEDDING_API_KEY(self) -> str:
        """LLM 嵌入模型真实 API Key，优先从 .env 读取"""
        return os.environ.get("LLM_EMBEDDING_API_KEY", "")

    @property
    def SERVER_PORT(self) -> int:
        """
        获取服务端口，优先级：
        1. 系统环境变量 PORT
        2. .env 文件 SERVER_PORT
        3. 默认值 8000
        """
        port = os.environ.get("PORT") or os.environ.get("SERVER_PORT")
        if port:
            try:
                return int(port)
            except (ValueError, TypeError):
                pass
        return self.DEFAULT_PORT

    @property
    def SERVER_HOST(self) -> str:
        return os.environ.get("HOST") or os.environ.get("SERVER_HOST") or self.DEFAULT_HOST

    def check_port_available(self) -> bool:
        """检查端口是否可用"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((self.SERVER_HOST, self.SERVER_PORT))
            sock.close()
            return result != 0  # 0 表示端口已被占用
        except Exception:
            return True  # 无法检测时默认允许启动


settings = Settings()
