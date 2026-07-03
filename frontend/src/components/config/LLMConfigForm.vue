<template>
  <div class="llm-config-form">
    <!-- ── 对话模型配置 ── -->
    <el-card shadow="hover" class="config-card">
      <div class="section-header">
        <span class="section-icon">💬</span>
        <div>
          <div class="section-title">对话模型配置</div>
          <div class="section-desc">用于 RAG 问答时生成回复，支持云端或本地</div>
        </div>
      </div>
      <el-form label-width="110px" size="default" class="config-form">
        <el-form-item label="Provider">
          <el-radio-group v-model="chatConfig.provider" class="provider-radio" @change="onChatProviderChange">
            <el-radio-button value="openai_compatible">OpenAI 兼容接口</el-radio-button>
            <el-radio-button value="ollama">Ollama 本地模型</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="API 地址">
          <el-input
            v-model="chatConfig.api_base"
            :placeholder="chatConfig.provider === 'ollama' ? 'http://localhost:11434' : 'https://api.openai.com/v1'"
          />
        </el-form-item>
        <el-form-item label="API Key" v-if="chatConfig.provider === 'openai_compatible'">
          <el-input v-model="chatConfig.api_key" type="password" show-password placeholder="sk-..." />
          <div class="form-tip">Ollama 无需 API Key</div>
        </el-form-item>
        <el-form-item label="模型名">
          <el-input
            v-model="chatConfig.model_name"
            :placeholder="chatConfig.provider === 'ollama' ? 'qwen2:7b' : 'gpt-4o-mini'"
          />
        </el-form-item>
        <el-form-item label="温度">
          <el-slider v-model="sharedConfig.temperature" :min="0" :max="2" :step="0.1" show-input style="width: 280px;" />
        </el-form-item>
        <el-form-item label="最大 Token">
          <el-input-number v-model="sharedConfig.max_tokens" :min="64" :max="32768" :step="256" />
        </el-form-item>
      </el-form>
      <div class="section-actions">
        <el-button size="small" :loading="testingLLM" @click="handleTestLLM">
          <el-icon><Connection /></el-icon>
          测试对话模型
        </el-button>
        <span v-if="testResultLLM" class="test-result" :class="testResultLLM.success ? 'success' : 'fail'">
          {{ testResultLLM.success ? '✅ 连接成功' : '❌ ' + testResultLLM.error }}
        </span>
      </div>
    </el-card>

    <!-- ── 嵌入模型配置（与对话模型完全独立） ── -->
    <el-card shadow="hover" class="config-card">
      <div class="section-header">
        <span class="section-icon">🔤</span>
        <div>
          <div class="section-title">嵌入模型配置</div>
          <div class="section-desc">用于将文档转为向量进行检索，建议用本地 Ollama 模型</div>
        </div>
      </div>
      <el-form label-width="110px" size="default" class="config-form">
        <el-form-item label="Provider">
          <el-radio-group v-model="embeddingConfig.provider" class="provider-radio" @change="onEmbeddingProviderChange">
            <el-radio-button value="openai_compatible">OpenAI 兼容接口</el-radio-button>
            <el-radio-button value="ollama">Ollama 本地模型</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="API 地址">
          <el-input
            v-model="embeddingConfig.api_base"
            :placeholder="embeddingConfig.provider === 'ollama' ? 'http://localhost:11434' : 'https://api.openai.com/v1'"
          />
        </el-form-item>
        <el-form-item label="API Key" v-if="embeddingConfig.provider === 'openai_compatible'">
          <el-input v-model="embeddingConfig.api_key" type="password" show-password placeholder="sk-..." />
          <div class="form-tip">Ollama 无需 API Key，推荐使用 nomic-embed-text</div>
        </el-form-item>
        <el-form-item label="模型名">
          <el-input
            v-model="embeddingConfig.model_name"
            :placeholder="embeddingConfig.provider === 'ollama' ? 'nomic-embed-text' : 'text-embedding-3-small'"
          />
        </el-form-item>
      </el-form>
      <div class="section-actions">
        <el-button size="small" :loading="testingEmbedding" @click="handleTestEmbedding">
          <el-icon><Connection /></el-icon>
          测试嵌入模型
        </el-button>
        <span v-if="testResultEmb" class="test-result" :class="testResultEmb.success ? 'success' : 'fail'">
          {{ testResultEmb.success ? `✅ 嵌入成功 (维度: ${testResultEmb.dim})` : '❌ ' + testResultEmb.error }}
        </span>
      </div>
    </el-card>

    <!-- 底部操作 -->
    <div class="action-bar">
      <el-button type="success" :loading="saving" @click="handleSave">
        <el-icon><Check /></el-icon>
        保存配置
      </el-button>
      <span v-if="lastSaved" class="save-time">上次保存：{{ lastSaved }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Connection } from '@element-plus/icons-vue'
