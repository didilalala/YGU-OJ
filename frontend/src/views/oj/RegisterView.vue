<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { authApi } from '@/api/auth'
import { useSiteStore } from '@/stores/site'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const site = useSiteStore()

const formRef = ref()
const loading = ref(false)
const form = reactive({ username: '', email: '', password: '', confirm: '' })
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    // 纯数字的是学号，留给在校学生绑定使用
    { pattern: /^\D+$|^\d*\D.*$/, message: '用户名不能是纯数字学号，学号请在绑定学号时使用', trigger: 'blur' },
    {
      pattern: /^[A-Za-z][A-Za-z0-9_]{2,31}$/,
      message: '以字母开头，只能包含字母、数字和下划线，长度 3–32 位',
      trigger: 'blur',
    },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
  confirm: [
    {
      validator: (_, value, callback) => (value === form.password ? callback() : callback(new Error('两次输入的密码不一致'))),
      trigger: 'blur',
    },
  ],
}

async function submit() {
  if (!(await formRef.value.validate().catch(() => false))) return
  loading.value = true
  try {
    const data = await authApi.register({ username: form.username, email: form.email, password: form.password })
    userStore.setSession(data)
    ElMessage.success('注册成功，欢迎加入！')
    router.replace(route.query.redirect || '/')
  } catch {
    // 用户名或邮箱已被使用等提示已由请求拦截器弹出
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <el-result v-if="!site.settings.allow_registration" icon="info" title="注册已关闭" sub-title="如需账号请联系任课教师。">
    <template #extra>
      <el-button type="primary" @click="router.push({ name: 'login' })">去登录</el-button>
    </template>
  </el-result>

  <div v-else>
    <div class="auth-head">
      <h2>创建账号</h2>
      <p>注册后即可参加公开竞赛、练习题目。</p>
    </div>
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large" @submit.prevent="submit">
      <el-form-item label="用户名" prop="username">
        <el-input v-model="form.username" maxlength="32" autocomplete="username" placeholder="用于登录，不能是纯数字学号" />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="form.email" maxlength="254" autocomplete="email" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input v-model="form.password" type="password" show-password autocomplete="new-password" placeholder="至少 8 位" />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirm">
        <el-input v-model="form.confirm" type="password" show-password autocomplete="new-password" />
      </el-form-item>
      <el-button type="primary" native-type="submit" :loading="loading" class="auth-submit">注册</el-button>
    </el-form>
    <p class="auth-hint">在校学生请先注册，登录后在右上角菜单中选择「绑定学号」。</p>
    <p class="auth-foot">
      已有账号？
      <router-link :to="{ name: 'login', query: route.query.redirect ? { redirect: route.query.redirect } : {} }">
        去登录
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
