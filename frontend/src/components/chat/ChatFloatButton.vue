<template>
  <div class="chat-float-container">
    <!-- 对话窗口 -->
    <ChatWindow
      :visible="windowVisible"
      :session-id="sessionId"
      @close="windowVisible = false"
      @minimize="windowVisible = false"
      @update:session-id="sessionId = $event"
    />

    <!-- 悬浮按钮 -->
    <div
      :class="['float-button', { 'is-open': windowVisible, 'is-loading': false }]"
      @click="toggleWindow"
    >
      <el-icon :size="26">
        <ChatDotSquare v-if="!windowVisible" />
        <Close v-else />
      </el-icon>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ChatDotSquare, Close } from '@element-plus/icons-vue'
import ChatWindow from './ChatWindow.vue'

const windowVisible = ref(false)

// 从 localStorage 恢复会话ID
const sessionId = ref(localStorage.getItem('chat_session_id') || '')

function toggleWindow() {
  windowVisible.value = !windowVisible.value
}
</script>

<style scoped>
.chat-float-container {
  position: fixed;
  bottom: 30px;
  right: 30px;
  z-index: 9999;
}

.float-button {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1890ff, #096dd9);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(24, 144, 255, 0.4);
  transition: all 0.3s ease;
}
.float-button:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 24px rgba(24, 144, 255, 0.55);
}
.float-button.is-open {
  background: #f56c6c;
  box-shadow: 0 4px 16px rgba(245, 108, 108, 0.4);
}
.float-button.is-open:hover {
  box-shadow: 0 6px 24px rgba(245, 108, 108, 0.55);
}
</style>
