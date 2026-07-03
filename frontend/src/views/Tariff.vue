<template>
  <div class="tariff-page">
    <PageTitle title="电价策略配置" icon="Money" />

    <el-row :gutter="16">
      <el-col :span="16">
        <Toolbar>
          <template #left>
            <el-button type="primary" @click="showAddDialog">
              <el-icon><Plus /></el-icon>添加电价策略
            </el-button>
          </template>
          <template #right>
            <span style="font-size: 13px; color: var(--text-tertiary)">共 {{ tariffs.length }} 个时段</span>
          </template>
        </Toolbar>

        <el-table :data="tariffs" border v-loading="loading">
          <el-table-column prop="period_name" label="时段名称" width="100">
            <template #default="{ row }">
              <el-tag :type="tagType(row.period_name)" round size="small">{{ row.period_name }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="start_time" label="开始时间" width="100" />
          <el-table-column prop="end_time" label="结束时间" width="100" />
          <el-table-column prop="price_per_kwh" label="电价(元/kWh)" width="130">
            <template #default="{ row }">
              <span :style="{ color: priceColor(row.price_per_kwh), fontWeight: 600 }">
                {{ row.price_per_kwh.toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="150" show-overflow-tooltip />
          <el-table-column prop="is_active" label="启用" width="80">
            <template #default="{ row }">
              <el-switch :model-value="row.is_active" disabled />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="showEditDialog(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-col>

      <el-col :span="8">
        <el-card header="当前时段电价">
          <div v-if="currentTariff" style="text-align: center; padding: 12px 0">
            <div style="font-size: 48px; font-weight: 700; background: var(--brand-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent">
              {{ currentTariff.price_per_kwh?.toFixed(2) || '0.80' }}
            </div>
            <div style="color: var(--text-tertiary); margin-top: 8px">元/kWh</div>
            <el-tag :type="tagType(currentTariff.period_name)" size="large" round style="margin-top: 12px">
              {{ currentTariff.period_name }}
            </el-tag>
            <div style="margin-top: 8px; color: var(--text-tertiary); font-size: 13px">
              {{ currentTariff.start_time }} - {{ currentTariff.end_time }}
            </div>
          </div>
        </el-card>

        <el-card header="时段电价概览" style="margin-top: 16px">
          <div v-for="t in tariffs" :key="t.id" class="tariff-bar">
            <div class="tariff-name">{{ t.period_name }}</div>
            <el-progress
              :percentage="(t.price_per_kwh / maxPrice) * 100"
              :color="progressColor(t.price_per_kwh)"
              :stroke-width="8"
              :show-text="false"
            />
            <div class="tariff-price">¥{{ t.price_per_kwh.toFixed(2) }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑电价策略' : '添加电价策略'" width="500px" top="5vh">
      <el-form :model="form" label-width="110px">
        <el-form-item label="时段名称">
          <el-select v-model="form.period_name" style="width: 100%">
            <el-option v-for="p in periods" :key="p" :label="p" :value="p" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-time-picker v-model="form.start_time" format="HH:mm" value-format="HH:mm" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-picker v-model="form.end_time" format="HH:mm" value-format="HH:mm" style="width: 100%" />
        </el-form-item>
        <el-form-item label="电价(元/kWh)">
          <el-input-number v-model="form.price_per_kwh" :min="0" :step="0.01" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getTariffs, createTariff, updateTariff, getCurrentTariff } from '../api/api.js'
import PageTitle from '../components/common/PageTitle.vue'
import Toolbar from '../components/common/Toolbar.vue'

const tariffs = ref([])
const currentTariff = ref(null)
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const periods = ['高峰', '平段', '低谷']

const form = ref({
  period_name: '平段', start_time: '09:00', end_time: '17:00',
  price_per_kwh: 0.80, description: '',
})

const maxPrice = computed(() => {
  if (tariffs.value.length === 0) return 1.5
  return Math.max(...tariffs.value.map(t => t.price_per_kwh), 1.5)
})

function tagType(period) {
  if (period === '高峰') return 'danger'
  if (period === '平段') return 'warning'
  return 'success'
}

function priceColor(price) {
  if (price > 1.0) return '#f5222d'
  if (price > 0.5) return '#faad14'
  return '#52c41a'
}

function progressColor(price) {
  if (price > 1.0) return '#f5222d'
  if (price > 0.5) return '#faad14'
  return '#52c41a'
}

function showAddDialog() {
  isEdit.value = false
  editId.value = null
  form.value = { period_name: '平段', start_time: '09:00', end_time: '17:00', price_per_kwh: 0.80, description: '' }
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
      await updateTariff(editId.value, form.value)
      ElMessage.success('电价策略更新成功')
    } else {
      await createTariff(form.value)
      ElMessage.success('电价策略创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function fetchData() {
  loading.value = true
  try {
    const [tariffRes, currentRes] = await Promise.all([getTariffs(), getCurrentTariff()])
    if (tariffRes.code === 200) tariffs.value = tariffRes.data
    if (currentRes.code === 200) currentTariff.value = currentRes.data
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.tariff-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.tariff-name {
  width: 50px;
  font-size: 13px;
  color: var(--text-secondary);
}
.tariff-price {
  width: 60px;
  text-align: right;
  font-weight: 600;
  font-size: 14px;
}
</style>
