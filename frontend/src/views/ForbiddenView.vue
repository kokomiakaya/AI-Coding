<template>
  <div class="forbidden">
    <el-result icon="warning" title="403" sub-title="没有权限访问该页面（仅管理员可进入管理后台）">
      <template #extra>
        <el-button type="primary" @click="$router.push({ name: 'chat' })">返回问答</el-button>
      </template>
    </el-result>
  </div>
</template>

<style scoped>
.forbidden {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
