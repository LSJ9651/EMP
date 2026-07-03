<template>
  <div class="devices-page">
    <PageTitle title="设备管理" icon="Monitor" />

    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="设备列表" name="list">
        <Toolbar>
          <template #left>
            <el-button type="primary" @click="showAddDialog">
              <el-icon><Plus /></el-icon>添加设备
            </el-button>
          </template>
          <template #right>
            <span style="font-size: 13px; color: var(--text-tertiary)">共 {{ devices.length }} 台设备</span>
          </template>
        </Toolbar>

        <el-table :data="devices" border v-loading="loading">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="设备名称" />
          <el-table-column prop="type" label="类型" width="120">
            <template #default="{ row }">
              <el-tag round>{{ row.type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="rated_power" label="额定功率(kW)" width="130" />
          <el-table-column prop="workshop" label="车间" width="100" />
          <el-table-column label="今日能耗(kWh)" width="140">
            <template #default="{ row }">
              {{ (row.today_energy_kwh ?? row.today_energy)?.toFixed(2) || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="7日负载率" width="160">
            <template #default="{ row }">
              <el-progress
                :percentage="Math.round((row.avg_load_rate ?? row.load_rate ?? 0) * 100)"
                :color="loadRateColor(row.avg_load_rate ?? row.load_rate ?? 0)"
                :stroke-width="14"
                :text-inside="true"
              />
            </template>
          </el-table-column>
          <el-table-column label="功率因数" width="100">
            <template #default="{ row }">
              {{ (row.avg_power_factor ?? row.power_factor)?.toFixed(2) || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="efficiency" label="效率" width="80">
            <template #default="{ row }">
              {{ (row.efficiency * 100).toFixed(0) }}%
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" round size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="280">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="showEditDialog(row)">编辑</el-button>
              <el-button link type="primary" size="small" :loading="analyzingId === row.id" @click="handleAnalyze(row)">
                <el-icon><DataAnalysis /></el-icon> 能耗分析
              </el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="能效排行榜" name="ranking">
        <Toolbar>
          <template #right>
            <span style="font-size: 13px; color: var(--text-tertiary)">按负载率从高到低排列</span>
          </template>
        </Toolbar>

        <el-table :data="rankingList" border stripe v-loading="rankingLoading" @row-click="goToDevice">
          <el-table-column label="排名" width="80">
            <template #default="{ $index }">
              <span v-if="$index === 0" style="font-size: 22px">🥇</span>
              <span v-else-if="$index === 1" style="font-size: 22px">🥈</span>
              <span v-else-if="$index === 2" style="font-size: 22px">🥉</span>
              <el-tag v-else :type="$index < 5 ? 'warning' : 'info'" size="small" round>
                {{ $index + 1 }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="设备名称" min-width="140">
            <template #default="{ row }">
              <el-link type="primary" :underline="false">{{ row.name }}</el-link>
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" width="120">
            <template #default="{ row }">
              <el-tag round>{{ row.type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="负载率" width="200">
            <template #default="{ row }">
              <el-progress
                :percentage="Math.round((row.avg_load_rate ?? row.load_rate ?? 0) * 100)"
                :color="loadRateColor(row.avg_load_rate ?? row.load_rate ?? 0)"
                :stroke-width="16"
                :text-inside="true"
              />
            </template>
          </el-table-column>
          <el-table-column label="今日能耗(kWh)" width="150">
            <template #default="{ row }">
              {{ (row.today_energy_kwh ?? row.today_energy)?.toFixed(2) || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="功率因数" width="100">
            <template #default="{ row }">
              {{ (row.avg_power_factor ?? row.power_factor)?.toFixed(2) || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="运行时长(h)" width="120">
            <template #default="{ row }">
              {{ row.runtime_minutes != null ? (row.runtime_minutes / 60).toFixed(1) : '-' }}
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑设备' : '添加设备'" width="500px" top="5vh">
      <el-form :model="form" label-width="100px">
        <el-form-item label="设备名称">
          <el-input v-model="form.name" placeholder="请输入设备名称" />
        </el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="form.type" style="width: 100%">
            <el-option v-for="t in types" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="额定功率(kW)">
          <el-input-number v-model="form.rated_power" :min="0" :step="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="车间">
          <el-input v-model="form.workshop" placeholder="如：一车间" />
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="form.location" placeholder="设备安装位置" />
        </el-form-item>
        <el-form-item label="产线编号">
          <el-input v-model="form.line_no" placeholder="如：A-01" />
        </el-form-item>
        <el-form-item label="效率系数">
          <el-input-number v-model="form.efficiency" :min="0" :max="1" :step="0.01" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 分析结果弹窗 -->
    <el-dialog v-model="analysisVisible" :title="`能耗分析结果 — ${analysisDeviceName}`" width="700px" destroy-on-close top="5vh">
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
                <el-tag :type="row.severity === 'high' ? 'danger' : 'warning'" size="small" round>
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

        <div style="margin-top: 16px; color: var(--text-tertiary); font-size: 13px">
          分析设备数: {{ analysisResult.analyzed_devices ?? 1 }} &nbsp;|&nbsp;
          平均功率: {{ analysisResult.total_power_avg ?? '-' }} kW &nbsp;|&nbsp;
          耗时: {{ analysisElapsed }}ms
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDevices, createDevice, updateDevice, deleteDevice, getDeviceRanking, runWorkflowAnalyze } from '../api/api.js'
import PageTitle from '../components/common/PageTitle.vue'
import Toolbar from '../components/common/Toolbar.vue'

const activeTab = ref('list')
const devices = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const types = ['空压机', '注塑机', '冷水机组', '照明', '其他']

const form = ref({
  name: '', type: '其他', rated_power: 10, workshop: '一车间',
  location: '', line_no: '', efficiency: 1.0,
})

// 排行榜
const rankingList = ref([])
const rankingLoading = ref(false)
const analyzingId = ref(null)
const analysisVisible = ref(false)
const analysisResult = ref(null)
const analysisMode = ref('local')
const analysisDeviceName = ref('')
const analysisElapsed = ref(0)

function statusType(status) {
  if (status === 'online') return 'success'
  if (status === 'offline') return 'info'
  return 'danger'
}

function loadRateColor(rate) {
  if (rate > 0.8) return '#52c41a'
  if (rate >= 0.5) return '#faad14'
  return '#f5222d'
}

function resetForm() {
  form.value = {
    name: '', type: '其他', rated_power: 10, workshop: '一车间',
    location: '', line_no: '', efficiency: 1.0,
  }
}

function showAddDialog() {
  isEdit.value = false
  editId.value = null
  resetForm()
  dialogVisible.value = true
}

function showEditDialog(row) {
  isEdit.value = true
  editId.value = row.id
  form.value = { ...row }
  dialogVisible.value = true
}

async function handleSave() {
  try {
    if (isEdit.value) {
      await updateDevice(editId.value, form.value)
      ElMessage.success('设备更新成功')
    } else {
      await createDevice(form.value)
      ElMessage.success('设备创建成功')
    }
    dialogVisible.value = false
    await fetchDevices()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除设备 "${row.name}" 吗？`, '确认删除', { type: 'warning' })
    await deleteDevice(row.id)
    ElMessage.success('设备已删除')
    await fetchDevices()
  } catch { /* canceled */ }
}

async function fetchDevices() {
  loading.value = true
  try {
    const res = await getDevices()
    if (res.code === 200) devices.value = res.data
  } catch (e) {
    ElMessage.error('获取设备列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchRanking() {
  rankingLoading.value = true
  try {
    const res = await getDeviceRanking()
    if (res.code === 200) {
      rankingList.value = res.data.ranking || []
    }
  } catch (e) {
    // silent
  } finally {
    rankingLoading.value = false
  }
}

function goToDevice(row) {
  activeTab.value = 'list'
}

async function handleAnalyze(row) {
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
    ElMessage.error('能耗分析失败')
  } finally {
    analyzingId.value = null
  }
}

function handleTabChange(name) {
  if (name === 'ranking') {
    fetchRanking()
  }
}

onMounted(async () => {
  await fetchDevices()
})
</script>
