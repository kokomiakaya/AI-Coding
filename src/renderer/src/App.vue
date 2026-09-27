<script setup lang="ts">
import { ref, markRaw } from 'vue'
import { Coin, List, PieChart } from '@element-plus/icons-vue'
import RecordPage from './pages/RecordPage.vue'
import ListPage from './pages/ListPage.vue'
import StatsPage from './pages/StatsPage.vue'

const currentPage = ref('record')

const pages = {
  record: markRaw(RecordPage),
  list: markRaw(ListPage),
  stats: markRaw(StatsPage)
}
</script>

<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="app-title">
        <span class="logo">🐴</span>
        <span class="app-name">黑马记账</span>
      </div>
      <el-menu
        :default-active="currentPage"
        class="side-menu"
        @select="(key: string) => (currentPage = key)"
      >
        <el-menu-item index="record">
          <el-icon><Coin /></el-icon>
          <span>记账</span>
        </el-menu-item>
        <el-menu-item index="list">
          <el-icon><List /></el-icon>
          <span>明细</span>
        </el-menu-item>
        <el-menu-item index="stats">
          <el-icon><PieChart /></el-icon>
          <span>统计</span>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer">v0.1 · 数据存于本机</div>
    </aside>
    <main class="content">
      <component :is="pages[currentPage]" />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100%;
}

.sidebar {
  display: flex;
  flex-direction: column;
  width: 200px;
  flex-shrink: 0;
  background-color: #232a35;
  padding: 20px 12px;
}

.app-title {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px 24px;
}

.logo {
  font-size: 26px;
}

.app-name {
  color: #ffffff;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 1px;
}

.side-menu {
  border-right: none;
  flex: 1;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: #c8cdd6;
  --el-menu-active-color: #ffffff;
  --el-menu-hover-bg-color: #2e3644;
}

.side-menu :deep(.el-menu-item.is-active) {
  background-color: #374151;
  border-radius: 8px;
}

.side-menu :deep(.el-menu-item) {
  border-radius: 8px;
  margin-bottom: 4px;
  height: 46px;
}

.sidebar-footer {
  color: #7a8291;
  font-size: 12px;
  text-align: center;
  padding-top: 12px;
}

.content {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}
</style>
