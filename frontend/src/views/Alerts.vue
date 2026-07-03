<template>
  <div class="alerts-page">
    <h2 class="page-title">告警管理</h2>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="告警记录" name="records">
        <div class="tab-header">
          <el-select v-model="filterDevice" placeholder="筛选设备" clearable style="width: 180px">
            <el-option v-for="d in devices" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
          <el-switch v-model="onlyUnresolved" active-text="仅未处理" style="margin-left: 16px" />
          <el-button @click="fetchRecords" style="margin-left: 16px" type="primary" size="small">刷新</el-button>
        </div>

        <el-table :data="records" border stripe v-loading="loading" style="margin-top: 16px">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="device_name" label="设备名称" width="120" />
          <el-table-column prop="alert_time" label="告警时间" width="180" />
          <el-table-column prop="param_type" label="参数" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ paramLabel(row.param_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="当前值" width="100" />
          <el-table-column prop="threshold_value" label="阈值" width="100" />
          <el-table-column prop="severity" label="严重程度" width="100">
            <template #default="{ row }">
              <el-tag :type="row.severity === 'critical' ? 'danger' : row.severity === 'warning' ? 'warning' : 'info'" size="small">
                {{ row.severity === 'critical' ? '严重' : row.severity === 'warning' ? '警告' : '提示' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="告警信息" min-width="200" />
          <el-table-column prop="is_resolved" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_resolved ? 'success' : 'danger'" size="small">
                {{ row.is_resolved ? '已处理' : '未处理' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button v-if="!row.is_resolved" size="small" type="success" @click="openResolveDialog(row)">
                处理
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="阈值配置" name="thresholds">
        <div class="tab-header">
          <el-select v-model="thresholdDevice" placeholder="选择设备" style="width: 200px" @change="fetchThresholds">
            <el-option v-for="d in devices" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
          <el-button @click="showAddThreshold" style="margin-left: 16px" type="primary" size="small">
            添加阈值
          </el-button>
        </div>

        <el-table :data="thresholds" border stripe v-loading="thLoading" style="margin-top: 16px">
          <el-table-column prop="device_id" label="设备ID" width="80" />
          <el-table-column prop="param_type" label="参数类型" width="120">
            <template #default="{ row }">
              <el-tag>{{ paramLabel(row.param_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="upper_limit" label="上限" width="120" />
          <el-table-column prop="lower_limit" label="下限" width="120" />
          <el-table-column prop="is_enabled" label="启用" width="80">
            <template #default="{ row }">
              <el-switch :model-value="row.is_enabled" @change="(val) => toggleThreshold(row, val)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button size="small" @click="showEditThreshold(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="统计分析" name="stats">
        <div v-loading="statsLoading">
          <el-row :gutter="16">
            <el-col :span="8">
              <div class="stat-card">
                <div class="stat-label">告警总数</div>
                <div class="stat-value">{{ stats.total_alerts || 0 }}<span class="unit">条</span></div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-card" style="border-left: 3px solid #f56c6c">
                <div class="stat-label">未处理数</div>
                <div class="stat-value">{{ stats.unresolved || 0 }}<span class="unit">条</span></div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-card" style="border-left: 3px solid #409eff">
                <div class="stat-label">平均响应时长</div>
                <div class="stat-value">{{ stats.avg_response_minutes || 0 }}<span class="unit">分钟</span></div>
              </div>
            </el-col>
          </el-row>

          <el-row :gutter="16" style="margin-top: 16px">
            <el-col :span="12">
              <el-card header="告警类型分布">
                <div ref="typeChartRef" style="width: 100%; height: 350px"></div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card header="严重程度分布">
                <div ref="severityChartRef" style="width: 100%; height: 350px"></div>
              </el-card>
            </el-col>
          </el-row>

          <el-row :gutter="16" style="margin-top: 16px">
            <el-col :span="24">
              <el-card header="近7天告警趋势">
                <div ref="trendChartRef" style="width: 100%; height: 350px"></div>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 阈值编辑对话框 -->
    <el-dialog v-model="thDialogVisible" :title="thIsEdit ? '编辑阈值' : '添加阈值'" width="450px">
      <el-form :model="thForm" label-width="100px">
        <el-form-item label="设备">
          <el-select v-model="thForm.device_id" :disabled="thIsEdit" style="width: 100%">
            <el-option v-for="d in devices" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="参数类型">
          <el-select v-model="thForm.param_type" :disabled="thIsEdit" style="width: 100%">
            <el-option v-for="p in paramTypes" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="上限值">
          <el-input-number v-model="thForm.upper_limit" :step="1" />
        </el-form-item>
        <el-form-item label="下限值">
          <el-input-number v-model="thForm.lower_limit" :step="1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="thDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleThresholdSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 处理告警对话框 -->
    <el-dialog v-model="resolveDialogVisible" title="处理告警" width="500px">
      <el-form :model="resolveForm" label-width="100px">
        <el-form-item label="处理人" required>
          <el-input v-model="resolveForm.handler" placeholder="请输入处理人姓名" />
        </el-form-item>
        <el-form-item label="处理措施" required>
          <el-input v-model="resolveForm.measure" type="textarea" :rows="3" placeholder="请输入处理措施" />
        </el-form-item>
      </el-form>

      <!-- 知识库建议 -->
      <div v-if="suggestions.length > 0" style="margin-top: 16px">
        <h4 style="margin-bottom: 8px; color: #303133">历史处理建议</h4>
        <div style="display: flex; flex-wrap: wrap; gap: 8px">
          <el-tag
            v-for="(s, idx) in suggestions"
            :key="idx"
            style="cursor: pointer"
            type="info"
            @click="applySuggestion(s)"
          >
            {{ s.measure || s }}
          </el-tag>
        </div>
      </div>
      <div v-else-if="suggestionsLoaded" style="margin-top: 16px; color: #909399">
        暂无同类告警的历史处理记录
      </div>

      <template #footer>
        <el-button @click="resolveDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmResolve" :loading="resolving">确认处理</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  getDevices, getAlertRecords, resolveAlert, getThresholds,
  updateThreshold, createThreshold, getAlertStats, getResolutionSuggestions
} from '../api/api.js'

const activeTab = ref('records')
const devices = ref([])
const records = ref([])
const thresholds = ref([])
const loading = ref(false)
const thLoading = ref(false)
const filterDevice = ref(null)
const onlyUnresolved = ref(true)
const thresholdDevice = ref(null)

const paramTypes = [
  { label: '功率', value: 'power' },
  { label: '温度', value: 'temperature' },
  { label: '电压', value: 'voltage' },
  { label: '电流', value: 'current' },
]

const thDialogVisible = ref(false)
const thIsEdit = ref(false)
const thEditId = ref(null)
const thForm = ref({ device_id: null, param_type: 'power', upper_limit: null, lower_limit: null })

// 处理告警对话框
const resolveDialogVisible = ref(false)
const resolving = ref(false)
const resolveRecord = ref(null)
const resolveForm = ref({ handler: '', measure: '' })

// 知识库建议
const suggestions = ref([])
const suggestionsLoaded = ref(false)

// 统计分析
const stats = ref({})
const statsLoading = ref(false)
const typeChartRef = ref(null)
const severityChartRef = ref(null)
const trendChartRef = ref(null)
let typeChart = null
let severityChart = null
let trendChart = null

function paramLabel(type) {
  const map = { power: '功率', temperature: '温度', voltage: '电压', current: '电流' }
  return map[type] || type
}

async function fetchDevicesList() {
  const res = await getDevices()
  if (res.code === 200) devices.value = res.data
}

async function fetchRecords() {
  loading.value = true
  try {
    const res = await getAlertRecords({
      device_id: filterDevice.value || undefined,
      only_unresolved: onlyUnresolved.value,
      limit: 100,
    })
    if (res.code === 200) records.value = res.data
  } finally { loading.value = false }
}

async function fetchThresholds() {
  thLoading.value = true
  try {
    const res = await getThresholds(thresholdDevice.value || undefined)
    if (res.code === 200) thresholds.value = res.data
  } finally { thLoading.value = false }
}

// 打开处理弹窗
function openResolveDialog(row) {
  resolveRecord.value = row
  resolveForm.value = { handler: '', measure: '' }
  suggestions.value = []
  suggestionsLoaded.value = false
  resolveDialogVisible.value = true
  fetchSuggestions(row)
}

// 获取知识库建议
async function fetchSuggestions(row) {
  try {
    const res = await getResolutionSuggestions(row.device_id, row.param_type)
    if (res.code === 200) {
      suggestions.value = res.data || []
    }
  } catch (e) {
    // silent
  } finally {
    suggestionsLoaded.value = true
  }
}

// 点击建议填充处理措施
function applySuggestion(s) {
  resolveForm.value.measure = typeof s === 'string' ? s : (s.measure || '')
}

// 确认处理
async function confirmResolve() {
  if (!resolveForm.value.handler.trim()) {
    ElMessage.warning('请输入处理人')
    return
  }
  if (!resolveForm.value.measure.trim()) {
    ElMessage.warning('请输入处理措施')
    return
  }
  resolving.value = true
  try {
    await resolveAlert(resolveRecord.value.id, {
      handler: resolveForm.value.handler,
      measure: resolveForm.value.measure,
    })
    ElMessage.success('告警已处理')
    resolveDialogVisible.value = false
    await fetchRecords()
  } catch (e) {
    ElMessage.error('处理失败')
  } finally {
    resolving.value = false
  }
}

function showAddThreshold() {
  thIsEdit.value = false
  thEditId.value = null
  thForm.value = { device_id: thresholdDevice.value, param_type: 'power', upper_limit: null, lower_limit: null }
  thDialogVisible.value = true
}

function showEditThreshold(row) {
  thIsEdit.value = true
  thEditId.value = row.id
  thForm.value = { ...row }
  thDialogVisible.value = true
}

async function toggleThreshold(row, val) {
  await updateThreshold(row.id, { is_enabled: val })
  ElMessage.success('已更新')
}

async function handleThresholdSave() {
  try {
    if (thIsEdit.value) {
      await updateThreshold(thEditId.value, thForm.value)
    } else {
      await createThreshold(thForm.value)
    }
    ElMessage.success('保存成功')
    thDialogVisible.value = false
    await fetchThresholds()
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

// 统计分析
async function fetchStats() {
  statsLoading.value = true
  try {
    const res = await getAlertStats()
    if (res.code === 200) {
      stats.value = res.data || {}
      await nextTick()
      renderCharts()
    }
  } catch (e) {
    // silent
  } finally {
    statsLoading.value = false
  }
}

function renderCharts() {
  renderTypeChart()
  renderSeverityChart()
  renderTrendChart()
}

function renderTypeChart() {
  if (!typeChartRef.value) return
  if (typeChart) typeChart.dispose()
  typeChart = echarts.init(typeChartRef.value)

  const data = stats.value.type_distribution || []
  // 后端返回 [{type, count, label}, ...] 数组格式
  const chartData = (Array.isArray(data) ? data : []).map(d => ({
    name: d.label || paramLabel(d.type),
    value: d.count || d.value || 0,
  }))

  typeChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: '5%' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      label: { show: true, formatter: '{b}: {c}' },
      data: chartData.length > 0 ? chartData : [{ name: '暂无数据', value: 0 }],
      itemStyle: {
        color: (params) => {
          const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272']
          return colors[params.dataIndex % colors.length]
        }
      }
    }]
  })
}

function renderSeverityChart() {
  if (!severityChartRef.value) return
  if (severityChart) severityChart.dispose()
  severityChart = echarts.init(severityChartRef.value)

  const data = stats.value.severity_distribution || []
  // 后端返回 [{severity, count, label}, ...] 数组格式
  const chartData = (Array.isArray(data) ? data : []).map(d => ({
    name: d.label || (d.severity === 'critical' ? '严重' : d.severity === 'warning' ? '警告' : (d.severity || '未知')),
    value: d.count || d.value || 0,
  }))

  const colors = { critical: '#f56c6c', warning: '#e6a23c', info: '#409eff' }

  severityChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: '5%' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      label: { show: true, formatter: '{b}: {c}' },
      data: chartData.length > 0 ? chartData : [{ name: '暂无数据', value: 0 }],
      itemStyle: {
        color: (params) => colors[params.name === '严重' ? 'critical' : params.name === '警告' ? 'warning' : 'info'] || '#909399'
      }
    }]
  })
}

function renderTrendChart() {
  if (!trendChartRef.value) return
  if (trendChart) trendChart.dispose()
  trendChart = echarts.init(trendChartRef.value)

  const data = stats.value.daily_trend || []
  const dates = data.map(d => d.date || d.day || '')
  const values = data.map(d => d.count || d.value || 0)

  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: dates.length > 0 ? dates : ['暂无数据']
    },
    yAxis: { type: 'value', name: '告警数量' },
    series: [{
      data: values.length > 0 ? values : [0],
      type: 'bar',
      itemStyle: {
        color: '#409eff',
        borderRadius: [4, 4, 0, 0],
      },
      barMaxWidth: 40,
    }]
  })
}

// 切换到统计分析 tab 时加载数据
watch(activeTab, (val) => {
  if (val === 'stats') {
    fetchStats()
  }
})

function disposeCharts() {
  if (typeChart) { typeChart.dispose(); typeChart = null }
  if (severityChart) { severityChart.dispose(); severityChart = null }
  if (trendChart) { trendChart.dispose(); trendChart = null }
}

onMounted(async () => {
  await fetchDevicesList()
  await fetchRecords()
  await fetchThresholds()
})

onUnmounted(() => {
  disposeCharts()
})
</script>

<style scoped>
.tab-header {
  display: flex;
  align-items: center;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stat-card .stat-label {
  font-size: 14px;
  color: #8c8c8c;
  margin-bottom: 8px;
}

.stat-card .stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a1a;
}

.stat-card .stat-value .unit {
  font-size: 14px;
  font-weight: 400;
  color: #8c8c8c;
  margin-left: 4px;
}
</style>
