<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useSiteStore } from '@/stores/site'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const site = useSiteStore()

const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名、学号或邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function submit() {
  if (!(await formRef.value.validate().catch(() => false))) return
  loading.value = true
  try {
    await userStore.login(form)
    // 仍为初始密码时，路由守卫会转到修改密码页
    router.replace(route.query.redirect || '/')
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
      <h2>登录</h2>
      <p>欢迎回来，继续你的练习。</p>
    </div>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large" @submit.prevent="submit">
      <el-form-item label="账号" prop="username">
        <el-input v-model="form.username" placeholder="用户名 / 学号 / 工号 / 邮箱" autocomplete="username" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input v-model="form.password" type="password" show-password autocomplete="current-password" />
      </el-form-item>
      <el-button type="primary" native-type="submit" :loading="loading" class="auth-submit">登录</el-button>
    </el-form>
    <p class="auth-hint">在校学生的初始密码为学号后六位，首次登录需修改密码。</p>
    <p v-if="site.settings.allow_registration" class="auth-foot">
      还没有账号？
      <router-link :to="{ name: 'register', query: route.query.redirect ? { redirect: route.query.redirect } : {} }">
        立即注册
      </router-link>
    </p>
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
</style>
