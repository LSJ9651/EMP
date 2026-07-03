# 能耗智能管理优化平台

> 工业能耗监控与智能优化系统 — 基于 Python FastAPI + Vue 3 + Vite + SQLite + ChromaDB/RAG + Coze AI 工作流

## 项目简介

能耗智能管理优化平台是一套面向工业场景的综合性能耗管理系统，覆盖**设备能耗实时监控、分时电价策略、异常告警、AI 智能分析与调度优化、RAG 知识库问答、智能对话助手、成本分摊、报告生成**等核心功能。系统支持本地规则引擎与 Coze 云端工作流双模式运行，可根据配置自动切换。

### 核心功能模块

| 模块 | 说明 |
|------|------|
| **看板总览** | 实时功率、今日能耗、CO₂排放、设备状态、能流桑基图、功率趋势 |
| **设备管理** | 设备 CRUD、能效排行、能耗详情 |
| **实时监控** | 各设备最新/当前功率、历史遥测数据查询 |
| **告警管理** | 阈值配置、告警记录、自动评估、知识库建议 |
| **电价策略** | 分时电价配置（峰/平/谷）、当前时段电价 |
| **智能分析** | 基于 Coze 工作流或本地规则的设备能耗异常检测与节能建议 |
| **调度优化** | 基于电价时段的设备启停方案优化，预估节费 |
| **智能对话** | 双轮工具调用（标签指令 → 设备匹配 → 能耗分析 → 二次对话），支持全量设备分析 |
| **RAG 知识库问答** | 上传 PDF/TXT/MD 文档 → 自动分块向量化 → 基于 ChromaDB 检索 → LLM 生成带引用回答 |
| **LLM 配置管理** | 可视化配置对话模型与嵌入模型（OpenAI 兼容 / Ollama 本地），支持混合模式 |
| **AI 配置管理** | 可视化配置 Coze API Key、工作流 ID、云端开关 |
| **成本分摊** | 按车间/设备维度的电费统计与明细 |
| **报表中心** | 日报/周报/月报，能耗与告警数据导出 |
| **报告订阅** | 定时自动生成分析报告，支持 Email/DingTalk 通知 |
| **用户认证** | 细粒度角色权限控制（admin/dispatcher/operator/viewer） |

## 最近更新

### v1.0.0 (2026-07-04)

- **RAG 知识库问答**：上传 PDF/TXT/MD 文档 → 自动解析分块 → ChromaDB 向量化 → LLM 检索增强生成，支持引用溯源
- **LLM 配置管理**：对话模型与嵌入模型独立配置，支持 OpenAI 兼容接口 / Ollama 本地模型混合模式
- **API Key 安全加固**：敏感 Key 迁移到 `.env` 环境变量存储，前端只显示占位符，杜绝脱敏 Key 覆盖问题
- **知识库管理**：可视化创建/编辑/删除知识库，拖拽上传文档，自动处理状态轮询
- **AI 配置页重构**：标签页拆分（云端智能体 / 本地 LLM），配置更清晰
- **聊天窗口扩展**：支持普通对话与 RAG 问答两种模式切换，状态指示器区分云端/本地模型
- **项目文档**：新增 `docs/RAG知识库问答.md` 完整功能说明

### 更早版本

