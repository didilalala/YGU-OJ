<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useExamStore } from '@/stores/exam'
import { useUserStore } from '@/stores/user'
import { ROLES, ROLE_LABELS } from '@/utils/constants'
import { formatDuration } from '@/utils/exam'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const examStore = useExamStore()

// 学生的考试提醒：每分钟刷新一次进行中的考试，每秒更新倒计时
const now = ref(Date.now())
const examLeft = computed(() =>
  examStore.active ? formatDuration((new Date(examStore.active.end_time).getTime() - now.value) / 1000) : '',
)
let clock = null
let poll = null

function refreshExam() {
  if (userStore.role === ROLES.STUDENT) examStore.refresh({ force: true })
}

onMounted(() => {
  refreshExam()
  clock = setInterval(() => {
    now.value = Date.now()
    if (examStore.active && new Date(examStore.active.end_time).getTime() < now.value) examStore.clear()
  }, 1000)
  poll = setInterval(refreshExam, 60 * 1000)
})
onBeforeUnmount(() => {
  clearInterval(clock)
  clearInterval(poll)
})
watch(() => userStore.role, refreshExam)

// /problems/12 等子页面也高亮「题目」菜单
const activeMenu = computed(() => '/' + (route.path.split('/')[1] || ''))

function onCommand(command) {
  if (command === 'logout') {
    userStore.logout()
    router.push({ name: 'home' })
  } else {
    router.push({ name: command })
  }
}
</script>

<template>
  <div class="oj-layout">
    <header class="oj-header">
      <div class="oj-header__inner">
        <router-link to="/" class="oj-logo">
          <span class="oj-logo__mark">YGU</span>
          <span class="oj-logo__text">Online Judge</span>
        </router-link>

        <!-- 窄屏时放不下的菜单项收进「…」 -->
        <el-menu mode="horizontal" router :default-active="activeMenu" class="oj-nav">
          <el-menu-item index="/">首页</el-menu-item>
          <!-- 考试期间题库与作业被锁定，不显示入口 -->
          <el-menu-item v-if="!examStore.active" index="/problems">题目</el-menu-item>
          <el-menu-item index="/contests">竞赛</el-menu-item>
          <el-menu-item v-if="userStore.isLoggedIn" index="/submissions">提交记录</el-menu-item>
          <el-menu-item v-if="userStore.role === ROLES.STUDENT && !examStore.active" index="/assignments">我的作业</el-menu-item>
          <el-menu-item v-if="userStore.role === ROLES.STUDENT" index="/exams">我的考试</el-menu-item>
          <el-menu-item v-if="userStore.role === ROLES.STUDENT && !examStore.active" index="/scores">我的成绩</el-menu-item>
          <el-menu-item v-if="userStore.role === ROLES.STUDENT" index="/classes">我的班级</el-menu-item>
        </el-menu>

        <div class="oj-header__user">
          <el-dropdown v-if="userStore.user" @command="onCommand">
            <span class="oj-user">
              {{ userStore.user.real_name || userStore.user.username }}
              <el-tag size="small" effect="plain" class="oj-user__role">{{ ROLE_LABELS[userStore.role] }}</el-tag>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="userStore.isStaff" command="admin-dashboard">管理后台</el-dropdown-item>
                <el-dropdown-item command="profile">个人主页</el-dropdown-item>
                <el-dropdown-item v-if="userStore.role === ROLES.REGULAR" command="bind-student">绑定学号</el-dropdown-item>
                <el-dropdown-item command="change-password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button v-else type="primary" plain @click="router.push({ name: 'login' })">登录</el-button>
        </div>
      </div>
    </header>

    <div v-if="examStore.active" class="exam-banner">
      考试「{{ examStore.active.title }}」进行中，剩余 {{ examLeft }}
      <router-link :to="{ name: 'exam-detail', params: { id: examStore.active.id } }">进入考场</router-link>
    </div>

    <main class="oj-container">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.oj-header {
  height: var(--oj-header-height);
  background: var(--oj-brand-navy);
}

.oj-header__inner {
  display: flex;
  align-items: center;
  gap: 24px;
  max-width: var(--oj-content-width);
  height: 100%;
  margin: 0 auto;
  padding: 0 16px;
}

.oj-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}

.oj-logo__mark {
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--oj-brand-orange);
}

.oj-nav {
  flex: 1;
  min-width: 0;
  height: 100%;
  border-bottom: none;
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.1);
  --el-menu-text-color: rgba(255, 255, 255, 0.8);
  --el-menu-active-color: #fff;
}

.exam-banner {
  padding: 8px 16px;
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger-dark-2);
  font-size: 14px;
  text-align: center;
}

.exam-banner a {
  margin-left: 8px;
  color: var(--el-color-danger);
  font-weight: 600;
}

.oj-header__user {
  flex-shrink: 0;
}

.oj-user {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  cursor: pointer;
}

@media (max-width: 640px) {
  .oj-header__inner {
    gap: 8px;
  }

  .oj-logo__text,
  .oj-user__role {
    display: none;
  }

  .oj-nav :deep(.el-menu-item) {
    padding: 0 10px;
  }
}
</style>
