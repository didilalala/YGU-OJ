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
  <el-card class="password-card" shadow="never">
    <h2>修改密码</h2>
    <el-alert
      v-if="userStore.mustChangePassword"
      type="warning"
      :closable="false"
      title="你仍在使用初始密码，请先修改密码后再继续使用。"
      class="password-card__alert"
    />
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
      <el-form-item label="原密码" prop="old_password">
        <el-input v-model="form.old_password" type="password" show-password autocomplete="current-password" />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password">
        <el-input v-model="form.new_password" type="password" show-password autocomplete="new-password" />
      </el-form-item>
      <el-form-item label="确认新密码" prop="confirm">
        <el-input v-model="form.confirm" type="password" show-password autocomplete="new-password" />
      </el-form-item>
      <el-button type="primary" native-type="submit" :loading="loading">保存</el-button>
    </el-form>
  </el-card>
</template>

<style scoped>
.password-card {
  max-width: 440px;
  margin: 40px auto;
}

.password-card h2 {
  margin-top: 0;
}

.password-card__alert {
  margin-bottom: 16px;
}
</style>
