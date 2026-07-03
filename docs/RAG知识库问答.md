# RAG 知识库问答

## 概述

RAG（Retrieval-Augmented Generation，检索增强生成）是本平台的智能问答核心能力。用户将文档上传至知识库，系统自动完成**解析 → 分块 → 向量化 → 存储**。在问答时，系统从知识库中检索与问题最相关的文档片段，连同问题一起提交给大语言模型（LLM），让模型基于知识库内容生成带引用的精准回答。

### 核心特性

| 特性 | 说明 |
|---|---|
| 多格式支持 | PDF、TXT、Markdown |
| 智能分块 | 基于 RecursiveCharacterTextSplitter，适合中英文混排 |
| 向量检索 | ChromaDB 向量数据库，相似度召回 Top-K |
| 引用溯源 | 每条回答标注参考来源（文档名、片段索引、相似度分数） |
| 双 Provider | 对话模型与嵌入模型可独立配置（OpenAI 兼容 / Ollama 本地） |
| SSE 流式输出 | 对话采用 Server-Sent Events 实时输出 |
| 多知识库 | 单个用户可建多个知识库，问答时可选择任意组合 |
| 会话管理 | 多轮对话历史自动保存，支持跨会话上下文 |

---

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + Element Plus)                │
│  KnowledgeBase.vue  ←→  LLMConfigForm.vue  ←→  ChatWindow.vue │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP / SSE
┌────────────────────────▼────────────────────────────────────┐
│                  后端 (FastAPI)                               │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ knowledge_base│  │ llm_config   │  │   rag_chat       │   │
│  │  (路由)       │  │  (路由)      │  │   (路由)         │   │
│  └──────┬───────┘  └──────┬───────┘  └───────┬──────────┘   │
│         │                 │                  │               │
│  ┌──────▼───────┐  ┌─────▼──────┐   ┌───────▼──────────┐   │
│  │document_     │  │llm_factory │   │ rag_chat_service │   │
│  │processor     │  │(工厂)      │   │ (对话流)         │   │
│  └──────┬───────┘  └─────┬──────┘   └───────┬──────────┘   │
│         │                │                  │               │
│  ┌──────▼───────┐  ┌─────▼──────┐   ┌───────▼──────────┐   │
│  │ ChromaDB     │  │ OpenAI /   │   │ rag_retriever    │   │
│  │ (向量存储)   │  │ Ollama     │   │ (检索器)         │   │
│  └──────────────┘  └────────────┘   └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 模块说明

| 模块 | 路径 | 职责 |
|---|---|---|
| 知识库路由 | `backend/routers/knowledge_base.py` | 知识库 CRUD、文档上传/删除/重处理 API |
| LLM 配置路由 | `backend/routers/llm_config.py` | LLM 配置的读取/保存/测试 API |
| RAG 对话路由 | `backend/routers/rag_chat.py` | RAG 对话 SSE 流式接口、会话管理 |
| 文档处理器 | `backend/services/document_processor.py` | 文档解析→分块→嵌入→存入 ChromaDB |
| LLM 工厂 | `backend/services/llm_factory.py` | 根据配置动态创建 LLM / Embeddings 实例 |
| RAG 对话服务 | `backend/services/rag_chat_service.py` | 对话流编排（检索→构建 Prompt→流式生成→保存） |
| RAG 检索器 | `backend/services/rag_retriever.py` | 向量检索 + 结果合并 + 上下文格式化 |
| LLM 配置服务 | `backend/services/llm_config_service.py` | `llm_config` 表读写 + API Key 脱敏 |
| RAG 数据模型 | `backend/models/rag.py` | KnowledgeBase、Document、DocumentChunk、RAGChatSession、RAGChatMessage、LLMConfig |

---

## 数据模型

### LLM 配置 (`llm_config` 表)

