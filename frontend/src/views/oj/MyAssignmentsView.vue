<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { assignmentApi } from '@/api/assignment'
import { ASSIGNMENT_STATUS, formatScore, latePolicy, timeLeft } from '@/utils/assignment'
import { formatDateTime } from '@/utils/judge'

const route = useRoute()
const router = useRouter()

const TABS = [
  { name: 'todo', label: '待完成' },
  { name: 'not_started', label: '未开始' },
  { name: 'ended', label: '已结束' },
]

const tab = computed(() => (TABS.some((t) => t.name === route.query.status) ? route.query.status : 'todo'))
const loading = ref(false)
const assignments = ref([])

async function load() {
  loading.value = true
  try {
    assignments.value = await assignmentApi.mine({ status: tab.value })
  } finally {
    loading.value = false
  }
}

watch(tab, load, { immediate: true })

function deadlineText(item) {
  if (item.status === 'not_started') return `${formatDateTime(item.start_time)} 开始`
  const left = timeLeft(item.end_time)
  if (left) return `距截止还有 ${left}`
  return item.status === 'late' ? `已截止，可迟交（${latePolicy(item).replace('允许迟交，', '')}）` : '已截止'
}

function urgent(item) {
  return item.status === 'in_progress' && new Date(item.end_time).getTime() - Date.now() < 24 * 3600 * 1000
}
</script>

<template>
  <el-card shadow="never">
    <template #header><span class="title">我的作业</span></template>

    <el-tabs :model-value="tab" @update:model-value="(name) => router.replace({ query: { status: name } })">
      <el-tab-pane v-for="item in TABS" :key="item.name" :label="item.label" :name="item.name" />
    </el-tabs>

    <div v-loading="loading" class="list">
      <el-empty v-if="!loading && !assignments.length" :description="tab === 'todo' ? '没有待完成的作业' : '暂无作业'" />
      <router-link
        v-for="item in assignments"
        :key="item.id"
        :to="{ name: 'assignment-detail', params: { id: item.id } }"
        class="assignment"
      >
        <div class="assignment__main">
          <div class="assignment__title">
            {{ item.title }}
            <el-tag :type="ASSIGNMENT_STATUS[item.status].type" size="small">{{ ASSIGNMENT_STATUS[item.status].label }}</el-tag>
          </div>
          <div class="assignment__meta">
            <span>{{ item.class_name }}</span>
            <span>{{ item.problem_count }} 题 · 满分 {{ item.total_score }}</span>
            <span :class="{ urgent: urgent(item) }">{{ deadlineText(item) }}</span>
          </div>
        </div>
        <div v-if="item.status !== 'not_started'" class="assignment__progress">
          <el-progress
            :percentage="item.problem_count ? Math.round((item.my_solved / item.problem_count) * 100) : 0"
            :stroke-width="8"
            :show-text="false"
            :status="item.my_solved === item.problem_count && item.problem_count ? 'success' : ''"
          />
          <div class="assignment__score">
            通过 {{ item.my_solved }}/{{ item.problem_count }} · 得分
            <strong>{{ formatScore(item.my_score) }}</strong>
            <el-tag v-if="item.my_late" type="warning" size="small" effect="plain">含迟交</el-tag>
          </div>
        </div>
      </router-link>
    </div>
  </el-card>
</template>

<style scoped>
.title {
  font-size: 16px;
  font-weight: 600;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 120px;
}

.assignment {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 24px;
  padding: 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-left: 3px solid var(--oj-brand-navy);
  border-radius: 6px;
  background: #fff;
  color: inherit;
  text-decoration: none;
  transition: box-shadow 0.15s;
}

.assignment:hover {
  box-shadow: var(--el-box-shadow-light);
}

.assignment__main {
  flex: 1;
  min-width: 220px;
}

.assignment__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.assignment__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.urgent {
  color: var(--el-color-danger);
}

.assignment__progress {
  width: 240px;
}

.assignment__score {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  color: var(--el-text-color-regular);
  font-size: 13px;
}

@media (max-width: 640px) {
  .assignment__progress {
    width: 100%;
  }
}
</style>
