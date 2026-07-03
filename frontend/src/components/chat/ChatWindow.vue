<template>
  <transition name="slide-up">
    <div v-if="visible" class="chat-window">
      <!-- 头部 -->
      <div class="chat-header">
        <div class="chat-header-left">
          <span class="chat-title">🤖 智能助手</span>
          <el-tooltip
            :content="agentStatus.detail"
            placement="bottom"
            effect="dark"
          >
            <el-tag
              :type="agentStatus.mode === 'cloud' ? 'success' : 'info'"
              size="small"
              effect="plain"
              class="agent-mode-tag"
            >
              <span class="agent-dot" :class="agentStatus.mode"></span>
              {{ agentStatus.mode === 'cloud' ? '云端智能体' : '本地智能体' }}
            </el-tag>
          </el-tooltip>
        </div>
        <div class="chat-header-actions">
          <el-button text circle size="small" @click="$emit('minimize')">
            <el-icon><ArrowDown /></el-icon>
          </el-button>
          <el-button text circle size="small" @click="$emit('close')">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="chat-messages" ref="msgContainerRef">
        <div v-if="messages.length === 0" class="chat-placeholder">
          <p>👋 你好！我是能耗智能管理助手</p>
          <p>请问有什么可以帮你的？</p>
        </div>
        <ChatMessage
          v-for="(msg, idx) in messages"
          :key="idx"
          :role="msg.role"
          :content="msg.content"
          :timestamp="msg.timestamp"
          :streaming="!!msg._streaming"
          :mode="msg.mode || 'local'"
          :_tool-used="!!msg._tool_used"
          :_tool-type="msg._tool_type || ''"
        />
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
          :disabled="!inputText.trim() || loading"
          @click="handleSend"
        />
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, reactive, nextTick, watch, onMounted, computed } from 'vue'
import { ArrowDown, Close, Promotion } from '@element-plus/icons-vue'
import { getAIConfigStatus } from '../../api/api.js'
import ChatMessage from './ChatMessage.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  sessionId: { type: String, default: '' },
})
const emit = defineEmits(['close', 'minimize', 'update:sessionId'])

const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const msgContainerRef = ref(null)

// ── AI 回复状态阶段 ──
// 'idle'      — 无操作
// 'thinking'  — 消息已发送，等待 AI 分析/思考
// 'typing'    — AI 正在生成/输出回复内容
const statusPhase = ref('idle')
const statusText = computed(() => {
  if (statusPhase.value === 'thinking') return 'AI 正在思考...'
  if (statusPhase.value === 'typing') return toolStatusMessage.value || 'AI 正在输入...'
  return ''
})

// 智能体状态
const agentStatus = reactive({
  mode: 'local',
  detail: '使用本地规则引擎',
})

// 获取智能体状态
async function fetchAgentStatus() {
  try {
    const res = await getAIConfigStatus()
    if (res.code === 200 && res.data && res.data.chat) {
      agentStatus.mode = res.data.chat.mode
      agentStatus.detail = res.data.chat.detail
    }
  } catch {
    // 静默失败，保持默认本地模式
  }
}

// 窗口可见时刷新状态
watch(
  () => props.visible,
  (val) => {
    if (val) fetchAgentStatus()
  }
)

onMounted(() => {
  if (props.visible) fetchAgentStatus()
})

// 自动滚动到底部
watch(
  () => messages.value.length,
  () => {
    nextTick(() => {
      if (msgContainerRef.value) {
        msgContainerRef.value.scrollTop = msgContainerRef.value.scrollHeight
      }
    })
  }
)