单行模式（始终 `id=1`），对话模型与嵌入模型可独立配置 Provider。

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `provider` | string | `openai_compatible` | 对话模型：`openai_compatible` / `ollama` |
| `api_base` | string | `""` | 对话模型 API 地址 |
| `api_key` | string | `""` | 对话模型 API 密钥 |
| `model_name` | string | `gpt-4o-mini` | 对话模型名 |
| `embedding_provider` | string | `openai_compatible` | 嵌入模型：`openai_compatible` / `ollama` |
| `embedding_api_base` | string | `""` | 嵌入模型 API 地址 |
| `embedding_api_key` | string | `""` | 嵌入模型 API 密钥 |
| `embedding_model` | string | `text-embedding-3-small` | 嵌入模型名 |
| `temperature` | float | `0.7` | 生成温度 |
| `max_tokens` | int | `2048` | 最大生成 Token 数 |
| `is_active` | bool | `true` | 是否启用 |

### 知识库 (`knowledge_bases` 表)

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 主键，自增 |
| `name` | string(200) | 知识库名称 |
| `description` | text | 描述 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

### 文档 (`documents` 表)

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 主键，自增 |
| `kb_id` | int | 所属知识库 ID（外键） |
| `filename` | string(500) | 原始文件名 |
| `file_path` | string(1000) | 存储路径 |
| `file_size` | int | 文件大小（bytes） |
| `mime_type` | string(100) | MIME 类型 |
| `doc_status` | string(20) | 状态：`pending` / `processing` / `ready` / `failed` |
| `chunk_count` | int | 分块数 |
| `error_message` | text | 处理失败原因 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

### 文档分块 (`document_chunks` 表)

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 主键，自增 |
| `doc_id` | int | 所属文档 ID（外键） |
| `chunk_index` | int | 块序号 |
| `chunk_text` | text | 文本内容 |
| `token_count` | int | 估算 Token 数 |

### RAG 会话 (`rag_chat_sessions` 表)

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 主键，自增 |
| `session_id` | string(100) | 会话 UUID（业务唯一标识） |
| `kb_ids` | JSON | 关联的知识库 ID 列表 |
| `title` | string(200) | 会话标题（自动从第一轮问题生成） |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

### RAG 消息 (`rag_chat_messages` 表)

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | 主键，自增 |
| `session_id` | string(100) | 会话 ID（外键） |
| `role` | string(20) | `user` / `assistant` |
| `content` | text | 消息内容 |
| `sources` | JSON | 引用来源：`[{doc_id, chunk_index, score, text_preview, filename}]` |
| `created_at` | datetime | 创建时间 |

---

## 文档处理流程

```
上传文档 → 保存到磁盘 → 创建 Document 记录（status=pending）
                                        ↓
                         后台线程启动 process_document()
                                        ↓
                          ① 加载文件（按扩展名选择解析器）
                                        ↓
                          ② 递归分块（500字符/块，重叠50字符）
                                        ↓
                          ③ 创建 Embeddings 实例（按 LLM 配置）
                                        ↓
                          ④ 存入 ChromaDB Collection（kb_{id}）
                                        ↓
                          ⑤ 更新 Document（status=ready, chunk_count=N）
```

### 支持的文件格式

| 格式 | 扩展名 | 解析器 |
|---|---|---|
| PDF | `.pdf` | PyPDFLoader |
| 纯文本 | `.txt` | TextLoader (UTF-8) |
| Markdown | `.md` | TextLoader (UTF-8) |

### 分块策略

- **分块大小**：500 字符
- **重叠窗口**：50 字符
- **分隔符优先级**：`\n\n` → `\n` → `。` → `.` → 空格 → `""`
- **估算 Token**：`字符数 / 4`

---

## 问答流程

