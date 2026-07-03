<template>
  <div class="ai-config-page">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
      <el-breadcrumb-item>系统设置</el-breadcrumb-item>
      <el-breadcrumb-item>AI 管理</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="page-header">
      <h2>🤖 AI 智能体管理</h2>
      <p class="subtitle">配置 Coze 智能体工作流，管理本地/云端模式切换</p>
    </div>

    <!-- 总开关 -->
    <el-card class="master-card" shadow="hover">
      <div class="master-switch-area">
        <div class="master-info">
          <span class="master-icon">🚀</span>
          <div>
            <div class="master-title">云端智能体总开关</div>
            <div class="master-desc">
              {{ config.enable_cloud_agent ? '已启用云端模式，各服务可独立切换' : '使用本地规则引擎模式' }}
            </div>
          </div>
        </div>
        <el-switch
          v-model="config.enable_cloud_agent"
          active-text="云端"
          inactive-text="本地"
          inline-prompt
          size="large"
          @change="onMasterChange"
        />
      </div>
    </el-card>

    <!-- API Key 配置 -->
    <el-card class="apikey-card" shadow="hover">
      <div class="apikey-header">
        <span class="master-icon">🔑</span>
        <div>
          <div class="master-title">Coze API 配置</div>
          <div class="master-desc">所有工作流和智能体共用的认证信息</div>
        </div>
      </div>
      <el-form label-width="100px" size="default" class="apikey-form">
        <el-form-item label="API Key">
          <el-input
            v-model="config.coze_api_key"
            placeholder="请输入 Coze API Key"
            type="password"
            show-password
          />
        </el-form-item>
        <el-form-item label="API 地址">
          <el-input
            v-model="config.coze_api_base"
            placeholder="https://api.coze.cn"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 三个服务卡片 -->
    <ServiceConfigCard
      title="能耗分析工作流"
      icon="📊"
      :service-type="'analyze'"
      :id-label="'工作流 ID'"
      v-model="config.analyze"
      :master-on="config.enable_cloud_agent"
    />
    <ServiceConfigCard
      title="调度优化工作流"
      icon="📋"
      :service-type="'optimize'"
      :id-label="'工作流 ID'"
      v-model="config.optimize"
      :master-on="config.enable_cloud_agent"
    />
    <ServiceConfigCard
      title="对话智能体"
      icon="💬"
      :service-type="'chat'"
      :id-label="'Bot ID'"
      v-model="config.chat"
      :master-on="config.enable_cloud_agent"
    />

    <!-- 底部操作 -->
    <div class="action-bar">
      <el-button type="primary" :loading="saving" @click="handleSave">
        <el-icon><Check /></el-icon>
        保存配置
      </el-button>
      <el-button @click="handleReset">
        <el-icon><RefreshLeft /></el-icon>
        恢复默认
      </el-button>
      <span v-if="lastSaved" class="save-time">上次保存：{{ lastSaved }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, RefreshLeft } from '@element-plus/icons-vue'
import { getAIConfig, saveAIConfig } from '../api/api.js'
import ServiceConfigCard from '../components/config/ServiceConfigCard.vue'

const defaultConfig = {
  enable_cloud_agent: false,
  coze_api_key: '',
  coze_api_base: 'https://api.coze.cn',
  analyze: { enabled: false, workflow_id: '', timeout: 120 },
  optimize: { enabled: false, workflow_id: '', timeout: 120 },
  chat: { enabled: false, bot_id: '', timeout: 30 },
}

const config = ref({ ...defaultConfig })
const saving = ref(false)
const lastSaved = ref('')
let autoSaveTimer = null

async function loadConfig() {
  try {
    const res = await getAIConfig()
    if (res.code === 200 && res.data) {
      config.value = {
        enable_cloud_agent: res.data.enable_cloud_agent,
        coze_api_key: res.data.coze_api_key || '',
        coze_api_base: res.data.coze_api_base || 'https://api.coze.cn',
        analyze: { ...res.data.analyze },
        optimize: { ...res.data.optimize },
        chat: { ...res.data.chat },
      }
    }
  } catch {
    ElMessage.warning('加载配置失败')
  }
}

async function handleSave() {
  saving.value = true
  try {
    const payload = {
      enable_cloud_agent: config.value.enable_cloud_agent,
      coze_api_key: config.value.coze_api_key,
      coze_api_base: config.value.coze_api_base,
      analyze_enabled: config.value.analyze.enabled,
      analyze_workflow_id: config.value.analyze.workflow_id,
      analyze_timeout: config.value.analyze.timeout,
      optimize_enabled: config.value.optimize.enabled,
      optimize_workflow_id: config.value.optimize.workflow_id,
      optimize_timeout: config.value.optimize.timeout,
      chat_enabled: config.value.chat.enabled,
      chat_bot_id: config.value.chat.bot_id,
      chat_timeout: config.value.chat.timeout,
    }
    await saveAIConfig(payload)
    ElMessage.success('配置保存成功')
    lastSaved.value = new Date().toLocaleTimeString()
  } catch (e) {
    const msg = e?.response?.data?.detail?.[0]?.msg || '保存失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

function handleReset() {
  ElMessageBox.confirm('确定要恢复默认配置吗？所有 API Key、工作流 ID 和开关将被清空。', '恢复默认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    config.value = {
      enable_cloud_agent: false,
      coze_api_key: '',
      coze_api_base: 'https://api.coze.cn',
      analyze: { enabled: false, workflow_id: '', timeout: 120 },
      optimize: { enabled: false, workflow_id: '', timeout: 120 },
      chat: { enabled: false, bot_id: '', timeout: 30 },
    }
    handleSave()
  }).catch(() => {})
}

function onMasterChange(val) {
  if (!val) {
    config.value.analyze.enabled = false
    config.value.optimize.enabled = false
    config.value.chat.enabled = false
  }
}

// 自动保存防抖（1.5s）
watch(
  config,
  () => {
    if (autoSaveTimer) clearTimeout(autoSaveTimer)
    autoSaveTimer = setTimeout(() => {
      handleSave()
    }, 1500)
  },
  { deep: true }
)

onMounted(loadConfig)
</script>

<style scoped>
.ai-config-page {
  max-width: 900px;
  margin: 0 auto;
}
.page-header {
  margin: 16px 0 24px;
}
.page-header h2 {
  margin: 0;
  font-size: 22px;
}
.subtitle {
  margin: 4px 0 0;
  color: #888;
  font-size: 14px;
}

.master-card {
  margin-bottom: 16px;
  border: 1px solid #e6f0ff;
  background: linear-gradient(135deg, #f5f9ff, #fff);
}
.master-switch-area {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.master-info {
  display: flex;
  align-items: center;
  gap: 12px;
}
.master-icon {
  font-size: 28px;
}
.master-title {
  font-size: 16px;
  font-weight: 700;
}
.master-desc {
  font-size: 13px;
  color: #888;
  margin-top: 2px;
}

.apikey-card {
  margin-bottom: 20px;
  border: 1px solid #fff3e0;
  background: linear-gradient(135deg, #fffaf5, #fff);
}
.apikey-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f5f5f5;
}
.apikey-form {
  margin-top: 4px;
}
.apikey-form .el-form-item {
  margin-bottom: 12px;
}

.action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}
.save-time {
  margin-left: auto;
  color: #aaa;
  font-size: 12px;
}
</style>
