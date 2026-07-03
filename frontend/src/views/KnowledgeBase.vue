<template>
  <div class="knowledge-base-page">
    <PageTitle title="知识库管理" icon="FolderOpened" subtitle="管理 RAG 知识库，上传文档供智能问答使用" />

    <!-- 知识库列表 -->
    <el-card shadow="hover" class="kb-card">
      <template #header>
        <div class="kb-header">
          <span class="kb-header-title">📚 知识库列表</span>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            新建知识库
          </el-button>
        </div>
      </template>

      <el-table :data="kbList" v-loading="loading" empty-text="暂无知识库" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="知识库名称" min-width="160" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="doc_count" label="文档数" width="80" align="center" />
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="handleViewDocs(row)">
              <el-icon><Document /></el-icon> 文档管理
            </el-button>
            <el-button size="small" type="warning" link @click="handleEdit(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 文档管理抽屉 -->
    <el-drawer
      v-model="docDrawerVisible"
      :title="`📄 ${currentKb?.name || ''} - 文档管理`"
      size="50%"
      destroy-on-close
    >
      <template v-if="currentKb">
        <!-- 上传区域 -->
        <el-upload
          drag
          multiple
          accept=".pdf,.txt,.md"
          :action="uploadAction"
          :headers="uploadHeaders"
          :on-success="onUploadSuccess"
          :on-error="onUploadError"
          :show-file-list="false"
          class="upload-area"
        >
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <div class="upload-text">拖拽文件到此处，或<em>点击上传</em></div>
          <template #tip>
            <div class="upload-tip">支持 PDF、TXT、Markdown 格式，单文件最大 50MB</div>
          </template>
        </el-upload>

        <!-- 文档列表 -->
        <el-table :data="docList" v-loading="docLoading" empty-text="暂无文档" stripe style="width: 100%; margin-top: 16px;">
          <el-table-column prop="filename" label="文件名" min-width="180" show-overflow-tooltip />
          <el-table-column prop="file_size" label="大小" width="100">
            <template #default="{ row }">
              {{ formatFileSize(row.file_size) }}
            </template>
          </el-table-column>
          <el-table-column prop="doc_status" label="状态" width="110">
            <template #default="{ row }">
              <el-tag v-if="row.doc_status === 'ready'" type="success" size="small">已就绪</el-tag>
              <el-tag v-else-if="row.doc_status === 'processing'" type="warning" size="small">处理中</el-tag>
              <el-tag v-else-if="row.doc_status === 'failed'" type="danger" size="small">处理失败</el-tag>
              <el-tag v-else size="info">等待处理</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="chunk_count" label="分块数" width="70" align="center" />
          <el-table-column prop="created_at" label="上传时间" width="160">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="130" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.doc_status === 'failed'"
                size="small" type="primary" link
                @click="handleReprocess(row)"
              >
                <el-icon><Refresh /></el-icon> 重试
              </el-button>
              <el-button size="small" type="danger" link @click="handleDeleteDoc(row)">
                <el-icon><Delete /></el-icon> 删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 失败消息展示 -->
        <div v-if="failedDoc?.error_message" class="error-message">
          <el-alert :title="`处理失败: ${failedDoc.filename}`" :description="failedDoc.error_message" type="error" show-icon closable />
        </div>
      </template>
    </el-drawer>

    <!-- 新建知识库对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建知识库" width="480px" destroy-on-close>
      <el-form :model="createForm" :rules="formRules" ref="createFormRef" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="createForm.name" placeholder="请输入知识库名称" maxlength="200" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="请输入知识库描述（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">确定创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑知识库对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑知识库" width="480px" destroy-on-close>
      <el-form :model="editForm" :rules="formRules" ref="editFormRef" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="editForm.name" placeholder="请输入知识库名称" maxlength="200" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="editForm.description" type="textarea" :rows="3" placeholder="请输入知识库描述（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleEditSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Document, UploadFilled, Refresh } from '@element-plus/icons-vue'
import {
  getKnowledgeBases, createKnowledgeBase, updateKnowledgeBase, deleteKnowledgeBase,
  getDocuments, uploadDocument, deleteDocument, reprocessDocument,
} from '../api/api.js'
import PageTitle from '../components/common/PageTitle.vue'

// ── 知识库列表 ──
const kbList = ref([])
const loading = ref(false)

async function loadKbList() {
  loading.value = true
  try {
    const res = await getKnowledgeBases()
    if (res.code === 200) kbList.value = res.data
  } catch (e) {
    ElMessage.error('加载知识库列表失败')
  } finally {
    loading.value = false
  }
}

