<template>
  <div :class="['chat-message', role]">
    <div :class="['message-bubble', role]">
      <!-- 模式标签只在 AI 回复中显示 -->
      <div v-if="role === 'assistant'" class="mode-tag">
        <span :class="['tag-dot', mode]"></span>
        <span v-if="mode === 'cloud'">☁️ 云端</span>
        <span v-else>🏠 本地</span>
      </div>
      <!-- 工具执行指示 -->
      <div v-if="role === 'assistant' && _toolUsed" class="tool-indicator">
        <span class="tool-dot"></span>
        <span class="tool-label">已调用 {{ _toolType || '工具' }}</span>
      </div>
      <div class="message-content" v-html="renderedContent" />
      <span v-if="streaming" class="stream-cursor">|</span>
      <!-- 引用来源 -->
      <div v-if="role === 'assistant' && sources && sources.length > 0" class="source-section">
        <div class="source-title">📎 参考来源</div>
        <div class="source-list">
          <div
            v-for="(src, i) in sources"
            :key="i"
            class="source-item"
            :title="`相关度: ${(src.score * 100).toFixed(0)}%`"
          >
            <span class="source-idx">[{{ i + 1 }}]</span>
            <span class="source-text">{{ truncateText(src.text_preview || '', 60) }}</span>
          </div>
        </div>
      </div>
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
  sources: { type: Array, default: () => [] },
  _toolUsed: { type: Boolean, default: false },
  _toolType: { type: String, default: '' },
})

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

function truncateText(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
}

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
  margin-bottom: 14px;
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
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
  position: relative;
}
.message-bubble.user {
  background: linear-gradient(135deg, #1890ff, #409eff);
  color: #fff;
  border-bottom-right-radius: 4px;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2);
}
.message-bubble.assistant {
  background: #fff;
  color: #333;
  border-bottom-left-radius: 4px;
  border: 1px solid #edf2f7;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.message-bubble.assistant::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  background: linear-gradient(180deg, transparent, #1890ff, transparent);
  border-radius: 3px 0 0 3px;
  opacity: 0.3;
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
  background: rgba(0,0,0,0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.message-content :deep(pre) {
  background: #f5f7fa;
  padding: 10px 12px;
  border-radius: 8px;
  overflow-x: auto;
  border: 1px solid #edf2f7;
}
.message-content :deep(pre code) {
  background: transparent;
  padding: 0;
}
.message-content :deep(a) {
  color: #1890ff;
  text-decoration: none;
}
.message-content :deep(blockquote) {
  border-left: 3px solid #e0e6ed;
  margin: 8px 0;
  padding: 4px 12px;
  color: #666;
}

.message-time {
  font-size: 11px;
  opacity: 0.55;
  margin-top: 4px;
  text-align: right;
}
.message-bubble.user .message-time { color: rgba(255,255,255,0.75); }

/* 模式标签 */
.mode-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 8px;
  margin-bottom: 6px;
}
.tag-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  border-radius: 50%;
}
.tag-dot.cloud {
  background: #52c41a;
  box-shadow: 0 0 3px rgba(82, 196, 26, 0.5);
}
.tag-dot.local {
  background: #bfbfbf;
}
.message-bubble.assistant .mode-tag {
  background: #f0f5ff;
  color: #409eff;
}

/* 流式光标 */
.stream-cursor {
  animation: blink 1s step-start infinite;
  font-weight: 200;
  color: #1890ff;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* 工具指示 */
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

/* 引用来源 */
.source-section {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #e5e9f0;
}
.source-title {
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
  font-weight: 500;
}
.source-list {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.source-item {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-size: 11px;
  color: #909399;
  line-height: 1.4;
}
.source-idx {
  color: #409eff;
  font-weight: 600;
  flex-shrink: 0;
}
.source-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
