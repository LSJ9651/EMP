<template>
  <div :class="['chat-message', role]">
    <div :class="['message-bubble', role]">
      <!-- 模式标签只在 AI 回复中显示 -->
      <div v-if="role === 'assistant' && mode === 'cloud'" class="mode-tag cloud">☁️ 云端</div>
      <div v-else-if="role === 'assistant' && mode === 'local'" class="mode-tag local">🏠 本地</div>
      <!-- 工具执行指示 -->
      <div v-if="role === 'assistant' && _toolUsed" class="tool-indicator">
        <span class="tool-dot"></span>
        <span class="tool-label">已调用 {{ _toolType || '工具' }}</span>
      </div>
      <div class="message-content" v-html="renderedContent" />
      <span v-if="streaming" class="stream-cursor">|</span>
      <div class="message-time">{{ formatTime(timestamp) }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  role: { type: String, required: true },
  content: { type: String, required: true },
  timestamp: { type: String, default: '' },
  streaming: { type: Boolean, default: false },
  mode: { type: String, default: 'local' },
  _toolUsed: { type: Boolean, default: false },
  _toolType: { type: String, default: '' },
})

// 过滤 <INTERNAL_CMD> 标签，隐藏平台内部指令
const cleanContent = computed(() => {
  return (props.content || '').replace(/<INTERNAL_CMD>[\s\S]*?<\/INTERNAL_CMD>/gi, '')
})

const renderedContent = computed(() => {
  try {
    return marked.parse(cleanContent.value)
  } catch {
    return cleanContent.value
  }
})

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}
</script>

<style scoped>
.chat-message {
  display: flex;
  margin-bottom: 12px;
}
.chat-message.user {
  justify-content: flex-end;
}
.chat-message.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 82%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}
.message-bubble.user {
  background: #1890ff;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.message-bubble.assistant {
  background: #f0f0f0;
  color: #333;
  border-bottom-left-radius: 4px;
}
.message-bubble.user .message-content {
  color: #fff;
}
.message-bubble.assistant .message-content {
  color: #333;
}

.message-content :deep(p) { margin: 4px 0; }
.message-content :deep(ul),
.message-content :deep(ol) { margin: 4px 0; padding-left: 18px; }
.message-content :deep(strong) { font-weight: 600; }
.message-content :deep(code) {
  background: rgba(0,0,0,0.08);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
}
.message-content :deep(pre) {
  background: rgba(0,0,0,0.06);
  padding: 8px;
  border-radius: 6px;
  overflow-x: auto;
}

.message-time {
  font-size: 11px;
  opacity: 0.55;
  margin-top: 4px;
  text-align: right;
}
.message-bubble.user .message-time { color: rgba(255,255,255,0.75); }

.mode-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  margin-bottom: 4px;
  display: inline-block;
}
.mode-tag.cloud {
  background: rgba(64, 158, 255, 0.15);
  color: #409eff;
}
.mode-tag.local {
  background: rgba(144, 147, 153, 0.15);
  color: #909399;
}

.stream-cursor {
  animation: blink 1s step-start infinite;
  font-weight: 200;
  color: #1890ff;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.tool-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #67c23a;
  margin-bottom: 4px;
}
.tool-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #67c23a;
  box-shadow: 0 0 4px rgba(103, 194, 58, 0.5);
}
.tool-label {
  opacity: 0.8;
}
</style>
