<template>
  <div>
    <el-dropdown @command="onCommand">
      <span class="user-menu-trigger">
        <el-icon><User /></el-icon>
        {{ auth.user?.username }}
        <el-icon><ArrowDown /></el-icon>
      </span>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="password">
            <el-icon><Key /></el-icon>修改密码
          </el-dropdown-item>
          <el-dropdown-item command="logout" divided>
            <el-icon><SwitchButton /></el-icon>退出登录
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="pwdVisible" title="修改密码" width="420px" append-to-body>
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="90px">
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="pwdForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm">
          <el-input v-model="pwdForm.confirm" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitPwd">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const pwdVisible = ref(false)
const saving = ref(false)
const pwdFormRef = ref<FormInstance>()
const pwdForm = reactive({ old_password: '', new_password: '', confirm: '' })
const pwdRules: FormRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        value !== pwdForm.new_password ? callback(new Error('两次输入的密码不一致')) : callback()
      },
      trigger: 'blur',
    },
  ],
}

function onCommand(command: string) {
  if (command === 'password') {
    pwdVisible.value = true
  } else if (command === 'logout') {
    auth.logout()
    router.push({ name: 'login' })
  }
}

async function submitPwd() {
  const form = pwdFormRef.value
  if (!form) return
  await form.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      await auth.changePassword(pwdForm.old_password, pwdForm.new_password)
      ElMessage.success('密码修改成功，请重新登录')
      pwdVisible.value = false
      auth.logout()
      router.push({ name: 'login' })
    } catch {
      /* 错误已由拦截器提示 */
    } finally {
      saving.value = false
    }
  })
}
</script>

<style scoped>
.user-menu-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: #303133;
  font-size: 14px;
  outline: none;
}
</style>
