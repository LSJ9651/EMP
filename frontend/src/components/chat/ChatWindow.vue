<template>
  <transition name="slide-up">
    <div v-if="visible" class="chat-window">
      <!-- 头部 -->
      <div class="chat-header">
        <div class="chat-header-left">
          <span class="chat-title">🤖 智能助手</span>
          <!-- 模式切换 -->
          <el-radio-group v-model="chatMode" size="small" class="mode-switch" @change="onModeChange">
            <el-radio-button value="general">普通对话</el-radio-button>
            <el-radio-button value="rag">RAG问答</el-radio-button>
          </el-radio-group>
        </div>
        <div class="chat-header-actions">
          <!-- 状态指示器：根据模式显示不同状态 -->
          <el-tooltip :content="statusBadge.detail" placement="bottom" effect="dark">
            <el-tag
              :type="statusBadge.type"
              size="small"
              effect="plain"
              class="status-tag"
            >
              <span class="status-dot" :class="statusBadge.dotClass"></span>
              {{ statusBadge.label }}
            </el-tag>
          </el-tooltip>
          <el-button text circle size="small" @click="$emit('minimize')">
            <el-icon><ArrowDown /></el-icon>
          </el-button>
          <el-button text circle size="small" @click="$emit('close')">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- RAG 知识库选择条 -->
      <div v-if="chatMode === 'rag'" class="kb-selector-bar">
        <div class="kb-selector-inner">
          <el-icon class="kb-icon"><FolderOpened /></el-icon>
          <el-select
            v-model="selectedKbIds"
            multiple
            placeholder="选择知识库..."
            size="small"
            class="kb-select"
            collapse-tags
            collapse-tags-tooltip
            @change="onKbChange"
          >
            <el-option
              v-for="kb in kbList"
              :key="kb.id"
              :label="kb.name"
              :value="kb.id"
            >
              <span>{{ kb.name }}</span>
              <span class="kb-doc-count">{{ kb.doc_count }} 文档</span>
            </el-option>
          </el-select>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="chat-messages" ref="msgContainerRef">
        <div v-if="messages.length === 0" class="chat-placeholder">
          <div class="placeholder-icon">💬</div>
          <p class="placeholder-title">你好！我是能耗智能管理助手</p>
          <p class="placeholder-desc">
            {{ chatMode === 'rag' ? '选择知识库后，输入问题开始 RAG 问答' : '请问有什么可以帮你的？' }}
          </p>
        </div>
        <transition-group name="msg-fade" tag="div" class="msg-list">
          <ChatMessage
            v-for="(msg, idx) in messages"
            :key="msg._key || idx"
            :role="msg.role"
            :content="msg.content"
            :timestamp="msg.timestamp"
            :streaming="!!msg._streaming"
            :mode="msg.mode || 'local'"
            :sources="msg.sources"
            :_tool-used="!!msg._tool_used"
            :_tool-type="msg._tool_type || ''"
          />
        </transition-group>
        <!-- AI 状态指示器 -->
        <transition name="status-fade">
          <div v-if="statusPhase !== 'idle'" class="status-bar" :class="statusPhase">
            <span class="status-dot"></span>
            <span class="status-text">{{ statusText }}</span>
          </div>
        </transition>
      </div>

      <!-- 输入区域 -->
      <div class="chat-input-area">
        <div class="input-wrapper">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="2"
            placeholder="输入问题，Enter 发送，Shift+Enter 换行"
            resize="none"
            :disabled="loading && messages.length > 0 && messages[messages.length - 1]?.role !== 'assistant'"
            @keydown="handleKeydown"
          />
          <el-button
            type="primary"
            :icon="Promotion"
            circle
            class="send-btn"
            :disabled="!inputText.trim() || loading"
            @click="handleSend"
          />
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, reactive, nextTick, watch, onMounted, computed } from 'vue'
import { ArrowDown, Close, Promotion, FolderOpened } from '@element-plus/icons-vue'
import { getAIConfigStatus, getKnowledgeBases, getLLMConfig } from '../../api/api.js'
import ChatMessage from './ChatMessage.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  sessionId: { type: String, default: '' },
})
const emit = defineEmits(['close', 'minimize', 'update:sessionId'])

// ── 模式切换 ──
const chatMode = ref('general')
const generalSessionId = ref(props.sessionId)
const ragSessionId = ref('')
const selectedKbIds = ref([])
const kbList = ref([])

const messages = ref([])
let msgKeyCounter = 0
const inputText = ref('')
const loading = ref(false)
const msgContainerRef = ref(null)

// ── 默认知识库选择 ──
function getLastUsedKbIds() {
  try {
    const saved = localStorage.getItem('rag_last_kb_ids')
    return saved ? JSON.parse(saved) : []
  } catch { return [] }
}
function saveLastUsedKbIds(ids) {
  localStorage.setItem('rag_last_kb_ids', JSON.stringify(ids))
}

