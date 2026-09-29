<template>
  <div class="viz-root">
    <!-- KPI 卡片 -->
    <el-row :gutter="16" class="kpi-row">
      <el-col :span="4" v-for="kpi in kpis" :key="kpi.label">
        <el-card shadow="never" class="kpi-card">
          <div class="kpi-value">{{ kpi.value }}</div>
          <div class="kpi-label">{{ kpi.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 消息量趋势 -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-title">问答消息量趋势（近 30 天）</div>
          <div ref="trendChartRef" class="chart-body"></div>
        </el-card>
      </el-col>
      <!-- token 消耗趋势 -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-title">Token 消耗趋势（近 30 天）</div>
          <div ref="tokenChartRef" class="chart-body"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <!-- 反馈统计 -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-title">
            用户反馈（近 30 天）
            <el-tag v-if="feedback.satisfaction_rate != null" size="small" type="success" style="margin-left: 10px">
              满意度 {{ (feedback.satisfaction_rate * 100).toFixed(1) }}%
            </el-tag>
          </div>
          <div ref="feedbackChartRef" class="chart-body"></div>
        </el-card>
      </el-col>
      <!-- 知识库分布 -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <div class="chart-title">各知识库问答量分布</div>
          <div ref="kbChartRef" class="chart-body"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { adminApi, type StatsOverview } from '../../api/admin'

// 参考调色板（dataviz 规范）：分类色固定顺序，单轴，状态色专用
const C = {
  surface: '#fcfcfb',
  textPrimary: '#0b0b0b',
  textSecondary: '#52514e',
  muted: '#898781',
  grid: '#e1e0d9',
  baseline: '#c3c2b7',
  series1: '#2a78d6', // blue
  series2: '#eb6834', // orange
  series3: '#1baf7a', // aqua
  good: '#0ca30c',
  critical: '#d03b3b',
}

const overview = ref<StatsOverview | null>(null)
const feedback = ref<{ likes: number; dislikes: number; satisfaction_rate: number | null; trend: any[] }>({
  likes: 0,
  dislikes: 0,
  satisfaction_rate: null,
  trend: [],
})

const trendChartRef = ref<HTMLElement>()
const tokenChartRef = ref<HTMLElement>()
const feedbackChartRef = ref<HTMLElement>()
const kbChartRef = ref<HTMLElement>()
const charts: echarts.ECharts[] = []

const kpis = computed(() => [
  { label: '注册用户', value: overview.value?.user_count ?? '-' },
  { label: '知识库', value: overview.value?.kb_count ?? '-' },
  { label: '文档 / 分块', value: `${overview.value?.document_count ?? 0} / ${overview.value?.chunk_count ?? 0}` },
  { label: '会话数', value: overview.value?.session_count ?? '-' },
  { label: '问答消息', value: overview.value?.message_count ?? '-' },
  { label: 'Token 消耗', value: overview.value ? formatNum(overview.value.total_tokens) : '-' },
])

function formatNum(n: number): string {
  if (n >= 10000) return `${(n / 10000).toFixed(1)}w`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

const baseAxis = {
  axisLine: { lineStyle: { color: C.baseline } },
  axisLabel: { color: C.muted, fontSize: 11 },
  splitLine: { lineStyle: { color: C.grid } },
}

function initChart(el: HTMLElement | undefined, option: any) {
  if (!el) return
  const chart = echarts.init(el)
  chart.setOption(option)
  charts.push(chart)
}

function resize() {
  charts.forEach((c) => c.resize())
}

onMounted(async () => {
  const [ov, trend, kbStats, fb] = await Promise.all([
    adminApi.statsOverview(),
    adminApi.statsTrend(30),
    adminApi.statsKb(),
    adminApi.statsFeedback(),
  ])
  overview.value = ov
  feedback.value = fb
  window.addEventListener('resize', resize)

  const dates = trend.items.map((d) => d.date.slice(5)) // MM-DD

  // 1. 消息量趋势：单序列折线（标题即图例）
  initChart(trendChartRef.value, {
    tooltip: { trigger: 'axis' },
    grid: { left: 44, right: 16, top: 30, bottom: 28 },
    xAxis: { type: 'category', data: dates, ...baseAxis },
    yAxis: { type: 'value', ...baseAxis, splitLine: { lineStyle: { color: C.grid } } },
    series: [
      {
        name: '消息数',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        data: trend.items.map((d) => d.messages),
        itemStyle: { color: C.series1 },
        lineStyle: { width: 2, color: C.series1 },
        areaStyle: { color: 'rgba(42,120,214,0.08)' },
      },
    ],
  })

  // 2. Token 消耗趋势：单序列折线
  initChart(tokenChartRef.value, {
    tooltip: { trigger: 'axis' },
    grid: { left: 54, right: 16, top: 30, bottom: 28 },
    xAxis: { type: 'category', data: dates, ...baseAxis },
    yAxis: { type: 'value', ...baseAxis, splitLine: { lineStyle: { color: C.grid } } },
    series: [
      {
        name: 'Token',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        data: trend.items.map((d) => d.tokens),
        itemStyle: { color: C.series2 },
        lineStyle: { width: 2, color: C.series2 },
        areaStyle: { color: 'rgba(235,104,52,0.08)' },
      },
    ],
  })

  // 3. 反馈柱状：双序列（赞/踩），图例 + 直接标注
  initChart(feedbackChartRef.value, {
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['有帮助', '不准确'],
      top: 0,
      textStyle: { color: C.textSecondary, fontSize: 12 },
      itemWidth: 14,
    },
    grid: { left: 44, right: 16, top: 34, bottom: 28 },
    xAxis: { type: 'category', data: fb.trend.map((d) => d.date.slice(5)), ...baseAxis },
    yAxis: { type: 'value', minInterval: 1, ...baseAxis, splitLine: { lineStyle: { color: C.grid } } },
    series: [
      {
        name: '有帮助',
        type: 'bar',
        barMaxWidth: 16,
        data: fb.trend.map((d) => d.likes),
        itemStyle: { color: C.series3, borderRadius: [3, 3, 0, 0] },
        label: {
          show: fb.trend.length <= 7,
          position: 'top',
          fontSize: 10,
          color: C.textSecondary,
        },
      },
      {
        name: '不准确',
        type: 'bar',
        barMaxWidth: 16,
        data: fb.trend.map((d) => d.dislikes),
        itemStyle: { color: C.series2, borderRadius: [3, 3, 0, 0] },
        label: {
          show: fb.trend.length <= 7,
          position: 'top',
          fontSize: 10,
          color: C.textSecondary,
        },
      },
    ],
  })

  // 4. 知识库问答量：横向条形图（中文长名称可读性好）
  const kbNames = kbStats.map((k) => k.name)
  const kbAnswers = kbStats.map((k) => k.answer_count)
  initChart(kbChartRef.value, {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 90, right: 40, top: 16, bottom: 28 },
    xAxis: { type: 'value', minInterval: 1, ...baseAxis, splitLine: { lineStyle: { color: C.grid } } },
    yAxis: { type: 'category', data: kbNames, ...baseAxis },
    series: [
      {
        name: '问答数',
        type: 'bar',
        barMaxWidth: 18,
        data: kbAnswers,
        itemStyle: { color: C.series1, borderRadius: [0, 3, 3, 0] },
        label: { show: true, position: 'right', fontSize: 11, color: C.textSecondary },
      },
    ],
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  charts.forEach((c) => c.dispose())
})
</script>

<style scoped>
.viz-root {
  --surface-1: #fcfcfb;
  color-scheme: light;
}

.kpi-row {
  margin-bottom: 16px;
}

.kpi-card {
  text-align: center;
  background: #fcfcfb;
}

.kpi-value {
  font-size: 24px;
  font-weight: 700;
  color: #0b0b0b;
  font-variant-numeric: tabular-nums;
}

.kpi-label {
  margin-top: 4px;
  font-size: 12px;
  color: #898781;
}

.chart-card {
  background: #fcfcfb;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.chart-body {
  height: 280px;
}
</style>