// 发送消息
async function handleSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({
    role: 'user',
    content: text,
    timestamp: new Date().toISOString(),
  })
  inputText.value = ''
  loading.value = true
  statusPhase.value = 'thinking'

  try {
    const res = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: props.sessionId }),
    })

    const contentType = res.headers.get('content-type') || ''

    if (contentType.includes('text/event-stream')) {
      // ── 流式 SSE 响应 ──
      await handleSSEStream(res)
    } else {
      // ── JSON 响应 ──
      const data = await res.json()
      if (data.code === 200 && data.data) {
        if (data.data.session_id && data.data.session_id !== props.sessionId) {
          emit('update:sessionId', data.data.session_id)
          localStorage.setItem('chat_session_id', data.data.session_id)
        }
        statusPhase.value = 'typing'
        messages.value.push({
          role: 'assistant',
          content: data.data.reply || '收到您的消息',
          timestamp: new Date().toISOString(),
          mode: data.data.mode || 'local',
        })
        await new Promise(r => setTimeout(r, 400))
      } else {
        messages.value.push({
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
  let streamMsgIdx = -1  // 流式消息在 messages 数组中的索引

  // 先插入一条占位消息
  streamMsgIdx = messages.value.length
  messages.value.push({
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
          await handleSSEEvent(event, streamMsgIdx)
        } catch {
          // 忽略非 JSON 行
        }
      }
    }
  } catch (e) {
    console.error('[SSE] 流读取异常:', e)
    if (streamMsgIdx >= 0 && !messages.value[streamMsgIdx].content) {
      messages.value[streamMsgIdx].content = '流式传输中断，请重试。'
    }
  }
}

const toolStatusMessage = ref('')  // 工具执行状态文本

function handleSSEEvent(event, streamMsgIdx) {
  if (event.type === 'tool_status') {
    // 工具执行状态事件
    statusPhase.value = 'typing'
    toolStatusMessage.value = event.message || '正在执行工具调用...'
    return
  }

  if (event.type === 'delta') {
    statusPhase.value = 'typing'
    // 追加 token 到流式消息
    if (streamMsgIdx >= 0 && streamMsgIdx < messages.value.length) {
      messages.value[streamMsgIdx].content += event.content
    }
  } else if (event.type === 'done') {
    // done 事件可能包含完整内容（当没有 delta 事件时）
    const doneContent = event.content || event.reply
    if (doneContent && streamMsgIdx >= 0 && streamMsgIdx < messages.value.length) {
      const currentContent = messages.value[streamMsgIdx].content || ''
      if (!currentContent) {
        messages.value[streamMsgIdx].content = doneContent
      }
    }
    // 流完成：更新 sessionId，标记消息完成
    if (event.session_id && event.session_id !== props.sessionId) {
      emit('update:sessionId', event.session_id)
      localStorage.setItem('chat_session_id', event.session_id)
    }
    if (streamMsgIdx >= 0 && streamMsgIdx < messages.value.length) {
      delete messages.value[streamMsgIdx]._streaming
      messages.value[streamMsgIdx].mode = event.mode || 'local'
      // 保存工具调用标记（用于展示状态指示）
      if (event.tool_used) {
        messages.value[streamMsgIdx]._tool_used = true
        messages.value[streamMsgIdx]._tool_type = event.tool_type || ''
      }
    }
    statusPhase.value = 'idle'
    toolStatusMessage.value = ''
  }
}

// 键盘事件：Enter 发送，Shift+Enter 换行
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
  height: 560px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 1000;
}

/* 响应式：移动端全屏 */
@media (max-width: 480px) {
  .chat-window {
    bottom: 0;
    right: 0;
    width: 100vw;
    height: 100vh;
    border-radius: 0;
  }
  .status-bar {
    max-width: 160px;
  }
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: linear-gradient(135deg, #1890ff, #096dd9);
  color: #fff;
  flex-shrink: 0;
}
.chat-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.chat-title {
  font-size: 15px;
  font-weight: 600;
}
.agent-mode-tag {
  border-color: rgba(255, 255, 255, 0.35) !important;
  background: rgba(255, 255, 255, 0.12) !important;
  color: #fff !important;
  font-size: 11px;
  padding: 0 8px;
  height: 22px;
  line-height: 22px;
}
.agent-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}
.agent-dot.cloud {
  background: #52c41a;
  box-shadow: 0 0 4px rgba(82, 196, 26, 0.6);
}
.agent-dot.local {
  background: #bfbfbf;
}
.chat-header-actions .el-button {
  color: #fff;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #fafbfc;
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

.chat-placeholder {
  text-align: center;
  color: #999;
  margin-top: 80px;
  font-size: 14px;
}

.chat-input-area {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 16px;
  border-top: 1px solid #eee;
  background: #fff;
  flex-shrink: 0;
}

/* 过渡动画 */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.25s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
