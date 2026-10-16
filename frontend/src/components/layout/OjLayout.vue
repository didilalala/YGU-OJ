<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Menu, Search } from '@element-plus/icons-vue'

import BrandLogo from '@/components/layout/BrandLogo.vue'
import GlobalSearch from '@/components/layout/GlobalSearch.vue'
import ThemeToggle from '@/components/layout/ThemeToggle.vue'
import Countdown from '@/components/ui/Countdown.vue'
import { useExamStore } from '@/stores/exam'
import { useSiteStore } from '@/stores/site'
import { useUserStore } from '@/stores/user'
import { ROLES, ROLE_LABELS } from '@/utils/constants'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const examStore = useExamStore()
const site = useSiteStore()

const isStudent = computed(() => userStore.role === ROLES.STUDENT)
const displayName = computed(() => userStore.user?.real_name || userStore.user?.username || '')
const initial = computed(() => displayName.value.slice(0, 1).toUpperCase())

// 学生的考试提醒：每分钟刷新一次进行中的考试
let poll = null
function refreshExam() {
  if (isStudent.value) examStore.refresh({ force: true })
}
onMounted(() => {
  refreshExam()
  poll = setInterval(refreshExam, 60 * 1000)
  window.addEventListener('keydown', onHotkey)
})
onBeforeUnmount(() => {
  clearInterval(poll)
  window.removeEventListener('keydown', onHotkey)
})
watch(() => userStore.role, refreshExam)

// 考试模式：学生正在考试，且在考场或考试题目页时，换成精简的考试顶栏
const examMode = computed(
  () => !!examStore.active && isStudent.value && ['exam-detail', 'problem-detail'].includes(route.name),
)
// 做题页铺满整个视口，不加页面内边距
const bleed = computed(() => !!route.meta.bleed)

// /problems/12 等子页面也高亮「题库」
const section = computed(() => route.path.split('/')[1] || '')
const LEARN_SECTIONS = ['assignments', 'exams', 'scores', 'classes']
const learnLinks = [
  { to: '/assignments', text: '我的作业', hideInExam: true },
  { to: '/exams', text: '我的考试' },
  { to: '/scores', text: '我的成绩', hideInExam: true },
  { to: '/classes', text: '我的班级' },
]
const visibleLearn = computed(() => learnLinks.filter((l) => !(l.hideInExam && examStore.active)))

const navItems = computed(() => {
  const items = [{ to: '/', text: '首页', key: '' }]
  // 考试期间题库被锁定，不显示入口
  if (!examStore.active) items.push({ to: '/problems', text: '题库', key: 'problems' })
  items.push({ to: '/contests', text: '竞赛', key: 'contests' })
  if (userStore.isLoggedIn) items.push({ to: '/submissions', text: '提交记录', key: 'submissions' })
  return items
})

