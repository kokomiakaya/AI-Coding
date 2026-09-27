<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { expenseCategories, incomeCategories } from '../data/categories'
import type { BillInput, MonthSummary } from '../../../shared/types'

type BillType = 'expense' | 'income'

const type = ref<BillType>('expense')
const amount = ref<number | undefined>(undefined)
const date = ref(new Date())
const expensePath = ref<string[]>([])
const incomeCategory = ref('')
const note = ref('')
const saving = ref(false)

const summary = ref<MonthSummary>({ incomeCents: 0, expenseCents: 0 })

const isExpense = computed(() => type.value === 'expense')

const balanceCents = computed(() => summary.value.incomeCents - summary.value.expenseCents)
const balanceText = computed(() => {
  const sign = balanceCents.value < 0 ? '-' : ''
  return `${sign}¥ ${(Math.abs(balanceCents.value) / 100).toFixed(2)}`
})

const cascaderProps = { value: 'name', label: 'name' }

function formatDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function currentYearMonth(): string {
  return formatDate(new Date()).slice(0, 7)
}

async function refreshSummary(): Promise<void> {
  const res = await window.api.getMonthSummary(currentYearMonth())
  if (res.ok && res.summary) summary.value = res.summary
}

onMounted(refreshSummary)

async function handleSave(): Promise<void> {
  if (!amount.value || amount.value <= 0) {
    ElMessage.warning('请先输入金额')
    return
  }
  if (isExpense.value && expensePath.value.length !== 2) {
    ElMessage.warning('请选择支出分类（先选大类，再选小类）')
    return
  }
  if (!isExpense.value && !incomeCategory.value) {
    ElMessage.warning('请选择收入分类')
    return
  }

  const bill: BillInput = {
    type: type.value,
    amountCents: Math.round(amount.value * 100),
    date: formatDate(date.value),
    categoryParent: isExpense.value ? expensePath.value[0] : '',
    category: isExpense.value ? expensePath.value[1] : incomeCategory.value,
    note: note.value.trim()
  }

  saving.value = true
  try {
    const res = await window.api.addBill(bill)
    if (res.ok) {
      ElMessage.success(isExpense.value ? '支出已记录 ✅' : '收入已记录 ✅')
      // 保存成功后清空表单，方便记下一笔
      amount.value = undefined
      expensePath.value = []
      incomeCategory.value = ''
      note.value = ''
      date.value = new Date()
      refreshSummary()
    } else {
      ElMessage.error(`保存失败：${res.error ?? '未知错误'}`)
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="card balance-card">
      <div class="balance-label">本月结余（收入 − 支出）</div>
      <div class="balance-amount" :class="{ negative: balanceCents < 0 }">{{ balanceText }}</div>
    </div>

    <div class="card form-card">
      <el-form label-position="top">
        <el-form-item label="类型">
          <el-radio-group v-model="type">
            <el-radio-button value="expense">支出</el-radio-button>
            <el-radio-button value="income">收入</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item :label="isExpense ? '花了多少钱（元）' : '收到多少钱（元）'">
          <el-input-number
            v-model="amount"
            :min="0"
            :precision="2"
            :controls="false"
            placeholder="请输入金额"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="日期">
          <el-date-picker v-model="date" type="date" :clearable="false" style="width: 100%" />
        </el-form-item>

        <el-form-item :label="isExpense ? '支出分类' : '收入分类'">
          <el-cascader
            v-if="isExpense"
            v-model="expensePath"
            :options="expenseCategories"
            :props="cascaderProps"
            :show-all-levels="false"
            separator=" / "
            placeholder="先选大类，再选小类"
            style="width: 100%"
          />
          <el-select
            v-else
            v-model="incomeCategory"
            placeholder="请选择收入分类"
            style="width: 100%"
          >
            <el-option
              v-for="c in incomeCategories"
              :key="c"
              :label="c"
              :value="c"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="备注（可选）">
          <el-input
            v-model="note"
            type="textarea"
            :rows="2"
            maxlength="50"
            show-word-limit
            placeholder="记一笔，例如：和同事聚餐"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          style="width: 100%"
          :loading="saving"
          @click="handleSave"
        >
          保存账单
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.balance-card {
  margin-bottom: 16px;
  text-align: center;
}

.balance-label {
  color: #909399;
  font-size: 14px;
  margin-bottom: 8px;
}

.balance-amount {
  font-size: 36px;
  font-weight: 700;
  color: #303133;
}

.balance-amount.negative {
  color: #f56c6c;
}

.form-card {
  max-width: 560px;
  margin: 0 auto;
}
</style>
