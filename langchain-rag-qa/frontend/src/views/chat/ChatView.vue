<template>
  <div class="chat-layout">
    <!-- 左侧：会话侧栏 -->
    <SessionSidebar
      :sessions="sessions"
      :active-id="currentSessionId"
      :has-more="sessionHasMore"
      @select="selectSession"
      @new-session="createSession"
      @search="onSearchSessions"
      @load-more="loadMoreSessions"
      @rename="renameSession"
      @delete="deleteSession"
      @export="exportSession"
    />

    <!-- 右侧：聊天主区 -->
    <div class="chat-main">
      <header class="chat-header">
        <div class="header-left">
          <span class="page-title">电商知识库问答</span>
          <el-tag v-if="currentSessionId" size="small" type="info" effect="plain">
            {{ currentTitle }}
          </el-tag>
        </div>
        <div class="header-right">
          <el-select
            v-model="currentKbId"
            placeholder="选择知识库"
            style="width: 200px"
            clearable
            @change="onKbChange"
          >
            <el-option
              v-for="kb in kbList"
              :key="kb.id ?? 0"
              :label="kb.name"
              :value="kb.id"
            />
          </el-select>
          <el-button v-if="auth.isAdmin" text type="primary" @click="$router.push('/admin')">
            <el-icon><Setting /></el-icon>&nbsp;管理后台
          </el-button>
          <UserMenu />
        </div>
      </header>

      <div ref="bodyRef" class="chat-body" @scroll="onBodyScroll">
        <div v-if="messageHasMore" class="load-more-msg" @click="loadMoreMessages">
          加载更早的消息（已显示 {{ messages.length }} / {{ messageTotal }}）
        </div>
        <MessageItem v-for="msg in messages" :key="msg.id" :message="msg" />
        <el-empty
          v-if="!messages.length && !sending"
          description="开始提问吧，例如：「星耀X1 的电池容量是多少？」"
          style="margin-top: 60px"
        />
      </div>

      <footer class="chat-footer">
        <el-input
          v-model="question"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 5 }"
          placeholder="输入商品相关问题，Enter 发送 / Shift+Enter 换行"
          resize="none"
          @keydown.enter.exact.prevent="send"
        />
        <div class="footer-actions">
          <span class="footer-tip">回答基于知识库检索生成，可点击回答中的引用角标查看来源片段</span>
          <el-button type="primary" :loading="sending" :disabled="!question.trim()" @click="send">
            发送<el-icon style="margin-left: 4px"><Promotion /></el-icon>
          </el-button>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../../stores/auth'
import { kbApi } from '../../api/kb'
import { sessionApi, type SessionItem } from '../../api/session'
import { streamChat } from '../../api/sse'
import SessionSidebar from '../../components/chat/SessionSidebar.vue'
import MessageItem, { type ChatMessage } from '../../components/chat/MessageItem.vue'
import UserMenu from '../../components/UserMenu.vue'

const auth = useAuthStore()
const PAGE_SIZE = 20

// ---------- 会话 ----------
const sessions = ref<SessionItem[]>([])
const sessionPage = ref(1)
const sessionTotal = ref(0)
const sessionHasMore = ref(false)
const sessionKeyword = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

// ---------- 知识库 ----------
const kbList = ref<Array<{ id: number | null; name: string }>>([])
const currentKbId = ref<number | null>(null)

// ---------- 消息 ----------
const messages = ref<ChatMessage[]>([])
const messagePage = ref(1)
const messageTotal = ref(0)
const messageHasMore = ref(false)
const currentSessionId = ref<number | null>(null)
const currentTitle = ref('')

const question = ref('')
const sending = ref(false)
const bodyRef = ref<HTMLElement>()
const autoScroll = ref(true)

onMounted(async () => {
  await Promise.all([loadKbs(), loadSessions(1)])
  if (sessions.value.length) {
    selectSession(sessions.value[0])
  }
})

async function loadKbs() {
  try {
    const list = await kbApi.list()
    kbList.value = [{ id: null, name: '全部知识库' }, ...list.map((k) => ({ id: k.id, name: k.name }))]
  } catch {
    /* 拦截器已提示 */
  }
}

// ---------- 会话列表 ----------
async function loadSessions(page: number, append = false) {
  const data = await sessionApi.list(page, PAGE_SIZE, sessionKeyword.value || undefined)
  sessions.value = append ? [...sessions.value, ...data.items] : data.items
  sessionTotal.value = data.total
  sessionPage.value = page
  sessionHasMore.value = sessions.value.length < data.total
}

function onSearchSessions(keyword: string) {
  sessionKeyword.value = keyword
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    loadSessions(1).catch(() => {})
  }, 300)
}

function loadMoreSessions() {
  if (sessionHasMore.value) loadSessions(sessionPage.value + 1, true).catch(() => {})
}

function selectSession(session: SessionItem) {
  currentSessionId.value = session.id
  currentTitle.value = session.title
  currentKbId.value = session.kb_id
  loadMessages(session.id, 1)
}

async function createSession() {
  try {
    const session = await sessionApi.create({ kb_id: currentKbId.value })
    sessions.value.unshift(session)
    sessionTotal.value += 1
    selectSession(session)
    ElMessage.success('已新建会话')
  } catch {
    /* 拦截器已提示 */
  }
}

