<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { expenseCategories, incomeCategories } from '../data/categories'

type BillType = 'expense' | 'income'

const type = ref<BillType>('expense')
const amount = ref<number | undefined>(undefined)
const date = ref(new Date())
const expensePath = ref<string[]>([])
const incomeCategory = ref('')
const note = ref('')

const isExpense = computed(() => type.value === 'expense')

const cascaderProps = { value: 'name', label: 'name' }

function handleSave(): void {
  // M3 阶段会接入真实的保存功能
  ElMessage.info('保存功能将在下一阶段（M3）提供，敬请期待')
}
</script>

<template>
  <div class="page">
    <div class="card balance-card">
      <div class="balance-label">本月结余（收入 − 支出）</div>
      <div class="balance-amount">¥ 0.00</div>
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
            :placeholder="isExpense ? '请输入金额' : '请输入金额'"
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

.form-card {
  max-width: 560px;
  margin: 0 auto;
}
</style>
