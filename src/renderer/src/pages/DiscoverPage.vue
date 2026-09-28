<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

// 每月预算（固定月度预算：设一个数，每个月通用）
const budgetInput = ref<number | undefined>(undefined)
const budgetCents = ref<number | null>(null)
const expenseCents = ref(0)
const savingBudget = ref(false)

// 金额展示：千分位 + 两位小数
const moneyFmt = new Intl.NumberFormat('zh-CN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

function fmtMoney(cents: number): string {
  return moneyFmt.format(cents / 100)
}

const monthLabel = computed(() => {
  const now = new Date()
  return `${now.getFullYear()} 年 ${now.getMonth() + 1} 月`
})

const hasBudget = computed(() => budgetCents.value !== null && budgetCents.value > 0)

const overBudget = computed(() => hasBudget.value && expenseCents.value > (budgetCents.value ?? 0))

const remainCents = computed(() => (budgetCents.value ?? 0) - expenseCents.value)

// 进度条百分比（超支时封顶 100%，具体超多少由下方文字说明）
const percent = computed(() => {
  if (!hasBudget.value) return 0
  return Math.min(100, Math.round((expenseCents.value / (budgetCents.value ?? 1)) * 100))
})

function currentYearMonth(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

async function loadBudget(): Promise<void> {
  const res = await window.api.getBudget()
  if (res.ok) {
    budgetCents.value = res.budgetCents ?? null
    if (budgetCents.value !== null) budgetInput.value = budgetCents.value / 100
  }
}

async function loadExpense(): Promise<void> {
  const res = await window.api.getMonthSummary(currentYearMonth())
  if (res.ok && res.summary) expenseCents.value = res.summary.expenseCents
}

onMounted(() => {
  loadBudget()
  loadExpense()
})

async function handleSaveBudget(): Promise<void> {
  if (!budgetInput.value || budgetInput.value <= 0) {
    ElMessage.warning('请先输入大于 0 的预算金额')
    return
  }
  savingBudget.value = true
  try {
    const res = await window.api.setBudget(Math.round(budgetInput.value * 100))
    if (res.ok) {
      ElMessage.success('每月预算已保存 ✅')
      await loadBudget()
    } else {
      ElMessage.error(`保存失败：${res.error ?? '未知错误'}`)
    }
  } finally {
    savingBudget.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>发现</h2>
    </div>

    <div class="card budget-card">
      <div class="card-title">💰 每月预算</div>
      <div class="budget-current">
        当前预算：<span class="budget-current-value">{{ hasBudget ? `¥ ${fmtMoney(budgetCents!)}` : '未设置' }}</span>
      </div>
      <div class="budget-form">
        <el-input-number
          v-model="budgetInput"
          :min="0"
          :precision="2"
          :controls="false"
          placeholder="请输入每月预算，例如 5000"
          style="width: 260px"
        />
        <span class="unit">元</span>
        <el-button type="primary" :loading="savingBudget" @click="handleSaveBudget">
          保存预算
        </el-button>
      </div>
      <div class="budget-tip">设置后，每个月都会用这个金额判断支出是否超支</div>
    </div>

    <div class="card" style="margin-top: 16px">
      <div class="card-title">📊 本月预算执行（{{ monthLabel }}）</div>

      <el-empty v-if="!hasBudget" description="还没有设置每月预算，先在上方设置吧" />

      <template v-else>
        <div class="exec-summary">
          <div class="exec-item">
            <div class="exec-label">本月支出</div>
            <div class="exec-value" :class="{ over: overBudget }">¥ {{ fmtMoney(expenseCents) }}</div>
          </div>
          <div class="exec-divider">/</div>
          <div class="exec-item">
            <div class="exec-label">每月预算</div>
            <div class="exec-value">¥ {{ fmtMoney(budgetCents!) }}</div>
          </div>
        </div>

        <el-progress
          class="exec-bar"
          :percentage="percent"
          :stroke-width="18"
          :color="overBudget ? '#f56c6c' : '#67c23a'"
          :show-text="false"
        />

        <div class="exec-result" :class="overBudget ? 'over' : 'ok'">
          <template v-if="overBudget">⚠️ 本月已超支 ¥ {{ fmtMoney(-remainCents) }}</template>
          <template v-else-if="remainCents === 0">🎯 预算刚刚好花完</template>
          <template v-else>✅ 本月还可花 ¥ {{ fmtMoney(remainCents) }}</template>
        </div>
        <div class="exec-percent" :class="{ over: overBudget }">预算已使用 {{ percent }}%</div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.budget-card {
  max-width: 560px;
}

.budget-current {
  font-size: 14px;
  color: #606266;
  margin-bottom: 12px;
}

.budget-current-value {
  font-weight: 600;
  color: #303133;
}

.budget-form {
  display: flex;
  align-items: center;
  gap: 8px;
}

.unit {
  color: #606266;
  font-size: 14px;
}

.budget-tip {
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
}

/* 执行情况 */
.exec-summary {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 12px;
}

.exec-item {
  min-width: 140px;
}

.exec-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.exec-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  font-variant-numeric: tabular-nums;
}

.exec-value.over {
  color: #f56c6c;
}

.exec-divider {
  font-size: 24px;
  color: #c0c4cc;
  font-weight: 300;
}

.exec-bar {
  margin-top: 12px;
}

.exec-result {
  margin-top: 12px;
  font-size: 16px;
  font-weight: 600;
}

.exec-result.ok {
  color: #67c23a;
}

.exec-result.over {
  color: #f56c6c;
}

.exec-percent {
  margin-top: 6px;
  font-size: 13px;
  color: #909399;
}

.exec-percent.over {
  color: #f56c6c;
}
</style>
