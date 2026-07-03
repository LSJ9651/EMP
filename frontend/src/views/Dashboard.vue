<template>
  <div class="dashboard">
    <h2 class="page-title">能耗看板</h2>

    <!-- 实时指标卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">实时总功率</div>
          <div class="stat-value">
            {{ overview.total_power_kw || 0 }}<span class="unit">kW</span>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">今日总能耗</div>
          <div class="stat-value">
            {{ overview.today_energy_kwh || 0 }}<span class="unit">kWh</span>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">碳排放估算</div>
          <div class="stat-value">
            {{ overview.co2_estimate_kg || 0 }}<span class="unit">kgCO₂</span>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" style="border-left: 3px solid #e6a23c">
          <div class="stat-label">未处理告警</div>
          <div class="stat-value">
            {{ overview.alert_count || 0 }}<span class="unit">条</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 设备状态 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="6" v-for="s in deviceStatuses" :key="s.label">
        <div class="stat-card">
          <div class="stat-label">{{ s.label }}</div>
          <div class="stat-value" :style="{ color: s.color }">
            {{ s.count }}<span class="unit">台</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 设备能耗监控 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="24">
        <el-card header="设备能耗监控">
          <el-table :data="deviceList" border stripe v-loading="deviceLoading" size="small">
            <el-table-column prop="name" label="设备名称" min-width="120" />
            <el-table-column prop="type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="今日能耗(kWh)" width="130">
              <template #default="{ row }">
                {{ (row.today_energy_kwh ?? row.today_energy)?.toFixed(2) || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="负载率" width="160">
              <template #default="{ row }">
                <el-progress
                  :percentage="Math.round((row.avg_load_rate ?? row.load_rate ?? 0) * 100)"
                  :color="row.avg_load_rate > 0.8 ? '#67c23a' : row.avg_load_rate >= 0.5 ? '#e6a23c' : '#f56c6c'"
                  :stroke-width="12"
                />
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'online' ? 'success' : row.status === 'offline' ? 'info' : 'danger'" size="small">
                  {{ row.status === 'online' ? '在线' : row.status === 'offline' ? '离线' : '告警' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button
                  size="small"
                  type="primary"
                  :loading="analyzingId === row.id"
                  @click="handleQuickAnalyze(row)"
                >
                  <el-icon><DataAnalysis /></el-icon>一键分析
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 能流图 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="12">
        <el-card header="能流图">
          <EnergyFlowChart :data="energyFlowData" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card header="实时功率趋势">
          <TrendChart :series="trendSeries" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 告警滚动条 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="24">
        <el-card header="最新告警">
          <div v-if="alerts.length === 0" style="color: #8c8c8c; text-align: center; padding: 20px">
            暂无告警
          </div>
          <el-timeline v-else>
            <el-timeline-item
              v-for="a in alerts"
              :key="a.id"
              :timestamp="a.alert_time"
              :color="a.severity === 'critical' ? '#f56c6c' : '#e6a23c'"
            >
              <strong>{{ a.device_name }}</strong> — {{ a.message }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>

    <!-- 分析结果弹窗 -->
    <el-dialog v-model="analysisVisible" :title="`能耗分析结果 — ${analysisDeviceName}`" width="700px" destroy-on-close>
      <div v-if="analysisResult">
        <el-tag :type="analysisMode === 'cloud' ? 'success' : 'info'" style="margin-bottom: 16px">
          {{ analysisMode === 'cloud' ? '☁ 云端智能分析' : '🖥 本地规则分析' }}
        </el-tag>
        <el-divider />
        <h4>分析摘要</h4>
        <el-alert :type="analysisResult.anomalies?.length ? 'warning' : 'success'" :closable="false">
          {{ analysisResult.summary || '暂无分析结果' }}
        </el-alert>

        <div v-if="analysisResult.anomalies?.length" style="margin-top: 16px">
          <h4>异常检测 ({{ analysisResult.anomalies.length }})</h4>
          <el-table :data="analysisResult.anomalies" border size="small" max-height="300">
            <el-table-column prop="device_name" label="设备" width="120" />
            <el-table-column prop="severity" label="严重度" width="90">
              <template #default="{ row }">
                <el-tag :type="row.severity === 'high' ? 'danger' : 'warning'" size="small">
                  {{ row.severity === 'high' ? '高' : '中' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="message" label="详情" min-width="280" show-overflow-tooltip />
          </el-table>
        </div>

        <div v-if="analysisResult.suggestions?.length" style="margin-top: 16px">
          <h4>节能建议</h4>
          <ul style="padding-left: 20px; line-height: 2">
            <li v-for="(s, i) in analysisResult.suggestions" :key="i">{{ s }}</li>
          </ul>
        </div>

        <div style="margin-top: 16px; color: #8c8c8c; font-size: 13px">
          分析设备数: {{ analysisResult.analyzed_devices ?? 1 }} &nbsp;|&nbsp;
          平均功率: {{ analysisResult.total_power_avg ?? '-' }} kW &nbsp;|&nbsp;
          耗时: {{ analysisElapsed }}ms
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getOverview, getEnergyFlow, getTrend, getAlertsBar, getDevices, runWorkflowAnalyze } from '../api/api.js'
import EnergyFlowChart from '../components/charts/EnergyFlowChart.vue'
import TrendChart from '../components/charts/TrendChart.vue'
import { ElMessage } from 'element-plus'

const overview = ref({})
const energyFlowData = ref({ nodes: [], links: [] })
const trendSeries = ref([])
const alerts = ref([])
const deviceList = ref([])
const deviceLoading = ref(false)
const analyzingId = ref(null)
const analysisVisible = ref(false)
const analysisResult = ref(null)
const analysisMode = ref('local')
const analysisDeviceName = ref('')
const analysisElapsed = ref(0)

let pollingTimer = null

const deviceStatuses = computed(() => {
  const stats = overview.value.device_stats || {}
  return [
    { label: '在线设备', count: stats.online || 0, color: '#67c23a' },
    { label: '离线设备', count: stats.offline || 0, color: '#909399' },
    { label: '告警设备', count: stats.alert || 0, color: '#f56c6c' },
  ]
})

async function fetchData() {
  try {
    const [ov, ef, tr, al] = await Promise.all([
      getOverview(),
      getEnergyFlow(),
      getTrend(null, 30),
      getAlertsBar(5),
    ])
    if (ov.code === 200) overview.value = ov.data
    if (ef.code === 200) energyFlowData.value = ef.data
    if (tr.code === 200) trendSeries.value = tr.data.series || []
    if (al.code === 200) alerts.value = al.data
  } catch (e) {
    console.error('Dashboard fetch error:', e)
  }
}

async function fetchDevicesList() {
  deviceLoading.value = true
  try {
    const res = await getDevices()
    if (res.code === 200) deviceList.value = res.data || []
  } catch (e) {
    // silent
  } finally {
    deviceLoading.value = false
  }
}

async function handleQuickAnalyze(row) {
  analyzingId.value = row.id
  try {
    const res = await runWorkflowAnalyze({ device_id: row.id })
    if (res.code === 200) {
      const wrapper = res.data
      analysisResult.value = wrapper.data || {}
      analysisMode.value = wrapper.mode_used || 'local'
      analysisDeviceName.value = row.name
      analysisElapsed.value = wrapper.elapsed_ms || 0
      analysisVisible.value = true
      const cloudErr = wrapper.data?._cloud_error
      if (wrapper.mode_used === 'cloud') {
        ElMessage.success(`[云端] 分析完成`)
      } else if (cloudErr) {
        ElMessage.warning(`[本地] ${cloudErr}`)
      } else {
        ElMessage.success(`[本地] 分析完成`)
      }
    }
  } catch (e) {
    ElMessage.error('分析失败')
  } finally {
    analyzingId.value = null
  }
}

onMounted(() => {
  fetchData()
  fetchDevicesList()
  pollingTimer = setInterval(fetchData, 5000)
})

onUnmounted(() => {
  clearInterval(pollingTimer)
})
</script>

<style scoped>
.stats-row {
  margin-bottom: 16px;
}
</style>
