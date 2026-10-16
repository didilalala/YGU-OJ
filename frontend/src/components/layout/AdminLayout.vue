<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Collection,
  DataAnalysis,
  Document,
  EditPen,
  Monitor,
  Notebook,
  Odometer,
  School,
  Setting,
} from '@element-plus/icons-vue'

import { useUserStore } from '@/stores/user'
import { ROLES, ROLE_LABELS } from '@/utils/constants'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 后台菜单：roles 为空表示教师和管理员都可见
const menus = [
  { path: '/admin', title: '仪表盘', icon: Odometer },
  { path: '/admin/problems', title: '题库', icon: Document },
  { path: '/admin/knowledge-points', title: '知识点', icon: Collection },
  { path: '/admin/classes', title: '班级', icon: School },
  { path: '/admin/assignments', title: '作业', icon: Notebook },
  { path: '/admin/exams', title: '考试', icon: EditPen },
  { path: '/admin/stats', title: '统计', icon: DataAnalysis },
  { path: '/admin/judge-servers', title: '判题服务器', icon: Monitor, roles: [ROLES.ADMIN] },
  { path: '/admin/languages', title: '支持语言', icon: Collection, roles: [ROLES.ADMIN] },
  { path: '/admin/settings', title: '网站参数', icon: Setting, roles: [ROLES.ADMIN] },
  // TODO: 用户管理、系统配置（roles: [ROLES.ADMIN]）
]

// /admin/problems/12/edit 等子页面高亮所属菜单
const activeMenu = computed(() => route.path.split('/').slice(0, 3).join('/'))

const visibleMenus = computed(() =>
  menus.filter((item) => !item.roles || item.roles.includes(userStore.role)),
)

function logout() {
  userStore.logout()
  router.push({ name: 'home' })
}
</script>

<template>
  <el-container class="admin-layout">
    <el-aside width="220px" class="admin-aside">
      <router-link to="/admin" class="admin-logo">
        <span class="admin-logo__mark">YGU</span> OJ 管理后台
      </router-link>
      <el-menu router :default-active="activeMenu" class="admin-menu">
        <el-menu-item v-for="item in visibleMenus" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <router-link to="/">返回前台</router-link>
        <span class="admin-header__user">
          {{ userStore.user?.real_name || userStore.user?.username }}（{{ ROLE_LABELS[userStore.role] }}）
          <el-button link type="primary" @click="logout">退出</el-button>
        </span>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin-layout {
  min-height: 100vh;
}

.admin-aside {
  background: var(--oj-brand-navy);
}

.admin-logo {
  display: block;
  padding: 18px 20px;
  color: #fff;
  font-weight: 600;
  text-decoration: none;
}

.admin-logo__mark {
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--oj-brand-orange);
}

.admin-menu {
  border-right: none;
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.1);
  --el-menu-text-color: rgba(255, 255, 255, 0.8);
  --el-menu-active-color: #fff;
}

.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid var(--el-border-color-light);
}

.admin-header a {
  color: var(--el-color-primary);
  text-decoration: none;
}
</style>
