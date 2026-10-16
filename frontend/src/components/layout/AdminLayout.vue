<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowDown,
  Collection,
  DataAnalysis,
  Document,
  EditPen,
  Expand,
  Fold,
  Menu,
  Monitor,
  Notebook,
  Odometer,
  School,
  Setting,
} from '@element-plus/icons-vue'

import BrandLogo from '@/components/layout/BrandLogo.vue'
import ThemeToggle from '@/components/layout/ThemeToggle.vue'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { useUserStore } from '@/stores/user'
import { ROLES, ROLE_LABELS } from '@/utils/constants'
import { loadLocal, saveLocal } from '@/utils/storage'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isNarrow = useMediaQuery('(max-width: 900px)')

// 后台菜单：roles 为空表示教师和管理员都可见
const groups = [
  {
    title: '教学',
    items: [
      { path: '/admin', title: '仪表盘', icon: Odometer },
      { path: '/admin/problems', title: '题库', icon: Document },
      { path: '/admin/knowledge-points', title: '知识点', icon: Collection },
      { path: '/admin/classes', title: '班级', icon: School },
      { path: '/admin/assignments', title: '作业', icon: Notebook },
      { path: '/admin/exams', title: '考试', icon: EditPen },
      { path: '/admin/stats', title: '统计', icon: DataAnalysis },
    ],
  },
  {
    title: '系统',
    roles: [ROLES.ADMIN],
    items: [
      { path: '/admin/judge-servers', title: '判题服务器', icon: Monitor },
      { path: '/admin/languages', title: '支持语言', icon: Collection },
      { path: '/admin/settings', title: '网站参数', icon: Setting },
    ],
  },
  // TODO: 用户管理
]

const visibleGroups = computed(() => groups.filter((g) => !g.roles || g.roles.includes(userStore.role)))

// /admin/problems/12/edit 等子页面高亮所属菜单
const activeMenu = computed(() => route.path.split('/').slice(0, 3).join('/'))
const currentTitle = computed(() => {
  for (const g of groups) for (const item of g.items) if (item.path === activeMenu.value) return item
  return null
})
// 面包屑：后台 / 一级菜单 /（子页面标题）
const crumbs = computed(() => {
  const list = [{ text: '管理后台', to: '/admin' }]
  if (currentTitle.value && currentTitle.value.path !== '/admin') {
    list.push({ text: currentTitle.value.title, to: route.path === currentTitle.value.path ? undefined : currentTitle.value.path })
    if (route.path !== currentTitle.value.path && route.meta.title) list.push({ text: route.meta.title })
  }
  return list
})

const collapsed = ref(loadLocal('admin-aside-collapsed') === '1')
function toggleCollapse() {
  collapsed.value = !collapsed.value
  saveLocal('admin-aside-collapsed', collapsed.value ? '1' : '0')
}

const drawer = ref(false)
watch(() => route.fullPath, () => (drawer.value = false))

const displayName = computed(() => userStore.user?.real_name || userStore.user?.username || '')

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
  <div class="admin">
    <aside v-if="!isNarrow" class="admin-aside" :class="{ 'admin-aside--collapsed': collapsed }">
      <div class="admin-aside__logo">
        <BrandLogo v-if="!collapsed" text="管理后台" />
        <router-link v-else to="/" class="admin-aside__mark" aria-label="返回前台">YGU</router-link>
      </div>
      <nav class="admin-nav" aria-label="后台导航">
        <template v-for="group in visibleGroups" :key="group.title">
          <div v-if="!collapsed" class="admin-nav__group">{{ group.title }}</div>
          <div v-else class="admin-nav__divider" />
          <el-tooltip
            v-for="item in group.items"
            :key="item.path"
            :content="item.title"
            placement="right"
            :disabled="!collapsed"
          >
            <router-link :to="item.path" class="admin-nav__item" :class="{ 'is-active': activeMenu === item.path }">
              <el-icon :size="18"><component :is="item.icon" /></el-icon>
              <span v-if="!collapsed">{{ item.title }}</span>
            </router-link>
          </el-tooltip>
        </template>
      </nav>
    </aside>

    <div class="admin-body">
      <header class="admin-header">
        <el-button v-if="isNarrow" :icon="Menu" text aria-label="打开菜单" @click="drawer = true" />
        <el-button v-else :icon="collapsed ? Expand : Fold" text :aria-label="collapsed ? '展开侧栏' : '收起侧栏'" @click="toggleCollapse" />
        <el-breadcrumb separator="/" class="admin-header__crumbs">
          <el-breadcrumb-item v-for="c in crumbs" :key="c.text" :to="c.to">{{ c.text }}</el-breadcrumb-item>
        </el-breadcrumb>
        <span class="spacer" />
        <router-link to="/" class="admin-header__back">返回前台</router-link>
        <ThemeToggle />
        <el-dropdown @command="onCommand">
          <button class="admin-user" type="button">
            <span class="admin-user__avatar">{{ displayName.slice(0, 1).toUpperCase() }}</span>
            <span class="admin-user__name">{{ displayName }}</span>
            <el-tag size="small" effect="plain">{{ ROLE_LABELS[userStore.role] }}</el-tag>
            <el-icon><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人主页</el-dropdown-item>
              <el-dropdown-item command="change-password">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>

      <main class="admin-main">
        <router-view />
      </main>
    </div>

    <el-drawer v-model="drawer" direction="ltr" size="260px" :with-header="false">
      <BrandLogo text="管理后台" class="drawer-logo" />
      <nav class="admin-nav admin-nav--drawer">
        <template v-for="group in visibleGroups" :key="group.title">
          <div class="admin-nav__group">{{ group.title }}</div>
          <router-link v-for="item in group.items" :key="item.path" :to="item.path" class="admin-nav__item" :class="{ 'is-active': activeMenu === item.path }">
            <el-icon :size="18"><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </router-link>
        </template>
      </nav>
    </el-drawer>
  </div>
