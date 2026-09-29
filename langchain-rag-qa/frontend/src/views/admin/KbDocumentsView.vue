<template>
  <div>
    <div class="page-head">
      <el-button text @click="$router.push('/admin/kb')">
        <el-icon><Back /></el-icon>&nbsp;返回知识库列表
      </el-button>
      <span class="kb-name">{{ kbName }}</span>
    </div>

    <el-row :gutter="16">
      <el-col :span="14">
        <!-- 上传面板 -->
        <el-card shadow="never" class="mb16">
          <div class="card-title">上传文档</div>
          <el-upload
            drag
            multiple
            :auto-upload="false"
            :on-change="onFileChange"
            :file-list="fileList"
            accept=".pdf,.docx,.txt,.md,.xlsx,.csv"
            style="margin-top: 12px"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处，或<em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF / DOCX / TXT / MD / XLSX / CSV，单个 ≤50MB。上传后异步解析入库（后台处理，可关闭页面）。
              </div>
            </template>
          </el-upload>
          <div class="upload-actions">
            <el-button text type="primary" @click="textDialogVisible = true">
              <el-icon><EditPen /></el-icon>&nbsp;录入文本
            </el-button>
            <span class="text-tip">不想建文件？直接粘贴文本内容入库解析</span>
            <el-button type="primary" :loading="uploading" :disabled="!fileList.length" @click="uploadFiles">
              开始上传（{{ fileList.length }} 个文件）
            </el-button>
          </div>
        </el-card>

        <!-- 文本录入对话框 -->
        <el-dialog v-model="textDialogVisible" title="录入文本入库" width="620px">
          <el-form label-width="80px">
            <el-form-item label="文档名称">
              <el-input v-model="textForm.filename" placeholder="如：新品卖点说明（可留空）" maxlength="100" />
            </el-form-item>
            <el-form-item label="文本内容">
              <el-input
                v-model="textForm.content"
                type="textarea"
                :rows="10"
                placeholder="粘贴需要入库的文本内容，将自动切分并向量化，作为问答的检索素材（如商品介绍、FAQ、售后政策等）"
              />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="textDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="textSaving" :disabled="!textForm.content.trim()" @click="submitText">
              录入并解析
            </el-button>
          </template>
        </el-dialog>

        <!-- 检索调试（答辩演示） -->
        <el-card shadow="never" class="mb16">
          <div class="card-title">
            检索调试
            <span class="card-sub">只跑检索不生成回答，用于检查命中效果（两阶段：混合检索 → 重排）</span>
          </div>
          <div class="search-test-row">
            <el-input
              v-model="testQuestion"
              placeholder="输入测试问题，如：星耀X1 电池容量"
              @keyup.enter="runSearchTest"
            />
            <el-button type="primary" :loading="testing" @click="runSearchTest">检索</el-button>
          </div>
          <div v-if="testResult" class="test-result">
            <div class="test-meta">共命中 {{ testResult.retrieved_count }} 条候选 {{ testResult.rerank_skipped ? '（重排已跳过）' : '' }}</div>
            <el-table :data="testResult.reranked.length ? testResult.reranked : testResult.hybrid" size="small" max-height="320">
              <el-table-column label="文档" min-width="140">
                <template #default="{ row }">{{ row.document_name }}</template>
              </el-table-column>
              <el-table-column label="位置" width="110">
                <template #default="{ row }">
                  <span v-if="row.page">第 {{ row.page }} 页</span>
                  <span v-else-if="row.row">第 {{ row.row }} 行</span>
                  <span v-else>—</span>
                </template>
              </el-table-column>
              <el-table-column label="片段" min-width="220" show-overflow-tooltip>
                <template #default="{ row }">{{ row.excerpt }}</template>
              </el-table-column>
              <el-table-column label="RRF分" width="90">
                <template #default="{ row }">{{ row.rrf_score }}</template>
              </el-table-column>
              <el-table-column label="重排分" width="90">
                <template #default="{ row }">
                  <el-tag v-if="row.relevance_score != null" size="small" :type="row.relevance_score >= 0.35 ? 'success' : 'warning'">
                    {{ row.relevance_score }}
                  </el-tag>
                  <span v-else>—</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>

      <!-- 文档列表 -->
      <el-col :span="10">
        <el-card shadow="never">
          <div class="card-title">
            文档列表
            <span class="card-sub">共 {{ total }} 个（自动刷新状态）</span>
          </div>
          <el-table :data="docs" v-loading="loading" size="small" max-height="560">
            <el-table-column prop="filename" label="文件名" min-width="140" show-overflow-tooltip />
            <el-table-column label="状态" width="96">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small" effect="light">
                  <el-icon v-if="row.status === 'embedding' || row.status === 'parsing'" class="is-loading" style="margin-right: 4px">
                    <Loading />
                  </el-icon>
                  {{ statusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="chunk_count" label="分块" width="60" align="center" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-tooltip v-if="row.status === 'failed'" :content="row.error_message || '处理失败'" placement="top">
                  <el-button link type="danger" size="small" @click="reEmbed(row)">重试</el-button>
                </el-tooltip>
                <el-button link type="primary" size="small" @click="previewChunks(row)">分块</el-button>
                <el-button link type="danger" size="small" @click="removeDoc(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 分块预览抽屉 -->
    <el-drawer v-model="chunkDrawer" title="分块预览" size="520px">
      <div class="drawer-sub">
        文档：{{ previewDoc?.filename }}（共 {{ chunkTotal }} 块，展示切分质量与来源定位）
      </div>
      <div v-for="c in chunkItems" :key="c.id" class="chunk-item">
        <div class="chunk-head">
          <el-tag size="small" type="info">#{{ c.chunk_index }}</el-tag>
          <span v-if="c.meta.page" class="chunk-loc">第 {{ c.meta.page }} 页</span>
          <span v-if="c.meta.sheet" class="chunk-loc">工作表 {{ c.meta.sheet }}</span>
          <span v-if="c.meta.row" class="chunk-loc">第 {{ c.meta.row }} 行</span>
        </div>
        <div class="chunk-content">{{ c.content }}</div>
      </div>
      <el-pagination
        v-if="chunkTotal > 20"
        layout="prev, pager, next"
        :total="chunkTotal"
        :page-size="20"
        :current-page="chunkPage"
        @current-change="loadChunks"
        style="margin-top: 12px; justify-content: center"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox, type UploadFile, type UploadUserFile } from 'element-plus'
import { kbApi } from '../../api/kb'
import { documentApi, type DocumentItem } from '../../api/document'

const route = useRoute()
const kbId = Number(route.params.id)

const kbName = ref('')
const docs = ref<DocumentItem[]>([])
const total = ref(0)
const loading = ref(false)

// 上传
const fileList = ref<UploadUserFile[]>([])
const uploading = ref(false)

// 文本录入
const textDialogVisible = ref(false)
const textSaving = ref(false)
const textForm = ref({ filename: '', content: '' })

// 检索调试
const testQuestion = ref('')
const testing = ref(false)
const testResult = ref<any>(null)

// 分块预览
const chunkDrawer = ref(false)
const previewDoc = ref<DocumentItem | null>(null)
const chunkItems = ref<any[]>([])
const chunkTotal = ref(0)
const chunkPage = ref(1)

let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  const kb = await kbApi.get(kbId).catch(() => null)
  kbName.value = kb?.name || `知识库 #${kbId}`
  await loadDocs()
  startPolling()
})

