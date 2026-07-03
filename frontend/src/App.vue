<template>
  <!-- 初始加载中：显示空白，等待路由就绪（由 index.html 的 spinner 覆盖） -->
  <div v-if="appLoading" class="app-loading-placeholder"></div>

  <!-- 登录页不使用 Layout 包裹 -->
  <template v-else-if="isLoginPage">
    <router-view />
  </template>

  <!-- 其他页面使用完整 Layout -->
  <el-container v-else class="app-container">
    <el-aside width="220px" class="app-sidebar">
      <div class="logo">
        <el-icon :size="28"><Odometer /></el-icon>
        <span>能耗管理平台</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :default-openeds="openedMenuGroups"
        router
        background-color="#001529"
        text-color="#ffffffb3"
        active-text-color="#1890ff"
        class="side-menu"
      >
        <!-- 总览监控（全部角色均可访问） -->
        <el-sub-menu index="group-monitor" v-if="hasRole('admin','dispatcher','operator','user') || hasPermission('energy_monitoring','view')">
          <template #title>
            <el-icon><Odometer /></el-icon>
            <span>总览监控</span>
          </template>
          <el-menu-item index="/">
            <el-icon><DataAnalysis /></el-icon>
            <span>能耗看板</span>
          </el-menu-item>
        </el-sub-menu>

        <!-- 设备与能耗（energy_monitoring 权限） -->
        <el-sub-menu index="group-device" v-if="hasRole('admin','dispatcher','operator','user') || hasModuleAccess('energy_monitoring')">
          <template #title>
            <el-icon><Monitor /></el-icon>
            <span>设备与能耗</span>
          </template>
          <el-menu-item index="/devices">
            <el-icon><Monitor /></el-icon>
            <span>设备管理</span>
          </el-menu-item>
          <el-menu-item index="/tariff" v-if="hasRole('admin','dispatcher') || hasPermission('scheduling','config')">
            <el-icon><Money /></el-icon>
            <span>电价策略</span>
          </el-menu-item>
        </el-sub-menu>

        <!-- 告警与报告（energy_monitoring.view + reports 权限） -->
        <el-sub-menu index="group-alert" v-if="hasModuleAccess('energy_monitoring') || hasModuleAccess('reports') || hasRole('dispatcher','user')">
          <template #title>
            <el-icon><Warning /></el-icon>
            <span>告警与报告</span>
          </template>
          <el-menu-item index="/alerts">
            <el-icon><Warning /></el-icon>
            <span>告警管理</span>
          </el-menu-item>
          <el-menu-item v-if="hasRole('admin','dispatcher') || hasPermission('reports','view')" index="/reports-center">
            <el-icon><DataBoard /></el-icon>
            <span>报表中心</span>
          </el-menu-item>
          <el-menu-item v-if="hasRole('admin','dispatcher') || hasPermission('reports','view') || hasPermission('ai_analysis','view')" index="/reports">
            <el-icon><Document /></el-icon>
            <span>智能报告</span>
          </el-menu-item>
        </el-sub-menu>

        <!-- 优化调度（scheduling 权限） -->
        <el-sub-menu v-if="hasRole('admin','dispatcher') || hasModuleAccess('scheduling')" index="group-schedule">
          <template #title>
            <el-icon><Timer /></el-icon>
            <span>优化调度</span>
          </template>
          <el-menu-item index="/schedule" v-if="hasRole('admin','dispatcher') || hasPermission('scheduling','execute')">
            <el-icon><Timer /></el-icon>
            <span>调度优化</span>
          </el-menu-item>
          <el-menu-item index="/cost-allocation" v-if="hasRole('admin','dispatcher') || hasPermission('scheduling','view') || hasPermission('reports','export')">
            <el-icon><Coin /></el-icon>
            <span>成本分摊</span>
          </el-menu-item>
        </el-sub-menu>

        <!-- 系统设置（system 权限，仅管理员或有系统权限的用户） -->
        <el-sub-menu v-if="hasRole('admin') || hasModuleAccess('system')" index="group-system">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </template>
          <el-menu-item index="/users" v-if="hasRole('admin') || hasPermission('system','user_manage')">
            <el-icon><Setting /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item index="/ai-config" v-if="hasRole('admin') || hasPermission('system','config')">
            <el-icon><Cpu /></el-icon>
            <span>AI 管理</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>
    <el-container class="app-main">
      <el-header class="app-header">
        <span class="header-title">能耗智能管理优化平台</span>
        <div class="header-right">
          <BellNotification />
          <span v-if="user" class="user-name">
            <el-icon><User /></el-icon>
            {{ user.username }}
          </span>
          <RealTimeClock />
          <el-tag type="success" effect="dark" size="small">
            <el-icon><Connection /></el-icon>
            系统运行中
          </el-tag>
          <el-button v-if="user" type="danger" link size="small" @click="handleLogout">
            退出登录
          </el-button>
        </div>
      </el-header>
      <el-main class="app-content">
        <router-view />
      </el-main>
    </el-container>
    <!-- 全局对话悬浮按钮 -->
    <ChatFloatButton v-if="user" />
  </el-container>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEnergyStore } from './store/energyStore.js'
