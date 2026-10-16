<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { assignmentApi } from '@/api/assignment'
import LearnTabs from '@/components/LearnTabs.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ProgressRing from '@/components/ui/ProgressRing.vue'
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
  <div>
    <PageHeader title="我的作业" subtitle="按截止时间完成老师布置的练习" />
    <LearnTabs />

    <div class="seg" role="tablist">
      <button
        v-for="item in TABS"
        :key="item.name"
        role="tab"
        :aria-selected="tab === item.name"
        :class="{ 'is-on': tab === item.name }"
        @click="router.replace({ query: { status: item.name } })"
      >
        {{ item.label }}
      </button>
    </div>

    <div class="list">
      <template v-if="loading"><el-skeleton v-for="n in 3" :key="n" animated :rows="2" class="assignment assignment--sk" /></template>
      <EmptyState
        v-else-if="!assignments.length"
        :title="tab === 'todo' ? '没有待完成的作业' : '暂无作业'"
        :description="tab === 'todo' ? '休息一下，或者去题库自己练练手。' : ''"
      >
        <el-button v-if="tab === 'todo'" type="primary" @click="router.push({ name: 'problems' })">去题库</el-button>
      </EmptyState>
      <router-link
        v-for="item in assignments"
        v-else
        :key="item.id"
        :to="{ name: 'assignment-detail', params: { id: item.id } }"
        class="assignment"
        :class="{ 'assignment--urgent': urgent(item) }"
      >
        <ProgressRing :done="item.my_solved" :total="item.problem_count" />
        <div class="assignment__main">
          <div class="assignment__title">
            {{ item.title }}
            <el-tag :type="ASSIGNMENT_STATUS[item.status].type" size="small" effect="plain">{{ ASSIGNMENT_STATUS[item.status].label }}</el-tag>
            <span v-if="urgent(item)" class="assignment__flag">即将截止</span>
          </div>
          <div class="assignment__meta">
            <span>{{ item.class_name }}</span>
            <span>{{ item.problem_count }} 题 · 满分 {{ item.total_score }}</span>
            <span>{{ deadlineText(item) }}</span>
          </div>
        </div>
        <div v-if="item.status !== 'not_started'" class="assignment__score">
          <strong class="num">{{ formatScore(item.my_score) }}</strong>
          <span>得分</span>
          <el-tag v-if="item.my_late" type="warning" size="small" effect="plain">含迟交</el-tag>
        </div>
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.seg {
  display: inline-flex;
  margin-bottom: var(--oj-space-4);
  padding: 3px;
  border-radius: var(--oj-radius-sm);
  background: var(--oj-surface-hover);
}

.seg button {
  height: 30px;
  padding: 0 16px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--oj-text-2);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.seg button.is-on {
  background: var(--oj-surface);
  box-shadow: var(--oj-shadow-sm);
  color: var(--oj-text);
}

.list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.assignment {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border: 1px solid var(--oj-border);
  border-radius: var(--oj-radius-md);
  background: var(--oj-surface);
  color: inherit;
  text-decoration: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.assignment:hover {
  border-color: var(--oj-border-strong);
  box-shadow: var(--oj-shadow-sm);
}

.assignment--urgent {
  border-color: var(--oj-accent-border);
  background: linear-gradient(90deg, var(--oj-accent-bg), var(--oj-surface) 40%);
}

.assignment--sk {
  display: block;
}

.assignment__main {
  flex: 1;
  min-width: 0;
}

.assignment__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: var(--oj-fs-md);
  font-weight: 600;
}

.assignment__flag {
  padding: 0 8px;
  border-radius: var(--oj-radius-pill);
  background: var(--oj-brand-orange-deep);
  color: #fff;
  font-size: var(--oj-fs-xs);
  font-weight: 600;
  line-height: 20px;
}

.assignment__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 16px;
  margin-top: 4px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-sm);
}

.assignment__score {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-xs);
}

.assignment__score strong {
  color: var(--oj-text);
  font-size: var(--oj-fs-lg);
}

@media (max-width: 640px) {
  .assignment {
    flex-wrap: wrap;
  }
}
</style>
