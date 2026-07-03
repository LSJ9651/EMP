# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.0.0] - 2026-07-04

### Added
- **RAG 知识库问答**：上传 PDF/TXT/MD 文档 → 自动解析分块 → ChromaDB 向量化 → LLM 检索增强生成，支持引用溯源
- **LLM 配置管理**：对话模型与嵌入模型独立配置，支持 OpenAI 兼容接口 / Ollama 本地模型混合模式
- **知识库管理**：可视化创建/编辑/删除知识库，拖拽上传文档，自动后台处理与状态轮询
- **API Key 安全加固**：敏感 Key 迁移到 `.env` 环境变量存储，前端只显示 `********` 占位符，杜绝脱敏 Key 覆盖
- **AI 配置页重构**：标签页拆分（云端智能体 / 本地 LLM），配置更清晰
- **聊天窗口扩展**：支持普通对话与 RAG 问答两种模式切换，状态指示器区分云端/本地模型
- **内联组件**：PageTitle、StatCard、Toolbar 等通用 UI 组件
- **项目文档**：新增 `docs/RAG知识库问答.md` 完整功能说明
- **作者声明**：新增 `作者声明.md`（仅限个人学习使用）

### Changed
- API Key 读取优先级：`.env` 环境变量 → 数据库 `llm_config` 表
- 前后端端口统一为 8000/5173，`start.bat` 和 `stop.bat` 兼容中英文 Windows
- `frontend/dist/`、`backend/backups/`、`backend/data/` 加入 `.gitignore`

### Fixed
- API Key 被脱敏值覆盖导致 LLM 调用失败的 Bug
- `backend/init_db.py` 被误删导致 `main.py` 启动报 `ModuleNotFoundError`
- `stop.bat` 在中文 Windows 上无法匹配 `LISTENING` 状态
- `start.bat` 依赖检测使用全局 Python 而非 venv 内的 Python
- 日志备份文件 (`backend.err`, `backend.log`) 清理

### Removed
- 清理冗余文件：`screenshot_test.py` / `screenshot_test2.py` / `backend/backups/`（47MB）/ `backend/test_*.db` / 空 `energy_optimizer.db`（根目录）
- 废弃重复脚本：`backend/init_db.py`（恢复后用精简版）、`backend/start.py`、`frontend/dist/`（构建产物）

## [1.0.0-rc] - 2026-06-21

### Added
- Email/DingTalk 报告订阅通知配置
- AI 对话双轮工具调用（标签指令 → 设备匹配 → 能耗分析 → 二次对话）
- 细粒度用户权限管理系统（admin/dispatcher/operator/viewer 四角色）
- 成本分摊功能（按车间/设备维度的电费统计）
- 报表中心（日报/周报/月报生成与 Excel 导出）
- 全部设备分析关键字支持（`["全部"]` 参数）
- 前端 SSE 流式渲染 + 工具状态指示
- 智能报告表单验证和加载状态
- 智能报告订阅功能（时间范围、分页）
- 设备同义词匹配引擎（精确/别名/模糊三级）
- 通知消息中心（铃铛组件 + 已读状态管理）
- bcrypt 密码哈希（兼容旧 SHA256 格式）
- 统一日志系统（结构化 logger 替换 print）
- 前端 vitest 测试框架（核心组件基础渲染测试）
- API 接口文档、部署指南、开发者指南
- 本项目 CHANGELOG

### Changed
- AI 对话响应状态指示（思考中/输入中/分析中）
- 移除快捷问题功能
- 侧边栏权限匹配修复
- Vite 代理目标改为 localhost:8080
- 后端 `models.py`（273 行单文件）拆分为 `models/` 包（7 个领域文件）
- 前端组件目录按 `common/` `chat/` `charts/` `config/` 分类重构
- 依赖版本锁定（httpx 0.28.1，cozepy 0.20.0，passlib[bcrypt] 1.7.4）
- 路由认证守卫补齐（devices/alerts/tariffs 变更端点）
- README 全面更新（架构设计、权限系统、智能体集成、贡献指南）
- 测试文件清理移入 `tests/fixtures/`

### Fixed
- Dashboard 500 错误（Vite 代理端口多次回退）
- Coze 4028 配额耗尽错误传播
- JSON 解析错误
- 智能体不可用错误提示
- estimated_cost_saved 显示为 0 的问题
- 前端组件重构后 import 路径断裂
- 前端构建失败（Can't resolve "../api/api.js"）
- 登录密码验证（bcrypt + 旧 SHA256 兼容）
- 后端端口一致化（统一使用 8000，配置优先级：环境变量 > .env > 默认值）