import { getLLMConfig, saveLLMConfig, testLLMConnection } from '../../api/api.js'

const emit = defineEmits(['saved'])

// ── 缓存各 Provider 的独立配置，切换时自动保存/恢复 ──
// 对话模型缓存
const chatProviderCache = {
  openai_compatible: {
    provider: 'openai_compatible',
    api_base: '',
    api_key: '',
    model_name: 'gpt-4o-mini',
  },
  ollama: {
    provider: 'ollama',
    api_base: 'http://localhost:11434',
    api_key: '',
    model_name: 'qwen2:7b',
  },
}

// 当前展示在界面上的对话配置
const chatConfig = reactive({
  provider: 'openai_compatible',
  api_base: '',
  api_key: '',
  model_name: 'gpt-4o-mini',
})

// 嵌入模型缓存
const embeddingProviderCache = {
  openai_compatible: {
    provider: 'openai_compatible',
    api_base: '',
    api_key: '',
    model_name: 'text-embedding-3-small',
  },
  ollama: {
    provider: 'ollama',
    api_base: 'http://localhost:11434',
    api_key: '',
    model_name: 'nomic-embed-text',
  },
}

// 当前展示在界面上的嵌入配置
const embeddingConfig = reactive({
  provider: 'openai_compatible',
  api_base: '',
  api_key: '',
  model_name: 'text-embedding-3-small',
})

// 公共参数
const sharedConfig = reactive({
  temperature: 0.7,
  max_tokens: 2048,
})

const saving = ref(false)
const testingLLM = ref(false)
const testingEmbedding = ref(false)
const testResultLLM = ref(null)
const testResultEmb = ref(null)
const lastSaved = ref('')

// ── Provider 切换处理：保存当前值到缓存，从缓存恢复目标值 ──
let lastChatProvider = 'openai_compatible'
function onChatProviderChange(newProvider) {
  if (newProvider === lastChatProvider) return
  // 先把当前表单值保存到上一个 Provider 的缓存
  Object.assign(chatProviderCache[lastChatProvider], {
    api_base: chatConfig.api_base,
    api_key: chatConfig.api_key,
    model_name: chatConfig.model_name,
  })
  // 从目标 Provider 缓存恢复
  const cached = chatProviderCache[newProvider]
  chatConfig.api_base = cached.api_base
  chatConfig.api_key = cached.api_key
  chatConfig.model_name = cached.model_name
  lastChatProvider = newProvider
}

let lastEmbeddingProvider = 'openai_compatible'
function onEmbeddingProviderChange(newProvider) {
  if (newProvider === lastEmbeddingProvider) return
  // 先把当前表单值保存到上一个 Provider 的缓存
  Object.assign(embeddingProviderCache[lastEmbeddingProvider], {
    api_base: embeddingConfig.api_base,
    api_key: embeddingConfig.api_key,
    model_name: embeddingConfig.model_name,
  })
  // 从目标 Provider 缓存恢复
  const cached = embeddingProviderCache[newProvider]
  embeddingConfig.api_base = cached.api_base
  embeddingConfig.api_key = cached.api_key
  embeddingConfig.model_name = cached.model_name
  lastEmbeddingProvider = newProvider
}

onMounted(async () => {
  try {
    const res = await getLLMConfig()
    if (res.code === 200 && res.data) {
      // 填充各 Provider 缓存
      chatProviderCache.openai_compatible.api_base = res.data.api_base || ''
      chatProviderCache.openai_compatible.api_key = res.data.api_key || ''
      chatProviderCache.openai_compatible.model_name = res.data.model_name || 'gpt-4o-mini'

      embeddingProviderCache.openai_compatible.api_base = res.data.embedding_api_base || ''
      embeddingProviderCache.openai_compatible.api_key = res.data.embedding_api_key || ''
      embeddingProviderCache.openai_compatible.model_name = res.data.embedding_model || 'text-embedding-3-small'

      // 设置当前显示的配置
      const curChatProvider = res.data.provider || 'openai_compatible'
      lastChatProvider = curChatProvider
      chatConfig.provider = curChatProvider
      chatConfig.api_base = chatProviderCache[curChatProvider].api_base
      chatConfig.api_key = chatProviderCache[curChatProvider].api_key
      chatConfig.model_name = chatProviderCache[curChatProvider].model_name

      const curEmbProvider = res.data.embedding_provider || 'openai_compatible'
      lastEmbeddingProvider = curEmbProvider
      embeddingConfig.provider = curEmbProvider
      embeddingConfig.api_base = embeddingProviderCache[curEmbProvider].api_base
      embeddingConfig.api_key = embeddingProviderCache[curEmbProvider].api_key
      embeddingConfig.model_name = embeddingProviderCache[curEmbProvider].model_name

      sharedConfig.temperature = res.data.temperature ?? 0.7
      sharedConfig.max_tokens = res.data.max_tokens ?? 2048
    }
  } catch {
    // 默认值已设置
  }
})

