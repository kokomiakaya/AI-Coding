<template>
  <el-card class="source-card" :class="{ flash: highlighted, 'is-cited': source.cited }" shadow="never">
    <div class="source-head">
      <span class="source-index" :class="{ cited: source.cited }">[{{ source.index }}]</span>
      <el-tooltip :content="source.document_name" placement="top">
        <span class="source-doc">{{ source.document_name }}</span>
      </el-tooltip>
      <el-tag v-if="source.cited" type="success" size="small" effect="light">回答已引用</el-tag>
      <span v-if="location" class="source-loc">{{ location }}</span>
    </div>
    <div class="source-score">
      <span class="score-label">相关度 {{ Math.round(source.relevance_score * 100) }}%</span>
      <el-progress
        :percentage="Math.round(source.relevance_score * 100)"
        :stroke-width="5"
        :show-text="false"
        color="#2a78d6"
      />
    </div>
    <div class="source-excerpt">{{ source.excerpt }}</div>
    <el-collapse-transition>
      <div v-if="expanded" class="source-full">{{ source.content }}</div>
    </el-collapse-transition>
    <el-button
      v-if="source.content && source.content.length > source.excerpt.length"
      link
      type="primary"
      size="small"
      class="expand-btn"
      @click="expanded = !expanded"
    >
      {{ expanded ? '收起完整片段' : '查看完整片段' }}
    </el-button>
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SourceItem } from '../../api/session'

const props = defineProps<{
  source: SourceItem
  highlighted?: boolean
}>()

const expanded = ref(false)

const location = computed(() => {
  const parts: string[] = []
  if (props.source.page) parts.push(`第 ${props.source.page} 页`)
  if (props.source.sheet) parts.push(`工作表 ${props.source.sheet}`)
  if (props.source.row) parts.push(`第 ${props.source.row} 行`)
  return parts.join(' · ')
})
</script>

<style scoped>
.source-card {
  margin-bottom: 8px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.source-card.is-cited {
  border-left: 3px solid #2a78d6;
}

.source-card.flash {
  border-color: #2a78d6;
  box-shadow: 0 0 0 2px rgba(42, 120, 214, 0.25);
}

.source-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.source-index {
  display: inline-block;
  min-width: 22px;
  padding: 0 5px;
  border-radius: 4px;
  background: #f2f3f5;
  color: #909399;
  font-size: 12px;
  text-align: center;
  font-weight: 600;
}

.source-index.cited {
  background: #e6f4ff;
  color: #1677ff;
}

.source-doc {
  font-weight: 600;
  font-size: 13px;
  color: #303133;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-loc {
  font-size: 12px;
  color: #909399;
  margin-left: auto;
}

.source-score {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.score-label {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

.source-excerpt,
.source-full {
  font-size: 13px;
  color: #52514e;
  line-height: 1.6;
  word-break: break-word;
}

.source-full {
  margin-top: 6px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 6px;
}

.expand-btn {
  margin-top: 4px;
  padding: 0;
}
</style>