- **密码安全升级**：SHA256 → bcrypt 哈希算法，兼容旧密码格式
- **路由认证守卫**：所有变更端点添加基于角色的权限依赖注入
- **统一日志系统**：替换散落的 `print()` 为结构化 logger
- **后端模型拆分**：单文件 273 行 `models.py` 拆分为按领域组织的 `models/` 包（9 个文件）
- **前端组件重构**：14+ 组件按 `common/` `chat/` `charts/` `config/` 分类
- **测试框架**：前端引入 vitest + @vue/test-utils + jsdom，核心组件覆盖基础渲染测试
- **依赖清理**：锁定版本号，补全 `passlib[bcrypt]` 等运行时依赖
- **Email/DingTalk 通知**：报告订阅支持邮件和钉钉机器人通知
- **AI 双轮工具调用**：标签指令解析 → 设备匹配 → 工作流调用 → 二次对话
- **全量设备分析**：支持 `["全部"]` 参数对全部设备执行能耗分析
- **成本分摊**：按车间维度的电费统计与明细
- **报告订阅**：定时生成日报/周报/分析报告

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | 0.104.1 |
| ASGI 服务器 | Uvicorn | 0.24.0 |
| ORM | SQLAlchemy | 2.0.23 |
| 数据验证 | Pydantic | 2.13.0 |
| AI 集成 | cozepy SDK (Coze) | 0.20.0 |
| 向量数据库 | ChromaDB | 0.4.24 |
| 安全 | passlib[bcrypt] | 1.7.4 |
| 前端框架 | Vue 3 | ^3.5.32 |
| 构建工具 | Vite | ^5.4.0 |
| UI 组件库 | Element Plus | ^2.14.0 |
| 图表库 | ECharts | ^5.6.0 |
| 状态管理 | Pinia | ^2.1.0 |
| 前端测试 | Vitest | ^4.1 |
| 数据库 | SQLite | - |

## 快速开始

### 环境要求

| 工具 | 最低版本 |
|------|---------|
| Python | >= 3.9 |
| Node.js | >= 18 |
| npm | >= 9 |

### 0. 一键启动（Windows）

在项目根目录直接运行 `start.bat`，脚本会自动完成环境检查、依赖安装并启动全部服务：

```powershell
start.bat
```

启动流程：
1. 检查 Python 和 Node.js 环境
2. 自动创建 Python 虚拟环境并安装后端依赖（`pip install -r requirements.txt`）
3. 安装前端依赖（`npm install`）
4. 启动后端服务 → http://localhost:8000（含健康检查等待）
5. 启动前端服务 → http://localhost:5173
6. 自动打开浏览器

停止服务，运行：

```powershell
stop.bat
```

脚本会自动查找并终止占用 8000（后端）和 5173（前端）端口的进程，兼容中文/英文 Windows。

---

### 1. 后端启动

```powershell
cd backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 初始化数据库与模拟数据（可选：服务启动时也会自动建表）
python scripts/init_db.py
python scripts/init_mock_data.py

# 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

后端运行后访问：
- API 文档：http://localhost:8000/docs
- ReDoc 文档：http://localhost:8000/redoc

### 2. 前端启动

```powershell
cd frontend
npm install
npm run dev
```

浏览器访问：http://localhost:5173

### 3. 测试账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |

> **停止服务**：运行项目根目录下的 `stop.bat` 即可一键终止后端和前端服务。

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Vite)                        │
│  登录 → 看板 → 设备管理 → 电价策略 → 告警管理                  │
│  调度优化 → 智能报告 → 报表中心 → 成本分摊 → AI配置            │
│  知识库管理 → 用户管理(admin) + 对话窗口(悬浮按钮)             │
│    (普通对话 / RAG问答 模式切换)                               │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/SSE (localhost:8000)
┌──────────────────────────▼──────────────────────────────────┐
│                  后端 (FastAPI + SQLAlchemy)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐│
│  │ Routers  │  │ Services │  │Middleware│  │   Scheduler  ││
│  │ 18模块   │  │ 19服务   │  │ 权限控制 │  │  定时分析    ││
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘│
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                 ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │   SQLite     │ │  Coze API    │ │  ChromaDB    │
   │   数据库     │ │ (云端智能体) │ │  (向量存储)  │
   └──────────────┘ └──────────────┘ └──────────────┘
```

### RAG 知识库问答数据流

```
上传文档(PDF/TXT/MD)
      ↓
文档处理器: 解析 → 递归分块(500ch) → 向量化(Embeddings) → ChromaDB
      ↓
用户提问(选择知识库)
      ↓
RAG 检索器: 向量相似度搜索 → Top-K 结果 → 格式化为上下文
      ↓
构建 Prompt: [System Prompt(上下文约束) + 历史消息 + 用户问题]
      ↓
LLM 流式生成 → SSE 返回前端(增量delta + 完成done + 引用来源)
```

### AI 对话数据流