</template>

<style scoped>
.admin {
  display: flex;
  min-height: 100vh;
}

.admin-aside {
  position: sticky;
  top: 0;
  flex-shrink: 0;
  width: var(--oj-admin-aside-width);
  height: 100vh;
  overflow-y: auto;
  border-right: 1px solid var(--oj-border);
  background: var(--oj-surface);
  transition: width 0.2s;
}

.admin-aside--collapsed {
  width: var(--oj-admin-aside-collapsed);
}

.admin-aside__logo {
  display: flex;
  align-items: center;
  justify-content: center;
  height: var(--oj-header-height);
  padding: 0 16px;
  border-bottom: 1px solid var(--oj-border);
}

.admin-aside:not(.admin-aside--collapsed) .admin-aside__logo {
  justify-content: flex-start;
}

.admin-aside__mark {
  padding: 2px 6px;
  border-radius: 6px;
  background: var(--oj-brand-orange-deep);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
}

.admin-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px;
}

.admin-nav__group {
  margin: 12px 8px 4px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-xs);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.admin-nav__group:first-child {
  margin-top: 0;
}

.admin-nav__divider {
  height: 1px;
  margin: 8px 4px;
  background: var(--oj-border);
}

.admin-nav__divider:first-child {
  display: none;
}

.admin-nav__item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 40px;
  padding: 0 12px;
  border-radius: var(--oj-radius-sm);
  color: var(--oj-text-2);
  font-weight: 500;
  text-decoration: none;
}

.admin-aside--collapsed .admin-nav__item {
  justify-content: center;
  padding: 0;
}

.admin-nav__item:hover {
  background: var(--oj-surface-hover);
  color: var(--oj-text);
}

.admin-nav__item.is-active {
  background: var(--el-color-primary-light-9);
  color: var(--oj-link);
}

.admin-nav__item.is-active::before {
  position: absolute;
  top: 10px;
  bottom: 10px;
  left: -12px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--oj-brand-orange);
  content: '';
}

.admin-nav--drawer {
  padding: 0;
}

.admin-nav--drawer .admin-nav__item.is-active::before {
  left: -4px;
}

.admin-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.admin-header {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 8px;
  height: var(--oj-header-height);
  padding: 0 16px;
  border-bottom: 1px solid var(--oj-border);
  background: var(--oj-header-bg);
  backdrop-filter: saturate(180%) blur(12px);
}

.spacer {
  flex: 1;
}

.admin-header__crumbs {
  margin-left: 4px;
}

.admin-header__back {
  margin-right: 4px;
  color: var(--oj-text-2);
  font-size: var(--oj-fs-sm);
  text-decoration: none;
}

.admin-header__back:hover {
  color: var(--oj-link);
}

.admin-user {
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

.admin-user:hover {
  background: var(--oj-surface-hover);
}

.admin-user__avatar {
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

html.dark .admin-user__avatar {
  background: #5a6bd8;
}

.admin-main {
  flex: 1;
  width: 100%;
  max-width: 1400px;
  padding: var(--oj-space-5) var(--oj-space-5) var(--oj-space-7);
  margin: 0 auto;
}

.drawer-logo {
  margin-bottom: 16px;
}

@media (max-width: 900px) {
  .admin-user__name,
  .admin-user :deep(.el-tag),
  .admin-header__back {
    display: none;
  }

  .admin-main {
    padding: var(--oj-space-4);
  }
}
</style>
