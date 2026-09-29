<template>
  <div class="msg-row" :class="message.role">
    <div class="avatar" :class="message.role">
      <el-icon v-if="message.role === 'assistant'"><Service /></el-icon>
      <el-icon v-else><UserFilled /></el-icon>
    </div>
    <div class="msg-main">
      <!-- 用户消息 -->
      <div v-if="message.role === 'user'" class="bubble user-bubble">{{ message.content }}</div>
      <!-- 助手消息 -->
      <template v-else>
        <div class="bubble assistant-bubble">
          <StreamingContent
            :content="message.content"
            :streaming="!!message.streaming"
            @cite-click="onCiteClick"
          />
          <div v-if="message.error" class="msg-error">{{ message.error }}</div>
        </div>
        <!-- 引用来源卡片 -->
        <div v-if="message.sources && message.sources.length" class="sources-area">
          <div class="sources-title">
            <el-icon><Document /></el-icon>
            引用来源（{{ message.sources.length }} 条）
          </div>
          <SourceCard
            v-for="s in message.sources"
            :key="s.index"
            :ref="(el) => setSourceRef(s.index, el)"
            :source="s"
            :highlighted="highlightIndex === s.index"
          />
        </div>
        <!-- 反馈与用量 -->
        <div v-if="!message.streaming" class="msg-footer">
          <FeedbackButtons :message="message" />
          <span v-if="message.latency_ms" class="usage-badge">
            {{ message.prompt_tokens + message.completion_tokens }} tokens ·
            {{ (message.latency_ms / 1000).toFixed(1) }}s
          </span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { MessageItem as ApiMessage } from '../../api/session'
import StreamingContent from './StreamingContent.vue'
import SourceCard from './SourceCard.vue'
import FeedbackButtons from './FeedbackButtons.vue'

/** 聊天消息（扩展流式占位与错误展示字段） */
export interface ChatMessage extends ApiMessage {
  streaming?: boolean
  error?: string
}

const props = defineProps<{ message: ChatMessage }>()

const highlightIndex = ref<number | null>(null)
const sourceEls: Record<number, HTMLElement> = {}

function setSourceRef(index: number, el: unknown) {
  if (el instanceof HTMLElement) sourceEls[index] = el
}

/** 点击引用角标 → 高亮并滚动到对应来源卡片 */
function onCiteClick(index: number) {
  highlightIndex.value = index
  sourceEls[index]?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  setTimeout(() => {
    if (highlightIndex.value === index) highlightIndex.value = null
  }, 2000)
}
</script>

<style scoped>
.msg-row {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}

.msg-row.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
  font-size: 16px;
}

.avatar.assistant {
  background: linear-gradient(135deg, #2a78d6, #5598e7);
}

.avatar.user {
  background: linear-gradient(135deg, #1baf7a, #3fce9e);
}

.msg-main {
  max-width: calc(100% - 60px);
  display: flex;
  flex-direction: column;
}

.msg-row.user .msg-main {
  align-items: flex-end;
}

.bubble {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.7;
}

.user-bubble {
  background: #2a78d6;
  color: #fff;
  white-space: pre-wrap;
  word-break: break-word;
  border-top-right-radius: 2px;
}

.assistant-bubble {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-top-left-radius: 2px;
  width: 100%;
  box-sizing: border-box;
}

.msg-error {
  color: #d03b3b;
  font-size: 13px;
  margin-top: 6px;
}

.sources-area {
  margin-top: 8px;
  width: 100%;
}

.sources-title {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: #52514e;
  margin-bottom: 6px;
}

.msg-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 6px;
}

.usage-badge {
  font-size: 12px;
  color: #898781;
}
</style>
