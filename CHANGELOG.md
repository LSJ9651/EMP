# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.0.0] - 2026-06-21

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
