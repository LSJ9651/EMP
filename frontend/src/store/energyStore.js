import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getDevices,
  getCurrentPower,
  getOverview,
  getAlertsBar,
  getTariffs,
  login as loginApi,
  logout as logoutApi,
  getUserPermissions,
} from '../api/api.js'

export const useEnergyStore = defineStore('energy', () => {
  // 设备列表
  const devices = ref([])
  // 实时功率
  const realtimePower = ref({ total_power_kw: 0, devices: [] })
  // 看板概览
  const overview = ref({})
  // 告警列表
  const alerts = ref([])
  // 电价策略
  const tariffs = ref([])
  // 加载状态
  const loading = ref(false)

  // 认证
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const isLoggedIn = computed(() => !!user.value)

  // 细粒度权限（从登录响应或 API 获取）
  const permissions = ref(JSON.parse(localStorage.getItem('user_permissions') || '{}'))

  async function login(username, password) {
    const res = await loginApi({ username, password })
    if (res.code === 200) {
      const data = res.data
      user.value = data

      // 存储权限（登录响应中已包含）
      const perms = data.permissions || {}
      permissions.value = perms

      localStorage.setItem('user', JSON.stringify(data))
      localStorage.setItem('user_permissions', JSON.stringify(perms))
    } else {
      throw new Error(res.message || '登录失败')
    }
  }

  function logout() {
    user.value = null
    permissions.value = {}
    localStorage.removeItem('user')
    localStorage.removeItem('user_permissions')
    logoutApi().catch(() => {})
  }

  /**
   * 同步刷新当前用户的权限（从后端拉取最新权限）
   * 用于管理员修改用户权限后，目标用户刷新可用
   */
  async function refreshPermissions(userId) {
    if (!userId) {
      userId = user.value?.id
      if (!userId) return
    }
    try {
      const res = await getUserPermissions(userId)
      if (res.code === 200) {
        // 提取扁平权限映射
        const flat = {}
        for (const mod of res.data.modules || []) {
          for (const feat of mod.features) {
            flat[`${mod.module}.${feat.feature}`] = feat.is_granted
          }
        }
        permissions.value = flat
        localStorage.setItem('user_permissions', JSON.stringify(flat))
      }
    } catch {
      // 静默失败，使用已有权限
    }
  }

  /**
   * 检查当前用户是否具有指定角色之一
   */
  function hasRole(...roles) {
    if (!user.value) return false
    return roles.includes(user.value.role)
  }

  /**
   * 检查当前用户是否具有指定模块+功能的细粒度权限
   * 管理员角色自动拥有所有权限
   * @param {string} module - 模块编码，如 'energy_monitoring'
   * @param {string} feature - 功能编码，如 'view'
   * @returns {boolean}
   */
  function hasPermission(module, feature) {
    if (!user.value) return false
    // 管理员默认全权限
    if (user.value.role === 'admin') return true
    // 检查细粒度权限
    const key = `${module}.${feature}`
    return !!permissions.value[key]
  }

  /**
   * 检查用户在指定模块下是否拥有任意权限
   * @param {string} module - 模块编码
   * @returns {boolean}
   */
  function hasModuleAccess(module) {
    if (!user.value) return false
    if (user.value.role === 'admin') return true
    const prefix = module + '.'
    return Object.keys(permissions.value).some(k => k.startsWith(prefix))
  }

  // ──── 数据获取 ────

  async function fetchDevices() {
    const res = await getDevices()
    if (res.code === 200) {
      devices.value = res.data
    }
  }

  async function fetchRealtimePower() {
    const res = await getCurrentPower()
    if (res.code === 200) {
      realtimePower.value = res.data
    }
  }

  async function fetchOverview() {
    const res = await getOverview()
    if (res.code === 200) {
      overview.value = res.data
    }
  }

  async function fetchAlerts() {
    const res = await getAlertsBar(10)
    if (res.code === 200) {
      alerts.value = res.data
    }
  }

  async function fetchTariffs() {
    const res = await getTariffs()
    if (res.code === 200) {
      tariffs.value = res.data
    }
  }

  async function refreshAll() {
    loading.value = true
    try {
      await Promise.all([
        fetchDevices(),
        fetchRealtimePower(),
        fetchOverview(),
        fetchAlerts(),
        fetchTariffs(),
      ])
    } finally {
      loading.value = false
    }
  }

  return {
    devices,
    realtimePower,
    overview,
    alerts,
    tariffs,
    loading,
    user,
    isLoggedIn,
    permissions,
    login,
    logout,
    refreshPermissions,
    hasRole,
    hasPermission,
    hasModuleAccess,
    fetchDevices,
    fetchRealtimePower,
    fetchOverview,
    fetchAlerts,
    fetchTariffs,
    refreshAll,
  }
})
