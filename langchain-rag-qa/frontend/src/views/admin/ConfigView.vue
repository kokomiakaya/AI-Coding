<template>
  <div>
    <el-alert
      title="提示词与检索参数热更新：保存后立即生效（免发版调优）。检索参数为全局默认值，知识库自身的参数优先。"
      type="info"
      :closable="false"
      style="margin-bottom: 16px"
    />

    <el-card v-if="configs" shadow="never" v-loading="loading">
      <el-form label-width="200px" label-position="left">
        <template v-for="group in groups" :key="group.title">
          <el-divider content-position="left">{{ group.title }}</el-divider>
          <el-form-item v-for="item in group.items" :key="item.key">
            <template #label>
              <span>{{ labelOf(item) }}</span>
              <el-tooltip :content="item.description" placement="top">
                <el-icon style="margin-left: 4px; color: #898781; cursor: help"><QuestionFilled /></el-icon>
              </el-tooltip>
            </template>
            <el-input
              v-if="isNumber(item)"
              v-model.number="values[item.key]"
              style="max-width: 240px"
            />
            <el-input
              v-else-if="isShort(item)"
              v-model="values[item.key]"
              style="max-width: 240px"
            />
            <el-input
              v-else
              v-model="values[item.key]"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 10 }"
            />
          </el-form-item>
        </template>
      </el-form>
      <div class="save-bar">
        <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
        <span class="save-tip">保存后缓存立即失效，下一次问答即使用新配置</span>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi, type ConfigItem } from '../../api/admin'

const configs = ref<ConfigItem[] | null>(null)
const values = ref<Record<string, any>>({})
const loading = ref(false)
const saving = ref(false)

const groups = computed(() => {
  const all = configs.value || []
  return [
    { title: '提示词模板', prefix: 'prompt', items: all.filter((c) => c.key.startsWith('prompt.')) },
    { title: '检索参数（全局默认）', prefix: 'retrieval', items: all.filter((c) => c.key.startsWith('retrieval.')) },
    { title: '模型配置', prefix: 'model', items: all.filter((c) => c.key.startsWith('model.')) },
    { title: '其他', prefix: 'other', items: all.filter((c) => !/^(prompt|retrieval|model)\./.test(c.key)) },
  ].filter((g) => g.items.length)
})

function labelOf(item: ConfigItem): string {
  const map: Record<string, string> = {
    'prompt.system': '问答生成提示词',
    'prompt.rewrite': '查询改写提示词',
    'chat.fallback_answer': '无结果兜底话术',
    'chat.history_max_turns': '多轮历史轮数',
    'retrieval.top_k': '返回片段数 top_k',
    'retrieval.candidates': '重排候选数',
    'retrieval.score_threshold': '相关性阈值',
    'model.chat': '对话模型',
    'model.embedding': '嵌入模型',
    'model.rerank': '重排模型',
    'upload.max_size_mb': '上传大小上限(MB)',
  }
  return map[item.key] || item.key
}

function isNumber(item: ConfigItem): boolean {
  return typeof item.value === 'number'
}

function isShort(item: ConfigItem): boolean {
  return isNumber(item) || item.key.startsWith('model.')
}

onMounted(async () => {
  loading.value = true
  try {
    configs.value = await adminApi.getConfigs()
    const vals: Record<string, any> = {}
    configs.value.forEach((c) => (vals[c.key] = c.value))
    values.value = vals
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  try {
    await adminApi.updateConfigs(values.value)
    ElMessage.success('配置已保存并生效')
  } catch {
    /* 拦截器已提示 */
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.save-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 8px;
}

.save-tip {
  font-size: 12px;
  color: #898781;
}
</style>
