# AI 智能体对话系统功能设计报告

> 能耗智能管理优化平台 — 与扣子（Coze）智能体交互机制

| 文档版本 | 修订日期 | 修订说明 | 修订人 |
|---------|---------|---------|-------|
| V1.0 | 2026-06-21 | 初始版本 | 系统架构组 |

---

## 目录

1. [系统概述](#1-系统概述)
2. [数据交互规范](#2-数据交互规范)
3. [平台侧数据处理流程](#3-平台侧数据处理流程)
4. [扣子智能体侧数据处理流程](#4-扣子智能体侧数据处理流程)
5. [交互时序图](#5-交互时序图)
6. [性能与安全考量](#6-性能与安全考量)

---

## 1. 系统概述

### 1.1 整体架构

能耗智能管理优化平台采用前端-后端-智能体三层架构，通过 REST API 和 SSE（Server-Sent Events）协议与扣子（Coze）智能体平台进行交互。用户在前端聊天窗口中输入自然语言消息后，消息经由后端服务转发至 Coze 智能体，智能体处理后返回流式响应，再由后端进行解析、加工和转发，最终呈现给用户。整体架构如图 1-1 所示。

```
┌─────────────┐     HTTP/SSE     ┌──────────────────┐    HTTPS/SSE     ┌──────────────┐
│  前端       │ ◄──────────────► │  后端服务平台    │ ◄──────────────► │  扣子智能体  │
│  (Vue 3)    │     JSON/Stream  │  (FastAPI)       │    stream()     │  (Coze Bot)  │
│  ChatWindow │                  │  Chat Service    │                 │              │
│  ChatMessage│                  │  Tag Parser      │                 │  能耗分析WF  │
│             │                  │  Tool Handler    │                 │  调度优化WF  │
└─────────────┘                  │  Agent Adapter   │                 └──────────────┘
                                 └──────────────────┘
```

**图 1-1 系统整体架构图**

### 1.2 核心功能目标

平台与扣子智能体交互的核心功能目标包括：

1. **自然语言对话**：用户通过自然语言与智能体进行多轮对话，获取能耗分析、设备状态、节能建议等信息。
2. **工具调用**：智能体识别用户意图后，通过嵌入在响应中的标签指令触发后端工作流执行具体的能耗分析或调度优化任务。
3. **双轮对话机制**：第一轮获取用户意图和工具调用指令，第二轮利用工具执行结果生成综合性分析报告。
4. **云端/本地双模式**：当云端智能体不可用时，自动降级为本地规则引擎，保证系统核心功能不中断。

### 1.3 核心技术栈

| 技术组件 | 版本 | 用途 |
|---------|------|------|
| cozepy SDK | 0.20.0 | Coze 平台官方 Python SDK，实现流式对话和工作流调用 |
| FastAPI | 0.104.1 | 后端框架，提供 StreamingResponse 支持 SSE |
| SSE 协议 | - | 服务器推送事件，实现流式数据传输 |
| TokenAuth | - | Coze 平台 API 认证方式 |
| SQLAlchemy | 2.0.23 | 数据库 ORM，持久化对话历史 |
| Passlib | 1.7.4 | 密码安全（系统认证） |

---

## 2. 数据交互规范

### 2.1 交互协议总览

平台与扣子智能体之间的数据交互采用 **HTTPS + SSE**（Server-Sent Events）作为核心通信协议。具体交互链路分为两个层次：

1. **前端 ↔ 后端**：基于 HTTP/1.1 协议，使用 SSE（Content-Type: text/event-stream）实现流式数据传输。
2. **后端 ↔ Coze SDK → Coze API**：基于 HTTPS 协议，cozepy SDK 封装了 Coze 平台 REST API 的调用，对话调用使用 SDK 的 `chat.stream()` 方法获取流式事件流。

### 2.2 数据类型定义

#### 2.2.1 用户消息 → 后端 → Coze（上行）

**格式**：JSON（HTTP Request Body / Coze SDK Method Parameters）

**前端 → 后端（ChatRequest）**：

| 字段 | 类型 | 必须 | 约束 | 说明 |
|------|------|:--:|------|------|
| `message` | string | ✔ | 1 ≤ length ≤ 1000 | 用户输入的自然语言消息 |
| `session_id` | string | ✘ | 自动生成（格式：`sess_YYYYMMDDHHMMSS_xxxxxx`） | 会话标识，不传时自动生成新会话 |

**请求示例**：

```json
// POST /api/agent/chat
// Content-Type: application/json
{
    "message": "分析一下一车间空压机的能耗情况",
    "session_id": "sess_20260621103000_a1b2c3"
}
```

**后端 → Coze（cozepy SDK 调用）**：

使用 Coze SDK 的 `chat.stream()` 接口，通过 `Message.build_user_question_text()` 构建消息对象。

| 参数 | 类型 | 必须 | 说明 |
|------|------|:--:|------|
| `bot_id` | string | ✔ | Coze 对话 Bot ID，从数据库 ai_config 表中读取 |
| `user_id` | string | ✔ | 映射为 session_id，用于区分不同会话 |
| `additional_messages` | list[Message] | ✔ | 包含用户消息的列表，由 `Message.build_user_question_text(message)` 构造 |

**Coze SDK 调用示例（Python）**：

```python
from cozepy import Coze, TokenAuth, Message, ChatEventType

coze = Coze(
    auth=TokenAuth(token="pat_xxxxxxxxxx"),
    base_url="https://api.coze.cn",
)

for event in coze.chat.stream(
    bot_id="bot_yyyyyyyyyy",
    user_id="sess_20260621103000_a1b2c3",
    additional_messages=[
        Message.build_user_question_text("分析一下一车间空压机的能耗情况"),
    ],
):
    if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
        print(event.message.content)
    if event.event == ChatEventType.CONVERSATION_CHAT_COMPLETED:
        print("对话完成", event.chat.usage.token_count)
```

#### 2.2.2 Coze → 后端（下行 — 流式事件）

**格式**：Coze SDK 事件流 → 后端解析为结构化事件

**SDK 事件类型**：

| 事件类型（ChatEventType） | 触发时机 | 数据字段 | 说明 |
|-------------------------|---------|---------|------|
| `CONVERSATION_MESSAGE_DELTA` | 智能体逐字生成回复时 | `event.message.content` (string) | 流式增量内容 |
| `CONVERSATION_CHAT_COMPLETED` | 智能体对话正常结束时 | `event.chat.usage.token_count` (int) | 对话完成，含 token 用量 |
| `CONVERSATION_CHAT_FAILED` | 智能体对话异常结束时 | `event.chat.status` (string) | 对话失败，含错误状态 |

**后端 → 前端（SSE 事件流）**：

**SSE 协议格式**：每行以 `data: ` 开头，JSON 数据体，以 `\n\n` 双换行结束。

**事件类型定义**：

| 事件类型 `type` 字段 | 方向 | 触发时机 | 附加字段 |
|---------------------|:--:|---------|---------|
| `delta` | 后端 → 前端 | 智能体逐字生成回复内容时 | `content` (string)：增量文本内容 |
| `tool_status` | 后端 → 前端 | 检测到工具调用指令并开始执行时 | `tool`, `phase`, `message`：工具状态更新 |
| `done` | 后端 → 前端 | 对话完整结束时 | `reply`, `session_id`, `mode`, `tool_used` 等 |
| `error` | 后端 → 前端 | 对话过程出现异常时 | `content` (string)：错误描述 |

**SSE 流式响应示例**：

```
data: {"type":"delta","content":"好的，我来分析一车间空压机的能耗情况。"}

data: {"type":"delta","content":"正在查询设备数据，请稍候..."}

data: {"type":"tool_status","tool":"analyze_energy","phase":"matching","message":"正在匹配设备名称..."}

data: {"type":"tool_status","tool":"analyze_energy","phase":"analyzing","message":"正在分析设备能耗数据..."}

data: {"type":"delta","content":"根据分析结果，1号空压机今日平均功率为45.2kW，"}

data: {"type":"delta","content":"运行状态正常，未发现异常。建议定期维护以保证能效。"}

data: {"type":"done","reply":"根据分析结果...","session_id":"sess_20260621103000_a1b2c3","mode":"cloud","tool_used":true,"tool_type":"analyze_energy","token_count":568,"elapsed":12.34,"fallback":false}

```

#### 2.2.3 <INTERNAL_CMD> 标签指令规范

**定义**：Coze 智能体在流式响应中通过嵌入 `<INTERNAL_CMD>` 标签来触发后端的工具调用。该标签是平台与智能体之间约定的一种轻量级 RPC（Remote Procedure Call）协议。

**标签格式**：

```
<INTERNAL_CMD>
{
    "tool": "analyze_energy",
    "parameters": {
        "device_names": ["1号空压机", "2号空压机"],
        "time_range": "today"
    },
    "request_id": "req_abc123"
}
</INTERNAL_CMD>
```

**字段定义**：

| 字段 | 类型 | 必须 | 约束 | 说明 |
|------|------|:--:|------|------|
| `tool` | string | ✔ | 取值仅限 `analyze_energy` | 要调用的工具类型 |
| `parameters.device_names` | list[string] | ✔ | 空列表视为无设备。支持 `["全部"]` 关键字 | 目标设备名称列表 |
| `parameters.time_range` | string | ✘ | 取值：`today` / `yesterday` / `this_week` / ISO 时间范围 | 分析时间范围 |
| `request_id` | string | ✘ | 建议格式：`req_` + 6位随机 hex | 请求追踪标识 |

**标签解析规则（TagParser）**：

1. 正则匹配：使用 `/<INTERNAL_CMD>\s*([\s\S]*?)\s*<\/INTERNAL_CMD>/i` 在流式累积内容中搜索标签。
2. JSON 解析：提取标签体内容进行 `json.loads()` 解析，解析失败时忽略标签并保留原始内容。
3. 工具校验：仅支持白名单中的工具类型（当前仅 `analyze_energy`），不支持的标签将被忽略。
4. 内容过滤：解析后的 `clean_content` 从原始内容中移除所有标签文本，仅保留纯净的用户可见内容。

**支持的设备名关键字（全量分析）**：

| 关键字 | 匹配行为 |
|--------|---------|
| `全部` | 匹配系统中所有设备 |
| `所有` | 同上 |
| `全部设备` | 同上 |
| `所有设备` | 同上 |
| `all` | 同上 |
| `全` | 同上 |

#### 2.2.4 工作流调用（后端 → Coze Workflow API）

后端在工具调用阶段，通过 Coze SDK 的 `workflows.runs.create()` 接口调用 Coze 工作流。

**请求参数规范**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `device_id` / `device_ids` | int / list[int] | 目标设备 ID（支持单设备 int 或多设备 list/tuple） |
| `start_time` / `end_time` | string (ISO 8601) | 分析时间范围 |
| `device_name` | string | 设备名称 |
| `rated_power` | float | 设备额定功率 |
| `statistics` | dict | 包含 avg_power, max_power, min_power, max_time, min_time, std_dev |
| `data_points` | list[dict] | 采样后的时序数据点（最多 200 个） |

**能耗分析工作流入参示例**：

```json
{
    "device_id": 1,
    "device_name": "1号空压机",
    "rated_power": 75.0,
    "start_time": "2026-06-21T00:00:00",
    "end_time": "2026-06-21T10:30:00",
    "statistics": {
        "avg_power": 45.2,
        "max_power": 72.1,
        "min_power": 12.3,
        "max_time": "14:30",
        "min_time": "03:15",
        "std_dev": 8.56
    },
    "data_points": [
        {"ts": "00:00", "power": 35.2},
        {"ts": "00:15", "power": 38.7},
        {"ts": "00:30", "power": 42.1},
        {"ts": "00:45", "power": 40.5}
    ]
}
```

**工作流响应示例**：

```json
{
    "execute_id": "7382910293",
    "data": "{\"summary\":\"1号空压机运行正常，平均功率45.2kW\",\"anomalies\":[],\"suggestions\":[\"定期检查维护空压机\"],\"total_power_avg\":45.2}"
}
```

工作流响应中的 `data` 字段为 JSON 字符串，内部 schema 由 Coze 工作流的 Output 节点定义，包含以下核心字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `summary` | string | 分析摘要 |
| `anomalies` | list[dict] | 异常列表（device_id, device_name, severity, message） |
| `suggestions` | list[string] | 节能建议列表 |
| `total_power_avg` | number | 平均功率 |

### 2.3 状态码与错误码约定

#### 2.3.1 HTTP 状态码

| 状态码 | 含义 | 触发场景 |
|-------|------|---------|
| 200 | 成功 | 正常完成对话并返回 SSE 流 |
| 400 | 请求参数错误 | `message` 字段为空或超长 |
| 401 | 未认证 | 请求未携带合法认证令牌 |
| 403 | 权限不足 | 用户角色无权访问该功能 |
| 500 | 服务器内部错误 | 后端或 SDK 调用发生未捕获异常 |
| 503 | 外部服务不可用 | Coze API 超时或配额耗尽 |

#### 2.3.2 Coze SDK 错误码分类

| 错误码 | 含义 | 处理策略 |
|:-----:|------|---------|
| 401 | API Key 无效 | 返回"Coze API Key 无效或未授权"，降级本地 |
| 4028 | API 配额已用尽 | 返回"Coze API 配额已用尽"，降级本地 |
| 403 | 未授权操作 | 返回"Coze API 未授权"，降级本地 |
| 500+ | Coze 服务端错误 | 返回错误信息，降级本地 |
| 超时 | 工作流执行超时 | 返回超时提示，降级本地 |

#### 2.3.3 SSE 事件流错误类型

SSE 事件流中的 `error` 类型事件定义：

```json
{"type": "error", "content": "Coze API 配额已用尽 (错误码 4028)"}
```

---

## 3. 平台侧数据处理流程

### 3.1 整体流程概览

平台侧的数据处理流程可概括为"六阶段处理管道"：

```
用户输入 → 预处理 → 第一轮Coze对话 → 标签解析 → 工具调用 → 第二轮Coze对话 → 结果输出
```

### 3.2 预处理阶段（Preprocessing）

**步骤 1.1 — 请求接收与验证**

后端 `chat.py` 路由层接收用户请求，通过 Pydantic 模型 `ChatRequest` 对请求参数进行自动校验。

```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="用户输入的消息内容")
    session_id: Optional[str] = Field(None, description="会话ID，不传则自动生成新会话")
```

校验规则：
- `message` 不可为空，长度限制 1-1000 字符。
- `session_id` 可选；若不提供，调用 `generate_session_id()` 生成，格式为 `sess_YYYYMMDDHHMMSS_xxxxxx`。

**步骤 1.2 — 消息持久化**

将用户消息写入 `chat_history` 数据表，记录以下字段：

| 字段 | 值 |
|------|-----|
| `session_id` | 当前会话 ID |
| `role` | `"user"` |
| `content` | 用户输入的消息原文 |
| `created_at` | 当前时间戳 |

**步骤 1.3 — 配置检查**

检查系统配置，判断是否启用云端智能体：

```
配置检查链：
1. enable_cloud_agent 全局开关是否为 true
2. chat.enabled 子开关是否为 true  
3. COZE_API_KEY 是否配置且非空
4. chat.bot_id（Coze Bot ID）是否配置且非空
```

若以上任一条件不满足，跳过云端调用，直接进入本地降级模式。

### 3.3 请求构建与发送阶段

**步骤 2.1 — 构建 Coze SDK 请求**

```python
coze = Coze(
    auth=TokenAuth(token=api_key),
    base_url="https://api.coze.cn",
    http_client=SyncHTTPClient(
        headers={"X-Coze-Client-Header": "energy-optimizer-platform"}
    ),
)
```

**步骤 2.2 — 流式对话启动**

调用 `coze.chat.stream()` 启动流式对话，以 session_id 作为 user_id 参数，确保同一会话的上下文连续性。

```python
for event in coze.chat.stream(
    bot_id=bot_id,
    user_id=session_id,
    additional_messages=[
        Message.build_user_question_text(message),
    ],
):
```

**步骤 2.3 — 事件流转发**

后端在循环中处理 SDK 返回的三种事件类型：

| 事件类型 | 处理逻辑 |
|---------|---------|
| `CONVERSATION_MESSAGE_DELTA` | 累积 `event.message.content` 到 `first_content`；同时以 SSE `delta` 事件转发到前端 |
| `CONVERSATION_CHAT_COMPLETED` | 记录 token 用量和耗时；标记第一轮对话结束 |
| `CONVERSATION_CHAT_FAILED` | 记录错误信息；设置 fallback 标志 |

### 3.4 响应后处理阶段

#### 3.4.1 标签解析（Tag Parsing）

第一轮 Coze 对话结束后，`first_content` 中累积了完整的响应内容。调用 `TagParser.parse()` 进行标签解析。

**解析流程**：

```
                        ┌──────────────────────────┐
                        │  第一次Coze的完整回复内容  │
                        └──────────┬───────────────┘
                                   ▼
                        ┌──────────────────────────┐
                        │   正则搜索 <INTERNAL_CMD>  │
                        └─────┬─────┬──────────────┘
                              │     │
                         匹配成功  无匹配
                              │     │
                              ▼     ▼
                    ┌─────────────┐  ┌─────────────────┐
                    │ JSON解析    │  │ 无标签 → 直接按   │
                    │ 工具白名单  │  │ 第一轮回复响应   │
                    │ 校验        │  │                 │
                    └──────┬──────┘  └─────────────────┘
                           │
                      ┌────┴──────┐
                      │ 提取工具   │
                      │ 类型和参数 │
                      └───────────┘
```

**解析结果分类处理**：

| 解析结果 | 处理路径 |
|---------|---------|
| `has_tag=True` + 工具类型在白名单内 | 进入 **工具调用阶段** |
| `has_tag=True` + 工具类型不在白名单内 | 忽略标签，按第一轮回复响应 |
| `has_tag=True` + JSON 解析失败 | 忽略标签，保留原始内容按第一轮回复响应 |
| `has_tag=False` | 按第一轮回复直接响应 |

#### 3.4.2 工具调用（Tool Calling）

工具调用的核心流程在 `ToolHandler` 中实现，以能耗分析工具（`analyze_energy`）为例：

**步骤 4.1 — 参数归一化**

```
原始参数: {"device_names": "全部", "time_range": "today"}
                  │
                  ▼
_normalize_device_names():
  - 字符串 "全部" → 列表 ["全部"]
  - 列表 ["全部"] → 列表 ["全部"]（不变）
  - 空值 → 空列表
                  │
                  ▼
归一化结果: {"device_names": ["全部"], "time_range": "today"}
```

**步骤 4.2 — 全量检测与设备匹配**

```
输入: ["全部"]
  │
  ├── _is_all_devices_request(["全部"]) → True
  │     └── 跳过 DeviceMatcher，直接查询所有设备
  │     └── 查询: SELECT * FROM devices → 12 台设备
  │     └── match_dict.matched = {"1号空压机": 1, "2号空压机": 2, ...}
  │     └── device_ids = [1, 2, 3, ..., 12]
  │
输入: ["1号空压机", "压缩机"]
  │
  └── DeviceMatcher.match(["1号空压机", "压缩机"])
        ├── "1号空压机" → 精确匹配 → device_id=1
        └── "压缩机" → 精确匹配失败
              ├── 同义词匹配 → 查询 DeviceSynonym 表
              │     └── 命中: "压缩机" → device_id=1
              │
              └── 若同义词未命中 → 模糊匹配
                    └── SequenceMatcher 计算相似度
                    └── 相似度 >= 0.85 → 自动匹配
                    └── 0.6 ≤ 相似度 < 0.85 → 低置信度匹配
                    └── 相似度 < 0.6 → 不匹配
```

**步骤 4.3 — 时间范围解析**

| 输入值 | 解析结果 |
|--------|---------|
| `today` | `(当前日期 00:00:00, 当前时间)` |
| `yesterday` | `(昨天 00:00:00, 昨天 23:59:59)` |
| `this_week` | `(本周一 00:00:00, 当前时间)` |
| 其他 | `(None, None)` → 查询全部 |

**步骤 4.4 — 工作流调用（云端模式）**

```python
# agent_adapter.py — 云端并行分析
semaphore = asyncio.Semaphore(5)  # 限制并发数为5

async def _analyze_one_device(device):
    async with semaphore:
        params = _build_analysis_params(device, start_time, end_time, db)
        try:
            result = await CozeClient.run_workflow(db, "analyze", params)
            # 解析工作流执行结果
            return {"summary": ..., "anomalies": ..., "suggestions": ...}
        except CozeAPIError:
            # 云端失败 → 自动降级到本地规则引擎
            local = _analyze_device_local(device, ...)
            local["_cloud_error"] = err_msg
            return local

tasks = [_analyze_one_device(d) for d in devices]
results = await asyncio.gather(*tasks)
```

**步骤 4.5 — 本地模式（规则引擎降级）**

当云端不可用或配置未开启时，使用本地规则引擎：

```python
def _analyze_device_local(device, start_time, end_time, db):
    records = db.query(Telemetry).filter(
        Telemetry.device_id == device.id,
        Telemetry.timestamp >= st,
        Telemetry.timestamp <= et,
    ).all()

    avg_power = sum(r.power for r in records) / len(records)
    anomalies = []

    # 规则1: 接近额定功率
    if max_power > device.rated_power * 0.95:
        anomalies.append({...})

    # 规则2: 长时间低负载
    if low_count / len(records) > 0.5:
        anomalies.append({...})

    return {"summary": ..., "anomalies": anomalies, "suggestions": ...}
```

#### 3.4.3 增强消息构建与第二轮对话

工具调用成功后，构建增强消息上下文：

```python
def _build_enriched_message(user_message, analysis_result, match_info):
    return (
        f"用户问题：{user_message}\n\n"
        f"设备能耗分析结果（共 {device_count} 台设备）：\n"
        f"{json.dumps(analysis_result, ...)}\n\n"
        f"请根据以上分析数据，用中文向用户清晰地报告各设备的能耗状况、异常情况和节能建议。"
    )
```

增强消息包含三个部分：
1. **用户原始问题** — 保持对话上下文连续性。
2. **结构化分析数据** — 工作流执行结果（JSON 格式）。
3. **生成指令** — 指示 Coze Bot 根据数据生成自然语言报告。

增强消息被发送到 Coze Bot 进行第二轮对话：

```
第二轮 Coze 对话：
  输入: (增强消息，含原始问题和分析数据)
  输出: (综合性的自然语言分析报告)
```

第二轮对话的输出即为最终展示给用户的回复内容。

#### 3.4.4 消息持久化（最终消息）

最终的回复内容（包括工具执行信息）被保存到 `chat_history` 表：

| 字段 | 值 |
|------|-----|
| `session_id` | 当前会话 ID |
| `role` | `"assistant"` |
| `content` | 最终回复文本 |
| `tool_type` | 实际调用的工具类型（如 `"analyze_energy"`） |
| `tool_params` | JSON 序列化的工具调用参数 |
| `tool_result` | JSON 序列化的工具执行结果 |
| `match_status` | JSON 序列化的设备匹配状态 |
| `is_final` | `True` |
| `needs_user_input` | `False`（工具成功时）/ `True`（工具失败需用户澄清时） |

### 3.5 错误处理机制

#### 3.5.1 云端调用失败降级

```
Coze 云端调用失败
      │
      ├── CozeAPIError (401/403/4028/500)
      │     └── 记录错误日志
      │     └── 返回本地分析结果 + 标记 _mode="local"
      │     └── 在结果中附带 _cloud_error 字段说明原因
      │
      ├── 网络超时 / 连接错误
      │     └── 记录错误日志
      │     └── 自动重试（工作流调用，非对话调用）
      │     └── 重试失败 → 降级本地
      │
      └── SDK 内部异常
            └── 记录错误日志
            └── 降级本地
```

#### 3.5.2 工具调用失败处理

```
ToolHandler.execute() 失败
      │
      ├── 设备匹配失败（无匹配设备）
      │     └── 返回 error = "设备名称匹配失败，请确认后重试"
      │     └── needs_user_input = True
      │     └── 前端提示用户确认设备名称
      │
      ├── 工作流执行失败
      │     └── 返回 error = "能耗分析工作流执行失败: {error_msg}"
      │     └── needs_user_input = True
      │     └── 前端提示用户稍后重试
      │
      └── 系统异常
            └── 返回 error = "工具执行异常，请稍后重试"
            └── 前端提示用户稍后重试
```

#### 3.5.3 完整降级链路

```
用户输入
    │
    ├── 云端启用 + 配置完整 → 第一轮 Coze 对话
    │     │
    │     ├── 成功 + 有标签 → 工具调用 → 第二轮 Coze 对话 → 返回结果
    │     ├── 成功 + 无标签 → 直接返回第一轮回复
    │     └── 失败 → 本地固定回复
    │
    └── 云端未启用/配置不完整 → 本地固定回复
```

**本地固定回复（`_local_fallback`）**：

```python
def _local_fallback(message):
    if any(w in message for w in ["你好", "hello", "hi"]):
        return "你好！我是能耗智能管理助手，有什么可以帮你的吗？"
    if any(w in message for w in ["功能", "能做什么", "帮助"]):
        return "我可以回答你关于能源管理的各种问题..."
    if any(w in message for w in ["谢谢", "感谢"]):
        return "不客气！如有其他问题，随时问我。"
    return "您好，当前运行在本地模式。如需更智能的对话体验，请在 AI 配置中启用云端智能体。"
```

---

## 4. 扣子智能体侧数据处理流程

### 4.1 请求接收与会话管理

Coze 平台接收来自 SDK 的请求后，首先进行以下处理：

1. **认证校验**：验证 HTTP Header 中的 `Authorization: Bearer pat_xxx` 令牌有效性。
2. **Bot ID 校验**：确认请求中的 `bot_id` 存在且处于已发布状态。
3. **会话管理**：根据 `user_id`（即 session_id）确定是否已有会话上下文。若 `user_id` 首次出现，创建新会话；若已存在，加载该会话的历史消息作为对话上下文。

### 4.2 意图识别与内部逻辑处理

#### 4.2.1 用户输入解析

Coze Bot 对用户输入进行 NLU（自然语言理解）处理，包含：

1. **意图分类**：将用户输入归类到 Bot 配置的意图体系中。
2. **实体抽取**：从用户输入中提取关键实体，如设备名称、时间描述、分析类型等。
3. **上下文关联**：结合同一会话中的历史消息，理解代词指代和省略信息。

#### 4.2.2 对话策略决策

基于意图分类结果，Bot 执行相应的对话策略：

| 用户意图 | Bot 处理策略 |
|---------|-------------|
| 能耗查询类（如"今天用电情况"） | 直接生成数据查询指令 → 输出 `<INTERNAL_CMD>` 标签 |
| 设备分析类（如"分析一下空压机"） | 提取设备名称和时间范围 → 输出 `<INTERNAL_CMD>` 标签 |
| 问候类（如"你好"） | 直接回复问候语，不产生工具调用 |
| 平台操作类（如"怎么查看报表"） | 基于知识库回复操作指引，不产生工具调用 |

#### 4.2.3 工具调用指令生成

当 Bot 判断需要调用后端工具时，按以下规则生成 `<INTERNAL_CMD>` 标签：

1. **工具选择**：根据意图选择工具类型，当前支持 `analyze_energy`。
2. **设备名称提取**：从用户输入中提取设备名称实体。
   - 用户说"所有设备"或"全部" → `device_names: ["全部"]`
   - 用户说"一车间空压机" → `device_names: ["1号空压机"]`（通过 Bot 侧的知识映射）
   - 用户说"空压机和注塑机" → `device_names: ["空压机", "注塑机"]`
3. **时间范围推断**：根据用户的时间描述推断：
   - "今天"、"今日" → `time_range: "today"`
   - "昨天"、"昨日" → `time_range: "yesterday"`
   - "本周" → `time_range: "this_week"`
   - 无时间描述 → 默认 `time_range: "today"`
4. **标签构造**：将上述信息构造为 JSON 格式，嵌入 `<INTERNAL_CMD>` 标签。

### 4.3 响应生成与格式化

#### 4.3.1 流式响应生成

Coze Bot 通过 SSE 协议逐 token 生成响应内容。响应流由 SDK 在事件循环中持续读取，主要包含以下阶段：

1. **思考阶段**（`thinking`）：Bot 内部推理和上下文分析。
2. **生成阶段**：按 token 逐步生成回复内容，通过 `CONVERSATION_MESSAGE_DELTA` 事件推送。
3. **完成阶段**：生成完毕，通过 `CONVERSATION_CHAT_COMPLETED` 事件返回。

#### 4.3.2 第一轮回复的标签嵌入

在需要工具调用的情况下，Bot 在第一轮回复中嵌入 `<INTERNAL_CMD>` 标签：

```
用户：分析一下空压机的能耗情况

Bot 回复（流式逐段输出）：
  "好的，我来分析空压机的能耗数据。"
  "正在查询..."
  "<INTERNAL_CMD>{\"tool\":\"analyze_energy\",\"parameters\":{\"device_names\":[\"空压机\"],\"time_range\":\"today\"},\"request_id\":\"req_a1b2c3\"}</INTERNAL_CMD>"
  "已找到相关信息，正在进行分析..."
```

#### 4.3.3 第二轮回复的数据分析与报告生成

第一轮工具调用执行完毕后，后端将分析数据构造为增强消息，重新发送到 Coze Bot。Bot 在第二轮回复中利用这些数据生成最终报告：

1. **读取输入数据**：解析增强消息中的设备列表、指标数据、异常信息等。
2. **生成自然语言报告**：将结构化数据转化为流畅的自然语言描述。
3. **格式化输出**：按合适的格式（如表格、要点列表、段落）呈现结果。
4. **流式输出**：通过 SSE 逐 token 输出最终报告。

---

## 5. 交互时序图

### 5.1 正常对话（无工具调用）

```
用户                    前端                    后端                    Coze Bot
  │                      │                      │                      │
  │  输入消息              │                      │                      │
  │──────────────────────►│                      │                      │
  │                      │  POST /api/agent/chat │                      │
  │                      │─────────────────────►│                      │
  │                      │                      │  保存用户消息到DB     │
  │                      │                      │──┐                    │
  │                      │                      │  │                    │
  │                      │                      │◄─┘                    │
  │                      │                      │                      │
  │                      │                      │  coze.chat.stream()   │
  │                      │                      │──────────────────────►│
  │                      │                      │                      │
  │                      │                      │  CONV_MESSAGE_DELTA   │
  │                      │                      │◄──────────────────────│
  │                      │  SSE: delta          │                      │
  │                      │◄─────────────────────│                      │
  │  逐字显示回复内容      │                      │                      │
  │◄─────────────────────│                      │                      │
  │                      │                      │  (持续流式输出...)    │
  │                      │                      │◄──────────────────────│
  │                      │                      │                      │
  │                      │                      │  CONV_CHAT_COMPLETED  │
  │                      │                      │◄──────────────────────│
  │                      │                      │                      │
  │                      │                      │  保存助手消息到DB     │
  │                      │                      │──┐                    │
  │                      │                      │  │                    │
  │                      │                      │◄─┘                    │
  │                      │  SSE: done           │                      │
  │                      │◄─────────────────────│                      │
  │  显示完成状态          │                      │                      │
```

### 5.2 对话含工具调用（完整双轮流程）

```
用户                    前端                    后端                    Coze Bot
  │                      │                      │                      │
  │ "分析空压机能耗"       │                      │                      │
  │──────────────────────►│                      │                      │
  │                      │  POST /api/agent/chat │                      │
  │                      │─────────────────────►│                      │
  │                      │                      │  保存用户消息         │
  │                      │                      │──┐                    │
  │                      │                      │  │                    │
  │                      │                      │◄─┘                    │
  │                      │                      │                      │
  │                      │                      │  第一轮: stream()     │
  │                      │                      │──────────────────────►│
  │                      │                      │                      │
  │                      │  SSE: delta          │  CONV_MESSAGE_DELTA   │
  │                      │◄─────────────────────│◄──────────────────────│
  │  "好的，正在分析..."   │                      │                      │
  │◄─────────────────────│                      │                      │
  │                      │                      │                      │
  │                      │                      │  (累积 first_content) │
  │                      │                      │──┐                    │
  │                      │                      │  │                    │
  │                      │                      │◄─┘                    │
  │                      │                      │                      │
  │                      │                      │  CONV_CHAT_COMPLETED  │
  │                      │                      │◄──────────────────────│
  │                      │                      │                      │
  │                      │                      │                      │
  │                      │                      │  ── 标签解析 ──       │
  │                      │                      │  TagParser.parse()    │
  │                      │                      │──┐                    │
  │                      │                      │  │ has_tag=True       │
  │                      │                      │◄─┘                    │
  │                      │                      │                      │
  │                      │  SSE: tool_status    │  ── 工具调用 ──       │
  │                      │◄─────────────────────│  DeviceMatcher.match()│
  │  "正在分析设备能耗..."  │                      │──┐                    │
  │◄─────────────────────│                      │  │                    │
  │                      │                      │◄─┘                    │
  │                      │                      │                      │
  │                      │                      │  ── 触发工作流 ──     │
  │                      │                      │  第二轮: stream()     │
  │                      │                      │───────┐               │
  │                      │                      │       │               │
  │                      │                      │◄──────┘               │
  │                      │                      │  (本地或云端)          │
  │                      │                      │                       │
  │                      │                      │  构建增强消息           │
  │                      │                      │──┐                     │
  │                      │                      │  │                     │
  │                      │                      │◄─┘                     │
  │                      │                      │                        │
  │                      │                      │  第二轮: Coze对话      │
  │                      │                      │───────────────────────►│
  │                      │                      │                        │
  │                      │                      │  CONV_MESSAGE_DELTA    │
  │                      │                      │◄───────────────────────│
  │                      │  SSE: delta          │                        │
  │                      │◄─────────────────────│                        │
  │  "分析报告: 空压机..." │                      │                        │
  │◄─────────────────────│                      │                        │
  │                      │                      │  CONV_CHAT_COMPLETED   │
  │                      │                      │◄───────────────────────│
  │                      │                      │                        │
  │                      │                      │  保存最终消息到DB      │
  │                      │                      │──┐                     │
  │                      │                      │  │                     │
  │                      │                      │◄─┘                     │
  │                      │  SSE: done           │                        │
  │                      │◄─────────────────────│                        │
```

### 5.3 异常降级流程

```
用户                    前端                    后端                    Coze Bot
  │                      │                      │                      │
  │ "今天用电情况"         │                      │                      │
  │──────────────────────►│                      │                      │
  │                      │  POST /api/agent/chat │                      │
  │                      │─────────────────────►│                      │
  │                      │                      │                      │
  │                      │                      │  云端配置检查          │
  │                      │                      │──┐                    │
  │                      │                      │  │ enable=false       │
  │                      │                      │  │ 或 api_key=""      │
  │                      │                      │  │ 或 bot_id=""       │
  │                      │                      │◄─┘                    │
  │                      │                      │                      │
  │                      │                      │  ──本地降级──          │
  │                      │                      │  _local_fallback()    │
  │                      │                      │──┐                    │
  │                      │                      │  │                    │
  │                      │                      │◄─┘                    │
  │                      │                      │                      │
  │                      │  SSE: done           │                      │
  │                      │◄─────────────────────│                      │
  │  "当前运行在本地模式"  │                      │                      │
  │◄─────────────────────│                      │                      │
```

---

## 6. 性能与安全考量

### 6.1 性能优化策略

#### 6.1.1 并发控制与限流

| 策略 | 实现方式 | 说明 |
|------|---------|------|
| 工作流并发数限制 | `asyncio.Semaphore(5)` | 多设备分析时，最多 5 路并发调用 Coze 工作流，防止 API 限流和资源耗尽 |
| SSE 心跳机制 | 每 15 秒发送空事件 | 防止代理服务器和负载均衡器因无数据流量而断开连接 |
| 数据采样 | `_sample_data(data, max_points=200)` | 遥测数据超过 200 点时进行等间隔降采样，防止 Token 溢出 |
| 超时控制 | `COZE_AGENT_TIMEOUT=120s` | 工作流调用超时限制，防止长时间等待 |
| | `COZE_CHAT_TIMEOUT=30s` | 对话调用超时限制，保障用户体验 |

#### 6.1.2 缓存策略（设计建议）

建议在以下场景引入缓存机制以进一步提升性能：

| 缓存目标 | 缓存键 | 缓存时间 | 说明 |
|---------|-------|---------|------|
| AI 配置 | `ai_config` | 60s | 配置读取频率高但变更极少 |
| 设备列表 | `devices_list` | 300s | 设备基础数据变更频率低 |
| 对话诊断 | `chat_diagnostics` | 30s | 诊断信息在短时间内稳定 |

#### 6.1.3 数据量控制

针对 Coze 工作流调用的 Token 限制，采取以下数据量控制措施：

```
遥测记录数 > 200？
  │
  ├── 是 → 等间隔采样: 每 N 条取 1 条
  │     └── step = len(data) / 200
  │     └── sampled = [data[int(i * step)] for i in range(200)]
  │
  └── 否 → 全量发送
```

分析结果中的节能建议上限控制：

```python
# 仅保留前 5 条建议
suggestions = list(all_suggestions)[:5]
```

#### 6.1.4 流式传输性能

SSE 流式传输的性能指标：

| 指标 | 目标值 | 测量方式 |
|------|-------|---------|
| 首字节时间（TTFB） | < 2000ms | 用户发送消息后到收到第一个 SSE `delta` 事件 |
| 流式吞吐量 | > 50 chars/s | 每秒输出的字符数 |
| 端到端延迟（无工具调用） | < 5s | 用户发送消息到收到 `done` 事件 |
| 端到端延迟（有工具调用） | < 30s | 同上（含工作流执行时间） |
| 并发连接数 | ≥ 20 | 同时建立的 SSE 连接数 |

### 6.2 安全性保障措施

#### 6.2.1 通信安全

| 安全措施 | 级别 | 说明 |
|---------|:---:|------|
| HTTPS 传输 | 传输层 | 前端 ↔ 后端、后端 ↔ Coze API 均使用 TLS 加密 |
| API Key 管理 | 凭据层 | Coze API Key 存储在数据库中加密读写，通过 ai_config_service 统一管理 |
| 认证令牌 | 应用层 | 前端使用 `Authorization: Bearer role:user_id` 传递用户身份 |

#### 6.2.2 输入安全

| 措施 | 说明 |
|------|------|
| 输入长度限制 | `message` 字段限制 1-1000 字符，防止超长输入导致 Token 溢出 |
| Pydantic 校验 | 所有 API 请求通过 Pydantic BaseModel 进行类型和约束校验 |
| 输出过滤 | `<INTERNAL_CMD>` 标签在推送到前端前被过滤，用户不可见 |
| 正则安全 | 标签解析使用编译后的正则表达式（re.compile），防止 ReDoS 攻击 |

#### 6.2.3 数据安全

| 措施 | 说明 |
|------|------|
| 对话历史持久化 | 所有用户消息和助手回复均持久化到数据库，支持审计追踪 |
| 参数序列化 | 工具调用参数和执行结果以 JSON 格式存储在 chat_history 表 |
| 数据库加密 | 密码等敏感信息使用 bcrypt 哈希存储（非明文） |

#### 6.2.4 降级策略的安全保障

在云端不可用降级到本地模式时：

1. **不泄露 API 凭据**：错误消息中不包含 API Key、Token 等敏感信息的明文。
2. **不暴露内部实现**：本地降级回复使用预设的固定消息，不泄露系统内部结构。
3. **限频保护**：防止恶意用户通过频繁调用耗尽 Coze API 配额。

```python
# 安全的错误消息处理
def _coze_error_message(e: Exception) -> str:
    if isinstance(e, CozeAPIError):
        if e.code == 4028:
            return "Coze API 配额已用尽 (错误码 4028)"
        elif e.code in (401, 403):
            return "Coze API Key 无效或未授权 (错误码 {e.code})"
        else:
            return f"Coze API 错误 (错误码 {e.code}): {e.msg}"
    return str(e)[:200]  # 截断长度，防止泄露敏感信息
```

### 6.3 监控与告警（设计建议）

建议增加以下监控指标以保障系统运行质量：

| 监控指标 | 告警阈值 | 说明 |
|---------|---------|------|
| Coze API 调用成功率 | < 90% | 每分钟成功率低于 90% 时告警 |
| SSE 流式对话响应时间 | > 10s (P95) | 95% 分位响应时间超过 10s 时告警 |
| 云端降级频率 | > 5次/小时 | 每小时云端降级超过 5 次时告警 |
| Coze API 配额剩余 | < 20% | 配额剩余少于 20% 时告警 |
| 数据库会话数 | > 50 | 同时活跃的数据库会话数超过 50 时告警 |

---

## 附录 A：关键术语表

| 术语 | 解释 |
|------|------|
| Coze（扣子） | 字节跳动推出的 AI Bot 开发平台，提供对话智能体、工作流编排等功能 |
| cozepy | Coze 平台官方 Python SDK |
| SSE (Server-Sent Events) | HTML5 标准中服务器向客户端推送事件的协议 |
| TokenAuth | Coze 平台基于 PAT（Personal Access Token）的认证方式 |
| Tool Calling | 智能体调用外部工具/API 的机制 |
| Tag Parser | 解析 Coze Bot 响应中 `<INTERNAL_CMD>` 标签的模块 |
| Device Matcher | 三级设备名称匹配引擎（精确/同义词/模糊） |
| Agent Adapter | 智能体适配层，封装云端/本地双模式切换逻辑 |
| Local Fallback | 云端不可用时的本地规则引擎降级模式 |
| Enhanced Message | 包含工具执行结果的增强对话上下文消息 |

## 附录 B：数据库表结构（对话相关）

**chat_history 表**：

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PK, AUTO_INCREMENT | 主键 |
| session_id | VARCHAR(64) | NOT NULL, INDEX | 会话 ID |
| role | VARCHAR(16) | NOT NULL | `user` 或 `assistant` |
| content | TEXT | NOT NULL | 消息内容 |
| intent | VARCHAR(32) | NULLABLE | 意图类型 |
| workflow_type | VARCHAR(32) | NULLABLE | 工作流类型 |
| tool_type | VARCHAR(32) | NULLABLE | 工具调用类型 |
| tool_params | TEXT | NULLABLE | 工具参数（JSON） |
| tool_result | TEXT | NULLABLE | 工具结果（JSON） |
| match_status | TEXT | NULLABLE | 设备匹配状态（JSON） |
| is_final | BOOLEAN | DEFAULT FALSE | 是否为最终消息 |
| needs_user_input | BOOLEAN | DEFAULT FALSE | 是否需要用户输入 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |

---

> 文档结束。本报告内容与代码实现保持同步，实际行为以仓库代码为准。
