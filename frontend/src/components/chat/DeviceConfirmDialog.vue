<template>
  <el-dialog
    v-model="visible"
    title="设备确认"
    width="450px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
  >
    <div class="confirm-content">
      <p class="confirm-tip">以下设备名称匹配到多个候选，请选择具体设备：</p>
      <div
        v-for="(candidates, name) in pendingConfirms"
        :key="name"
        class="device-group"
      >
        <span class="device-label">{{ name }}</span>
        <el-radio-group v-model="selected[name]" class="device-radios">
          <el-radio
            v-for="c in candidates"
            :key="c.device_id"
            :label="c.device_id"
            size="small"
          >
            {{ c.name }}
            <span class="match-score">({{ (c.score * 100).toFixed(0) }}%)</span>
          </el-radio>
        </el-radio-group>
      </div>
    </div>
    <template #footer>
      <el-button @click="cancel">取消</el-button>
      <el-button type="primary" @click="confirm" :disabled="!canConfirm">
        确认选择
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  pendingConfirms: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const selected = ref({})

// 重置选择当弹窗打开
watch(visible, (val) => {
  if (val) {
    selected.value = {}
  }
})

const canConfirm = computed(() => {
  const names = Object.keys(props.pendingConfirms)
  if (names.length === 0) return false
  return names.every((name) => selected.value[name] != null)
})

function confirm() {
  const result = {}
  for (const [name, deviceId] of Object.entries(selected.value)) {
    result[name] = deviceId
  }
  emit('confirm', result)
  visible.value = false
}

function cancel() {
  emit('cancel')
  visible.value = false
}
</script>

<style scoped>
.confirm-content {
  padding: 4px 0;
}
.confirm-tip {
  font-size: 14px;
  color: #606266;
  margin-bottom: 16px;
}
.device-group {
  margin-bottom: 14px;
}
.device-label {
  display: block;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}
.device-radios {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-left: 8px;
}
.match-score {
  font-size: 11px;
  color: #909399;
  margin-left: 6px;
}
</style>
