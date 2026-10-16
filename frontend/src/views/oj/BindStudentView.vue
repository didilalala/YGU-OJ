<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { authApi } from '@/api/auth'
import PageHeader from '@/components/ui/PageHeader.vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref()
const loading = ref(false)
const form = reactive({ student_no: '', initial_password: '' })
const rules = {
  student_no: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  initial_password: [{ required: true, message: '请输入初始密码（学号后六位）', trigger: 'blur' }],
}

async function submit() {
  if (!(await formRef.value.validate().catch(() => false))) return
  try {
    await ElMessageBox.confirm(
      `绑定后你的账号将成为学号 ${form.student_no} 的在校学生，之后用注册时的用户名或邮箱登录。已有的提交、竞赛与成绩会保留。确定绑定吗？`,
      '绑定学号',
      { type: 'warning', confirmButtonText: '绑定', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  loading.value = true
  try {
    await authApi.bindStudent({ student_no: form.student_no.trim(), initial_password: form.initial_password })
    // 刷新角色与真实姓名，菜单随之变化
    await userStore.fetchMe()
    ElMessage.success('绑定成功，你现在是在校学生了')
    router.replace({ name: 'my-classes' })
  } catch {
    // 学号或初始密码错误、失败次数过多等提示已由请求拦截器弹出
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="bind">
    <PageHeader title="绑定学号" subtitle="把你的账号和学校名单中的学号关联起来" />
    <el-card shadow="never">
      <ol class="bind__steps">
        <li><b>输入学号</b>：仅限任课教师已导入名单的学生。</li>
        <li><b>输入初始密码</b>：学号的初始密码为学号后六位。</li>
        <li><b>完成绑定</b>：账号变为在校学生，可加入班级、完成作业、参加课堂考试；已有的提交和竞赛成绩全部保留。</li>
      </ol>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large" @submit.prevent="submit">
        <el-form-item label="学号" prop="student_no">
          <el-input v-model="form.student_no" maxlength="32" autocomplete="off" />
        </el-form-item>
        <el-form-item label="初始密码" prop="initial_password">
          <el-input v-model="form.initial_password" type="password" show-password maxlength="32" autocomplete="off" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading">绑定学号</el-button>
      </el-form>
      <p class="muted bind__note">连续 5 次输错会临时锁定 10 分钟。</p>
    </el-card>
  </div>
</template>

<style scoped>
.bind {
  max-width: 520px;
  margin: 0 auto;
}

.bind__steps {
  margin: 0 0 var(--oj-space-5);
  padding-left: 20px;
  color: var(--oj-text-2);
  line-height: 1.8;
}

.bind__steps b {
  color: var(--oj-text);
}

.bind__note {
  margin: var(--oj-space-4) 0 0;
  font-size: var(--oj-fs-sm);
}
</style>
