<template>
  <div class="report-center-page">
    <h2 class="page-title">报表中心</h2>

    <el-tabs v-model="activeTab">
      <!-- Tab 1: 能耗报表 -->
      <el-tab-pane label="能耗报表" name="energy">
        <div class="tab-header">
          <el-radio-group v-model="reportType" @change="onReportTypeChange">
            <el-radio-button value="daily">日报</el-radio-button>
            <el-radio-button value="weekly">周报</el-radio-button>
            <el-radio-button value="monthly">月报</el-radio-button>
          </el-radio-group>
          <el-date-picker
            v-model="reportDate"
            :type="datePickerType"
            :placeholder="datePickerPlaceholder"
            style="margin-left: 16px; width: 200px"
            @change="fetchCurrentReport"
          />
          <el-button type="primary" style="margin-left: 16px" @click="exportExcel">
            <el-icon><Download /></el-icon>导出Excel
          </el-button>
          <el-button type="success" @click="exportPDF">
            <el-icon><Printer /></el-icon>导出PDF
          </el-button>
        </div>

        <div v-loading="reportLoading" element-loading-text="加载报表数据...">
          <el-row :gutter="16" style="margin-top: 16px">
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-label">总能耗</div>
                <div class="stat-value">
                  {{ displayData.total_energy_kwh || 0 }}<span class="unit">kWh</span>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-label">峰时用电</div>
                <div class="stat-value">
                  {{ displayData.peak_energy_kwh || 0 }}<span class="unit">kWh</span>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-label">平时用电</div>
                <div class="stat-value">
                  {{ displayData.flat_energy_kwh || 0 }}<span class="unit">kWh</span>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-label">谷时用电</div>
                <div class="stat-value">
                  {{ displayData.valley_energy_kwh || 0 }}<span class="unit">kWh</span>
                </div>
              </div>
            </el-col>
          </el-row>

          <el-row :gutter="16" style="margin-top: 16px">
            <el-col :span="8">
              <div class="stat-card">
                <div class="stat-label">碳排放估算</div>
                <div class="stat-value">
                  {{ displayData.co2_kg || 0 }}<span class="unit">kgCO₂</span>
                </div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-card">
                <div class="stat-label">预估成本</div>
                <div class="stat-value">
                  ¥{{ (displayData.cost_yuan || 0).toFixed(2) }}<span class="unit">元</span>
                </div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-card">
                <div class="stat-label">最大功率</div>
                <div class="stat-value">
                  {{ displayData.max_power_kw || 0 }}<span class="unit">kW</span>
                </div>
              </div>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 设备数据导出 -->
      <el-tab-pane label="设备数据导出" name="device">
        <div class="tab-header">
          <el-select v-model="deviceFilter" placeholder="选择设备" clearable style="width: 200px">
            <el-option v-for="d in devices" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
          <el-date-picker
            v-model="deviceDateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            style="margin-left: 16px; width: 360px"
          />
          <el-button type="primary" style="margin-left: 16px" :loading="exportingDevice" @click="exportDevice">
            <el-icon><Download /></el-icon>导出
          </el-button>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 告警历史导出 -->
      <el-tab-pane label="告警历史导出" name="alert">
        <div class="tab-header">
          <el-date-picker
            v-model="alertDateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            style="width: 360px"
          />
          <el-select v-model="alertSeverity" placeholder="严重程度" clearable style="margin-left: 16px; width: 140px">
            <el-option label="严重" value="critical" />
            <el-option label="警告" value="warning" />
            <el-option label="提示" value="info" />
          </el-select>
          <el-button type="primary" style="margin-left: 16px" :loading="exportingAlert" @click="exportAlert">
            <el-icon><Download /></el-icon>导出
          </el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDevices, getDailyReport, getWeeklyReport, getMonthlyReport, exportDailyReport, exportWeeklyReport, exportMonthlyReport, exportDeviceData, exportAlertHistory } from '../api/api.js'

