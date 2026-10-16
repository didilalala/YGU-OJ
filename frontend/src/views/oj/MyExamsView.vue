<script setup>
import { computed, onMounted, ref } from 'vue'

import { examApi } from '@/api/exam'
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
  <el-card v-loading="loading" shadow="never">
    <template #header><span class="title">我的考试</span></template>
    <el-empty v-if="!loading && !exams.length" description="暂无考试" />

    <template v-for="group in groups" :key="group.key">
      <section v-if="group.items.length" class="group">
        <h3 class="group__title">{{ group.title }}</h3>
        <router-link
          v-for="exam in group.items"
          :key="exam.id"
          :to="{ name: 'exam-detail', params: { id: exam.id } }"
          :class="['exam', `exam--${exam.status}`]"
        >
          <div class="exam__main">
            <div class="exam__title">
              {{ exam.title }}
              <el-tag :type="EXAM_STATUS[exam.status].type" size="small">{{ EXAM_STATUS[exam.status].label }}</el-tag>
            </div>
            <div class="exam__meta">
              <span>{{ exam.class_name }}</span>
              <span>{{ RULE_LABELS[exam.rule_type] }} · {{ exam.problem_count }} 题</span>
              <span>{{ formatDateTime(exam.start_time) }} 至 {{ formatDateTime(exam.end_time) }}</span>
            </div>
          </div>
          <div class="exam__state">{{ participation(exam) }}</div>
        </router-link>
      </section>
    </template>
  </el-card>
</template>

<style scoped>
.title {
  font-size: 16px;
  font-weight: 600;
}

.group + .group {
  margin-top: 20px;
}

.group__title {
  margin: 0 0 10px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.exam {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 24px;
  margin-bottom: 10px;
  padding: 14px 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-left: 3px solid var(--el-border-color);
  border-radius: 6px;
  background: #fff;
  color: inherit;
  text-decoration: none;
}

.exam:hover {
  box-shadow: var(--el-box-shadow-light);
}

.exam--in_progress {
  border-left-color: var(--el-color-danger);
}

.exam--not_started {
  border-left-color: var(--oj-brand-navy);
}

.exam__main {
  flex: 1;
  min-width: 220px;
}

.exam__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.exam__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.exam__state {
  color: var(--el-text-color-regular);
  font-size: 13px;
}
</style>
