<template>
  <el-card class="service-card" shadow="hover">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <span class="icon">{{ icon }}</span>
          <span class="title">{{ title }}</span>
          <el-tag :type="modelValue.enabled ? 'success' : 'info'" size="small" effect="plain">
            {{ modelValue.enabled ? '云端' : '本地' }}
          </el-tag>
        </div>
        <el-switch
          :model-value="modelValue.enabled"
          :disabled="!masterOn"
          @change="onSwitchChange"
        />
      </div>
    </template>

    <el-form label-width="100px" size="default">
      <el-form-item :label="idLabel">
        <el-input
          v-model="localServiceId"
          :placeholder="`请输入${idLabel}`"
          :disabled="!modelValue.enabled"
        />
      </el-form-item>
      <el-form-item label="超时时间">
        <el-input-number
          v-model="localTimeout"
          :min="1"
          :max="300"
          :disabled="!modelValue.enabled"
          controls-position="right"
        />
        <span class="unit">秒</span>
      </el-form-item>
      <el-form-item label="连接状态">
        <div class="status-area">
          <el-tag :type="statusTagType" size="default" effect="plain">
            {{ statusLabel }}
          </el-tag>
          <span v-if="responseTime" class="response-time">
            响应时间：{{ responseTime }}ms
          </span>
          <span v-if="errorMsg" class="error-msg">{{ errorMsg }}</span>
          <el-button
            :type="isTesting ? 'warning' : 'default'"
            size="small"
            :loading="isTesting"
            @click="handleTest"
          >
            {{ isTesting ? '测试中...' : '测试连接' }}
          </el-button>
        </div>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { testConnection } from '../../api/api.js'

const props = defineProps({
  title: { type: String, required: true },
  icon: { type: String, default: '🔧' },
  modelValue: { type: Object, required: true },
  masterOn: { type: Boolean, default: true },
  serviceType: { type: String, required: true },
  idLabel: { type: String, default: '工作流 ID' },
})

const emit = defineEmits(['update:modelValue', 'status-change'])

// modelValue = { enabled, workflow_id/bot_id, timeout }
const localServiceId = ref(props.modelValue.workflow_id || props.modelValue.bot_id || '')
const localTimeout = ref(props.modelValue.timeout || 120)
const isTesting = ref(false)
const status = ref('unknown')
const responseTime = ref(null)
const errorMsg = ref('')

// 同步外部变化
watch(
  () => props.modelValue,
  (v) => {
    localServiceId.value = v.workflow_id || v.bot_id || ''
    localTimeout.value = v.timeout || 120
  },
  { deep: true }
)

// 本地修改同步回父组件
watch(
  [localServiceId, localTimeout],
  () => {
    emit('update:modelValue', {
      enabled: props.modelValue.enabled,
      workflow_id: props.serviceType === 'chat' ? undefined : localServiceId.value,
      bot_id: props.serviceType === 'chat' ? localServiceId.value : undefined,
      timeout: localTimeout.value,
    })
  },
  { deep: true }
)

function onSwitchChange(val) {
  emit('update:modelValue', {
    enabled: val,
    workflow_id: props.serviceType === 'chat' ? undefined : localServiceId.value,
    bot_id: props.serviceType === 'chat' ? localServiceId.value : undefined,
    timeout: localTimeout.value,
  })
  if (!val) {
    status.value = 'unknown'
    responseTime.value = null
    errorMsg.value = ''
  }
}

async function handleTest() {
  if (isTesting.value) return
  isTesting.value = true
  status.value = 'testing'
  errorMsg.value = ''

  try {
    const res = await testConnection(props.serviceType)
    if (res.code === 200 && res.data) {
      status.value = res.data.status
      responseTime.value = res.data.response_time_ms
      errorMsg.value = res.data.error_message || ''
    }
  } catch {
    status.value = 'failed'
    errorMsg.value = '测试请求失败'
  } finally {
    isTesting.value = false
  }
}

const statusTagType = computed(() => {
  const map = { connected: 'success', failed: 'danger', testing: 'warning', unknown: 'info' }
  return map[status.value] || 'info'
})

const statusLabel = computed(() => {
  const map = {
    connected: '✅ 连接正常',
    failed: '❌ 连接失败',
    testing: '⏳ 测试中...',
    unknown: '⏸ 未测试',
  }
  return map[status.value] || '未知'
})
</script>

<style scoped>
.service-card {
  margin-bottom: 16px;
  border-radius: 8px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.icon {
  font-size: 20px;
}
.title {
  font-weight: 600;
  font-size: 15px;
}
.unit {
  margin-left: 6px;
  color: #888;
  font-size: 13px;
}
.status-area {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.response-time {
  color: #67c23a;
  font-size: 13px;
}
.error-msg {
  color: #f56c6c;
  font-size: 12px;
  max-width: 240px;
  word-break: break-all;
}
</style>