```
用户输入问题
      ↓
① 获取/创建会话（保存用户消息）
      ↓
② 检索知识库（rag_retriever.retrieve）
      │  ┌─ 对每个选中的知识库：
      │  │   └─ ChromaDB similarity_search_with_score(query, k=5)
      │  └─ 合并结果，按相似度排序，取 Top-5
      ↓
③ 构建 System Prompt：
      "你是一个智能知识库助手…仅根据以下上下文回答问题…
       引用格式 [1][2]… === 上下文内容 === {检索结果}"
      ↓
④ 构建消息列表：[System Prompt, 历史消息..., 用户问题]
      ↓
⑤ 调用 LLM（create_llm → llm.stream()）
      ↓
⑥ SSE 流式返回给前端（delta 事件逐块推送）
      ↓
⑦ 保存 AI 回复（含引用来源）到数据库
      ↓
⑧ SSE 发送 done 事件（含完整回复、来源列表、会话 ID）
```

### System Prompt 模板

```text
你是一个智能知识库助手，基于用户提供的知识库文档回答用户的问题。

请遵循以下规则：
1. 仅根据以下提供的"上下文内容"回答问题。如果上下文中没有足够信息，
   如实说明"知识库中没有相关信息"。
2. 回答时引用信息来源，格式为 [1]、[2] 等，并在文末列出"参考来源"。
3. 使用中文回答，语言简洁专业。
4. 不要编造信息，不要使用外部知识补充。

=== 上下文内容 ===

[1] (来源: 文件名1)
文本内容...

[2] (来源: 文件名2)
文本内容...

=== 上下文结束 ===
```

---

## API 接口

### 知识库管理

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/knowledge-bases/` | 获取知识库列表（含文档计数） |
| POST | `/api/knowledge-bases/` | 创建知识库 |
| PUT | `/api/knowledge-bases/{kb_id}` | 更新知识库 |
| DELETE | `/api/knowledge-bases/{kb_id}` | 删除知识库（级联删除文档+向量） |
| GET | `/api/knowledge-bases/{kb_id}/documents` | 获取文档列表 |
| POST | `/api/knowledge-bases/{kb_id}/documents/upload` | 上传文档（multipart） |
| DELETE | `/api/knowledge-bases/{kb_id}/documents/{doc_id}` | 删除文档（含向量） |
| POST | `/api/knowledge-bases/{kb_id}/documents/{doc_id}/reprocess` | 重新处理文档 |

### LLM 配置

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/llm-config/` | 获取配置（API Key 脱敏） |
| POST | `/api/llm-config/` | 保存配置 |
| POST | `/api/llm-config/test` | 测试连接（支持 `llm` / `embedding` / `all`） |

### RAG 对话

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/rag/chat` | 发起 RAG 对话（SSE 流式响应） |
| GET | `/api/rag/sessions` | 获取会话列表 |
| POST | `/api/rag/sessions` | 创建新会话 |
| DELETE | `/api/rag/sessions/{session_id}` | 删除会话 |
| GET | `/api/rag/sessions/{session_id}/messages` | 获取消息历史 |

### SSE 事件格式

```json
// 增量事件
data: {"type": "delta", "content": "部分回复内容"}

// 工具状态事件
data: {"type": "tool_status", "message": "正在执行工具调用..."}

// 完成事件
data: {"type": "done", "reply": "完整回复", "session_id": "xxx",
       "sources": [{"doc_id":1, "chunk_index":0, "score":0.1234,
                     "text_preview":"...", "filename":"doc.pdf"}],
       "mode": "local"}