const activeTab = ref('energy')
const reportType = ref('daily')
const reportDate = ref(new Date())

// ──── 缓存：按类型缓存报表数据，避免重复请求 ────
const reportCache = ref({ daily: null, weekly: null, monthly: null })
const reportLoading = ref(false)
const dailyList = ref([])

const devices = ref([])
const deviceFilter = ref(null)
const deviceDateRange = ref([])
const exportingDevice = ref(false)

const alertDateRange = ref([])
const alertSeverity = ref(null)
const exportingAlert = ref(false)

// ──── 计算属性：从缓存读取当前报表数据，周报/月报自动汇总 ────
const reportData = computed(() => {
  return reportCache.value[reportType.value]
})

const displayData = computed(() => {
  const data = reportData.value
  if (!data) return {}
  if (reportType.value === 'daily') {
    return data
  }
  // 周报/月报：从每日汇总数组中计算总览
  const list = Array.isArray(data) ? data : []
  if (list.length === 0) return {}
  return {
    total_energy_kwh: round2(list.reduce((s, d) => s + (d.total_energy_kwh || 0), 0)),
    peak_energy_kwh: round2(list.reduce((s, d) => s + (d.peak_energy_kwh || 0), 0)),
    flat_energy_kwh: round2(list.reduce((s, d) => s + (d.flat_energy_kwh || 0), 0)),
    valley_energy_kwh: round2(list.reduce((s, d) => s + (d.valley_energy_kwh || 0), 0)),
    max_power_kw: round2(Math.max(...list.map(d => d.max_power_kw || 0), 0)),
    co2_kg: round2(list.reduce((s, d) => s + (d.co2_kg || 0), 0)),
    cost_yuan: round2(list.reduce((s, d) => s + (d.cost_yuan || 0), 0)),
  }
})

function round2(val) {
  return Math.round(val * 100) / 100
}

const datePickerType = computed(() => {
  if (reportType.value === 'daily') return 'date'
  if (reportType.value === 'weekly') return 'week'
  return 'month'
})

const datePickerPlaceholder = computed(() => {
  if (reportType.value === 'daily') return '选择日期'
  if (reportType.value === 'weekly') return '选择周'
  return '选择月份'
})

// ──── 数据获取 ────

async function fetchDevicesList() {
  const res = await getDevices()
  if (res.code === 200) devices.value = res.data
}

/** 按类型请求报表（带缓存检查） */
async function fetchReportByType(type) {
  const cacheKey = type
  let res
  if (type === 'daily') {
    const dateStr = formatDate(reportDate.value)
    res = await getDailyReport({ date: dateStr })
  } else if (type === 'weekly') {
    res = await getWeeklyReport()
  } else {
    res = await getMonthlyReport()
  }
  if (res.code === 200) {
    reportCache.value[cacheKey] = res.data
    if (Array.isArray(res.data)) {
      dailyList.value = res.data
    }
  }
}

/** 仅请求当前选中的报表类型 */
async function fetchCurrentReport() {
  reportLoading.value = true
  try {
    await fetchReportByType(reportType.value)
  } catch (e) {
    ElMessage.error('获取报表失败')
  } finally {
    reportLoading.value = false
  }
}

/** 切换报表类型：优先使用缓存，无缓存时才请求 */
function onReportTypeChange() {
  if (reportCache.value[reportType.value]) {
    // 命中缓存，直接展示（无loading闪烁）
    return
  }
  fetchCurrentReport()
}

// ──── 导出功能 ────