```
用户提问 → Coze Bot(第一次) → SSE流式返回(含<INTERNAL_CMD>标签)
  → TagParser解析标签 → DeviceMatcher设备匹配
  → ToolHandler调用能耗分析 → 构建增强消息
  → Coze Bot(第二次) → SSE流式返回分析报告 → 前端渲染
```

## 项目结构

```
energy-optimizer-platform/
├── README.md
├── CHANGELOG.md
├── .gitignore                      # 忽略规则（含 api key、数据库、构建产物）
├── start.bat                       # Windows 一键启动脚本
├── stop.bat                        # Windows 一键停止脚本
├── scripts/
│   └── check_port_consistency.py   # 端口一致性检查
├── docs/                           # 文档
│   ├── RAG知识库问答.md             # RAG 功能完整说明
│   ├── AI智能体对话系统功能设计报告.md
│   ├── API接口文档.md
│   ├── 部署指南.md
│   ├── 开发者指南.md
│   └── ...（更多文档）
├── backend/                        # 后端服务
│   ├── main.py                     # 应用入口（路由注册、CORS、生命周期）
│   ├── init_db.py                  # 启动时建表 + 管理员初始化
│   ├── database.py                 # 数据库连接管理
│   ├── config.py                   # 应用配置（环境变量读取）
│   ├── requirements.txt            # Python 依赖（开发环境）
│   ├── requirements.prod.txt       # Python 依赖（生产环境）
│   ├── .env                        # 环境变量（敏感信息，已 gitignore）
│   ├── .env.example                # 环境变量示例
│   ├── models/                     # 数据模型包（9 个文件）
│   │   ├── __init__.py             # 统一导出
│   │   ├── base.py                 # ORM 基类
│   │   ├── user.py                 # User, UserPermission
│   │   ├── device.py               # Device, DeviceSynonym
│   │   ├── alert.py                # AlertThreshold, AlertRecord
│   │   ├── energy.py               # Telemetry, TariffPolicy
│   │   ├── ai.py                   # AgentReport, ScheduleTask, AIConfigEntry 等
│   │   ├── rag.py                  # KnowledgeBase, Document, DocumentChunk,
│   │   │                           #   RAGChatSession, RAGChatMessage, LLMConfig
│   │   └── subscription.py         # ReportSubscription, Notification
│   ├── routers/                    # API 路由模块（18 个）
│   │   ├── auth.py                 # 认证管理
│   │   ├── dashboard.py            # 看板
│   │   ├── devices.py              # 设备管理
│   │   ├── telemetry.py            # 实时数据
│   │   ├── tariffs.py              # 电价策略
│   │   ├── alerts.py               # 告警管理
│   │   ├── agent.py                # 智能体（分析/优化/报告/订阅）
│   │   ├── chat.py                 # 智能对话助手（SSE 流式）
│   │   ├── reports.py              # 报告导出
│   │   ├── report_center.py        # 报表中心
│   │   ├── cost_allocation.py      # 成本分摊
│   │   ├── ai_config.py            # Coze 云端智能体配置
│   │   ├── llm_config.py           # 本地 LLM 配置
│   │   ├── workflows.py            # 工作流统一调用
│   │   ├── notifications.py        # 消息通知
│   │   ├── knowledge_base.py       # 知识库管理（CRUD + 文档上传）
│   │   └── rag_chat.py             # RAG 对话（SSE 流式 + 会话管理）
│   ├── services/                   # 业务服务层（19 个）
│   │   ├── agent_adapter.py        # 智能体适配层（云端/本地双模式）
│   │   ├── ai_config_service.py    # AI 配置读写
│   │   ├── alert_evaluator.py      # 告警评估器
│   │   ├── chat_service.py         # 对话服务
│   │   ├── coze_client.py          # Coze SDK 客户端封装
│   │   ├── cost_allocation_service.py # 成本分摊计算
│   │   ├── data_simulator.py       # 模拟数据生成
│   │   ├── device_matcher.py       # 三级设备匹配引擎
│   │   ├── document_processor.py   # 文档解析 + 分块 + 向量化
│   │   ├── intent_recognizer.py    # 意图识别
│   │   ├── llm_config_service.py   # LLM 配置读写 + API Key 安全保护
│   │   ├── llm_factory.py          # LLM / Embeddings 工厂（OpenAI/Ollama）
│   │   ├── notification_dispatcher.py # 通知分发（邮件/钉钉）
│   │   ├── rag_chat_service.py     # RAG 对话流编排（检索→生成→保存）
│   │   ├── rag_retriever.py        # ChromaDB 向量检索 + 结果格式化
│   │   ├── scheduling_core.py      # 调度核心算法
│   │   ├── tag_parser.py           # 智能体标签指令解析
│   │   ├── tool_handler.py         # 工具调用处理器
│   │   └── workflow_service.py     # 工作流服务封装
│   ├── middleware/
│   │   └── permission.py           # 角色权限控制与依赖注入
│   ├── utils/                      # 工具模块
│   │   ├── crypto.py               # bcrypt 密码哈希
│   │   └── logger.py               # 统一日志配置
│   ├── scripts/
│   │   ├── init_db.py              # 初始化数据库（含种子数据）
│   │   ├── init_mock_data.py       # 生成模拟测试数据
│   │   ├── data_cleanup.py         # 数据清理维护
│   │   ├── generate_report.py      # 报告生成脚本
│   │   └── verify_apis.py          # API 验证脚本
│   └── tests/                      # 测试用例
│       ├── test_api.py
│       ├── test_all_devices_analysis.py
│       ├── test_notify_config.py
│       └── fixtures/               # 测试数据 JSON
├── frontend/                       # 前端应用
│   ├── package.json
│   ├── vite.config.js
│   ├── vitest.config.js            # Vitest 测试配置
│   ├── index.html
│   ├── .env                        # 前端环境变量（已 gitignore）
│   └── src/
│       ├── main.js                 # Vue 应用入口
│       ├── App.vue                 # 根组件（布局 + 导航）
│       ├── style.scss              # 全局样式
│       ├── api/api.js              # API 接口层
│       ├── router/index.js         # 路由配置
│       ├── store/                  # Pinia 状态管理
│       │   ├── authStore.js        # 认证状态
│       │   └── energyStore.js      # 能耗数据状态
│       ├── views/                  # 页面视图（12 个）
│       │   ├── Login.vue           # 登录
│       │   ├── Dashboard.vue       # 看板总览
│       │   ├── Devices.vue         # 设备管理
│       │   ├── Alerts.vue          # 告警管理
│       │   ├── Tariff.vue          # 电价策略
│       │   ├── CostAllocation.vue  # 成本分摊
│       │   ├── ReportCenter.vue    # 报表中心
│       │   ├── AgentReports.vue    # 智能体报告
│       │   ├── ScheduleOptimize.vue# 调度优化
│       │   ├── AIConfig.vue        # AI 配置（云端+本地LLM标签页）
│       │   ├── KnowledgeBase.vue   # 知识库管理
│       │   └── UserManagement.vue  # 用户管理
│       └── components/             # 通用组件
│           ├── LoginBackground.vue # 登录背景
│           ├── common/             # 通用 UI
│           │   ├── BellNotification.vue # 通知铃铛
│           │   ├── PageTitle.vue        # 页面标题
│           │   ├── StatCard.vue         # 统计卡片
│           │   ├── Toolbar.vue          # 工具栏
│           │   └── RealTimeClock.vue    # 实时时钟
│           ├── chat/               # 对话相关
│           │   ├── ChatFloatButton.vue    # 悬浮按钮
│           │   ├── ChatWindow.vue         # 对话窗口（普通+RAG双模式）
│           │   ├── ChatMessage.vue        # 消息气泡（支持引用来源）
│           │   └── DeviceConfirmDialog.vue# 设备确认弹窗
│           ├── charts/             # 图表组件
│           │   ├── EnergyFlowChart.vue # 能流图
│           │   ├── SankeyChart.vue     # 桑基图
│           │   ├── GanttChart.vue      # 甘特图
│           │   ├── TrendChart.vue      # 趋势图
│           │   └── chartTheme.js       # 图表主题
│           ├── config/             # 配置相关
│           │   ├── LLMConfigForm.vue          # LLM 配置表单
│           │   ├── EmailNotifyConfig.vue      # 邮件通知配置
│           │   ├── DingtalkNotifyConfig.vue   # 钉钉通知配置
│           │   ├── ServiceConfigCard.vue      # 服务配置卡片
│           │   └── ReportCard.vue             # 报告卡片
│           └── __tests__/          # 组件测试
│               └── BellNotification.test.js
```

