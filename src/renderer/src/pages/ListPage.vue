<script setup lang="ts">
import { ref } from 'vue'

// M4 阶段接入真实账单列表
const month = ref(new Date())
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h2>明细</h2>
      <el-date-picker
        v-model="month"
        type="month"
        :clearable="false"
        format="YYYY年M月"
        placeholder="选择月份"
      />
    </div>

    <div class="card">
      <el-empty description="还没有账单，去「记账」页记一笔吧" />
    </div>
  </div>
</template>
