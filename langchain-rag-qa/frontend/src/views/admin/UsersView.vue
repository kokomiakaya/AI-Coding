<template>
  <el-card shadow="never">
    <div class="toolbar">
      <div>
        <span class="card-title">用户管理</span>
        <span class="card-sub">共 {{ total }} 个用户；禁用后该用户立即被踢出且无法登录</span>
      </div>
      <div class="filters">
        <el-input
          v-model="keyword"
          placeholder="搜索用户名"
          clearable
          style="width: 200px"
          @input="reload"
          @clear="reload"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="roleFilter" placeholder="角色" clearable style="width: 120px" @change="reload">
          <el-option label="管理员" value="admin" />
          <el-option label="普通用户" value="user" />
        </el-select>
      </div>
    </div>

    <el-table :data="users" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" min-width="140">
        <template #default="{ row }">
          <el-icon v-if="row.role === 'admin'" color="#2a78d6" style="vertical-align: -2px"><UserFilled /></el-icon>
          {{ row.username }}
        </template>
      </el-table-column>
      <el-table-column label="角色" width="110">
        <template #default="{ row }">
          <el-select
            :model-value="row.role"
            size="small"
            :disabled="row.id === auth.user?.id"
            @change="(v: string) => changeRole(row, v)"
          >
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-switch
            :model-value="row.is_active"
            :disabled="row.id === auth.user?.id"
            @change="(v: any) => toggleActive(row, v)"
          />
        </template>
      </el-table-column>
      <el-table-column label="最近登录" width="160">
        <template #default="{ row }">{{ formatDateTime(row.last_login_at) || '从未登录' }}</template>
      </el-table-column>
      <el-table-column label="注册时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > pageSize"
      style="margin-top: 16px; justify-content: flex-end"
      layout="total, prev, pager, next"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      @current-change="onPage"
    />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { adminApi } from '../../api/admin'
import { useAuthStore } from '../../stores/auth'
import type { UserInfo } from '../../stores/auth'
import { formatDateTime } from '../../utils/markdown'

const auth = useAuthStore()
const users = ref<UserInfo[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const keyword = ref('')
const roleFilter = ref('')
const loading = ref(false)

onMounted(reload)

async function reload() {
  loading.value = true
  try {
    const data = await adminApi.listUsers(page.value, pageSize, keyword.value || undefined, roleFilter.value || undefined)
    users.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onPage(p: number) {
  page.value = p
  reload()
}

async function toggleActive(row: UserInfo, value: boolean) {
  try {
    await adminApi.updateUser(row.id, { is_active: value })
    row.is_active = value
    ElMessage.success(value ? '已启用' : '已禁用（该用户将被踢出且无法登录）')
  } catch {
    /* 拦截器已提示 */
  }
}

async function changeRole(row: UserInfo, role: string) {
  try {
    await adminApi.updateUser(row.id, { role })
    row.role = role
    ElMessage.success('角色已更新')
  } catch {
    /* 拦截器已提示 */
  }
}
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.card-sub {
  margin-left: 12px;
  font-size: 12px;
  color: #898781;
}

.filters {
  display: flex;
  gap: 10px;
}
</style>