function onModeChange(mode) {
  messages.value = []
  ragSessionId.value = ''
  if (mode === 'rag') {
    loadKbList()
    loadRagHistory()
    fetchLLMStatus()
  }
}

// 加载知识库列表
async function loadKbList() {
  try {
    const res = await getKnowledgeBases()
    if (res.code === 200) {
      kbList.value = res.data.filter(kb => kb.doc_count > 0)
      // 自动选择：只有1个知识库时直接用，否则用上次使用的
      if (kbList.value.length === 1) {
        selectedKbIds.value = [kbList.value[0].id]
      } else {
        const lastUsed = getLastUsedKbIds()
        const valid = lastUsed.filter(id => kbList.value.some(kb => kb.id === id))
        if (valid.length > 0) {
          selectedKbIds.value = valid
        }
      }
    }
  } catch { /* 静默 */ }
}

function onKbChange() {
  saveLastUsedKbIds(selectedKbIds.value)
}

// 加载 RAG 对话历史
async function loadRagHistory() {
  try {
    const { getRagSessions, getRagMessages } = await import('../../api/api.js')
    const sessionsRes = await getRagSessions()
    if (sessionsRes.code === 200 && sessionsRes.data.length > 0) {
      const latest = sessionsRes.data[0]
      ragSessionId.value = latest.session_id
      if (latest.kb_ids && latest.kb_ids.length > 0 && selectedKbIds.value.length === 0) {
        selectedKbIds.value = latest.kb_ids
      }

      const msgRes = await getRagMessages(latest.session_id)
      if (msgRes.code === 200) {
        messages.value = msgRes.data.map(m => ({
          _key: `rag-${m.id || msgKeyCounter++}`,
          role: m.role,
          content: m.content,
          timestamp: m.created_at,
          mode: 'local',
          sources: m.sources || [],
        }))
      }
    }
  } catch { /* 静默 */ }
}

// ── 双状态指示器 ──
// General 模式：Coze 云端/本地智能体状态
const agentStatus = reactive({ mode: 'local', detail: '使用本地规则引擎' })
// RAG 模式：LLM 云端/本地模型状态
const llmStatus = reactive({ mode: 'local', detail: '使用本地模型', label: '本地模型' })

const statusBadge = computed(() => {
  if (chatMode.value === 'rag') {
    return {
      label: llmStatus.label,
      detail: llmStatus.detail,
      type: llmStatus.mode === 'cloud' ? 'success' : 'info',
      dotClass: llmStatus.mode,
    }
  }
  return {
    label: agentStatus.mode === 'cloud' ? '云端智能体' : '本地智能体',
    detail: agentStatus.detail,
    type: agentStatus.mode === 'cloud' ? 'success' : 'info',
    dotClass: agentStatus.mode,
  }
})

async function fetchAgentStatus() {
  try {
    const res = await getAIConfigStatus()
    if (res.code === 200 && res.data && res.data.chat) {
      agentStatus.mode = res.data.chat.mode
      agentStatus.detail = res.data.chat.detail
    }
  } catch { /* 静默 */ }
}

async function fetchLLMStatus() {
  try {
    const res = await getLLMConfig()
    if (res.code === 200 && res.data) {
      const isCloud = res.data.provider === 'openai_compatible'
      llmStatus.mode = isCloud ? 'cloud' : 'local'
      llmStatus.detail = isCloud
        ? `云端对话模型: ${res.data.model_name}`
        : `本地对话模型: ${res.data.model_name}`
      llmStatus.label = isCloud ? '云端模型' : '本地模型'
    }
  } catch {
    llmStatus.mode = 'local'
    llmStatus.detail = '未配置，使用本地模型'
    llmStatus.label = '本地模型'
  }
}

// 窗口可见时刷新状态
watch(() => props.visible, (val) => {
  if (val) {
    fetchAgentStatus()
    if (chatMode.value === 'rag') fetchLLMStatus()
  }
})

onMounted(() => {
  if (props.visible) {
    fetchAgentStatus()
    if (chatMode.value === 'rag') fetchLLMStatus()
  }
})

// ── AI 回复状态 ──
const statusPhase = ref('idle')
const statusText = computed(() => {
  if (statusPhase.value === 'thinking') return 'AI 正在思考...'
  if (statusPhase.value === 'typing') return toolStatusMessage.value || 'AI 正在输入...'
  return ''
})
const toolStatusMessage = ref('')

watch(() => messages.value.length, () => {
  nextTick(() => {
    if (msgContainerRef.value) {
      msgContainerRef.value.scrollTop = msgContainerRef.value.scrollHeight
    }
  })
})

