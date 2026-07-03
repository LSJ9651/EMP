<template>
  <div class="clock-container">
    <el-icon class="clock-icon"><Clock /></el-icon>
    <span class="clock-text">{{ timeString }}</span>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const timeString = ref('')
let timer = null

const WEEKDAYS = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

function pad(n) {
  return n.toString().padStart(2, '0')
}

function updateTime() {
  const now = new Date()
  const year = now.getFullYear()
  const month = pad(now.getMonth() + 1)
  const day = pad(now.getDate())
  const hours = pad(now.getHours())
  const minutes = pad(now.getMinutes())
  const seconds = pad(now.getSeconds())
  const weekday = WEEKDAYS[now.getDay()]

  timeString.value = `${year}-${month}-${day} ${hours}:${minutes}:${seconds} ${weekday}`
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<style scoped>
.clock-container {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 14px;
  background: #f0f5ff;
  border-radius: 6px;
  border: 1px solid #d6e4ff;
}

.clock-icon {
  font-size: 16px;
  color: #1890ff;
}

.clock-text {
  font-family: 'Consolas', 'Source Code Pro', 'Menlo', monospace;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  letter-spacing: 0.5px;
  white-space: nowrap;
}
</style>
