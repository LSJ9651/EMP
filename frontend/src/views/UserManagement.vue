<template>
  <div class="user-management-page">
    <PageTitle title="用户管理" icon="User" />

    <Toolbar>
      <template #left>
        <el-button type="primary" @click="showAddDialog">
          <el-icon><Plus /></el-icon>添加用户
        </el-button>
      </template>
      <template #right>
        <span style="font-size: 13px; color: var(--text-tertiary)">共 {{ users.length }} 个用户</span>
      </template>
    </Toolbar>

    <el-table :data="users" border v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" width="150" />
      <el-table-column prop="role" label="角色" width="120">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" size="small" round>
            {{ row.role === 'admin' ? '管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small" round>
            {{ row.status === 'active' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="workshop" label="车间" width="120">
        <template #default="{ row }">
          {{ row.workshop || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" min-width="240">
        <template #default="{ row }">
          <el-button link type="success" size="small" @click="showPermissionDialog(row)">权限</el-button>
          <el-button link type="primary" size="small" @click="showEditDialog(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑用户对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '添加用户'" width="450px" top="5vh">
      <el-form :model="form" label-width="100px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" :disabled="isEdit" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item label="车间">
          <el-input v-model="form.workshop" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 权限配置对话框 -->
    <el-dialog v-model="permDialogVisible" width="720px" :close-on-click-modal="false" top="5vh">
      <template #header>
        <div style="display: flex; align-items: center; gap: 12px">
          <h3 style="margin: 0">权限配置：{{ permTargetUser?.username }}</h3>
          <el-tag :type="permTargetUser?.role === 'admin' ? 'danger' : 'primary'" size="small" round>
            {{ permTargetUser?.role === 'admin' ? '管理员' : '普通用户' }}
          </el-tag>
        </div>
      </template>

      <div v-loading="permLoading">
        <el-alert
          v-if="permTargetUser?.role === 'admin'"
          title="管理员拥有所有权限，无需单独配置"
          type="info"
          show-icon
          :closable="false"
          style="margin-bottom: 16px"
        />

        <div v-if="permModules.length" class="perm-matrix">
          <div v-for="mod in permModules" :key="mod.module" class="perm-module-card">
            <div class="perm-module-header">
              <span class="perm-module-icon">{{ moduleIcon(mod.module) }}</span>
              <strong>{{ mod.label }}</strong>
            </div>
            <div class="perm-features">
              <el-checkbox
                v-for="feat in mod.features"
                :key="feat.feature"
                v-model="feat.is_granted"
                :disabled="permTargetUser?.role === 'admin'"
                :label="feat.label"
                size="small"
              >
                <el-tooltip :content="feat.desc" placement="top">
                  <span style="font-size: 12px">{{ feat.label }}</span>
                </el-tooltip>
              </el-checkbox>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div style="display: flex; justify-content: space-between">
          <div>
            <el-button link type="primary" @click="checkAllPerm(true)" :disabled="permTargetUser?.role === 'admin'">
              全选
            </el-button>
            <el-button link type="warning" @click="checkAllPerm(false)" :disabled="permTargetUser?.role === 'admin'">
              全不选
            </el-button>
          </div>
          <div>
            <el-button @click="permDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="handleSavePermissions" :loading="permSaving" :disabled="permTargetUser?.role === 'admin'">
              保存权限
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUsers, createUser, updateUser, getUserPermissions, updateUserPermissions } from '../api/api.js'
import PageTitle from '../components/common/PageTitle.vue'
import Toolbar from '../components/common/Toolbar.vue'

const users = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)

const form = ref({
  username: '',
  password: '',
  role: 'user',
  status: 'active',
  workshop: '',
})

// ===== 权限配置 =====
const permDialogVisible = ref(false)
const permTargetUser = ref(null)
const permModules = ref([])
const permLoading = ref(false)
const permSaving = ref(false)

function moduleIcon(mod) {
  const map = {
    energy_monitoring: '📊',
    ai_analysis: '🤖',
    scheduling: '⏱️',
    reports: '📑',
    system: '⚙️',
  }
  return map[mod] || '📌'
}

function checkAllPerm(granted) {
  for (const mod of permModules.value) {
    for (const feat of mod.features) {
      feat.is_granted = granted
    }
  }
}

async function showPermissionDialog(user) {
  permTargetUser.value = user
  permModules.value = []
  permDialogVisible.value = true

  if (user.role === 'admin') return

  permLoading.value = true
  try {
    const res = await getUserPermissions(user.id)
    if (res.code === 200) {
      permModules.value = res.data.modules
    }
  } catch (e) {
    ElMessage.error('获取权限列表失败')
  } finally {
    permLoading.value = false
  }
}

async function handleSavePermissions() {
  if (!permTargetUser.value) return

  const permissions = []
  for (const mod of permModules.value) {
    for (const feat of mod.features) {
      permissions.push({
        module: mod.module,
        feature: feat.feature,
        is_granted: feat.is_granted,
      })
    }
  }

  permSaving.value = true
  try {
    const res = await updateUserPermissions(permTargetUser.value.id, permissions)
    if (res.code === 200) {
      ElMessage.success('权限配置已保存并生效')
      permDialogVisible.value = false
    }
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '保存权限失败')
  } finally {
    permSaving.value = false
  }
}

function resetForm() {
  form.value = {
    username: '',
    password: '',
    role: 'user',
    status: 'active',
    workshop: '',
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
  form.value = {
    username: row.username,
    password: '',
    role: row.role,
    status: row.status,
    workshop: row.workshop || '',
  }
  dialogVisible.value = true
}

async function handleSave() {
  try {
    if (isEdit.value) {
      await updateUser(editId.value, {
        role: form.value.role,
        status: form.value.status,
        workshop: form.value.workshop,
      })
      ElMessage.success('用户更新成功')
    } else {
      if (!form.value.password) {
        ElMessage.warning('请输入密码')
        return
      }
      await createUser(form.value)
      ElMessage.success('用户创建成功')
    }
    dialogVisible.value = false
    await fetchUsers()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '操作失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除用户 "${row.name}" 吗？`, '确认删除', { type: 'warning' })
    await updateUser(row.id, { status: 'deleted' })
    ElMessage.success('用户已删除')
    await fetchUsers()
  } catch { /* canceled */ }
}

async function fetchUsers() {
  loading.value = true
  try {
    const res = await getUsers()
    if (res.code === 200) users.value = res.data
  } catch (e) {
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchUsers)
</script>

<style scoped>
.user-management-page {
  padding: 0;
}

/* ──── 权限矩阵 ──── */
.perm-matrix {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.perm-module-card {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  transition: border-color 0.2s;
}
.perm-module-card:hover {
  border-color: var(--brand-primary);
}

.perm-module-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px dashed var(--border-light);
}

.perm-module-icon {
  font-size: 18px;
}

.perm-features {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
}
</style>