## 环境变量

### 后端（`backend/.env`）

| 变量名 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接 URL | `sqlite:///./energy_optimizer.db` |
| `DEBUG` | 调试模式开关 | `false` |
| `SERVER_PORT` | 后端服务端口 | `8000` |
| `SERVER_HOST` | 绑定地址 | `0.0.0.0` |
| `LLM_API_KEY` | LLM 对话模型 API Key（OpenAI 兼容） | (留空则用数据库值) |
| `LLM_EMBEDDING_API_KEY` | LLM 嵌入模型 API Key | (留空则用数据库值) |
| `COZE_API_KEY` | Coze API 访问令牌 | (留空则使用本地模式) |
| `COZE_API_BASE` | Coze API 端点 | `https://api.coze.cn` |
| `COZE_ANALYZE_WORKFLOW_ID` | 能耗分析工作流 ID | (留空则使用本地模式) |
| `COZE_OPTIMIZE_WORKFLOW_ID` | 调度优化工作流 ID | (留空则使用本地模式) |
| `COZE_CHAT_BOT_ID` | 对话智能体 Bot ID | (留空则使用本地模式) |
| `COZE_AGENT_TIMEOUT` | 工作流调用超时（秒） | `120` |
| `COZE_CHAT_TIMEOUT` | 对话智能体超时（秒） | `30` |

