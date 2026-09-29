<template>
  <div
    class="md-body"
    :class="{ 'streaming-cursor': streaming }"
    v-html="rendered"
    @click="onClick"
  ></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderWithCitations } from '../../utils/markdown'

const props = defineProps<{
  content: string
  streaming?: boolean
}>()

const emit = defineEmits<{ (e: 'cite-click', index: number): void }>()

const rendered = computed(() => renderWithCitations(props.content))

/** 事件委托：点击引用角标时抛出编号 */
function onClick(ev: MouseEvent) {
  const target = (ev.target as HTMLElement).closest('.cite-chip') as HTMLElement | null
  const idx = target?.dataset.cite
  if (idx) emit('cite-click', Number(idx))
}
</script>
