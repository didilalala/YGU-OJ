<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { authApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)
const form = reactive({ old_password: '', new_password: '', confirm: '' })
const rules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '新密码至少 8 位', trigger: 'blur' },
  ],
  confirm: [
    {
      validator: (_, value, callback) =>
        value === form.new_password ? callback() : callback(new Error('两次输入的密码不一致')),
      trigger: 'blur',
    },
  ],
}

async function submit() {
  if (!(await formRef.value.validate().catch(() => false))) return
  loading.value = true
  try {
    await authApi.changePassword({ old_password: form.old_password, new_password: form.new_password })
    await userStore.fetchMe()
    ElMessage.success('密码已修改')
    router.replace('/')
  } catch {
    // 错误提示已由请求拦截器弹出
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <div class="auth-head">
      <h2>修改密码</h2>
      <p v-if="!userStore.mustChangePassword">定期更换密码可以保护你的账号安全。</p>
    </div>
    <el-alert
      v-if="userStore.mustChangePassword"
      type="warning"
      :closable="false"
      show-icon
      title="你仍在使用初始密码，请先修改密码后再继续使用。"
      class="alert"
    />
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large" @submit.prevent="submit">
      <el-form-item label="原密码" prop="old_password">
        <el-input v-model="form.old_password" type="password" show-password autocomplete="current-password" />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="form.new_password" type="password" show-password autocomplete="new-password" placeholder="至少 8 位" />
      </el-form-item>
      <el-form-item label="确认新密码" prop="confirm">
        <el-input v-model="form.confirm" type="password" show-password autocomplete="new-password" />
      </el-form-item>
      <el-button type="primary" native-type="submit" :loading="loading" class="auth-submit">保存</el-button>
    </el-form>
    <p v-if="!userStore.mustChangePassword" class="auth-foot"><router-link to="/">返回首页</router-link></p>
  </div>
</template>

<style scoped>
.auth-head h2 {
  margin: 0 0 6px;
  font-size: var(--oj-fs-xl);
  letter-spacing: -0.01em;
}

.auth-head p {
  margin: 0 0 var(--oj-space-5);
  color: var(--oj-text-3);
}

.auth-submit {
  width: 100%;
  margin-top: 4px;
}

.auth-foot {
  margin: var(--oj-space-5) 0 0;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-sm);
  text-align: center;
}

.auth-foot a {
  font-weight: 600;
}

.auth-hint {
  margin-top: var(--oj-space-4);
  padding: 10px 12px;
  border-radius: var(--oj-radius-sm);
  background: var(--oj-surface-hover);
  color: var(--oj-text-2);
  font-size: var(--oj-fs-sm);
}

.alert {
  margin-bottom: var(--oj-space-4);
}
</style>