### 前端（`frontend/.env`）

| 变量名 | 说明 | 默认值 |
|------|------|--------|
| `BACKEND_PORT` | 后端服务端口（Vite 代理目标） | `8000` |
| `BACKEND_HOST` | 后端服务地址 | `localhost` |

> **API Key 安全**：LLM_API_KEY 和 LLM_EMBEDDING_API_KEY 仅存在于 `.env` 文件（已 gitignore），前端配置页始终显示 `********` 占位符，杜绝 Key 泄露。服务内部优先读取环境变量，降级到数据库存储。

> **本地/云端切换规则**：系统依次检查 `enable_cloud_agent` 总开关 → 各服务子开关 → API Key → Workflow/Bot ID，任一条件不满足则自动降级为本地规则引擎。管理员可在 AI 管理页中可视化配置。

## API 接口概览

<details>
<summary><b>认证管理 — /api/auth</b></summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 用户登录 |
| GET | `/api/auth/users` | 用户列表 |
| POST | `/api/auth/users` | 创建用户 |
| PUT | `/api/auth/users/{id}` | 更新用户 |
</details>

<details>
<summary><b>看板 — /api/dashboard</b></summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard/overview` | 看板概览（功率/能耗/CO₂/告警/设备） |
| GET | `/api/dashboard/energyflow` | 能流桑基图数据 |
| GET | `/api/dashboard/trend` | 多设备功率趋势 |
| GET | `/api/dashboard/alerts-bar` | 最新告警滚动条 |
</details>

<details>
<summary><b>设备管理 — /api/devices</b></summary>

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|:---:|
| GET | `/api/devices/list` | 设备列表 | - |
| GET | `/api/devices/ranking` | 能效排行榜 | - |
| GET | `/api/devices/{id}` | 设备详情 | - |
| POST | `/api/devices/` | 创建设备 | ✔ |
| PUT | `/api/devices/{id}` | 更新设备 | ✔ |
| DELETE | `/api/devices/{id}` | 删除设备 | ✔ |
</details>

<details>
<summary><b>实时数据 — /api/telemetry</b></summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/telemetry/latest` | 各设备最新能耗 |
| GET | `/api/telemetry/current` | 所有设备当前功率 |
| GET | `/api/telemetry/range` | 历史能耗查询 |
</details>

<details>
<summary><b>电价策略 — /api/tariffs</b></summary>

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|:---:|
| GET | `/api/tariffs/` | 电价列表 | - |
| POST | `/api/tariffs/` | 创建电价 | ✔ |
| PUT | `/api/tariffs/{id}` | 更新电价 | ✔ |
| GET | `/api/tariffs/current` | 当前时段电价 | - |
</details>

