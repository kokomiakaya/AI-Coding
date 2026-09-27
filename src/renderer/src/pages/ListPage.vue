<script setup lang="ts">
import { ref, computed, onMounted, watch, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  expenseCategories,
  incomeCategories,
  expenseIcon,
  incomeIcon
} from '../data/categories'
import type { BillRecord, BillInput, BillType } from '../../../shared/types'

// ---------- 列表与筛选 ----------
const month = ref(new Date())
const typeFilter = ref<'all' | BillType>('all')
const bills = ref<BillRecord[]>([])
const loading = ref(false)

function formatMonth(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function formatDate(d: Date): string {
  return `${formatMonth(d)}-${String(d.getDate()).padStart(2, '0')}`
}

// 'YYYY-MM-DD' → 本地时区的 Date（避免 UTC 解析导致日期偏移）
function parseDate(s: string): Date {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

async function loadBills(): Promise<void> {
  loading.value = true
  try {
    const res = await window.api.listBills(formatMonth(month.value))
    if (res.ok && res.bills) bills.value = res.bills
  } finally {
    loading.value = false
  }
}

onMounted(loadBills)
watch(month, loadBills)

const filtered = computed(() =>
  typeFilter.value === 'all'
    ? bills.value
    : bills.value.filter((b) => b.type === typeFilter.value)
)

// 按日期分组（数据已按日期倒序）
const groups = computed(() => {
  const map = new Map<string, BillRecord[]>()
  for (const b of filtered.value) {
    const list = map.get(b.date) ?? []
    list.push(b)
    map.set(b.date, list)
  }
  return Array.from(map.entries())
})

const monthExpenseCents = computed(() =>
  bills.value.filter((b) => b.type === 'expense').reduce((s, b) => s + b.amountCents, 0)
)
const monthIncomeCents = computed(() =>
  bills.value.filter((b) => b.type === 'income').reduce((s, b) => s + b.amountCents, 0)
)

function fmtMoney(cents: number): string {
  return (cents / 100).toFixed(2)
}

function iconFor(bill: BillRecord): string {
  return bill.type === 'income' ? incomeIcon : expenseIcon(bill.categoryParent)
}

function labelFor(bill: BillRecord): string {
  return bill.type === 'income' ? bill.category : `${bill.category} · ${bill.categoryParent}`
}

// ---------- 修改 ----------
const editVisible = ref(false)
const editSaving = ref(false)
const editingId = ref<number | null>(null)
const editForm = reactive({
  type: 'expense' as BillType,
  amount: undefined as number | undefined,
  date: new Date(),
  expensePath: [] as string[],
  incomeCategory: '',
  note: ''
})
const cascaderProps = { value: 'name', label: 'name' }

function openEdit(bill: BillRecord): void {
  editingId.value = bill.id
  editForm.type = bill.type
  editForm.amount = bill.amountCents / 100
  editForm.date = parseDate(bill.date)
  editForm.note = bill.note
  if (bill.type === 'expense') {
    editForm.expensePath = [bill.categoryParent, bill.category]
    editForm.incomeCategory = ''
  } else {
    editForm.incomeCategory = bill.category
    editForm.expensePath = []
  }
  editVisible.value = true
}

async function saveEdit(): Promise<void> {
  if (!editForm.amount || editForm.amount <= 0) {
    ElMessage.warning('请先输入金额')
    return
  }
  if (editForm.type === 'expense' && editForm.expensePath.length !== 2) {
    ElMessage.warning('请选择支出分类（先选大类，再选小类）')
    return
  }
  if (editForm.type === 'income' && !editForm.incomeCategory) {
    ElMessage.warning('请选择收入分类')
    return
  }
  const bill: BillInput = {
    type: editForm.type,
    amountCents: Math.round(editForm.amount * 100),
    date: formatDate(editForm.date),
    categoryParent: editForm.type === 'expense' ? editForm.expensePath[0] : '',
    category: editForm.type === 'expense' ? editForm.expensePath[1] : editForm.incomeCategory,
    note: editForm.note.trim()
  }
  editSaving.value = true
  try {
    const res = await window.api.updateBill(editingId.value!, bill)
    if (res.ok) {
      ElMessage.success('已修改 ✅')
      editVisible.value = false
      loadBills()
    } else {
      ElMessage.error(`修改失败：${res.error ?? '未知错误'}`)
    }
  } finally {
    editSaving.value = false
  }
}

// ---------- 删除 ----------
async function removeBill(bill: BillRecord): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定删除这笔${bill.type === 'expense' ? '支出' : '收入'}吗？（${labelFor(bill)} ¥${fmtMoney(bill.amountCents)}）删除后无法恢复`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return // 用户点了取消
  }
  const res = await window.api.deleteBill(bill.id)
  if (res.ok) {
    ElMessage.success('已删除 ✅')
    loadBills()
  } else {
    ElMessage.error(`删除失败：${res.error ?? '未知错误'}`)
  }
}
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>明细</h2>
      <div class="filters">
        <el-radio-group v-model="typeFilter" size="small">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="expense">支出</el-radio-button>
          <el-radio-button value="income">收入</el-radio-button>
        </el-radio-group>
        <el-date-picker
          v-model="month"
          type="month"
          :clearable="false"
          format="YYYY年M月"
          placeholder="选择月份"
          style="width: 150px"
        />
      </div>
    </div>

    <div class="card month-summary">
      本月共记 <b>{{ bills.length }}</b> 笔：支出
      <span class="expense-text">¥{{ fmtMoney(monthExpenseCents) }}</span> · 收入
      <span class="income-text">¥{{ fmtMoney(monthIncomeCents) }}</span>
    </div>

    <div v-loading="loading" class="card list-card">
      <template v-if="groups.length > 0">
        <div v-for="[date, items] in groups" :key="date" class="day-group">
          <div class="day-header">{{ date }} · {{ items.length }} 笔</div>
          <div v-for="bill in items" :key="bill.id" class="bill-row">
            <div class="bill-icon">{{ iconFor(bill) }}</div>
            <div class="bill-info">
              <div class="bill-category">{{ labelFor(bill) }}</div>
              <div v-if="bill.note" class="bill-note">{{ bill.note }}</div>
            </div>
            <div class="bill-amount" :class="bill.type">
              {{ bill.type === 'income' ? '+' : '-' }}¥{{ fmtMoney(bill.amountCents) }}
            </div>
            <div class="bill-actions">
              <el-button link type="primary" size="small" @click="openEdit(bill)">修改</el-button>
              <el-button link type="danger" size="small" @click="removeBill(bill)">删除</el-button>
            </div>
          </div>
        </div>
      </template>
      <el-empty
        v-else-if="!loading"
        description="这个月还没有账单，去「记账」页记一笔吧"
      />
    </div>

    <el-dialog v-model="editVisible" title="修改账单" width="440px">
      <el-form label-position="top">
        <el-form-item label="类型">
          <el-radio-group v-model="editForm.type">
            <el-radio-button value="expense">支出</el-radio-button>
            <el-radio-button value="income">收入</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="editForm.type === 'expense' ? '花了多少钱（元）' : '收到多少钱（元）'">
          <el-input-number
            v-model="editForm.amount"
            :min="0"
            :precision="2"
            :controls="false"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="editForm.date"
            type="date"
            :clearable="false"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item :label="editForm.type === 'expense' ? '支出分类' : '收入分类'">
          <el-cascader
            v-if="editForm.type === 'expense'"
            v-model="editForm.expensePath"
            :options="expenseCategories"
            :props="cascaderProps"
            :show-all-levels="false"
            separator=" / "
            style="width: 100%"
          />
          <el-select
            v-else
            v-model="editForm.incomeCategory"
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
            v-model="editForm.note"
            type="textarea"
            :rows="2"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="saveEdit">保存修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.filters {
  display: flex;
  align-items: center;
  gap: 12px;
}

.month-summary {
  margin-bottom: 16px;
  padding: 14px 24px;
  color: #606266;
  font-size: 14px;
}

.expense-text {
  color: #f56c6c;
  font-weight: 600;
}

.income-text {
  color: #67c23a;
  font-weight: 600;
}

.list-card {
  padding: 8px 24px;
}

.day-group {
  margin: 12px 0;
}

.day-header {
  color: #909399;
  font-size: 13px;
  padding: 8px 4px;
}

.bill-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 4px;
  border-radius: 8px;
}

.bill-row:hover {
  background-color: #f5f7fa;
}

.bill-icon {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background-color: #f0f2f5;
  border-radius: 50%;
}

.bill-info {
  flex: 1;
  min-width: 0;
}

.bill-category {
  font-size: 14px;
  color: #303133;
}

.bill-note {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bill-amount {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  flex-shrink: 0;
}

.bill-amount.income {
  color: #67c23a;
}

.bill-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
</style>