// ── 新建知识库 ──
const showCreateDialog = ref(false)
const creating = ref(false)
const createFormRef = ref(null)
const createForm = ref({ name: '', description: '' })
const formRules = { name: [{ required: true, message: '请输入知识库名称', trigger: 'blur' }] }

async function handleCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  creating.value = true
  try {
    await createKnowledgeBase(createForm.value)
    ElMessage.success('知识库创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', description: '' }
    await loadKbList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

// ── 编辑知识库 ──
const showEditDialog = ref(false)
const saving = ref(false)
const editFormRef = ref(null)
const editForm = ref({ id: null, name: '', description: '' })

function handleEdit(row) {
  editForm.value = { id: row.id, name: row.name, description: row.description || '' }
  showEditDialog.value = true
}

async function handleEditSave() {
  const valid = await editFormRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await updateKnowledgeBase(editForm.value.id, { name: editForm.value.name, description: editForm.value.description })
    ElMessage.success('更新成功')
    showEditDialog.value = false
    await loadKbList()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '更新失败')
  } finally {
    saving.value = false
  }
}

// ── 删除知识库 ──
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除「${row.name}」吗？所有文档将被永久删除。`, '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
    await deleteKnowledgeBase(row.id)
    ElMessage.success('删除成功')
    await loadKbList()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

// ── 文档管理 ──
const docDrawerVisible = ref(false)
const currentKb = ref(null)
const docList = ref([])
const docLoading = ref(false)
let docPollTimer = null

function handleViewDocs(row) {
  currentKb.value = row
  docDrawerVisible.value = true
  loadDocs(row.id)
}

// 关闭抽屉时停止轮询
watch(docDrawerVisible, (val) => {
  if (!val && docPollTimer) {
    clearInterval(docPollTimer)
    docPollTimer = null
  }
})

async function loadDocs(kbId) {
  docLoading.value = true
  try {
    const res = await getDocuments(kbId)
    if (res.code === 200) docList.value = res.data
  } catch (e) {
    ElMessage.error('加载文档列表失败')
  } finally {
    docLoading.value = false
  }
}

// 检查是否还有待处理文档，有则轮询
function startDocPolling(kbId) {
  if (docPollTimer) clearInterval(docPollTimer)
  const hasPending = () => docList.value.some(d => d.doc_status === 'pending' || d.doc_status === 'processing')
  if (!hasPending()) return
  docPollTimer = setInterval(async () => {
    await loadDocs(kbId)
    if (!hasPending()) {
      clearInterval(docPollTimer)
      docPollTimer = null
    }
  }, 3000)
}

const uploadAction = computed(() => `/api/knowledge-bases/${currentKb.value?.id}/documents/upload`)
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`,
}))

function onUploadSuccess(response) {
  if (response?.code === 200) {
    ElMessage.success('上传成功，后台处理中...')
    loadDocs(currentKb.value.id)
    startDocPolling(currentKb.value.id)
  } else {
    ElMessage.error(response?.message || '上传失败')
  }
}

function onUploadError() {
  ElMessage.error('上传失败，请重试')
}

// ── 文档操作 ──
const failedDoc = computed(() => docList.value.find(d => d.doc_status === 'failed'))

async function handleDeleteDoc(row) {
  try {
    await ElMessageBox.confirm(`确定要删除「${row.filename}」吗？`, '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
    await deleteDocument(currentKb.value.id, row.id)
    ElMessage.success('删除成功')
    loadDocs(currentKb.value.id)
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function handleReprocess(row) {
  try {
    await reprocessDocument(currentKb.value.id, row.id)
    ElMessage.success('已重新开始处理')
    loadDocs(currentKb.value.id)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

// ── 工具函数 ──
function formatTime(t) {
  if (!t) return '-'
  const d = new Date(t)
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function formatFileSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

onMounted(loadKbList)
</script>

<style scoped>
.knowledge-base-page {
  max-width: 1100px;
  margin: 0 auto;
}

.kb-card {
  border: 1px solid #e6f0ff;
  background: linear-gradient(135deg, #f5f9ff, #fff);
}

.kb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.kb-header-title {
  font-size: 15px;
  font-weight: 600;
}

.upload-area {
  margin-bottom: 20px;
}
.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
}
.upload-text {
  font-size: 14px;
  color: #606266;
  margin-top: 8px;
}
.upload-text em {
  color: #1890ff;
  font-style: normal;
}
.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.error-message {
  margin-top: 12px;
}
</style>
