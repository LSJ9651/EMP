<template>
  <div class="notify-config-dingtalk">
    <el-form
      ref="formRef"
      :model="config"
      :rules="rules"
      label-width="130px"
      size="small"
    >
      <el-form-item label="Webhook URL" prop="webhook_url">
        <el-input
          v-model="config.webhook_url"
          placeholder="例如：https://oapi.dingtalk.com/robot/send?access_token=xxx"
        />
      </el-form-item>
      <el-form-item label="访问令牌" prop="access_token">
        <el-input
          v-model="config.access_token"
          type="password"
          show-password
          placeholder="钉钉机器人安全设置中的访问令牌（可选，已含在 URL 中则留空）"
        />
      </el-form-item>
      <el-form-item label="消息模板" prop="msg_template">
        <el-input
          v-model="config.msg_template"
          type="textarea"
          :rows="3"
          placeholder="可选，自定义消息模板。可用变量：{{report_name}}、{{report_summary}}、{{report_time}}、{{device_count}}"
        />
      </el-form-item>
      <el-form-item label="通知频率" prop="notify_frequency">
        <el-radio-group v-model="config.notify_frequency">
          <el-radio value="immediately">即时发送</el-radio>
          <el-radio value="batch">批量汇总</el-radio>
          <el-radio value="daily_summary">每日摘要</el-radio>
        </el-radio-group>
        <div class="freq-desc">
          <template v-if="config.notify_frequency === 'immediately'">每次报告生成时立即推送</template>
          <template v-else-if="config.notify_frequency === 'batch'">按固定间隔汇总后批量推送</template>
          <template v-else>每天定时发送前一天报告摘要</template>
        </div>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'validate'])

const formRef = ref(null)

const defaultConfig = {
  webhook_url: '',
  access_token: '',
  msg_template: '',
  notify_frequency: 'immediately',
}

const config = reactive({ ...defaultConfig, ...props.modelValue })

// 验证规则
const rules = {
  webhook_url: [
    { required: true, message: '请输入钉钉 Webhook URL', trigger: 'blur' },
    {
      pattern: /^https:\/\/oapi\.dingtalk\.com\/robot\/send\?access_token=/,
      message: 'URL 格式不正确，应为 https://oapi.dingtalk.com/robot/send?access_token=...',
      trigger: 'blur',
    },
  ],
}

function validate() {
  if (!formRef.value) return Promise.resolve(true)
  return formRef.value.validate().then(valid => {
    emit('validate', valid)
    return valid
  }).catch(() => {
    emit('validate', false)
    return false
  })
}

function getConfig() {
  return {
    webhook_url: config.webhook_url || '',
    access_token: config.access_token || '',
    msg_template: config.msg_template || '',
    notify_frequency: config.notify_frequency || 'immediately',
  }
}

watch(config, () => {
  emit('update:modelValue', { ...config })
}, { deep: true })

defineExpose({ validate, getConfig })
</script>

<style scoped>
.notify-config-dingtalk {
  padding: 8px 4px;
}
.freq-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
