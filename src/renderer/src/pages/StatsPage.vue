<template>
  <div class="page">
    <div class="page-header">
      <h2>统计（本月）</h2>
    </div>

    <el-row :gutter="16">
      <el-col :span="8">
        <div class="card stat-card">
          <div class="stat-label">本月收入</div>
          <div class="stat-amount income">¥ 0.00</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card stat-card">
          <div class="stat-label">本月支出</div>
          <div class="stat-amount expense">¥ 0.00</div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="card stat-card">
          <div class="stat-label">本月结余</div>
          <div class="stat-amount">¥ 0.00</div>
        </div>
      </el-col>
    </el-row>

    <div class="card" style="margin-top: 16px">
      <el-empty description="图表统计将在 M5 阶段提供" />
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

.stat-amount {
  font-size: 24px;
  font-weight: 600;
}

.stat-amount.income {
  color: #67c23a;
}

.stat-amount.expense {
  color: #f56c6c;
}
</style>