const searchVisible = ref(false)
const drawerVisible = ref(false)
function onHotkey(event) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    if (!examStore.active) searchVisible.value = true
  }
}
watch(() => route.fullPath, () => (drawerVisible.value = false))

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
  <div class="oj-layout" :class="{ 'oj-layout--bleed': bleed }">
    <!-- 考试模式的顶栏 -->
    <header v-if="examMode" class="oj-header oj-header--exam">
      <div class="oj-header__inner">
        <BrandLogo text="考试中" />
        <span class="exam-title">{{ examStore.active.title }}</span>
        <span class="spacer" />
        <router-link
          v-if="route.name !== 'exam-detail'"
          :to="{ name: 'exam-detail', params: { id: examStore.active.id } }"
          class="exam-back"
        >
          返回考场
        </router-link>
        <span class="exam-clock">
          剩余
          <Countdown :end="examStore.active.end_time" @finish="examStore.clear()" />
        </span>
        <ThemeToggle />
      </div>
    </header>

    <header v-else class="oj-header">
      <div class="oj-header__inner">
        <el-button class="oj-burger" :icon="Menu" text aria-label="打开菜单" @click="drawerVisible = true" />
        <BrandLogo />

        <nav class="oj-nav" aria-label="主导航">
          <router-link
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="oj-nav__item"
            :class="{ 'is-active': section === item.key }"
          >
            {{ item.text }}
          </router-link>
          <el-dropdown v-if="isStudent" trigger="hover" @command="(to) => router.push(to)">
            <span class="oj-nav__item oj-nav__item--menu" :class="{ 'is-active': LEARN_SECTIONS.includes(section) }">
              学习中心 <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="l in visibleLearn" :key="l.to" :command="l.to">{{ l.text }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </nav>

        <span class="spacer" />

        <button v-if="!examStore.active" class="oj-search" type="button" @click="searchVisible = true">
          <el-icon><Search /></el-icon>
          <span class="oj-search__text">搜索题目</span>
          <kbd>Ctrl K</kbd>
        </button>

        <ThemeToggle />

        <el-dropdown v-if="userStore.user" @command="onCommand">
          <button class="oj-user" type="button">
            <span class="oj-user__avatar">{{ initial }}</span>
            <span class="oj-user__name">{{ displayName }}</span>
            <el-icon class="oj-user__caret"><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <div class="oj-user__card">
                <strong>{{ displayName }}</strong>
                <span>{{ ROLE_LABELS[userStore.role] }}</span>
              </div>
              <el-dropdown-item v-if="userStore.isStaff" command="admin-dashboard" divided>管理后台</el-dropdown-item>
              <el-dropdown-item command="profile" :divided="!userStore.isStaff">个人主页</el-dropdown-item>
              <el-dropdown-item v-if="userStore.role === ROLES.REGULAR" command="bind-student">绑定学号</el-dropdown-item>
              <el-dropdown-item command="change-password">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <template v-else>
          <el-button class="oj-login" @click="router.push({ name: 'login' })">登录</el-button>
          <el-button
            v-if="site.settings.allow_registration"
            class="oj-register"
            type="primary"
            @click="router.push({ name: 'register' })"
          >
            注册
          </el-button>
        </template>
      </div>
    </header>

    <div v-if="examStore.active && !examMode" class="exam-banner" role="status">
      <span class="exam-banner__dot" />
      考试「{{ examStore.active.title }}」进行中，剩余
      <Countdown :end="examStore.active.end_time" @finish="examStore.clear()" />
      <router-link :to="{ name: 'exam-detail', params: { id: examStore.active.id } }">进入考场 →</router-link>
    </div>

    <main :class="bleed ? 'oj-main--bleed' : 'oj-container'">
      <router-view />
    </main>

    <footer v-if="!bleed && !examMode" class="oj-footer">
      <span>{{ site.settings.site_name }}</span>
      <span>YGU Online Judge</span>
    </footer>

    <GlobalSearch v-model="searchVisible" />

    <el-drawer v-model="drawerVisible" direction="ltr" size="260px" :with-header="false">
      <BrandLogo class="drawer-logo" />
      <nav class="drawer-nav">
        <router-link v-for="item in navItems" :key="item.to" :to="item.to" :class="{ 'is-active': section === item.key }">
          {{ item.text }}
        </router-link>
        <template v-if="isStudent">
          <div class="drawer-nav__group">学习中心</div>
          <router-link v-for="l in visibleLearn" :key="l.to" :to="l.to">{{ l.text }}</router-link>
        </template>
        <a v-if="!examStore.active" href="#" @click.prevent="(drawerVisible = false), (searchVisible = true)">搜索题目</a>
      </nav>
    </el-drawer>
  </div>
</template>

<style scoped>
.oj-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.oj-layout--bleed {
  height: 100vh;
  overflow: hidden;
}

.oj-header {
  position: sticky;
  top: 0;
  z-index: 100;
  flex-shrink: 0;
  height: var(--oj-header-height);
  border-bottom: 1px solid var(--oj-border);
  background: var(--oj-header-bg);
  backdrop-filter: saturate(180%) blur(12px);
}

.oj-header--exam {
  border-bottom: 2px solid var(--oj-brand-orange);
}

.oj-header__inner {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: var(--oj-content-width);
  height: 100%;
  margin: 0 auto;
  padding: 0 16px;
}

.oj-layout--bleed .oj-header__inner {
  max-width: none;
}

.spacer {
  flex: 1;
}

.oj-burger {
  display: none;
  margin-left: -8px;
}

.oj-nav {
  display: flex;
  align-items: stretch;
  align-self: stretch;
  gap: 4px;
  margin-left: 24px;
}

.oj-nav__item {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 12px;
  color: var(--oj-text-2);
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition: color 0.15s;
}

.oj-nav__item:hover {
  color: var(--oj-text);
}

.oj-nav__item.is-active {
  color: var(--oj-link);
}

.oj-nav__item.is-active::after {
  position: absolute;
  right: 12px;
  bottom: -1px;
  left: 12px;
  height: 2px;
  border-radius: 2px 2px 0 0;
  background: var(--el-color-primary);
  content: '';
}

.oj-nav :deep(.el-dropdown) {
  display: flex;
  align-items: stretch;
  color: inherit;
}

.oj-search {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--oj-border);
  border-radius: var(--oj-radius-sm);
  background: var(--oj-surface-2);
  color: var(--oj-text-3);
  font: inherit;
  font-size: var(--oj-fs-sm);
  cursor: pointer;
}

