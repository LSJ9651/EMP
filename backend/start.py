#!/usr/bin/env python
"""统一服务启动脚本 — 替代直接调用 uvicorn 或 python main.py"""

import sys
import os

# 确保在 backend 目录执行
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from config import settings

if __name__ == "__main__":
    host = settings.SERVER_HOST
    port = settings.SERVER_PORT
    reload = "--reload" in sys.argv or "-r" in sys.argv

    # 端口检查
    if not settings.check_port_available():
        print(f"[警告] 端口 {port} 已被其他进程占用！")
        print(f"  Windows: netstat -ano | findstr :{port}")
        print(f"  Linux:   lsof -i :{port}")
        print(f"  或设置环境变量更换端口: PORT=9000 python start.py")
        print()

    print(f"=" * 50)
    print(f"  能耗智能管理优化平台 v1.0.0")
    print(f"=" * 50)
    print(f"  服务地址: http://localhost:{port}")
    print(f"  API 文档: http://localhost:{port}/docs")
    print(f"  ReDoc:   http://localhost:{port}/redoc")
    print(f"=" * 50)
    print()

    import uvicorn
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
    )