<details>
<summary><b>告警管理 — /api/alerts</b></summary>

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|:---:|
| GET | `/api/alerts/thresholds` | 阈值配置列表 | - |
| POST | `/api/alerts/thresholds` | 创建阈值 | ✔ |
| PUT | `/api/alerts/thresholds/{id}` | 更新阈值 | ✔ |
| GET | `/api/alerts/records` | 告警记录 | - |
| PUT | `/api/alerts/records/{id}/resolve` | 处理告警 | ✔ |
| GET | `/api/alerts/stats` | 告警统计 | - |
| GET | `/api/alerts/suggestions` | 处理建议 | - |
</details>

<details>
<summary><b>智能体 — /api/agent</b></summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/agent/analyze` | 能耗分析（云端/本地双模式） |
| POST | `/api/agent/optimize` | 调度优化 |
| GET | `/api/agent/reports` | 分析报告列表 |
| GET | `/api/agent/subscriptions` | 订阅列表 |
| POST | `/api/agent/subscriptions` | 创建订阅 |
| PUT | `/api/agent/subscriptions/{id}` | 更新订阅 |
| DELETE | `/api/agent/subscriptions/{id}` | 删除订阅 |
| POST | `/api/agent/subscriptions/{id}/run` | 手动触发定时任务 |
</details>

<details>
<summary><b>智能对话 — /api/agent/chat</b></summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/agent/chat` | 发送消息（SSE 流式返回） |
| GET | `/api/agent/chat/history` | 对话历史 |
</details>

<details>
<summary><b>RAG 对话 — /api/rag</b></summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/rag/chat` | RAG 对话（SSE 流式，含引用来源） |
| GET | `/api/rag/sessions` | 会话列表 |
| POST | `/api/rag/sessions` | 创建会话 |
| DELETE | `/api/rag/sessions/{session_id}` | 删除会话 |
| GET | `/api/rag/sessions/{session_id}/messages` | 消息历史 |
</details>

<details>
<summary><b>知识库管理 — /api/knowledge-bases</b></summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/knowledge-bases/` | 知识库列表 |
| POST | `/api/knowledge-bases/` | 创建知识库 |
| PUT | `/api/knowledge-bases/{kb_id}` | 更新知识库 |
| DELETE | `/api/knowledge-bases/{kb_id}` | 删除知识库 |
| GET | `/api/knowledge-bases/{kb_id}/documents` | 文档列表 |
| POST | `/api/knowledge-bases/{kb_id}/documents/upload` | 上传文档（PDF/TXT/MD） |
| DELETE | `/api/knowledge-bases/{kb_id}/documents/{doc_id}` | 删除文档 |
| POST | `/api/knowledge-bases/{kb_id}/documents/{doc_id}/reprocess` | 重新处理文档 |
</details>

<details>
<summary><b>LLM 配置 — /api/llm-config</b></summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/llm-config/` | 获取配置（API Key 显示占位符） |
| POST | `/api/llm-config/` | 保存配置（占位符不覆盖真实 Key） |
| POST | `/api/llm-config/test` | 测试 LLM / Embeddings 连接 |
</details>

<details>
<summary><b>工作流 — /api/workflows</b></summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/workflows/analyze` | 执行能耗分析工作流 |
| POST | `/api/workflows/optimize` | 执行调度优化工作流 |
| GET | `/api/workflows/history` | 执行历史 |
| GET | `/api/workflows/history/{id}` | 执行详情 |
</details>

<details>
<summary><b>AI 配置 — /api/ai-config</b></summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ai-config` | 获取配置 |
| POST | `/api/ai-config` | 保存配置 |
| POST | `/api/ai-config/test` | 测试连接 |
| GET | `/api/ai-config/status` | 云端/本地模式状态 |
</details>

<details>
<summary><b>报表中心 — /api/report-center</b></summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/report-center/daily` | 日报 |
| GET | `/api/report-center/weekly` | 周报 |
| GET | `/api/report-center/monthly` | 月报 |
| GET | `/api/report-center/devices/export` | 设备明细导出 |
| GET | `/api/report-center/alerts/export` | 告警历史导出 |
</details>