.oj-search:hover {
  border-color: var(--oj-border-strong);
}

.oj-search__text {
  min-width: 64px;
  text-align: left;
}

.oj-user {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px 4px 4px;
  border: none;
  border-radius: var(--oj-radius-pill);
  background: transparent;
  color: var(--oj-text);
  font: inherit;
  cursor: pointer;
}

.oj-user:hover {
  background: var(--oj-surface-hover);
}

.oj-user__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--oj-navy-700);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
}

html.dark .oj-user__avatar {
  background: #5a6bd8;
}

.oj-user__name {
  max-width: 96px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.oj-user__caret {
  color: var(--oj-text-3);
}

.oj-user__card {
  display: flex;
  flex-direction: column;
  padding: 6px 16px 8px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-xs);
}

.oj-user__card strong {
  color: var(--oj-text);
  font-size: var(--oj-fs-base);
}

.exam-title {
  margin-left: 12px;
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.exam-clock {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin: 0 8px;
  font-size: var(--oj-fs-md);
  font-weight: 600;
}

.exam-back {
  margin-right: 8px;
  font-weight: 500;
  text-decoration: none;
}

.exam-banner {
  display: flex;
  flex-shrink: 0;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--oj-accent-bg);
  border-bottom: 1px solid var(--oj-accent-border);
  color: var(--oj-accent-text);
  font-size: var(--oj-fs-sm);
}

.exam-banner a {
  font-weight: 600;
  color: inherit;
}

.exam-banner__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--oj-brand-orange);
  animation: pulse 1.6s infinite;
}

@keyframes pulse {
  50% {
    opacity: 0.3;
  }
}

.oj-container {
  flex: 1;
  width: 100%;
}

.oj-main--bleed {
  flex: 1;
  min-height: 0;
}

.oj-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  max-width: var(--oj-content-width);
  width: 100%;
  margin: 0 auto;
  padding: 24px 16px;
  border-top: 1px solid var(--oj-border);
  color: var(--oj-text-3);
  font-size: var(--oj-fs-xs);
}

.drawer-logo {
  margin-bottom: 16px;
}

.drawer-nav {
  display: flex;
  flex-direction: column;
}

.drawer-nav a {
  padding: 12px 8px;
  border-radius: var(--oj-radius-sm);
  color: var(--oj-text);
  text-decoration: none;
}

.drawer-nav a.is-active {
  background: var(--el-color-primary-light-9);
  color: var(--oj-link);
  font-weight: 600;
}

.drawer-nav__group {
  margin: 16px 8px 4px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-xs);
}

@media (max-width: 900px) {
  .oj-burger {
    display: inline-flex;
  }

  .oj-nav,
  .oj-search__text,
  .oj-search kbd,
  .oj-user__name,
  .oj-user__caret {
    display: none;
  }

  .oj-search {
    width: 34px;
    justify-content: center;
    padding: 0;
  }
}

@media (max-width: 480px) {
  .oj-register {
    display: none;
  }
}
</style>
