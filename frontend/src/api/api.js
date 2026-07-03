import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 请求拦截器：自动添加 Token
http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (err) => Promise.reject(err)
)

// 响应拦截器
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    console.error('API Error:', err)

    // 401 未授权，跳转登录
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      localStorage.removeItem('user_permissions')
      window.location.href = '/login'
    }

    return Promise.reject(err)
  }
)

// ========== 设备管理 ==========
export const getDevices = () => http.get('/devices/list')
export const getDevice = (id) => http.get(`/devices/${id}`)
export const createDevice = (data) => http.post('/devices/', data)
export const updateDevice = (id, data) => http.put(`/devices/${id}`, data)
export const deleteDevice = (id) => http.delete(`/devices/${id}`)

// ========== 实时数据 ==========
export const getLatestTelemetry = (deviceId) =>
  http.get('/telemetry/latest', { params: { device_id: deviceId } })
export const getCurrentPower = () => http.get('/telemetry/current')
export const getTelemetryRange = (deviceId, start, end) =>
  http.get('/telemetry/range', { params: { device_id: deviceId, start, end } })

// ========== 电价策略 ==========
export const getTariffs = () => http.get('/tariffs/')
export const createTariff = (data) => http.post('/tariffs/', data)
export const updateTariff = (id, data) => http.put(`/tariffs/${id}`, data)
export const getCurrentTariff = () => http.get('/tariffs/current')

// ========== 告警管理 ==========
export const getThresholds = (deviceId) =>
  http.get('/alerts/thresholds', { params: { device_id: deviceId } })
export const updateThreshold = (id, data) => http.put(`/alerts/thresholds/${id}`, data)
export const createThreshold = (data) => http.post('/alerts/thresholds', data)
export const getAlertRecords = (params) => http.get('/alerts/records', { params })
export const resolveAlert = (id, data) => http.put(`/alerts/records/${id}/resolve`, data)

// ========== 智能体 ==========
export const analyzeEnergy = (data) => http.post('/agent/analyze', data, { timeout: 300000 })
export const getAgentReports = (params) => http.get('/agent/reports', { params })
export const getSubscriptionReports = (subId, params) =>
  http.get(`/agent/subscriptions/${subId}/reports`, { params })

// ========== 看板 ==========
export const getOverview = () => http.get('/dashboard/overview')
export const getEnergyFlow = () => http.get('/dashboard/energyflow')
export const getTrend = (deviceIds, minutes) =>
  http.get('/dashboard/trend', { params: { device_ids: deviceIds, minutes } })
export const getAlertsBar = (limit) =>
  http.get('/dashboard/alerts-bar', { params: { limit } })

// ========== 报告 ==========
export const getReportSummary = () => http.get('/reports/summary')
export const exportExcel = (params) =>
  http.get('/reports/export/excel', { params, responseType: 'blob' })

// ========== 认证 ==========
export const login = (data) => http.post('/auth/login', data)
export const logout = () => http.post('/auth/logout')
export const getUsers = () => http.get('/auth/users')
export const createUser = (data) => http.post('/auth/users', data)
export const updateUser = (id, data) => http.put(`/auth/users/${id}`, data)

// ========== 用户权限管理 ==========
export const getPermissionModules = () => http.get('/auth/permissions/modules')
export const getUserPermissions = (userId) => http.get(`/auth/users/${userId}/permissions`)
export const updateUserPermissions = (userId, permissions) =>
  http.put(`/auth/users/${userId}/permissions`, { permissions })

// ========== 报表中心 ==========
export const getDailyReport = (params, config) => http.get('/report-center/daily', { params, ...config })
export const getWeeklyReport = (params, config) => http.get('/report-center/weekly', { params, ...config })
export const getMonthlyReport = (params, config) => http.get('/report-center/monthly', { params, ...config })
export const exportDailyReport = (params) => http.get('/report-center/daily/export', { params, responseType: 'blob' })
export const exportWeeklyReport = (params) => http.get('/report-center/weekly/export', { params, responseType: 'blob' })
export const exportMonthlyReport = (params) => http.get('/report-center/monthly/export', { params, responseType: 'blob' })
export const exportDeviceData = (params, config) =>
  http.get('/report-center/devices/export', { params, ...config })
export const exportAlertHistory = (params, config) =>
  http.get('/report-center/alerts/export', { params, ...config })

// ========== 执行追踪 ==========
export const executeSchedule = (reportId) => http.post('/agent/execute', { report_id: reportId })
export const getExecutions = () => http.get('/agent/executions')
export const completeExecution = (id) => http.post(`/agent/executions/${id}/complete`)

// ========== 告警统计 ==========
export const getAlertStats = () => http.get('/alerts/stats')
export const getResolutionSuggestions = (deviceId, paramType) =>
  http.get('/alerts/suggestions', { params: { device_id: deviceId, param_type: paramType } })

// ========== 设备排名 ==========
export const getDeviceRanking = () => http.get('/devices/ranking')

// ========== 成本分摊 ==========
export const getCostByWorkshop = (params) =>
  http.get('/cost-allocation/workshop-summary', { params })
export const getWorkshopDetail = (workshop, params) =>
  http.get(`/cost-allocation/workshop-detail/${workshop}`, { params })
export const getCostByDevice = (params) =>
  http.get('/cost-allocation/device-cost', { params })
export const getCostRules = () =>
  http.get('/cost-allocation/rules')
export const updateCostRule = (rule_type) =>
  http.put('/cost-allocation/rules', null, { params: { rule_type } })
export const exportCostCsv = (params) =>
  http.get('/cost-allocation/export', { params, responseType: 'blob' })

// ========== 报告订阅 ==========
export const getSubscriptions = () => http.get('/agent/subscriptions')
export const createSubscription = (data) => http.post('/agent/subscriptions', data)
export const updateSubscription = (id, data) => http.put(`/agent/subscriptions/${id}`, data)
export const deleteSubscription = (id) => http.delete(`/agent/subscriptions/${id}`)
export const runSubscription = (id) => http.post(`/agent/subscriptions/${id}/run`, null, { timeout: 300000 })

// ========== 通知消息 ==========
export const getNotifications = (params) => http.get('/notifications/list', { params })
export const getUnreadCount = () => http.get('/notifications/unread-count')
export const markNotificationRead = (id) => http.put(`/notifications/${id}/read`)
export const markAllNotificationsRead = () => http.put('/notifications/read-all')

// ========== 智能对话助手 ==========
export const chatSend = (message, sessionId) =>
  http.post('/agent/chat', { message, session_id: sessionId })
export const getChatHistory = (sessionId, limit = 50) =>
  http.get('/agent/chat/history', { params: { session_id: sessionId, limit } })

// ========== AI 配置管理 ==========
export const getAIConfig = () => http.get('/ai-config')
export const saveAIConfig = (data) => http.post('/ai-config', data)
export const testConnection = (type) => http.post('/ai-config/test', { type })
export const getAIConfigStatus = () => http.get('/ai-config/status')

// ========== 工作流管理 ==========
export const runWorkflowAnalyze = (data) => http.post('/workflows/analyze', data, { timeout: 300000 })
export const runWorkflowOptimize = (data) => http.post('/workflows/optimize', data, { timeout: 300000 })
export const getWorkflowHistory = (params) => http.get('/workflows/history', { params })
export const getWorkflowDetail = (id) => http.get(`/workflows/history/${id}`)
