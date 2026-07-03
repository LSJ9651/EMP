<template>
  <div class="cost-allocation-page">
    <PageTitle title="成本分摊" icon="Coin" />

    <!-- 工具栏 -->
    <Toolbar>
      <template #left>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="fetchData"
          style="width: 280px"
        />
        <el-select v-model="ruleType" @change="onRuleChange" style="width: 180px; margin-left: 12px">
          <el-option label="按比例分摊" value="ratio" />
          <el-option label="按设备类型细分" value="by_device_type" />
        </el-select>
      </template>
      <template #right>
        <el-dropdown @command="handleExport" style="margin-right: 12px">
          <el-button :loading="exporting">
            <el-icon><Download /></el-icon>导出
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="workshop">车间汇总</el-dropdown-item>
              <el-dropdown-item command="device">设备明细</el-dropdown-item>
              <el-dropdown-item command="detail">日明细</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button type="primary" @click="fetchData" :loading="loading">
          <el-icon><Search /></el-icon>查询
        </el-button>
      </template>
    </Toolbar>

    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-top: 16px" v-if="summaryData">
      <el-col :span="6">
        <StatCard
          title="总电费"
          :value="`¥${(summaryData.total_cost || 0).toFixed(2)}`"
          icon="Money"
          color="#f5222d"
        />
      </el-col>
      <el-col :span="6">
        <StatCard
          title="总用电量"
          :value="summaryData.total_energy_kwh?.toFixed(0) || 0"
          unit="kWh"
          icon="Lightning"
          color="#4f8cf7"
        />
      </el-col>
      <el-col :span="6">
        <StatCard
          title="车间数"
          :value="workshops.length"
          icon="OfficeBuilding"
          color="#faad14"
        />
      </el-col>
      <el-col :span="6">
        <StatCard
          title="分摊规则"
          :value="ruleLabel"
          icon="Document"
          color="#52c41a"
        />
      </el-col>
    </el-row>

    <!-- 图表区 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="12">
        <el-card header="各车间电费">
          <div ref="barChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card :header="chartTabHeader">
          <template #header>
            <div class="chart-header-row">
              <span>电费占比</span>
              <el-segmented v-model="pieMode" :options="pieOptions" size="small" @change="updatePieChart" />
            </div>
          </template>
          <div ref="pieChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据校验警告 -->
    <el-alert
      v-if="warnings.length"
      :title="'数据校验警告: ' + warnings.join('; ')"
      type="warning"
      :closable="false"
      show-icon
      style="margin-top: 12px"
    />

    <!-- 车间电费明细 -->
    <el-card header="车间电费明细" style="margin-top: 16px">
      <el-table :data="workshops" border v-loading="loading" @row-click="onWorkshopRowClick">
        <el-table-column prop="workshop" label="车间" width="150" />
        <el-table-column prop="energy_kwh" label="用电量(kWh)" width="140">
          <template #default="{ row }">{{ (row.energy_kwh || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="cost" label="电费(元)" width="140">
          <template #default="{ row }">
            <span style="font-weight: 600; color: #f5222d">¥{{ (row.cost || 0).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="peak_cost" label="峰时电费" width="130">
          <template #default="{ row }">¥{{ (row.peak_cost || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="flat_cost" label="平时电费" width="130">
          <template #default="{ row }">¥{{ (row.flat_cost || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="valley_cost" label="谷时电费" width="130">
          <template #default="{ row }">¥{{ (row.valley_cost || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="percentage" label="占比" width="140">
          <template #default="{ row }">
            <el-progress :percentage="row.percentage || 0" :stroke-width="8" :color="progressColor(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="showWorkshopDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="total-row" v-if="summaryData">
        总计: <span class="total-cost">¥{{ (summaryData.total_cost || 0).toFixed(2) }}</span>
        &nbsp;&nbsp;|&nbsp;&nbsp;
        用电: {{ (summaryData.total_energy_kwh || 0).toFixed(2) }} kWh
        &nbsp;&nbsp;|&nbsp;&nbsp;
        范围: {{ summaryData.start_date }} ~ {{ summaryData.end_date }}
      </div>
    </el-card>

    <!-- 设备级成本明细 -->
    <el-card header="设备成本明细" style="margin-top: 16px" v-if="deviceData.length">
      <el-table :data="deviceData" border max-height="400" v-loading="deviceLoading">
        <el-table-column prop="device_name" label="设备名称" width="150" />
        <el-table-column prop="device_type" label="类型" width="100" />
        <el-table-column prop="workshop" label="车间" width="100" />
        <el-table-column prop="rated_power" label="额定功率(kW)" width="130" />
        <el-table-column prop="cost" label="电费(元)" width="120">
          <template #default="{ row }">
            <span style="font-weight: 600; color: #f5222d">¥{{ (row.cost || 0).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="energy_kwh" label="用电量(kWh)" width="130">
          <template #default="{ row }">{{ (row.energy_kwh || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="peak_cost" label="峰时电费" width="120">
          <template #default="{ row }">¥{{ (row.peak_cost || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="flat_cost" label="平时电费" width="120">
          <template #default="{ row }">¥{{ (row.flat_cost || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="valley_cost" label="谷时电费" width="120">
          <template #default="{ row }">¥{{ (row.valley_cost || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="percentage" label="占比" width="120">
          <template #default="{ row }">
            <el-progress :percentage="row.percentage || 0" :stroke-width="8" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 车间详情弹窗 -->
    <el-dialog v-model="detailVisible" :title="`${detailWorkshop} - 每日明细`" width="700px" top="5vh">
      <el-table :data="detailData" border max-height="450">
        <el-table-column prop="date" label="日期" width="130" />
        <el-table-column prop="cost" label="电费(元)" width="130">
          <template #default="{ row }">¥{{ (row.cost || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="energy_kwh" label="用电量(kWh)" width="140">
          <template #default="{ row }">{{ (row.energy_kwh || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="max_power_kw" label="最大功率(kW)" width="140">
          <template #default="{ row }">{{ (row.max_power_kw || 0).toFixed(2) }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Download } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  getCostByWorkshop,
  getCostByDevice,
  getCostRules,
  updateCostRule,
  exportCostCsv,
  getWorkshopDetail,
} from '../api/api.js'
import StatCard from '../components/common/StatCard.vue'
import PageTitle from '../components/common/PageTitle.vue'
import Toolbar from '../components/common/Toolbar.vue'

// ─── 状态 ───
const dateRange = ref([])
const ruleType = ref('ratio')
const loading = ref(false)
const exporting = ref(false)
const deviceLoading = ref(false)

const summaryData = ref(null)
const workshops = ref([])
const deviceData = ref([])
const warnings = ref([])

const detailVisible = ref(false)
const detailWorkshop = ref('')
const detailData = ref([])

const barChartRef = ref(null)
const pieChartRef = ref(null)
let barChart = null
let pieChart = null

const pieMode = ref('workshop')
const pieOptions = [
  { label: '车间', value: 'workshop' },
  { label: '峰平谷', value: 'peak_flat_valley' },
]

const ruleLabel = computed(() => {
  const labels = { ratio: '比例分摊', by_device_type: '按类型细分' }
  return labels[ruleType.value] || ruleType.value
})

const chartTabHeader = computed(() => {
  return pieMode.value === 'workshop' ? '车间电费占比' : '峰平谷电费占比'
})

// ─── 数据获取 ───
function formatDate(date) {
  const d = new Date(date)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function fetchData() {
  loading.value = true
  try {
    const params = { rule_type: ruleType.value }
    if (dateRange.value?.length === 2) {
      params.start = formatDate(dateRange.value[0])
      params.end = formatDate(dateRange.value[1])
    }
    const res = await getCostByWorkshop(params)
    if (res.code === 200) {
      const data = res.data
      summaryData.value = data
      workshops.value = data.workshops || []
      warnings.value = data.validation_warnings || []
      updateCharts()
      fetchDeviceData()
    }
  } catch (e) {
    ElMessage.error('获取成本数据失败')
  } finally {
    loading.value = false
  }
}

async function fetchDeviceData() {
  deviceLoading.value = true
  try {
    const params = {}
    if (dateRange.value?.length === 2) {
      params.start = formatDate(dateRange.value[0])
      params.end = formatDate(dateRange.value[1])
    }
    const res = await getCostByDevice(params)
    if (res.code === 200) {
      deviceData.value = res.data || []
    }
  } catch {
    // 静默
  } finally {
    deviceLoading.value = false
  }
}

async function fetchRules() {
  try {
    const res = await getCostRules()
    if (res.code === 200 && res.data) {
      ruleType.value = res.data.rule_type || 'ratio'
    }
  } catch {
    // 使用默认值
  }
}

async function onRuleChange(val) {
  try {
    await updateCostRule(val)
    ElMessage.success('分摊规则已更新')
  } catch {
    ElMessage.warning('规则保存失败，当前仅本次生效')
  }
  await fetchData()
}

async function showWorkshopDetail(row) {
  detailWorkshop.value = row.workshop
  detailVisible.value = true
  loading.value = true
  try {
    const res = await getWorkshopDetail(row.workshop, { days: 30 })
    detailData.value = res.data || []
  } catch {
    ElMessage.error('获取明细失败')
  } finally {
    loading.value = false
  }
}

async function handleExport(type) {
  exporting.value = true
  try {
    const params = { export_type: type }
    if (dateRange.value?.length === 2) {
      params.start = formatDate(dateRange.value[0])
      params.end = formatDate(dateRange.value[1])
    }
    const res = await exportCostCsv(params)
    const url = window.URL.createObjectURL(new Blob([res]))
    const a = document.createElement('a')
    a.href = url
    a.download = `cost_${type}_${Date.now()}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

// ─── 图表 ───
const CHART_COLORS = ['#4f8cf7', '#52c41a', '#faad14', '#f5222d', '#8c8c8c', '#722ed1']

function progressColor(row) {
  return row.percentage > 50 ? '#f5222d' : row.percentage > 25 ? '#faad14' : '#4f8cf7'
}

function initCharts() {
  if (barChartRef.value && !barChart) barChart = echarts.init(barChartRef.value)
  if (pieChartRef.value && !pieChart) pieChart = echarts.init(pieChartRef.value)
  if (workshops.value.length) updateCharts()
}

function updateCharts() {
  updateBarChart()
  updatePieChart()
}

function updateBarChart() {
  if (!barChart || !workshops.value.length) return

  const names = workshops.value.map(d => d.workshop)
  const costs = workshops.value.map(d => d.cost || 0)
  const peakCosts = workshops.value.map(d => d.peak_cost || 0)
  const flatCosts = workshops.value.map(d => d.flat_cost || 0)
  const valleyCosts = workshops.value.map(d => d.valley_cost || 0)

  barChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['峰时', '平时', '谷时'], bottom: 0 },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: names },
    yAxis: { type: 'value', name: '元' },
    series: [
      { name: '峰时', type: 'bar', stack: 'total', data: peakCosts, color: '#f5222d' },
      { name: '平时', type: 'bar', stack: 'total', data: flatCosts, color: '#faad14' },
      { name: '谷时', type: 'bar', stack: 'total', data: valleyCosts, color: '#52c41a' },
    ],
  }, true)
}

function updatePieChart() {
  if (!pieChart || !workshops.value.length) return

  let pieData
  if (pieMode.value === 'workshop') {
    pieData = workshops.value.map(d => ({ name: d.workshop, value: d.cost || 0 }))
  } else {
    const peak = workshops.value.reduce((s, d) => s + (d.peak_cost || 0), 0)
    const flat = workshops.value.reduce((s, d) => s + (d.flat_cost || 0), 0)
    const valley = workshops.value.reduce((s, d) => s + (d.valley_cost || 0), 0)
    pieData = [
      { name: '峰时', value: peak },
      { name: '平时', value: flat },
      { name: '谷时', value: valley },
    ]
  }

  pieChart.setOption({
    tooltip: { formatter: '{b}: ¥{c} ({d}%)' },
    legend: { bottom: 0, data: pieData.map(d => d.name) },
    series: [{
      type: 'pie', radius: ['50%', '75%'], center: ['50%', '45%'],
      data: pieData, color: CHART_COLORS,
      label: { formatter: '{b}\n{d}%', fontSize: 11 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } },
    }],
  }, true)
}

function handleResize() {
  barChart?.resize()
  pieChart?.resize()
}

function onWorkshopRowClick(row) {
  showWorkshopDetail(row)
}

onMounted(async () => {
  await fetchRules()
  initCharts()
  window.addEventListener('resize', handleResize)
  await fetchData()
})

onUnmounted(() => {
  barChart?.dispose()
  pieChart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.chart-box {
  width: 100%;
  height: 320px;
}

.total-row {
  margin-top: 16px;
  text-align: right;
  font-size: 15px;
  color: var(--text-secondary);
}
.total-cost {
  color: #f5222d;
  font-weight: 700;
  font-size: 20px;
}
.chart-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
