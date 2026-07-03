<template>
  <div class="schedule-page">
    <PageTitle title="调度优化" icon="Timer" />

    <el-row :gutter="16">
      <el-col :span="8">
        <el-card header="优化参数">
          <el-form label-width="100px">
            <el-form-item label="生产目标">
              <el-input-number v-model="form.production_goal" :min="1" :step="100" style="width: 100%" />
            </el-form-item>
            <el-form-item label="截止时间">
              <el-date-picker v-model="form.deadline" type="datetime" style="width: 100%" />
            </el-form-item>
            <el-form-item label="可用设备">
              <el-select v-model="form.devices" multiple placeholder="全部设备" style="width: 100%">
                <el-option v-for="d in devices" :key="d.id" :label="d.name" :value="d.id" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="runOptimize" :loading="optimizing" style="width: 100%">
                <el-icon><MagicStick /></el-icon>AI 智能优化
              </el-button>
              <div style="text-align: center; margin-top: 8px" v-if="modeUsed">
                <el-tag :type="modeUsed === 'cloud' ? 'success' : 'info'" size="small" round>
                  {{ modeUsed === 'cloud' ? '☁ 云端优化' : '💻 本地优化' }}
                </el-tag>
              </div>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card header="优化结果" style="margin-top: 16px" v-if="result">
          <div class="result-stat">
            <div class="result-label">预计节省成本</div>
            <div class="result-value">¥{{ result.estimated_cost_saved || 0 }}</div>
          </div>
          <el-alert :title="result.reasoning" type="success" :closable="false" style="margin-top: 12px" />
          <div style="margin-top: 12px; text-align: center">
            <el-button type="success" @click="dispatchExecution" :loading="dispatching">
              <el-icon><Promotion /></el-icon>下发执行
            </el-button>
            <div v-if="executionStatus" style="margin-top: 8px">
              <el-tag :type="execStatusType" round>
                {{ executionStatus }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card header="调度计划甘特图">
          <GanttChart v-if="scheduleData.length > 0" :data="scheduleData" />
          <div v-else style="text-align: center; padding: 80px 0; color: var(--text-tertiary)">
            <el-icon :size="48"><Timer /></el-icon>
            <div style="margin-top: 12px">请先执行调度优化</div>
          </div>
        </el-card>

        <el-card header="调度明细" style="margin-top: 16px" v-if="scheduleData.length > 0">
          <el-table :data="scheduleData" border size="small">
            <el-table-column prop="device_name" label="设备" width="120" />
            <el-table-column prop="start" label="开始" width="80" />
            <el-table-column prop="end" label="结束" width="80" />
            <el-table-column prop="action" label="动作" width="80">
              <template #default="{ row }">
                <el-tag :type="actionType(row.action)" size="small" round>{{ actionLabel(row.action) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="price_per_kwh" label="电价(元)" width="80">
              <template #default="{ row }">
                {{ row.price_per_kwh?.toFixed(2) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 执行追踪对比卡片 -->
    <el-row :gutter="16" style="margin-top: 16px" v-if="executions.length > 0 || result">
      <el-col :span="24">
        <el-card header="预估节费 vs 实际节费">
          <el-row :gutter="16">
            <el-col :span="12">
              <div class="comparison-card estimated">
                <div class="comparison-label">预估节费</div>
                <div class="comparison-value" style="color: #52c41a">¥{{ totalEstimatedSaving }}</div>
                <div class="comparison-detail">基线成本 ¥{{ totalBaselineCost }}</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="comparison-card actual">
                <div class="comparison-label">实际节费</div>
                <div class="comparison-value" style="color: #4f8cf7">¥{{ totalActualSaving }}</div>
                <div class="comparison-detail">实际成本 ¥{{ totalActualCost }}</div>
              </div>
            </el-col>
          </el-row>

          <el-table :data="executions" border style="margin-top: 16px" v-loading="execLoading">
            <el-table-column prop="id" label="执行ID" width="80" />
            <el-table-column prop="report_id" label="报告ID" width="80" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small" round>
                  {{ row.status === 'completed' ? '已完成' : row.status === 'running' ? '运行中' : row.status === 'failed' ? '失败' : '待执行' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="baseline_cost" label="基线成本" width="120">
              <template #default="{ row }">¥{{ row.baseline_cost?.toFixed(2) || '0.00' }}</template>
            </el-table-column>
            <el-table-column prop="actual_cost" label="实际成本" width="120">
              <template #default="{ row }">¥{{ row.actual_cost?.toFixed(2) || '0.00' }}</template>
            </el-table-column>
            <el-table-column label="节省" width="120">
              <template #default="{ row }">
                <span v-if="row.baseline_cost && row.actual_cost" :style="{ color: (row.baseline_cost - row.actual_cost) > 0 ? '#52c41a' : '#f5222d', fontWeight: 600 }">
                  ¥{{ ((row.baseline_cost || 0) - (row.actual_cost || 0)).toFixed(2) }}
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="start_time" label="时间" width="180" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'running'"
                  link
                  type="primary"
                  size="small"
                  @click="handleComplete(row)"
                  :loading="completingId === row.id"
                >
                  核算完成
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getDevices, runWorkflowOptimize, executeSchedule, getExecutions, completeExecution } from '../api/api.js'
import GanttChart from '../components/charts/GanttChart.vue'
import PageTitle from '../components/common/PageTitle.vue'

const devices = ref([])
const optimizing = ref(false)
const result = ref(null)
const scheduleData = ref([])
const modeUsed = ref('')
const currentReportId = ref(null)

const form = ref({
  production_goal: 1000,
  deadline: null,
  devices: [],
})

// 执行追踪
const dispatching = ref(false)
const executionStatus = ref('')
const executions = ref([])
const execLoading = ref(false)
const completingId = ref(null)
let execPollTimer = null

const execStatusType = computed(() => {
  const s = executionStatus.value
  if (s.includes('成功')) return 'success'
  if (s.includes('失败')) return 'danger'
  return 'warning'
})

const totalEstimatedSaving = computed(() => {
  return (result.value?.estimated_cost_saved || 0).toFixed(2)
})

const totalBaselineCost = computed(() => {
  return executions.value.reduce((sum, e) => sum + (e.baseline_cost || 0), 0).toFixed(2)
})

const totalActualCost = computed(() => {
  return executions.value.reduce((sum, e) => sum + (e.actual_cost || 0), 0).toFixed(2)
})

const totalActualSaving = computed(() => {
  const baseline = executions.value.reduce((sum, e) => sum + (e.baseline_cost || 0), 0)
  const actual = executions.value.reduce((sum, e) => sum + (e.actual_cost || 0), 0)
  return (baseline - actual).toFixed(2)
})

function actionType(action) {
  if (action === 'run') return 'success'
  if (action === 'idle') return 'warning'
  return 'info'
}

function actionLabel(action) {
  if (action === 'run') return '运行'
  if (action === 'idle') return '待机'
  return '关机'
}

async function fetchDevicesList() {
  const res = await getDevices()
  if (res.code === 200) devices.value = res.data
}

async function runOptimize() {
  optimizing.value = true
  modeUsed.value = ''
  try {
    const res = await runWorkflowOptimize({
      production_goal: form.value.production_goal,
      deadline: form.value.deadline?.toISOString() || undefined,
      device_ids: form.value.devices.length > 0 ? form.value.devices : undefined,
    })
    if (res.code === 200) {
      const d = res.data
      modeUsed.value = d.mode_used || 'local'
      currentReportId.value = d.report_id || null
      result.value = d.data
      scheduleData.value = d.data?.schedule || []
      const cloudErr = d.data?._cloud_error
      if (modeUsed.value === 'cloud') {
        ElMessage.success(`[云端] 优化完成，耗时 ${d.elapsed_ms}ms`)
      } else if (cloudErr) {
        ElMessage.warning(`[本地] ${cloudErr}，耗时 ${d.elapsed_ms}ms`)
      } else {
        ElMessage.success(`[本地] 优化完成，耗时 ${d.elapsed_ms}ms`)
      }
    }
  } catch (e) {
    ElMessage.error('优化失败')
  } finally {
    optimizing.value = false
  }
}

async function dispatchExecution() {
  if (!currentReportId.value) {
    ElMessage.warning('请先执行调度优化')
    return
  }
  dispatching.value = true
  try {
    const res = await executeSchedule(currentReportId.value)
    if (res.code === 200) {
      executionStatus.value = '下发成功'
      ElMessage.success('调度方案已下发执行')
      await fetchExecutions()
    }
  } catch (e) {
    executionStatus.value = '下发失败'
    ElMessage.error('下发执行失败')
  } finally {
    dispatching.value = false
  }
}

async function fetchExecutions() {
  execLoading.value = true
  try {
    const res = await getExecutions()
    if (res.code === 200) {
      executions.value = res.data || []
      const hasRunning = executions.value.some(e => e.status === 'running')
      if (hasRunning) {
        startExecPolling()
      } else {
        stopExecPolling()
      }
    }
  } catch (e) {
    // silent
  } finally {
    execLoading.value = false
  }
}

function startExecPolling() {
  if (execPollTimer) return
  execPollTimer = setInterval(async () => {
    await fetchExecutions()
    const hasRunning = executions.value.some(e => e.status === 'running')
    if (!hasRunning) {
      stopExecPolling()
    }
  }, 1000)
}

function stopExecPolling() {
  if (execPollTimer) {
    clearInterval(execPollTimer)
    execPollTimer = null
  }
}

async function handleComplete(row) {
  completingId.value = row.id
  try {
    const res = await completeExecution(row.id)
    if (res.code === 200) {
      ElMessage.success('核算完成')
      await fetchExecutions()
    }
  } catch (e) {
    ElMessage.error('核算失败')
  } finally {
    completingId.value = null
  }
}

onMounted(async () => {
  await fetchDevicesList()
  await fetchExecutions()
})

onUnmounted(() => {
  stopExecPolling()
})
</script>

<style scoped>
.result-stat {
  text-align: center;
  padding: 16px;
}
.result-label {
  font-size: 14px;
  color: var(--text-tertiary);
}
.result-value {
  font-size: 32px;
  font-weight: 700;
  color: #52c41a;
  margin-top: 8px;
}

.comparison-card {
  background: var(--card-bg, #fff);
  border-radius: var(--radius-md, 8px);
  padding: 24px;
  text-align: center;
}
.comparison-card.estimated {
  border: 2px solid #52c41a;
}
.comparison-card.actual {
  border: 2px solid #4f8cf7;
}
.comparison-label {
  font-size: 14px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}
.comparison-value {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 4px;
}
.comparison-detail {
  font-size: 13px;
  color: var(--text-tertiary);
}
</style>
