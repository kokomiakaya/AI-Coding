<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'
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

// ---------- 饼图 ----------
// 饼图最多展示 5 个分类 + 1 块「其他」，防止分类过多时颜色混在一起看不清；
// 完整的分类明细由下方的条形列表承担
const PIE_COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300']
const OTHER_COLOR = '#b8b6ae'
const MAX_SLICES = 5

const pieData = computed<CategoryStat[]>(() => {
  const sorted = [...categoryStats.value].sort((a, b) => b.totalCents - a.totalCents)
  if (sorted.length <= MAX_SLICES + 1) return sorted
  const top = sorted.slice(0, MAX_SLICES)
  const rest = sorted
    .slice(MAX_SLICES)
    .reduce((s, c) => s + c.totalCents, 0)
  return [...top, { parent: '其他', totalCents: rest }]
})

const pieRef = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

function pieColorAt(index: number, parent: string): string {
  return parent === '其他' ? OTHER_COLOR : PIE_COLORS[index]
}

function renderPie(): void {
  if (!chart) return
  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (p: { name: string; value: number; percent: number }) =>
        `${p.name}<br/>¥ ${fmtMoney(p.value)} · ${p.percent}%`
    },
    series: [
      {
        type: 'pie',
        radius: ['58%', '78%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderColor: '#ffffff',
          borderWidth: 2
        },
        label: {
          formatter: '{d}%',
          color: '#606266',
          fontSize: 12
        },
        labelLayout: { hideOverlap: true },
        data: pieData.value.map((c, i) => ({
          name: c.parent,
          value: c.totalCents,
          itemStyle: { color: pieColorAt(i, c.parent) }
        }))
      }
    ]
  })
}

onMounted(loadStats)
watch(month, loadStats)

// 饼图容器在有数据时才渲染（v-if），所以在容器出现/消失时初始化/释放图表
watch(pieRef, (el) => {
  if (!el) {
    resizeObserver?.disconnect()
    resizeObserver = null
    chart?.dispose()
    chart = null
    return
  }
  if (!chart) {
    chart = echarts.init(el)
    renderPie()
    resizeObserver = new ResizeObserver(() => chart?.resize())
    resizeObserver.observe(el)
  }
})

watch(pieData, renderPie)

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
  chart = null
})
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

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="10">
        <div v-loading="loading" class="card pie-card">
          <div class="card-title">支出构成</div>
          <template v-if="categoryStats.length > 0">
            <div class="pie-wrap">
              <div ref="pieRef" class="pie-chart"></div>
              <div class="pie-center">
                <div class="pie-center-label">本月总支出</div>
                <div class="pie-center-value">¥ {{ fmtMoney(summary.expenseCents) }}</div>
              </div>
            </div>
            <div class="pie-legend">
              <div v-for="(item, i) in pieData" :key="item.parent" class="legend-row">
                <span
                  class="legend-swatch"
                  :style="{ backgroundColor: pieColorAt(i, item.parent) }"
                ></span>
                <span class="legend-emoji">{{ item.parent === '其他' ? '📦' : expenseIcon(item.parent) }}</span>
                <span class="legend-name">{{ item.parent }}</span>
                <span class="legend-amount">¥ {{ fmtMoney(item.totalCents) }}</span>
                <span class="legend-pct">{{ percentOf(item).toFixed(1) }}%</span>
              </div>
            </div>
          </template>
          <el-empty v-else-if="!loading" description="本月还没有支出记录" />
        </div>
      </el-col>

      <el-col :span="14">
        <div v-loading="loading" class="card">
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
      </el-col>
    </el-row>
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

/* 饼图 */
.pie-wrap {
  position: relative;
}

.pie-chart {
  width: 100%;
  height: 260px;
}

.pie-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  pointer-events: none;
}

.pie-center-label {
  color: #909399;
  font-size: 13px;
}

.pie-center-value {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin-top: 4px;
  font-variant-numeric: proportional-nums;
}

.pie-legend {
  margin-top: 8px;
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  font-size: 13px;
}

.legend-swatch {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  flex-shrink: 0;
}

.legend-emoji {
  font-size: 14px;
  flex-shrink: 0;
}

.legend-name {
  flex: 1;
  min-width: 0;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.legend-amount {
  flex-shrink: 0;
  color: #606266;
  font-variant-numeric: tabular-nums;
}

.legend-pct {
  flex-shrink: 0;
  width: 48px;
  text-align: right;
  color: #909399;
  font-variant-numeric: tabular-nums;
}

/* 条形列表 */
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