function formatDate(date) {
  const d = new Date(date)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

async function exportExcel() {
  if (!reportDate.value) {
    ElMessage.warning('请先选择日期')
    return
  }
  try {
    const dateStr = formatDate(reportDate.value)
    let res
    if (reportType.value === 'daily') {
      res = await exportDailyReport({ date: dateStr })
    } else if (reportType.value === 'weekly') {
      res = await exportWeeklyReport({ date: dateStr })
    } else {
      res = await exportMonthlyReport({ date: dateStr })
    }
    downloadBlob(res, `能耗${reportType.value === 'daily' ? '日报' : reportType.value === 'weekly' ? '周报' : '月报'}_${dateStr}.xlsx`)
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  }
}

function exportPDF() {
  if (!reportDate.value) {
    ElMessage.warning('请先选择日期')
    return
  }
  const printWindow = window.open('', '_blank', 'width=800,height=600')
  if (!printWindow) {
    ElMessage.warning('请允许弹出窗口')
    return
  }
  const dateStr = formatDate(reportDate.value)
  const exportData = displayData.value
  printWindow.document.write(`
    <html><head><title>能耗报表</title>
    <style>
      body { font-family: 'Microsoft YaHei', sans-serif; padding: 40px; }
      h1 { text-align: center; color: #1a1a1a; }
      table { width: 100%; border-collapse: collapse; margin-top: 24px; }
      th, td { border: 1px solid #ddd; padding: 12px; text-align: center; }
      th { background: #f5f7fa; }
    </style></head><body>
    <h1>能耗${reportType.value === 'daily' ? '日报' : reportType.value === 'weekly' ? '周报' : '月报'} (${dateStr})</h1>
    <table>
      <tr><th>指标</th><th>数值</th></tr>
      <tr><td>总能耗</td><td>${exportData.total_energy_kwh || 0} kWh</td></tr>
      <tr><td>峰时用电</td><td>${exportData.peak_energy_kwh || 0} kWh</td></tr>
      <tr><td>平时用电</td><td>${exportData.flat_energy_kwh || 0} kWh</td></tr>
      <tr><td>谷时用电</td><td>${exportData.valley_energy_kwh || 0} kWh</td></tr>
      <tr><td>碳排放估算</td><td>${exportData.co2_kg || 0} kgCO₂</td></tr>
      <tr><td>预估成本</td><td>¥${(exportData.cost_yuan || 0).toFixed(2)}</td></tr>
      <tr><td>最大功率</td><td>${exportData.max_power_kw || 0} kW</td></tr>
    </table>
    </body></html>
  `)
  printWindow.document.close()
  setTimeout(() => printWindow.print(), 300)
}

async function exportDevice() {
  if (!deviceFilter.value || !deviceDateRange.value?.length) {
    ElMessage.warning('请选择设备和时间范围')
    return
  }
  exportingDevice.value = true
  try {
    const [start, end] = deviceDateRange.value
    const res = await exportDeviceData({
      device_id: deviceFilter.value,
      start: start.toISOString(),
      end: end.toISOString(),
    }, { responseType: 'blob' })
    downloadBlob(res, '设备数据导出.xlsx')
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  } finally {
    exportingDevice.value = false
  }
}

async function exportAlert() {
  if (!alertDateRange.value?.length) {
    ElMessage.warning('请选择时间范围')
    return
  }
  exportingAlert.value = true
  try {
    const [start, end] = alertDateRange.value
    const res = await exportAlertHistory({
      start: start.toISOString(),
      end: end.toISOString(),
      severity: alertSeverity.value || undefined,
    }, { responseType: 'blob' })
    downloadBlob(res, '告警历史导出.xlsx')
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  } finally {
    exportingAlert.value = false
  }
}

function downloadBlob(data, filename) {
  const url = window.URL.createObjectURL(new Blob([data]))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  window.URL.revokeObjectURL(url)
}

// ──── 生命周期：预加载三种报表 + 设备列表 ────
onMounted(async () => {
  // 设备列表和当前日报并行加载
  await Promise.all([
    fetchDevicesList(),
    fetchReportByType('daily'),
  ])
  // 后台静默预加载周报和月报，不阻塞首屏
  fetchReportByType('weekly')
  fetchReportByType('monthly')
})
</script>

<style scoped>
.tab-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
