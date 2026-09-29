<template>
  <div class="feedback-btns">
    <el-tooltip content="回答有帮助">
      <el-button
        size="small"
        text
        :type="local === 1 ? 'success' : 'info'"
        @click="submit(1)"
      >
        <el-icon><CaretTop /></el-icon>
        有帮助
      </el-button>
    </el-tooltip>
    <el-tooltip content="回答不准确">
      <el-button
        size="small"
        text
        :type="local === -1 ? 'danger' : 'info'"
        @click="submit(-1)"
      >
        <el-icon><CaretBottom /></el-icon>
        不准确
      </el-button>
    </el-tooltip>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/axios'
import type { MessageItem } from '../../api/session'

const props = defineProps<{ message: MessageItem }>()

const local = ref<number | null>(props.message.feedback ?? null)

watch(
  () => props.message.feedback,
  (v) => (local.value = v ?? null),
)

async function submit(rate: number) {
  try {
    await http.post(`/messages/${props.message.id}/feedback`, { rate })
    local.value = rate
    ElMessage.success(rate === 1 ? '感谢您的反馈' : '已记录，我们会持续改进')
  } catch {
    /* 拦截器已提示 */
  }
}
</script>

<style scoped>
.feedback-btns {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
</style>
