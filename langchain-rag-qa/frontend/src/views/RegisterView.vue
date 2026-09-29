<template>
  <div class="auth-container">
    <div class="auth-card">
      <h2 style="text-align: center; margin-bottom: 20px">注册账号</h2>
      <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="submit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名（3-50 位）">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="密码（至少 6 位）">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item prop="confirm">
          <el-input v-model="form.confirm" type="password" show-password placeholder="确认密码">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width: 100%" :loading="loading" @click="submit">
            注 册
          </el-button>
        </el-form-item>
      </el-form>
      <div style="text-align: center; font-size: 13px; color: #606266">
        已有账号？
        <el-link type="primary" :underline="false" @click="$router.push({ name: 'login' })">
          返回登录
        </el-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({ username: '', password: '', confirm: '' })
const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度 3-50 位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        value !== form.password ? callback(new Error('两次输入的密码不一致')) : callback()
      },
      trigger: 'blur',
    },
  ],
}

async function submit() {
  const f = formRef.value
  if (!f) return
  await f.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await auth.register(form.username, form.password)
      ElMessage.success('注册成功，正在自动登录…')
      await auth.login(form.username, form.password)
      router.push({ name: 'chat' })
    } catch {
      /* 错误已由拦截器提示 */
    } finally {
      loading.value = false
    }
  })
}
</script>
