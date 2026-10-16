<script setup>
import { computed, onMounted, ref } from 'vue'

import { examApi } from '@/api/exam'
import LearnTabs from '@/components/LearnTabs.vue'
import Countdown from '@/components/ui/Countdown.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { formatScore } from '@/utils/assignment'
import { EXAM_STATUS, RULE_LABELS } from '@/utils/exam'
import { formatDateTime } from '@/utils/judge'

const loading = ref(true)
const exams = ref([])

const groups = computed(() => [
  { key: 'in_progress', title: '进行中', items: exams.value.filter((e) => e.status === 'in_progress') },
  { key: 'not_started', title: '即将开始', items: exams.value.filter((e) => e.status === 'not_started') },
  // 已结束的按时间倒序
  { key: 'ended', title: '已结束', items: exams.value.filter((e) => e.status === 'ended').reverse() },
])

onMounted(async () => {
  try {
    exams.value = await examApi.mine()
  } finally {
    loading.value = false
  }
})

function participation(exam) {
  if (exam.status === 'ended') {
    if (!exam.is_score_published) return '成绩尚未公布'
    return `得分 ${formatScore(exam.my_score)} / ${exam.total_score}`
  }
  if (exam.finished) return '已交卷'
  if (exam.joined) return '已进入考试'
  return exam.status === 'in_progress' ? '尚未进入考试' : ''
}
</script>

<template>
  <div>
    <PageHeader title="我的考试" subtitle="课堂考试与已参加的竞赛" />
    <LearnTabs />

    <el-skeleton v-if="loading" animated :rows="4" />
    <EmptyState v-else-if="!exams.length" title="暂无考试" description="老师安排考试后会显示在这里。" />

    <template v-for="group in groups" :key="group.key">
      <section v-if="group.items.length" class="group">
        <h2 class="group__title">{{ group.title }} <span class="num">{{ group.items.length }}</span></h2>
        <router-link
          v-for="exam in group.items"
          :key="exam.id"
          :to="{ name: 'exam-detail', params: { id: exam.id } }"
          :class="['exam', `exam--${exam.status}`]"
        >
          <div class="exam__main">
            <div class="exam__title">
              {{ exam.title }}
              <el-tag :type="EXAM_STATUS[exam.status].type" size="small" effect="plain">{{ EXAM_STATUS[exam.status].label }}</el-tag>
            </div>
            <div class="exam__meta">
              <span>{{ exam.class_name }}</span>
              <span>{{ RULE_LABELS[exam.rule_type] }} · {{ exam.problem_count }} 题</span>
              <span>{{ formatDateTime(exam.start_time) }} 至 {{ formatDateTime(exam.end_time) }}</span>
            </div>
          </div>
          <div class="exam__state">
            <Countdown v-if="exam.status === 'in_progress'" :end="exam.end_time" />
            <span>{{ participation(exam) }}</span>
          </div>
        </router-link>
      </section>
    </template>
  </div>
</template>

<style scoped>
.group + .group {
  margin-top: var(--oj-space-5);
}

.group__title {
  margin: 0 0 var(--oj-space-3);
  color: var(--oj-text-3);
  font-size: var(--oj-fs-sm);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.exam {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 24px;
  margin-bottom: 12px;
  padding: 16px 20px;
  border: 1px solid var(--oj-border);
  border-left: 3px solid var(--oj-border-strong);
  border-radius: var(--oj-radius-md);
  background: var(--oj-surface);
  color: inherit;
  text-decoration: none;
  transition: box-shadow 0.15s;
}

.exam:hover {
  box-shadow: var(--oj-shadow-sm);
}

.exam--in_progress {
  border-left-color: var(--oj-v-wa-fg);
}

.exam--not_started {
  border-left-color: var(--el-color-primary);
}

.exam__main {
  flex: 1;
  min-width: 220px;
}

.exam__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--oj-fs-md);
  font-weight: 600;
}

.exam__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 16px;
  margin-top: 4px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-sm);
}

.exam__state {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  color: var(--oj-text-2);
  font-size: var(--oj-fs-sm);
}
</style>
