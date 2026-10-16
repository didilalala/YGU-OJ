<script setup>
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
</script>

<template>
  <el-card shadow="never">
    <template #header>管理后台</template>
    <p>你好，{{ userStore.user?.real_name || userStore.user?.username }}。</p>
    <!-- TODO(M11): 本人班级概况、近期作业完成率等统计卡片 -->
  </el-card>
</template>