// 错误事件
data: {"type": "error", "message": "错误信息"}
```

---

## 配置指南

### Provider 配置

LLM（对话模型）与 Embeddings（嵌入模型）可以独立配置 Provider：

| 场景 | 对话 Provider | 嵌入 Provider | 适用场景 |
|---|---|---|---|
| 全云端 | OpenAI 兼容接口 | OpenAI 兼容接口 | API Key 充足，追求质量 |
| 全本地 | Ollama 本地模型 | Ollama 本地模型 | 离线环境，数据安全 |
| 混合模式 | OpenAI 兼容接口 | Ollama 本地模型 | 对话用云端，嵌入用本地 |

### 推荐模型

#### Ollama 本地模型

| 用途 | 推荐模型 | 拉取命令 |
|---|---|---|
| 对话 | `qwen2:7b` | `ollama pull qwen2:7b` |
| 对话 | `qwen2.5:7b` | `ollama pull qwen2.5:7b` |
| 嵌入 | `nomic-embed-text` | `ollama pull nomic-embed-text` |
| 嵌入 | `bge-m3` | `ollama pull bge-m3` |

#### OpenAI 兼容接口

适用于任何兼容 OpenAI API 格式的服务（OpenAI、Azure、vLLM、OneAPI 等）。

| 用途 | 推荐模型 | 说明 |
|---|---|---|
| 对话 | `gpt-4o-mini` | 性价比最高 |
| 对话 | `gpt-4o` | 高质量但成本较高 |
| 嵌入 | `text-embedding-3-small` | 1536 维，性价比高 |
| 嵌入 | `text-embedding-3-large` | 3072 维，精度更高 |

---

## 操作说明

### 1. 配置 LLM

路径：**AI 智能体管理 → 本地 LLM 标签页**

1. 选择对话模型的 Provider（OpenAI 兼容接口 / Ollama 本地模型）
2. 填写 API 地址、Key（如需）、模型名
3. 点击"测试对话模型"验证连接
4. 同样配置嵌入模型
5. 点击"保存配置"

### 2. 创建知识库并上传文档

路径：**知识库管理**

1. 点击"新建知识库"，填写名称和描述
2. 选中知识库，点击"文档管理"
3. 拖拽或点击上传文档（支持 PDF、TXT、MD，最大 50MB）
4. 系统自动在后台处理：解析 → 分块 → 向量化
5. 状态变为"已就绪"后即可使用

### 3. 开始 RAG 问答

路径：**右下角聊天窗口 → 切换到 RAG 问答模式**

1. 在聊天窗口顶部切换到 "RAG 问答" 模式
2. 选择一个或多个知识库
3. 输入问题，AI 将基于知识库内容回答

---

## 依赖列表

```
# 后端（requirements.txt 新增项）
chromadb==0.4.24
langchain-chroma==0.1.3
langchain-community==0.3.1
langchain-core==0.3.15
langchain-openai==0.2.3
langchain-ollama==0.2.0
langchain-text-splitters==0.3.0
pypdf==4.3.0
```

---

## 开发扩展

### 添加新的文档格式支持

在 `document_processor.py` 的 `SUPPORTED_EXTENSIONS` 字典中添加扩展名，并在 `load_document()` 中添加对应的加载逻辑：

```python
SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".txt": "text",
    ".md": "text",
    ".docx": "docx",   # 新增
    ".html": "html",   # 新增
}
```

### 调整分块参数

在 `document_processor.py` 的 `split_texts()` 函数中调整：

```python
def split_texts(texts: list[str], chunk_size: int = 500, chunk_overlap: int = 50) -> list[str]:
```

### 自定义检索策略

在 `rag_retriever.py` 中修改 `retrieve()` 函数。当前使用 `similarity_search_with_score`（L2 距离），可替换为：
- `similarity_search`：仅返回文档，不返回分数
- `max_marginal_relevance_search`：结合相似度与多样性

---

## 常见问题

**Q：文档上传后状态一直是 "处理中"？**
A：检查 LLM 配置是否已保存且测试通过，以及 Ollama（如使用本地模型）是否正在运行。

**Q：RAG 问答返回 "知识库中未找到相关内容"？**
A：确认已选择知识库，且知识库中有状态为"已就绪"的文档。检查嵌入模型的配置是否正确。

**Q：对话模型测试失败？**
A：确认 API 地址可达、API Key 有效、模型名正确。Ollama 用户用 `ollama list` 确认模型已拉取。

**Q：嵌入模型测试失败？**
A：确认嵌套模型（Embeddings）的配置独立于对话模型。Ollama 用户需先 `ollama pull nomic-embed-text`。

**Q：如何清空 ChromaDB 向量数据？**
A：删除 `backend/data/chromadb/` 目录并重启服务即可。
