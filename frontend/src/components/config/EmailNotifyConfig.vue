<template>
  <div class="notify-config-email">
    <el-form
      ref="formRef"
      :model="config"
      :rules="rules"
      label-width="130px"
      size="small"
    >
      <el-form-item label="SMTP 服务器" prop="smtp_server">
        <el-input v-model="config.smtp_server" placeholder="例如：smtp.example.com" />
      </el-form-item>
      <el-form-item label="端口号" prop="smtp_port">
        <el-input-number
          v-model="config.smtp_port"
          :min="1"
          :max="65535"
          :step="1"
          style="width: 160px"
        />
        <span class="port-hint">常用端口：25(非加密)、465(SSL)、587(TLS)</span>
      </el-form-item>
      <el-form-item label="发送邮箱" prop="sender_email">
        <el-input v-model="config.sender_email" placeholder="例如：noreply@example.com" />
      </el-form-item>
      <el-form-item label="认证用户名" prop="auth_username">
        <el-input v-model="config.auth_username" placeholder="留空则与发送邮箱相同" />
      </el-form-item>
      <el-form-item label="认证密码" prop="auth_password">
        <el-input
          v-model="config.auth_password"
          type="password"
          show-password
          placeholder="SMTP 授权码或密码"
        />
      </el-form-item>
      <el-form-item label="启用 TLS">
        <el-switch v-model="config.use_tls" />
        <span class="switch-hint">{{ config.use_tls ? '加密传输 (推荐)' : '非加密传输' }}</span>
      </el-form-item>
      <el-form-item label="邮件模板" prop="email_template">
        <el-input
          v-model="config.email_template"
          type="textarea"
          :rows="3"
          placeholder="可选，自定义邮件正文模板。可用变量：{{report_name}}、{{report_summary}}、{{report_time}}"
        />
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
  smtp_server: '',
  smtp_port: 587,
  sender_email: '',
  auth_username: '',
  auth_password: '',
  use_tls: true,
  email_template: '',
}

const config = reactive({ ...defaultConfig, ...props.modelValue })

// 验证规则
const rules = {
  smtp_server: [
    { required: true, message: '请输入 SMTP 服务器地址', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/, message: '请输入有效的服务器地址', trigger: 'blur' },
  ],
  smtp_port: [
    { required: true, type: 'number', min: 1, max: 65535, message: '端口范围 1~65535', trigger: 'blur' },
  ],
  sender_email: [
    { required: true, message: '请输入发送邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  auth_password: [
    { required: true, message: '请输入认证密码或授权码', trigger: 'blur' },
  ],
}

// 暴露一个验证方法让父组件调用
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
    smtp_server: config.smtp_server || '',
    smtp_port: config.smtp_port || 587,
    sender_email: config.sender_email || '',
    auth_username: config.auth_username || config.sender_email || '',
    auth_password: config.auth_password || '',
    use_tls: config.use_tls !== false,
    email_template: config.email_template || '',
  }
}

watch(config, () => {
  emit('update:modelValue', { ...config })
}, { deep: true })

defineExpose({ validate, getConfig })
</script>

<style scoped>
.notify-config-email {
  padding: 8px 4px;
}
.port-hint {
  font-size: 11px;
  color: #909399;
  margin-left: 8px;
}
.switch-hint {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}
</style>
