<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { expenseIcon } from '../data/categories'
import type { CategoryStat, MonthSummary } from '../../../shared/types'

const month = ref(new Date())
const summary = ref<MonthSummary>({ incomeCents: 0, expenseCents: 0 })
const categoryStats = ref<CategoryStat[]>([])
const loading = ref(false)

function formatMonth(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

async function loadStats(): Promise<void> {
  loading.value = true
  try {
    const ym = formatMonth(month.value)
    const [summaryRes, statsRes] = await Promise.all([
      window.api.getMonthSummary(ym),
      window.api.getCategoryStats(ym)
    ])
    if (summaryRes.ok && summaryRes.summary) summary.value = summaryRes.summary
    if (statsRes.ok && statsRes.stats) categoryStats.value = statsRes.stats
  } finally {
    loading.value = false
  }
}

onMounted(loadStats)
watch(month, loadStats)

const balanceCents = computed(() => summary.value.incomeCents - summary.value.expenseCents)

// 金额展示：千分位 + 两位小数
const moneyFmt = new Intl.NumberFormat('zh-CN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

function fmtMoney(cents: number): string {
  return moneyFmt.format(cents / 100)
}

const totalExpenseCents = computed(() =>
  categoryStats.value.reduce((s, c) => s + c.totalCents, 0)
)

function percentOf(c: CategoryStat): number {
  if (totalExpenseCents.value === 0) return 0
  return (c.totalCents / totalExpenseCents.value) * 100
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>统计</h2>
      <el-date-picker
        v-model="month"
        type="month"
        :clearable="false"
        format="YYYY年M月"
        placeholder="选择月份"
        style="width: 150px"
      />
    </div>

    <el-row :gutter="16" v-loading="loading">
      <el-col :span="8">
        <div class="card stat-card">
          <div class="stat-label">本月收入</div>
          <div class="stat-value income">¥ {{ fmtMoney(summary.incomeCents) }}</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card stat-card">
          <div class="stat-label">本月支出</div>
          <div class="stat-value expense">¥ {{ fmtMoney(summary.expenseCents) }}</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card stat-card">
          <div class="stat-label">本月结余</div>
          <div class="stat-value" :class="{ negative: balanceCents < 0 }">
            ¥ {{ fmtMoney(Math.abs(balanceCents)) }}
          </div>
        </div>
      </el-col>
    </el-row>

    <div v-loading="loading" class="card" style="margin-top: 16px">
      <div class="card-title">支出分类占比</div>
      <template v-if="categoryStats.length > 0">
        <div v-for="c in categoryStats" :key="c.parent" class="cat-row">
          <span class="cat-icon">{{ expenseIcon(c.parent) }}</span>
          <span class="cat-name">{{ c.parent }}</span>
          <el-progress
            class="cat-bar"
            :percentage="percentOf(c)"
            :show-text="false"
            :stroke-width="6"
            color="#409EFF"
          />
          <span class="cat-amount">¥ {{ fmtMoney(c.totalCents) }}</span>
          <span class="cat-percent">{{ percentOf(c).toFixed(1) }}%</span>
        </div>
      </template>
      <el-empty v-else-if="!loading" description="本月还没有支出记录" />
    </div>
  </div>
</template>

<style scoped>
.stat-card {
  text-align: center;
}

.stat-label {
  color: #909399;
  font-size: 14px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  font-variant-numeric: proportional-nums;
}

.stat-value.income {
  color: #67c23a;
}

.stat-value.expense {
  color: #f56c6c;
}

.stat-value.negative {
  color: #f56c6c;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 12px;
}

.cat-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}

.cat-icon {
  font-size: 18px;
  flex-shrink: 0;
  width: 28px;
  text-align: center;
}

.cat-name {
  flex-shrink: 0;
  width: 76px;
  font-size: 14px;
  color: #303133;
}

.cat-bar {
  flex: 1;
  min-width: 0;
}

.cat-amount {
  flex-shrink: 0;
  width: 96px;
  text-align: right;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  font-variant-numeric: tabular-nums;
}

.cat-percent {
  flex-shrink: 0;
  width: 52px;
  text-align: right;
  font-size: 13px;
  color: #909399;
  font-variant-numeric: tabular-nums;
}
</style>