onBeforeUnmount(() => stopPolling())

async function loadDocs() {
  loading.value = true
  try {
    const data = await documentApi.list(kbId, 1, 50)
    docs.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

const hasProcessing = computed(() =>
  docs.value.some((d) => ['pending', 'parsing', 'embedding'].includes(d.status)),
)

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (hasProcessing.value) loadDocs()
  }, 2000)
}

function stopPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
}

function onFileChange(_file: UploadFile, list: UploadUserFile[]) {
  fileList.value = list
}

async function uploadFiles() {
  uploading.value = true
  try {
    const files = fileList.value.map((f) => f.raw as File).filter(Boolean)
    await documentApi.upload(kbId, files)
    fileList.value = []
    ElMessage.success('已接收文件，后台处理中')
    await loadDocs()
  } catch {
    /* 拦截器已提示 */
  } finally {
    uploading.value = false
  }
}

async function submitText() {
  textSaving.value = true
  try {
    await documentApi.createText(kbId, textForm.value.filename.trim(), textForm.value.content)
    textForm.value = { filename: '', content: '' }
    textDialogVisible.value = false
    ElMessage.success('文本已入库，后台解析中')
    await loadDocs()
  } catch {
    /* 拦截器已提示 */
  } finally {
    textSaving.value = false
  }
}

function statusType(status: string) {
  switch (status) {
    case 'ready':
      return 'success'
    case 'failed':
      return 'danger'
    case 'pending':
      return 'info'
    default:
      return 'primary'
  }
}

function statusText(status: string) {
  switch (status) {
    case 'pending':
      return '排队中'
    case 'parsing':
      return '解析中'
    case 'embedding':
      return '向量化中'
    case 'ready':
      return '已完成'
    case 'failed':
      return '失败'
    default:
      return status
  }
}

async function reEmbed(row: DocumentItem) {
  await documentApi.reEmbed(row.id)
  ElMessage.success('已重新加入处理队列')
  await loadDocs()
}

async function removeDoc(row: DocumentItem) {
  try {
    await ElMessageBox.confirm(`确定删除文档「${row.filename}」吗？其分块与向量将一并删除。`, '删除确认', {
      type: 'warning',
    })
  } catch {
    return
  }
  await documentApi.remove(row.id)
  ElMessage.success('文档已删除')
  await loadDocs()
}

async function previewChunks(row: DocumentItem) {
  previewDoc.value = row
  chunkPage.value = 1
  chunkDrawer.value = true
  await loadChunks(1)
}

async function loadChunks(page: number) {
  const data = await documentApi.chunks(previewDoc.value!.id, page, 20)
  chunkItems.value = data.items
  chunkTotal.value = data.total
  chunkPage.value = page
}

async function runSearchTest() {
  if (!testQuestion.value.trim()) return
  testing.value = true
  try {
    testResult.value = await kbApi.searchTest(kbId, testQuestion.value.trim())
  } catch {
    /* 拦截器已提示 */
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.kb-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.mb16 {
  margin-bottom: 16px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.card-sub {
  margin-left: 10px;
  font-size: 12px;
  font-weight: 400;
  color: #898781;
}

.upload-actions {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: flex-end;
}

.text-tip {
  font-size: 12px;
  color: #898781;
  margin-right: auto;
}

.search-test-row {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.test-result {
  margin-top: 12px;
}

.test-meta {
  font-size: 12px;
  color: #898781;
  margin-bottom: 8px;
}

.drawer-sub {
  font-size: 13px;
  color: #606266;
  margin-bottom: 12px;
}

.chunk-item {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 10px;
}

.chunk-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.chunk-loc {
  font-size: 12px;
  color: #2a78d6;
}

.chunk-content {
  font-size: 13px;
  color: #52514e;
  line-height: 1.6;
  word-break: break-word;
}

.format-size {
  font-size: 12px;
  color: #898781;
}
</style>
