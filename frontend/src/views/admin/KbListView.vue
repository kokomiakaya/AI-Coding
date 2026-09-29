<template>
  <div>
    <el-card shadow="never">
      <div class="toolbar">
        <div>
          <span class="card-title">知识库列表</span>
          <span class="card-sub">共 {{ kbs.length }} 个知识库（仅管理员可维护）</span>
        </div>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>&nbsp;新建知识库
        </el-button>
      </div>

      <el-table :data="kbs" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.description || '—' }}</template>
        </el-table-column>
        <el-table-column label="切分参数" width="130">
          <template #default="{ row }">{{ row.chunk_size }} / 重叠 {{ row.chunk_overlap }}</template>
        </el-table-column>
        <el-table-column label="检索参数" width="130">
          <template #default="{ row }">top_k={{ row.top_k }} · 阈值 {{ row.score_threshold }}</template>
        </el-table-column>
        <el-table-column label="查询改写" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.rewrite_enabled ? 'success' : 'info'" size="small">
              {{ row.rewrite_enabled ? '开启' : '关闭' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="启用" width="80" align="center">
          <template #default="{ row }">
            <el-switch :model-value="row.is_active" @change="(v: any) => toggleActive(row, v)" />
          </template>
        </el-table-column>
        <el-table-column label="文档/分块" width="100" align="center">
          <template #default="{ row }">{{ row.document_count }} / {{ row.chunk_count }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="150">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="$router.push(`/admin/kb/${row.id}/documents`)">
              文档管理
            </el-button>
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="removeKb(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑知识库' : '新建知识库'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="130px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如：商品知识库" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="用途说明（可选）" />
        </el-form-item>
        <el-divider content-position="left">切分参数（仅影响新上传文档）</el-divider>
        <el-form-item label="分块大小" prop="chunk_size">
          <el-input-number v-model="form.chunk_size" :min="100" :max="2000" :step="50" />
          <span class="form-tip">字符数，中文商品信息建议 300-800</span>
        </el-form-item>
        <el-form-item label="分块重叠">
          <el-input-number v-model="form.chunk_overlap" :min="0" :max="500" :step="10" />
        </el-form-item>
        <el-divider content-position="left">检索参数</el-divider>
        <el-form-item label="返回片段数 top_k">
          <el-input-number v-model="form.top_k" :min="1" :max="20" />
        </el-form-item>
        <el-form-item label="相关性阈值">
          <el-input-number v-model="form.score_threshold" :min="0" :max="1" :step="0.05" :precision="2" />
          <span class="form-tip">低于阈值不引用、直接兜底回答（防幻觉）</span>
        </el-form-item>
        <el-form-item label="查询改写">
          <el-switch v-model="form.rewrite_enabled" />
          <span class="form-tip">结合多轮历史改写检索查询</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { kbApi, type KnowledgeBase } from '../../api/kb'
import { formatDateTime } from '../../utils/markdown'

const kbs = ref<KnowledgeBase[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const saving = ref(false)
const editing = ref<KnowledgeBase | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  description: '',
  chunk_size: 500,
  chunk_overlap: 50,
  top_k: 5,
  score_threshold: 0.5,
  rewrite_enabled: true,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
}

onMounted(loadKbs)

async function loadKbs() {
  loading.value = true
  try {
    kbs.value = await kbApi.list()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, {
    name: '',
    description: '',
    chunk_size: 500,
    chunk_overlap: 50,
    top_k: 5,
    score_threshold: 0.5,
    rewrite_enabled: true,
  })
  dialogVisible.value = true
}

function openEdit(row: KnowledgeBase) {
  editing.value = row
  Object.assign(form, {
    name: row.name,
    description: row.description,
    chunk_size: row.chunk_size,
    chunk_overlap: row.chunk_overlap,
    top_k: row.top_k,
    score_threshold: row.score_threshold,
    rewrite_enabled: row.rewrite_enabled,
  })
  dialogVisible.value = true
}

async function save() {
  const f = formRef.value
  if (!f) return
  await f.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      if (editing.value) {
        await kbApi.update(editing.value.id, { ...form })
        ElMessage.success('知识库已更新')
      } else {
        await kbApi.create({ ...form })
        ElMessage.success('知识库已创建')
      }
      dialogVisible.value = false
      loadKbs()
    } catch {
      /* 拦截器已提示 */
    } finally {
      saving.value = false
    }
  })
}

async function toggleActive(row: KnowledgeBase, value: boolean) {
  try {
    await kbApi.update(row.id, { is_active: value })
    row.is_active = value
    ElMessage.success(value ? '已启用' : '已停用（用户端不再可选）')
  } catch {
    /* 拦截器已提示 */
  }
}

async function removeKb(row: KnowledgeBase) {
  try {
    await ElMessageBox.confirm(
      `确定删除知识库「${row.name}」吗？将级联删除 ${row.document_count} 个文档、${row.chunk_count} 个分块及其向量，不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确认删除' },
    )
  } catch {
    return
  }
  await kbApi.remove(row.id)
  ElMessage.success('知识库已删除')
  loadKbs()
}
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.card-sub {
  margin-left: 12px;
  font-size: 12px;
  color: #898781;
}

.form-tip {
  margin-left: 10px;
  font-size: 12px;
  color: #898781;
}
</style>
