# 能耗智能管理优化平台 — API 接口文档

> 版本：v1.0 | Base URL: `http://localhost:8000/api`

## 目录

1. [认证](#1-认证)
2. [看板](#2-看板)
3. [设备管理](#3-设备管理)
4. [遥测数据](#4-遥测数据)
5. [电价策略](#5-电价策略)
6. [告警管理](#6-告警管理)
7. [智能体/工作流](#7-智能体工作流)
8. [智能对话](#8-智能对话)
9. [报表中心](#9-报表中心)
10. [成本分摊](#10-成本分摊)
11. [AI 配置](#11-ai-配置)
12. [消息通知](#12-消息通知)

---

## 1. 认证

### POST /api/auth/login

**描述**：用户登录认证

**认证要求**：无

**请求体**：

```json
{
  "username": "admin",
  "password": "admin123"
}
```

**成功响应 (200)**：

```json
{
  "code": 200,
  "data": {
    "id": 1,
    "username": "admin",
    "display_name": "系统管理员",
    "role": "admin",
    "token": "admin:1"
  },
  "message": "登录成功"
}
```

**错误响应 (401)**：

```json
{
  "detail": "用户名或密码错误"
}
```

### GET /api/auth/users

**描述**：用户列表（需 admin 角色）

**请求头**：`Authorization: Bearer admin:1`

**成功响应 (200)**：

```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "username": "admin",
      "display_name": "系统管理员",
      "role": "admin",
      "is_active": true
    }
  ]
}
```

### POST /api/auth/users

**描述**：创建用户

**请求头**：`Authorization: Bearer admin:1`

**请求体**：

```json
{
  "username": "newuser",
  "password": "password123",
  "display_name": "新用户",
  "role": "operator"
}
```

**成功响应 (201)**：

```json
{
  "code": 201,
  "data": { "id": 2, "username": "newuser" },
  "message": "用户创建成功"
}
```

### PUT /api/auth/users/{id}

**描述**：更新用户信息

**请求体**：

```json
{
  "display_name": "更新后的名称",
  "role": "dispatcher",
  "is_active": true
}
```

---

## 2. 看板

### GET /api/dashboard/overview

**描述**：看板概览数据

**响应**：

```json
{
  "code": 200,
  "data": {
    "total_active_power": 125.5,
    "today_energy_kwh": 850.2,
    "co2_emission_kg": 425.1,
    "device_count": 12,
    "online_count": 10,
    "alert_count": 2,
    "alert_records": []
  }
}
```

### GET /api/dashboard/energyflow

**描述**：能流桑基图数据

**响应**：

```json
{
  "code": 200,
  "data": {
    "nodes": [{ "name": "总供电" }, { "name": "空压机" }],
    "links": [{ "source": "总供电", "target": "空压机", "value": 45.2 }]
  }
}
```

### GET /api/dashboard/trend

**描述**：多设备功率趋势

**查询参数**：`?hours=24`（默认 24 小时）

### GET /api/dashboard/alerts-bar

**描述**：最新告警滚动条

---

## 3. 设备管理

### GET /api/devices/list

**描述**：设备列表

### GET /api/devices/ranking

**描述**：能效排行榜

### GET /api/devices/{id}

**描述**：设备详情

### POST /api/devices/

**描述**：创建设备

**认证要求**：✔ `manage_devices`

**请求体**：

```json
{
  "name": "1号空压机",
  "type": "空压机",
  "rated_power": 75.0,
  "workshop": "一车间",
  "line_no": "L1",
  "location": "厂房A区"
}
```

### PUT /api/devices/{id}

**描述**：更新设备

**认证要求**：✔ `manage_devices`

### DELETE /api/devices/{id}

**描述**：删除设备

**认证要求**：✔ `manage_devices`

---

## 4. 遥测数据

### GET /api/telemetry/latest

**描述**：各设备最新能耗读数

### GET /api/telemetry/current

**描述**：所有设备当前功率

**响应**：

```json
{
  "code": 200,
  "data": [
    { "device_id": 1, "device_name": "1号空压机", "power": 45.2, "timestamp": "2026-06-21T10:30:00" }
  ]
}
```

### GET /api/telemetry/range

**描述**：历史能耗查询

**查询参数**：
- `device_id` (int) — 设备 ID
- `start` (ISO datetime) — 开始时间
- `end` (ISO datetime) — 结束时间

---

## 5. 电价策略

### GET /api/tariffs/

**描述**：电价列表

### POST /api/tariffs/

**描述**：创建电价策略

**认证要求**：✔ `manage_tariffs`

**请求体**：

```json
{
  "period_name": "高峰",
  "start_time": "08:00",
  "end_time": "11:30",
  "price_per_kwh": 1.20,
  "is_active": true,
  "description": "峰时段电价"
}
```

### PUT /api/tariffs/{id}

**描述**：更新电价

**认证要求**：✔ `manage_tariffs`

### GET /api/tariffs/current

**描述**：当前时段电价

---

## 6. 告警管理

### GET /api/alerts/thresholds

**描述**：阈值配置列表

### POST /api/alerts/thresholds

**描述**：创建告警阈值

**认证要求**：✔ `manage_alerts`

**请求体**：

```json
{
  "device_id": 1,
  "param_type": "power",
  "upper_limit": 80.0,
  "lower_limit": 0.0,
  "is_enabled": true
}
```

### PUT /api/alerts/thresholds/{id}

**描述**：更新阈值

**认证要求**：✔ `manage_alerts`

### GET /api/alerts/records

**描述**：告警记录列表

**查询参数**：`?device_id=1&is_resolved=false`

### PUT /api/alerts/records/{id}/resolve

**描述**：处理告警

**认证要求**：✔ `manage_alerts`

**请求体**：

```json
{
  "handler": "张三",
  "measure": "已降低设备功率至安全范围"
}
```

### GET /api/alerts/stats

**描述**：告警统计

### GET /api/alerts/suggestions

**描述**：处理建议（基于知识库）

---

## 7. 智能体/工作流

### POST /api/agent/analyze

**描述**：能耗分析（云端/本地双模式）

**请求体**：

```json
{
  "device_ids": [1, 2, 3]
}
```

**响应**：

```json
{
  "code": 200,
  "data": {
    "report_id": 42,
    "mode": "cloud",
    "summary": "共分析 3 台设备...",
    "details": []
  }
}
```

### POST /api/agent/optimize

**描述**：调度优化

**请求体**：

```json
{
  "device_ids": [1, 2],
  "target_date": "2026-06-21"
}
```

### GET /api/agent/reports

**描述**：分析报告列表

### GET /api/agent/subscriptions

**描述**：订阅列表

### POST /api/agent/subscriptions

**描述**：创建订阅

**请求体**：

```json
{
  "name": "日报自动化",
  "report_type": "daily",
  "cron_time": "08:00",
  "device_ids": "1,2,3",
  "is_active": true,
  "notify_method": "email",
  "notify_config": "{\"email\":\"admin@example.com\"}"
}
```

### PUT /api/agent/subscriptions/{id}

**描述**：更新订阅

### DELETE /api/agent/subscriptions/{id}

**描述**：删除订阅

### POST /api/agent/subscriptions/{id}/run

**描述**：手动触发订阅

---

## 8. 智能对话

### POST /api/agent/chat

**描述**：发送消息（SSE 流式返回）

**Content-Type**：`text/event-stream`

**请求体**：

```json
{
  "message": "今天用电情况怎么样",
  "session_id": "session-abc-123"
}
```

**SSE 事件流**：

```
data: {"type":"thinking","content":"正在分析..."}

data: {"type":"content","content":"今日总用电量850kWh"}

data: {"type":"done","session_id":"session-abc-123"}
```

### GET /api/agent/chat/history

**描述**：对话历史

**查询参数**：`?session_id=session-abc-123`

---

## 9. 报表中心

### GET /api/report-center/daily

**描述**：日报

**查询参数**：`?date=2026-06-21`

### GET /api/report-center/weekly

**描述**：周报

### GET /api/report-center/monthly

**描述**：月报

### GET /api/report-center/devices/export

**描述**：设备明细导出（Excel）

### GET /api/report-center/alerts/export

**描述**：告警历史导出（Excel）

---

## 10. 成本分摊

### GET /api/cost-allocation/workshop-summary

**描述**：车间电费汇总

**响应**：

```json
{
  "code": 200,
  "data": [
    { "workshop": "一车间", "total_cost": 1020.50, "device_count": 5 }
  ]
}
```

### GET /api/cost-allocation/workshop-detail/{workshop}

**描述**：车间电费明细

---

## 11. AI 配置

### GET /api/ai-config

**描述**：获取所有 AI 配置

### POST /api/ai-config

**描述**：保存配置

**请求体**：

```json
{
  "coze_api_key": "pat-xxx",
  "analyze_workflow_id": "wf-xxx",
  "optimize_workflow_id": "wf-yyy",
  "chat_bot_id": "bot-zzz",
  "enable_cloud_agent": true
}
```

### POST /api/ai-config/test

**描述**：测试 Coze 连接

### GET /api/ai-config/status

**描述**：云端/本地模式运行状态

**响应**：

```json
{
  "code": 200,
  "data": {
    "mode": "cloud",
    "analyze_available": true,
    "optimize_available": true,
    "chat_available": true
  }
}
```

---

## 12. 消息通知

### GET /api/notifications/

**描述**：通知列表

**查询参数**：`?is_read=false&category=alert`

### PUT /api/notifications/{id}/read

**描述**：标记已读

### PUT /api/notifications/read-all

**描述**：全部已读

---

## 错误码参考

| HTTP 状态码 | 说明 |
|-----------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或认证失败 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 资源冲突（如用户名重复） |
| 500 | 服务器内部错误 |
| 503 | 外部服务不可用（如 Coze API 超时） |

## 认证说明

需要认证的端点需在请求头中携带：

```
Authorization: Bearer {role}:{user_id}
```

示例：`Authorization: Bearer admin:1`

权限校验由 `middleware/permission.py` 中的 `require_permission(action)` 依赖注入实现。