<details>
<summary><b>成本分摊 — /api/cost-allocation</b></summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/cost-allocation/workshop-summary` | 车间电费汇总 |
| GET | `/api/cost-allocation/workshop-detail/{workshop}` | 车间电费明细 |
| GET | `/api/cost-allocation/device-cost` | 设备电费 |
| GET | `/api/cost-allocation/rules` | 分摊规则 |
| PUT | `/api/cost-allocation/rules` | 更新分摊规则 |
| GET | `/api/cost-allocation/export` | 导出 CSV |
</details>

<details>
<summary><b>消息通知 — /api/notifications</b></summary>

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/notifications/list` | 通知列表 |
| GET | `/api/notifications/unread-count` | 未读数 |
| PUT | `/api/notifications/{id}/read` | 标记已读 |
| PUT | `/api/notifications/read-all` | 全部已读 |
</details>

## 智能体集成

### 功能

- **能耗分析**：智能体识别用户意图 → 匹配设备 → 调用工作流 → 返回分析报告
- **自然语言问答**：基于平台知识库的问答，涵盖平台操作、功能说明等
- **调度优化**：基于电价时段和负荷预测的生产调度优化建议
- **全量设备分析**：支持 `["全部"]` 关键字，对系统中所有设备执行能耗分析

### 双轮工具调用机制

对话系统采用独特的 `标签指令 → 设备匹配 → 工作流调用 → 二次对话` 双轮机制：

1. 用户提问发送到 Coze Bot（第一次）
2. Bot 返回 SSE 流式响应，其中嵌入 `<INTERNAL_CMD>` JSON 标签指令
3. 后端 `TagParser` 解析标签，`DeviceMatcher` 进行三级设备匹配（精确/别名/模糊）
4. `ToolHandler` 调用对应的 Coze 工作流执行能耗分析
5. 工作流结果构建为增强消息，发送到 Coze Bot（第二次）
6. Bot 返回最终分析报告，前端 SSE 流式渲染

### RAG 知识库问答

- **文档处理流水线**：上传 PDF/TXT/MD → 解析 → 递归分块（500字符/块，重叠50字符）→ Embeddings 向量化 → 存入 ChromaDB
- **检索**：基于向量相似度搜索 → Top-K 召回 → 格式化为生成上下文
- **生成**：System Prompt 约束 → LLM 流式生成 → SSE 推送到前端（含引用来源）
- **混合模式**：对话模型与嵌入模型可独立配置（全云端/全本地/混合）

### 云端模式 / 本地模式

系统支持云端（Coze）和本地规则引擎双模式运行：

- **云端模式**：需配置 Coze API Key 和对应 Bot/Workflow ID
- **本地模式**：使用内置规则引擎，离线可用

切换方式：「AI 管理」→ 启用/禁用云端智能体

### 智能体双模式降级

```
用户请求
    ↓
┌─────────────────────────┐
│  ai_config_service      │  ← 检查 DB 配置
│  enable_cloud_agent?    │
│  → analyze_enabled?     │
│  → coze_api_key ≠ ""?   │
│  → workflow_id ≠ ""?    │
└────────┬───────────────┘
         │
    ┌────┴────┐
    ↓         ↓
 ┌──────┐  ┌──────┐
 │ 云端  │  │ 本地  │
 │ Coze │  │ Mock │
 │ 工作流│  │ 规则  │
 └──┬───┘  └──┬───┘
    │         │
    └────┬────┘
         ↓
    汇总统一返回
```

- **云端模式**：通过 `cozepy` SDK 调用 Coze 平台工作流，支持并行分析多设备（Semaphore 5 路并发），失败自动降级
- **本地模式**：规则引擎 + 模拟分析，基于限额检测（空压机/制冷机）、峰谷电价策略等生成分析结果
- **降级策略**：任何云端调用失败均自动回退本地，保证系统可用性不中断

## 权限系统

### 角色定义