// 发送消息
async function handleSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({
    _key: `msg-${msgKeyCounter++}`,
    role: 'user',
    content: text,
    timestamp: new Date().toISOString(),
  })
  inputText.value = ''
  loading.value = true
  statusPhase.value = 'thinking'

  const isRag = chatMode.value === 'rag'

  try {
    const body = isRag
      ? { message: text, session_id: ragSessionId.value || undefined, kb_ids: selectedKbIds.value }
      : { message: text, session_id: props.sessionId }

    const res = await fetch(`/api/${isRag ? 'rag' : 'agent'}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    const contentType = res.headers.get('content-type') || ''

    if (contentType.includes('text/event-stream')) {
      await handleSSEStream(res)
    } else {
      const data = await res.json()
      if (data.code === 200 && data.data) {
        if (data.data.session_id && data.data.session_id !== props.sessionId) {
          if (isRag) {
            ragSessionId.value = data.data.session_id
          } else {
            emit('update:sessionId', data.data.session_id)
            localStorage.setItem('chat_session_id', data.data.session_id)
          }
        }
        statusPhase.value = 'typing'
        messages.value.push({
          _key: `msg-${msgKeyCounter++}`,
          role: 'assistant',
          content: data.data.reply || '收到您的消息',
          timestamp: new Date().toISOString(),
          mode: data.data.mode || 'local',
        })
        await new Promise(r => setTimeout(r, 400))
      } else {
        messages.value.push({
          _key: `msg-${msgKeyCounter++}`,
          role: 'assistant',
          content: data.message || '响应异常，请稍后重试',
          timestamp: new Date().toISOString(),
          mode: 'local',
        })
      }
    }
  } catch (e) {
    const msg = e.message || String(e)
    messages.value.push({
      _key: `msg-${msgKeyCounter++}`,
      role: 'assistant',
      content: `抱歉，智能体暂时不可用。${msg ? '（' + msg + '）' : ''}`,
      timestamp: new Date().toISOString(),
    })
  } finally {
    loading.value = false
    statusPhase.value = 'idle'
  }
}

// SSE 流式处理
async function handleSSEStream(res) {
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let streamMsgIdx = -1

  streamMsgIdx = messages.value.length
  messages.value.push({
    _key: `msg-${msgKeyCounter++}`,
    role: 'assistant',
    content: '',
    timestamp: new Date().toISOString(),
    _streaming: true,
  })

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const jsonStr = line.substring(6)
        try {
          const event = JSON.parse(jsonStr)
          handleSSEEvent(event, streamMsgIdx)
        } catch { /* 忽略 */ }
      }
    }
  } catch (e) {
    console.error('[SSE] 流读取异常:', e)
    if (streamMsgIdx >= 0 && !messages.value[streamMsgIdx].content) {
      messages.value[streamMsgIdx].content = '流式传输中断，请重试。'
    }
  }
}

function handleSSEEvent(event, streamMsgIdx) {
  if (event.type === 'tool_status') {
    statusPhase.value = 'typing'
    toolStatusMessage.value = event.message || '正在执行工具调用...'
    return
  }

  if (event.type === 'delta') {
    statusPhase.value = 'typing'
    if (streamMsgIdx >= 0 && streamMsgIdx < messages.value.length) {
      messages.value[streamMsgIdx].content += event.content
    }
  } else if (event.type === 'done') {
    const doneContent = event.content || event.reply
    if (doneContent && streamMsgIdx >= 0 && streamMsgIdx < messages.value.length) {
      const currentContent = messages.value[streamMsgIdx].content || ''
      if (!currentContent) {
        messages.value[streamMsgIdx].content = doneContent
      }
    }
    if (event.session_id) {
      if (chatMode.value === 'rag') {
        ragSessionId.value = event.session_id
        saveLastUsedKbIds(selectedKbIds.value)
      } else if (event.session_id !== props.sessionId) {
        emit('update:sessionId', event.session_id)
        localStorage.setItem('chat_session_id', event.session_id)
      }
    }
    if (streamMsgIdx >= 0 && streamMsgIdx < messages.value.length) {
      delete messages.value[streamMsgIdx]._streaming
      messages.value[streamMsgIdx].mode = event.mode || 'local'
      if (event.sources && Array.isArray(event.sources) && event.sources.length > 0) {
        messages.value[streamMsgIdx].sources = event.sources
      }
      if (event.tool_used) {
        messages.value[streamMsgIdx]._tool_used = true
        messages.value[streamMsgIdx]._tool_type = event.tool_type || ''
      }
    }
    statusPhase.value = 'idle'
    toolStatusMessage.value = ''
  }
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<style scoped>
.chat-window {
  position: fixed;
  bottom: 90px;
  right: 30px;
  width: 420px;
  height: 600px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.15), 0 2px 10px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 1000;
}

@media (max-width: 480px) {
  .chat-window {
    bottom: 0;
    right: 0;
    width: 100vw;
    height: 100vh;
    border-radius: 0;
  }
}

/* ── 头部 ── */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  color: #fff;
  flex-shrink: 0;
  position: relative;
  z-index: 2;
}
.chat-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: rgba(255, 255, 255, 0.15);
}
.chat-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.chat-title {
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
}
.mode-switch {
  margin: 0 4px;
  flex-shrink: 0;
}
.mode-switch .el-radio-button__inner {
  padding: 0 8px;
  font-size: 11px;
  height: 24px;
  line-height: 24px;
  border-color: rgba(255, 255, 255, 0.3);
  background: transparent;
  color: rgba(255, 255, 255, 0.75);
  transition: all 0.2s;
}
.mode-switch .el-radio-button__original-radio:checked + .el-radio-button__inner {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  border-color: rgba(255, 255, 255, 0.5);
  box-shadow: none;
}
.chat-header-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
}
.chat-header-actions .el-button {
  color: #fff;
}
.chat-header-actions .el-button:hover {
  background: rgba(255, 255, 255, 0.15);
}

/* 状态标签 */
.status-tag {
  border-color: rgba(255, 255, 255, 0.35) !important;
  background: rgba(255, 255, 255, 0.12) !important;
  color: #fff !important;
  font-size: 11px;
  padding: 0 8px;
  height: 22px;
  line-height: 22px;
  border-radius: 11px;
  margin-right: 4px;
}
.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
  position: relative;
  top: -1px;
}
.status-dot.cloud {
  background: #52c41a;
  box-shadow: 0 0 4px rgba(82, 196, 26, 0.6);
}
.status-dot.local {
  background: #bfbfbf;
}

/* ── 知识库选择条 ── */
.kb-selector-bar {
  padding: 8px 12px;
  background: #f8fafc;
  border-bottom: 1px solid #edf2f7;
  flex-shrink: 0;
}
.kb-selector-inner {
  display: flex;
  align-items: center;
  gap: 8px;
}
.kb-icon {
  color: #1890ff;
  font-size: 16px;
  flex-shrink: 0;
}
.kb-select {
  width: 100%;
}
.kb-doc-count {
  float: right;
  color: #909399;
  font-size: 11px;
  margin-left: 8px;
}

/* ── 消息列表 ── */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f7f9fc;
}
.chat-messages::-webkit-scrollbar {
  width: 4px;
}
.chat-messages::-webkit-scrollbar-thumb {
  background: #d0d5dd;
  border-radius: 4px;
}
.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.msg-list {
  min-height: 100%;
}

/* ── 消息过渡动画 ── */
.msg-fade-enter-active {
  transition: all 0.3s ease;
}
.msg-fade-leave-active {
  transition: all 0.2s ease;
}
.msg-fade-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.msg-fade-leave-to {
  opacity: 0;
}

/* ── 占位 ── */
.chat-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: #999;
  user-select: none;
}
.placeholder-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.5;
}
.placeholder-title {
  font-size: 15px;
  font-weight: 600;
  color: #666;
  margin: 0 0 6px 0;
}
.placeholder-desc {
  font-size: 13px;
  color: #999;
  margin: 0;
}

/* ── AI 状态栏 ── */
.status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  margin-top: 10px;
  background: #f0f7ff;
  border-radius: 10px;
  border: 1px solid #d6e8ff;
  max-width: 200px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-bar.thinking .status-dot {
  background: #faad14;
  animation: status-pulse 0.8s ease-in-out infinite;
}
.status-bar.typing .status-dot {
  background: #1890ff;
  animation: status-blink 1s step-start infinite;
}
.status-text {
  font-size: 12px;
  color: #666;
}
.status-bar.thinking .status-text { color: #ad6800; }
.status-bar.typing .status-text { color: #096dd9; }

@keyframes status-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.85); }
}
@keyframes status-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}
.status-fade-enter-active,
.status-fade-leave-active {
  transition: all 0.3s ease;
}
.status-fade-enter-from,
.status-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* ── 输入区域 ── */
.chat-input-area {
  padding: 10px 16px 14px;
  border-top: 1px solid #edf2f7;
  background: #fff;
  flex-shrink: 0;
}
.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.input-wrapper .el-textarea__inner {
  border-radius: 10px;
  background: #f7f9fc;
  border: 1px solid #e5e9f0;
  padding: 8px 14px;
  font-size: 13px;
  line-height: 1.5;
  transition: border-color 0.2s;
}
.input-wrapper .el-textarea__inner:focus {
  border-color: #1890ff;
  background: #fff;
}
.send-btn {
  margin-bottom: 2px;
  flex-shrink: 0;
}

/* ── 滑入动画 ── */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(24px) scale(0.96);
}
</style>
