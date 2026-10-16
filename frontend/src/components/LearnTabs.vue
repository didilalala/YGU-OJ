<script setup>
/** 学习中心的页面标签：作业 / 考试 / 成绩 / 班级。考试期间作业与成绩被锁定，不显示 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { useExamStore } from '@/stores/exam'

const route = useRoute()
const examStore = useExamStore()

const tabs = computed(() =>
  [
    { name: 'my-assignments', text: '我的作业', locked: true },
    { name: 'my-exams', text: '我的考试' },
    { name: 'my-scores', text: '我的成绩', locked: true },
    { name: 'my-classes', text: '我的班级' },
  ].filter((t) => !(t.locked && examStore.active)),
)
</script>

<template>
  <nav class="learn-tabs" aria-label="学习中心">
    <router-link v-for="t in tabs" :key="t.name" :to="{ name: t.name }" :class="{ 'is-active': route.name === t.name }">
      {{ t.text }}
    </router-link>
  </nav>
</template>

<style scoped>
.learn-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: var(--oj-space-5);
  padding: 4px;
  border: 1px solid var(--oj-border);
  border-radius: var(--oj-radius-md);
  background: var(--oj-surface);
  overflow-x: auto;
}

.learn-tabs a {
  flex: 0 0 auto;
  padding: 6px 16px;
  border-radius: var(--oj-radius-sm);
  color: var(--oj-text-2);
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
}

.learn-tabs a:hover {
  background: var(--oj-surface-hover);
}

.learn-tabs a.is-active {
  background: var(--el-color-primary-light-9);
  color: var(--oj-link);
  font-weight: 600;
}
</style>