import { useAuthStore } from './store/authStore.js'
import RealTimeClock from './components/common/RealTimeClock.vue'
import ChatFloatButton from './components/chat/ChatFloatButton.vue'
import BellNotification from './components/common/BellNotification.vue'

const route = useRoute()
const router = useRouter()
const store = useEnergyStore()
const authStore = useAuthStore()

// 初始加载状态：路由就绪后关闭
const appLoading = ref(true)
router.isReady().then(() => {
  appLoading.value = false
})

const isLoginPage = computed(() => route.path === '/login')
const activeMenu = computed(() => route.path)
const user = computed(() => store.user)
// 轮询定时器 ID
let pollTimer = null

// 权限检查：委托给 store
function hasRole(...roles) {
  return store.hasRole(...roles)
}
function hasPermission(module, feature) {
  return store.hasPermission(module, feature)
}
function hasModuleAccess(module) {
  return store.hasModuleAccess(module)
}

// ──── 权限实时同步 ────

/** 跨标签页同步：当其他标签页修改 localStorage 中的权限时自动刷新 */
function onStorageChange(e) {
  if (e.key === 'user_permissions' && e.newValue) {
    try {
      const fresh = JSON.parse(e.newValue)
      store.permissions = fresh
    } catch { /* 忽略解析错误 */ }
  }
}

// 根据当前路由自动展开所属分组
const routeGroupMap = {
  '/': 'group-monitor',
  '/devices': 'group-device',
  '/tariff': 'group-device',
  '/alerts': 'group-alert',
  '/reports-center': 'group-alert',
  '/reports': 'group-alert',
  '/schedule': 'group-schedule',
  '/cost-allocation': 'group-schedule',
  '/users': 'group-system',
  '/ai-config': 'group-system',
}

const openedMenuGroups = computed(() => {
  const group = routeGroupMap[route.path]
  return group ? [group] : []
})

// 页面挂载时同步刷新权限（处理 localStorage 有缓存但因权限变更而过期的情况）
// 同时启动轮询检测权限变更（每 60 秒从后端拉取最新权限）
onMounted(() => {
  if (store.isLoggedIn) {
    store.refreshPermissions()
    pollTimer = setInterval(() => store.refreshPermissions(), 60000)
  }
  window.addEventListener('storage', onStorageChange)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  window.removeEventListener('storage', onStorageChange)
})

function handleLogout() {
  authStore.logout()
  store.logout()
  router.push('/login')
}
</script>

<style scoped>
/* 初始加载占位 */
.app-loading-placeholder {
  width: 100%;
  height: 100vh;
  background: transparent;
}

/* 子菜单分组样式 */
.side-menu .el-sub-menu__title {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.5px;
  opacity: 0.85;
}

.side-menu .el-sub-menu .el-menu-item {
  padding-left: 56px !important;
  font-size: 13px;
}

/* 子菜单展开高亮分隔 */
.side-menu .el-sub-menu.is-opened > .el-sub-menu__title {
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
</style>
