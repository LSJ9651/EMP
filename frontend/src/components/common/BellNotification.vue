<template>
  <el-popover
    placement="bottom-end"
    :width="380"
    trigger="click"
    :show-after="0"
    @show="onOpen"
  >
    <template #reference>
      <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" class="bell-badge">
        <el-button link class="bell-btn">
          <el-icon :size="20"><Bell /></el-icon>
        </el-button>
      </el-badge>
    </template>

    <div class="notify-panel">
      <div class="notify-header">
        <span class="notify-title">消息中心</span>
        <el-button
          v-if="unreadCount > 0"
          link
          type="primary"
          size="small"
          @click="handleMarkAllRead"
        >
          全部已读
        </el-button>
      </div>

      <div v-loading="loading" class="notify-list">
        <template v-if="notifications.length === 0">
          <div class="notify-empty">
            <el-icon :size="40" color="#c0c4cc"><Bell /></el-icon>
            <p>暂无通知消息</p>
          </div>
        </template>

        <div
          v-for="item in notifications"
          :key="item.id"
          class="notify-item"
          :class="{ unread: !item.is_read }"
          @click="handleClick(item)"
        >
          <div class="notify-dot" v-if="!item.is_read"></div>
          <div class="notify-body">
            <div class="notify-item-title">
              <el-tag size="small" :type="categoryTagType(item.category)">
                {{ categoryLabel(item.category) }}
              </el-tag>
              <span class="notify-time">{{ formatTime(item.created_at) }}</span>
            </div>
            <div class="notify-item-title-text">{{ item.title }}</div>
            <div class="notify-item-content" v-if="item.content">{{ item.content }}</div>
          </div>
        </div>
      </div>

      <div class="notify-footer" v-if="total > notifications.length">
        <el-button link type="primary" size="small" @click="loadMore" :loading="loadingMore">
          加载更多
        </el-button>
      </div>
    </div>
  </el-popover>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import {
  getNotifications, getUnreadCount,
  markNotificationRead, markAllNotificationsRead,
} from '../../api/api.js'

const unreadCount = ref(0)
const notifications = ref([])
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const pageSize = 10
let pollTimer = null
const router = useRouter()

// ──── 分类标签 ────
function categoryLabel(c) {
  const map = { subscription: '订阅', alert: '告警', report: '报告', system: '系统' }
  return map[c] || c
}

function categoryTagType(c) {
  const map = { subscription: 'success', alert: 'danger', report: 'warning', system: 'info' }
  return map[c] || 'info'
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return d.toLocaleDateString()
}

// ──── 数据加载 ────
async function fetchUnreadCount() {
  try {
    const res = await getUnreadCount()
    if (res.code === 200) unreadCount.value = res.data?.count || 0
  } catch (e) { /* silent */ }
}

async function fetchNotifications(append = false) {
  if (!append) loading.value = true
  else loadingMore.value = true
  try {
    const res = await getNotifications({
      limit: pageSize,
      offset: append ? notifications.value.length : 0,
    })
    if (res.code === 200) {
      if (append) {
        notifications.value.push(...(res.data?.items || []))
      } else {
        notifications.value = res.data?.items || []
      }
      total.value = res.data?.total || 0
    }
  } catch (e) { /* silent */ }
  finally {
    loading.value = false
    loadingMore.value = false
  }
}

function onOpen() {
  if (notifications.value.length === 0) {
    fetchNotifications()
  }
  fetchUnreadCount()
}

function loadMore() {
  fetchNotifications(true)
}

// ──── 操作 ────
async function handleClick(item) {
  if (!item.is_read) {
    try {
      await markNotificationRead(item.id)
      item.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch (e) { /* silent */ }
  }

  // 报告/订阅类通知：点击跳转到「智能报告」页面查看分析结果
  if ((item.category === 'report' || item.category === 'subscription') && item.source_type === 'agent_report' && item.source_id) {
    router.push({ path: '/reports', query: { report_id: item.source_id, tab: 'analysis' } })
  }
}

async function handleMarkAllRead() {
  try {
    await markAllNotificationsRead()
    notifications.value.forEach(n => { n.is_read = true })
    unreadCount.value = 0
  } catch (e) { /* silent */ }
}

// ──── 轮询 ────
onMounted(() => {
  fetchUnreadCount()
  pollTimer = setInterval(fetchUnreadCount, 30000) // 每30秒刷新未读数
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.bell-btn {
  color: #555;
  font-size: 20px;
}
.bell-btn:hover {
  color: #1890ff;
}
.bell-badge {
  cursor: pointer;
}

.notify-panel {
  max-height: 480px;
  display: flex;
  flex-direction: column;
}

.notify-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid #ebeef5;
}

.notify-title {
  font-size: 16px;
  font-weight: 600;
}

.notify-list {
  flex: 1;
  overflow-y: auto;
  min-height: 120px;
  max-height: 380px;
}

.notify-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 0;
  color: #c0c4cc;
}
.notify-empty p {
  margin-top: 8px;
  font-size: 14px;
}

.notify-item {
  display: flex;
  align-items: flex-start;
  padding: 12px 0;
  border-bottom: 1px solid #f2f3f5;
  cursor: pointer;
  transition: background .15s;
}
.notify-item:hover {
  background: #f5f7fa;
}
.notify-item.unread {
  background: #ecf5ff;
}

.notify-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f56c6c;
  margin-top: 4px;
  margin-right: 10px;
  flex-shrink: 0;
}

.notify-body {
  flex: 1;
  min-width: 0;
}

.notify-item-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.notify-item-title-text {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}
.notify-item-content {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.5;
}
.notify-time {
  font-size: 11px;
  color: #c0c4cc;
}

.notify-footer {
  text-align: center;
  padding-top: 8px;
  border-top: 1px solid #ebeef5;
}
</style>