| 角色 | 标识 | 默认权限范围 |
|------|------|-------------|
| 管理员 | admin | 全部功能 + 用户管理 + AI 配置 |
| 调度员 | dispatcher | 除用户管理、AI 配置外全部 |
| 操作员 | operator | 看板、设备、告警处理、分析执行 |
| 观察者 | viewer | 只读查看 |

### 权限矩阵

| 权限 | admin | dispatcher | operator | viewer |
|------|:---:|:---:|:---:|:---:|
| 查看看板/设备/数据 | ✔ | ✔ | ✔ | ✔ |
| 查看报表/告警 | ✔ | ✔ | ✔ | ✔ |
| 创建设备/配置 | ✔ | ✔ | ✔ | ✘ |
| 执行分析/优化 | ✔ | ✔ | ✔ | ✘ |
| 管理电价策略 | ✔ | ✔ | ✘ | ✘ |
| 管理告警阈值 | ✔ | ✔ | ✘ | ✘ |
| 管理报告订阅 | ✔ | ✔ | ✘ | ✘ |
| 管理用户 | ✔ | ✘ | ✘ | ✘ |
| 管理 AI 配置 | ✔ | ✘ | ✘ | ✘ |

### 权限粒度

系统支持模块级（module）+ 功能级（feature）的细粒度权限控制，通过「用户管理」→ 权限矩阵进行可视化配置。认证令牌格式为 `Bearer role:user_id`，后端通过 `permission.py` 中间件解析角色并校验对应 action 权限。

## 部署

### 生产环境

```bash
# 后端
cd backend
pip install -r requirements.prod.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# 前端构建
cd frontend
npm install
npm run build
# 将 dist/ 目录部署到 Nginx 或 CDN
```

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 360s;      # Coze 工作流 + LLM 流式推理耗时较长
    }
}
```

### systemd 服务配置

```ini
[Unit]
Description=Energy Optimizer Backend
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=/opt/energy-optimizer/backend
ExecStart=/opt/energy-optimizer/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

## 开发指南

### 项目结构约定

- **后端**：`routers/` 定义 API 端点，`services/` 封装业务逻辑，`models/` 按领域拆分数据模型（9 个文件）
- **前端**：`views/` 页面级组件（12 个），`components/common/` 通用 UI，`components/chat/` 对话相关（支持普通+RAG双模式），`components/charts/` 图表（5 个），`components/config/` 配置（5 个）
- **提交规范**：`feat:` / `fix:` / `refactor:` / `docs:` / `test:` / `chore:`

### 分支管理

1. `master` — 稳定分支
2. `develop` — 开发分支
3. 功能分支 `feature/xxx` — 新功能开发
4. 修复分支 `fix/xxx` — Bug 修复

### 运行测试

```bash
# 后端
cd backend
pytest tests/ -v --cov=. --cov-report=term-missing

# 前端
cd frontend
npm test            # 单次运行
npm run test:watch  # 监听模式
```

### 代码规范

```bash
# Python
cd backend
flake8 . --max-line-length=120

# 前端
cd frontend
npm run build       # 构建检查
```

### 添加新的 API 端点

1. 在 `backend/routers/` 创建路由文件
2. 定义 Pydantic 请求/响应模型
3. 实现路由处理函数
4. 在 `backend/main.py` 注册路由
5. 在 `frontend/src/api/api.js` 添加前端 API 方法
6. 编写单元测试

### 数据库模型

9 个文件，按领域组织在 `backend/models/` 包中：

| 文件 | 包含模型 |
|------|---------|
| `models/user.py` | `User`, `UserPermission` |
| `models/device.py` | `Device`, `DeviceSynonym` |
| `models/alert.py` | `AlertThreshold`, `AlertRecord` |
| `models/energy.py` | `Telemetry`, `TariffPolicy` |
| `models/ai.py` | `AgentReport`, `ScheduleTask`, `ScheduleExecution`, `ChatHistory`, `AIConfigEntry`, `WorkflowExecution` |
| `models/rag.py` | `KnowledgeBase`, `Document`, `DocumentChunk`, `RAGChatSession`, `RAGChatMessage`, `LLMConfig` |
| `models/subscription.py` | `ReportSubscription`, `Notification` |

## 许可证

MIT License

Copyright (c) 2026 能耗智能管理优化平台

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
