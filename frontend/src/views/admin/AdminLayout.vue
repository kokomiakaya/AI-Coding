<template>
  <el-container class="admin-layout">
    <el-aside width="210px" class="admin-aside">
      <div class="admin-logo">
        <el-icon :size="22"><Platform /></el-icon>
        <span>管理后台</span>
      </div>
      <el-menu :default-active="$route.path" router class="admin-menu">
        <el-menu-item index="/admin/kb">
          <el-icon><Collection /></el-icon>知识库管理
        </el-menu-item>
        <el-menu-item index="/admin/users">
          <el-icon><UserFilled /></el-icon>用户管理
        </el-menu-item>
        <el-menu-item index="/admin/stats">
          <el-icon><DataLine /></el-icon>统计看板
        </el-menu-item>
        <el-menu-item index="/admin/config">
          <el-icon><Tools /></el-icon>系统配置
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="admin-header">
        <el-button text @click="$router.push('/chat')">
          <el-icon><Back /></el-icon>&nbsp;返回问答
        </el-button>
        <UserMenu />
      </el-header>
      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import UserMenu from '../../components/UserMenu.vue'
</script>

<style scoped>
.admin-layout {
  height: 100%;
}

.admin-aside {
  background: #1d2333;
  display: flex;
  flex-direction: column;
}

.admin-logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.admin-menu {
  border-right: none;
  background: transparent;
  --el-menu-text-color: #a3a6ad;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.06);
  --el-menu-active-color: #ffffff;
  --el-menu-bg-color: transparent;
}

.admin-menu .el-menu-item {
  background: transparent;
}

.admin-menu .el-menu-item.is-active {
  background: #2a78d6;
}

.admin-header {
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.admin-main {
  background: #f5f7fa;
  padding: 20px;
}
</style>