async function handleSave() {
  saving.value = true
  testResultLLM.value = null
  testResultEmb.value = null
  try {
    // 分别取各自配置，确保互不干扰
    await saveLLMConfig({
      provider: chatConfig.provider,
      api_base: chatConfig.api_base,
      api_key: chatConfig.api_key,
      model_name: chatConfig.model_name,
      embedding_provider: embeddingConfig.provider,
      embedding_api_base: embeddingConfig.api_base,
      embedding_api_key: embeddingConfig.api_key,
      embedding_model: embeddingConfig.model_name,
      temperature: sharedConfig.temperature,
      max_tokens: sharedConfig.max_tokens,
      is_active: true,
    })
    ElMessage.success('LLM 配置保存成功')
    lastSaved.value = new Date().toLocaleTimeString()
    emit('saved')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function buildTestPayload(testType) {
  return {
    test_type: testType,
    // 对话模型测试参数
    provider: chatConfig.provider,
    api_base: chatConfig.api_base,
    api_key: chatConfig.api_key,
    model_name: chatConfig.model_name,
    // 嵌入模型测试参数
    embedding_provider: embeddingConfig.provider,
    embedding_api_base: embeddingConfig.api_base,
    embedding_api_key: embeddingConfig.api_key,
    embedding_model: embeddingConfig.model_name,
    temperature: sharedConfig.temperature,
    max_tokens: sharedConfig.max_tokens,
  }
}

async function handleTestLLM() {
  testingLLM.value = true
  testResultLLM.value = null
  try {
    const payload = buildTestPayload('llm')
    const res = await testLLMConnection(payload)
    const detail = res.data?.details?.llm
    if (res.code === 200 && detail?.success) {
      testResultLLM.value = { success: true, reply: detail.reply }
      ElMessage.success('对话模型连接测试成功')
    } else {
      const err = res.data?.error || res.message || '测试失败'
      testResultLLM.value = { success: false, error: err }
      ElMessage.error(err)
    }
  } catch (e) {
    const msg = e?.response?.data?.detail || e.message || '测试失败'
    testResultLLM.value = { success: false, error: msg }
    ElMessage.error(msg)
  } finally {
    testingLLM.value = false
  }
}

async function handleTestEmbedding() {
  testingEmbedding.value = true
  testResultEmb.value = null
  try {
    const payload = buildTestPayload('embedding')
    const res = await testLLMConnection(payload)
    const detail = res.data?.details?.embedding
    if (res.code === 200 && detail?.success) {
      testResultEmb.value = { success: true, dim: detail.dimension }
      ElMessage.success(`嵌入模型测试成功 (输出维度: ${detail.dimension})`)
    } else {
      const err = res.data?.error || res.message || '测试失败'
      testResultEmb.value = { success: false, error: err }
      ElMessage.error(err)
    }
  } catch (e) {
    const msg = e?.response?.data?.detail || e.message || '测试失败'
    testResultEmb.value = { success: false, error: msg }
    ElMessage.error(msg)
  } finally {
    testingEmbedding.value = false
  }
}
</script>

<style scoped>
.llm-config-form {
  max-width: 800px;
}

.config-card {
  margin-bottom: 20px;
  border: 1px solid var(--el-border-color-light, #f0f0f0);
  background: linear-gradient(135deg, #fafcff, #fff);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter, #f0f0f0);
}
.section-icon {
  font-size: 26px;
}
.section-title {
  font-size: 15px;
  font-weight: 600;
}
.section-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.provider-radio {
  display: flex;
  gap: 0;
}

.config-form .el-form-item {
  margin-bottom: 14px;
}
.form-tip {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 8px;
  border-top: 1px dashed var(--el-border-color-lighter, #eee);
}
.test-result {
  font-size: 13px;
}
.test-result.success { color: #67c23a; }
.test-result.fail { color: #f56c6c; }

.action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-light, #f0f0f0);
}
.save-time {
  margin-left: auto;
  color: #909399;
  font-size: 12px;
}
</style>