async function renameSession(session: SessionItem) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新的会话名称', '重命名会话', {
      inputValue: session.title,
      inputValidator: (v: string) => (v.trim() ? true : '名称不能为空'),
    })
    await sessionApi.update(session.id, { title: value.trim() })
    session.title = value.trim()
    if (session.id === currentSessionId.value) currentTitle.value = value.trim()
    ElMessage.success('已重命名')
  } catch {
    /* 取消或失败 */
  }
}

async function deleteSession(session: SessionItem) {
  try {
    await ElMessageBox.confirm(`确定删除会话「${session.title}」吗？消息记录将一并删除。`, '删除确认', {
      type: 'warning',
    })
  } catch {
    return
  }
  await sessionApi.remove(session.id)
  sessions.value = sessions.value.filter((s) => s.id !== session.id)
  sessionTotal.value -= 1
  if (session.id === currentSessionId.value) {
    currentSessionId.value = null
    currentTitle.value = ''
    messages.value = []
    messageHasMore.value = false
  }
  ElMessage.success('会话已删除')
}

async function exportSession(session: SessionItem) {
  try {
    await sessionApi.exportSession(session.id)
    ElMessage.success('已导出 Markdown 文件')
  } catch {
    ElMessage.error('导出失败')
  }
}

// ---------- 消息 ----------
async function loadMessages(sessionId: number, page: number) {
  const data = await sessionApi.messages(sessionId, page, PAGE_SIZE)
  if (page === 1) {
    messages.value = data.items.map((m) => ({ ...m, streaming: false }))
  } else {
    const older = data.items.map((m) => ({ ...m, streaming: false }))
    const prevHeight = bodyRef.value?.scrollHeight || 0
    messages.value = [...older, ...messages.value]
    await nextTick()
    if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight - prevHeight
  }
  messageTotal.value = data.total
  messagePage.value = page
  messageHasMore.value = messages.value.length < data.total
  if (page === 1) scrollToBottom()
}

function loadMoreMessages() {
  if (messageHasMore.value && currentSessionId.value) {
    loadMessages(currentSessionId.value, messagePage.value + 1).catch(() => {})
  }
}

// ---------- 发送 ----------
async function send() {
  const q = question.value.trim()
  if (!q || sending.value) return
  sending.value = true
  question.value = ''

  const now = new Date().toISOString()
  const userMsg: ChatMessage = {
    id: -Date.now(),
    role: 'user',
    content: q,
    sources: null,
    prompt_tokens: 0,
    completion_tokens: 0,
    latency_ms: 0,
    meta: {},
    feedback: null,
    created_at: now,
  }
  const assistantMsg: ChatMessage = {
    id: -Date.now() + 1,
    role: 'assistant',
    content: '',
    sources: null,
    prompt_tokens: 0,
    completion_tokens: 0,
    latency_ms: 0,
    meta: {},
    feedback: null,
    created_at: now,
    streaming: true,
  }
  messages.value.push(userMsg, assistantMsg)
  scrollToBottom()

  try {
    await streamChat(
      { question: q, session_id: currentSessionId.value, kb_id: currentKbId.value },
      {
        onMeta: (data) => {
          // 新会话：拿到后端分配的会话 ID 与标题
          if (!currentSessionId.value) {
            currentSessionId.value = data.session_id
            currentTitle.value = data.session_title
            refreshSessionsSilently()
          }
        },
        onDelta: (content) => {
          assistantMsg.content += content
          if (autoScroll.value) scrollToBottom()
        },
        onSources: (sources) => {
          assistantMsg.sources = sources
        },
        onUsage: (usage) => {
          assistantMsg.latency_ms = usage.latency_ms
          assistantMsg.prompt_tokens = usage.prompt_tokens
          assistantMsg.completion_tokens = usage.completion_tokens
        },
        onDone: () => {
          assistantMsg.streaming = false
          refreshSessionsSilently()
        },
        onError: (detail) => {
          assistantMsg.streaming = false
          assistantMsg.error = detail
        },
      },
    )
  } catch (e: any) {
    assistantMsg.streaming = false
    assistantMsg.error = e?.message || '请求失败，请稍后重试'
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

function refreshSessionsSilently() {
  loadSessions(1).catch(() => {})
}

// ---------- 滚动 ----------
function scrollToBottom() {
  nextTick(() => {
    if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  })
}

function onBodyScroll() {
  const el = bodyRef.value
  if (!el) return
  autoScroll.value = el.scrollTop + el.clientHeight >= el.scrollHeight - 80
}

// ---------- 知识库切换 ----------
async function onKbChange(value: number | null) {
  currentKbId.value = value
  if (currentSessionId.value) {
    try {
      await sessionApi.update(currentSessionId.value, { kb_id: value })
    } catch {
      /* 拦截器已提示 */
    }
  }
}
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100%;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  height: 56px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

.load-more-msg {
  text-align: center;
  padding: 8px;
  margin-bottom: 12px;
  font-size: 12px;
  color: #2a78d6;
  cursor: pointer;
  background: #f0f6ff;
  border-radius: 6px;
}

.chat-footer {
  padding: 12px 24px 16px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}

.footer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}

.footer-tip {
  font-size: 12px;
  color: #898781;
}
</style>
