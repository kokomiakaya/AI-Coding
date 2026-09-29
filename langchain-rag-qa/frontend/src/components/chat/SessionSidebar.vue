<template>
  <div class="session-sidebar">
    <div class="sidebar-header">
      <el-button type="primary" style="width: 100%" @click="$emit('new-session')">
        <el-icon><Plus /></el-icon>&nbsp;新建会话
      </el-button>
      <el-input
        v-model="keyword"
        placeholder="搜索会话…"
        clearable
        @input="onSearch"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
    </div>
    <el-scrollbar class="sidebar-list">
      <div
        v-for="s in sessions"
        :key="s.id"
        class="session-item"
        :class="{ active: s.id === activeId }"
        @click="$emit('select', s)"
      >
        <div class="session-title">{{ s.title }}</div>
        <div class="session-meta">
          <span class="session-preview">{{ s.last_message || '（暂无消息）' }}</span>
        </div>
        <div class="session-bottom">
          <span class="session-time">{{ shortTime(s.updated_at) }}</span>
          <span v-if="s.message_count" class="session-count">{{ s.message_count }} 条</span>
        </div>
        <el-dropdown
          class="session-menu"
          trigger="click"
          @click.stop
          @command="(cmd: string) => onCommand(cmd, s)"
        >
          <el-icon><MoreFilled /></el-icon>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="rename">
                <el-icon><EditPen /></el-icon>重命名
              </el-dropdown-item>
              <el-dropdown-item command="export">
                <el-icon><Download /></el-icon>导出 Markdown
              </el-dropdown-item>
              <el-dropdown-item command="delete" divided>
                <el-icon><Delete /></el-icon>删除会话
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <div v-if="hasMore" class="load-more" @click="$emit('load-more')">加载更多会话…</div>
      <el-empty
        v-if="!sessions.length"
        description="暂无会话"
        :image-size="70"
        style="padding: 30px 0"
      />
    </el-scrollbar>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { SessionItem } from '../../api/session'

defineProps<{
  sessions: SessionItem[]
  activeId: number | null
  hasMore: boolean
}>()

const emit = defineEmits<{
  (e: 'select', session: SessionItem): void
  (e: 'new-session'): void
  (e: 'search', keyword: string): void
  (e: 'load-more'): void
  (e: 'rename', session: SessionItem): void
  (e: 'delete', session: SessionItem): void
  (e: 'export', session: SessionItem): void
}>()

const keyword = ref('')

function onSearch() {
  emit('search', keyword.value.trim())
}

function onCommand(cmd: string, session: SessionItem) {
  if (cmd === 'rename') emit('rename', session)
  else if (cmd === 'delete') emit('delete', session)
  else if (cmd === 'export') emit('export', session)
}

function shortTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  const sameDay = d.toDateString() === now.toDateString()
  return sameDay
    ? `${pad(d.getHours())}:${pad(d.getMinutes())}`
    : `${d.getMonth() + 1}-${pad(d.getDate())}`
}
</script>

<style scoped>
.session-sidebar {
  width: 260px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-right: 1px solid #e4e7ed;
}

.sidebar-header {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.sidebar-list {
  flex: 1;
}

.session-item {
  position: relative;
  padding: 10px 34px 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f5f5f5;
  transition: background 0.15s;
}

.session-item:hover {
  background: #f5f7fa;
}

.session-item.active {
  background: #ecf3fd;
  border-left: 3px solid #2a78d6;
}

.session-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 3px;
}

.session-meta {
  overflow: hidden;
}

.session-preview {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.session-bottom {
  display: flex;
  justify-content: space-between;
  margin-top: 3px;
}

.session-time,
.session-count {
  font-size: 11px;
  color: #c0c4cc;
}

.session-menu {
  position: absolute;
  top: 10px;
  right: 8px;
  color: #909399;
  cursor: pointer;
}

.load-more {
  padding: 10px;
  text-align: center;
  font-size: 12px;
  color: #2a78d6;
  cursor: pointer;
}
</style>
