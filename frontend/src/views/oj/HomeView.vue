<script setup>
import { computed } from 'vue'

import { useSiteStore } from '@/stores/site'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const site = useSiteStore()
const announcement = computed(() => site.settings.home_announcement?.trim() ?? '')
</script>

<template>
  <section class="banner">
    <h1>{{ site.settings.site_name }}</h1>
    <p>支持 {{ site.languages.map((lang) => lang.name).join('、') }} 在线提交与自动评测</p>
  </section>

  <el-card shadow="never">
    <template #header>公告</template>
    <!-- TODO(M2): 公告列表，目前只有管理员设置的一条首页公告 -->
    <p v-if="announcement" class="announcement">{{ announcement }}</p>
    <el-empty v-else description="暂无公告" />
  </el-card>

  <p v-if="userStore.user" class="welcome">欢迎回来，{{ userStore.user.real_name || userStore.user.username }}</p>
</template>

<style scoped>
.announcement {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.7;
}

.banner {
  margin-bottom: 24px;
  padding: 40px 32px;
  border-radius: 8px;
  border-left: 6px solid var(--oj-brand-orange);
  background: var(--oj-brand-navy);
  color: #fff;
}

.banner h1 {
  margin: 0 0 8px;
  font-size: 28px;
}

.banner p {
  margin: 0;
  opacity: 0.85;
}

.welcome {
  color: var(--el-text-color-secondary);
}
</style>
