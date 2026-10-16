<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CircleCheckFilled } from '@element-plus/icons-vue'

import { assignmentApi } from '@/api/assignment'
import DifficultyTag from '@/components/DifficultyTag.vue'
import MarkdownView from '@/components/MarkdownView.vue'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { ASSIGNMENT_STATUS, formatScore, latePolicy, timeLeft } from '@/utils/assignment'
import { formatDateTime } from '@/utils/judge'

const route = useRoute()
const router = useRouter()
const isMobile = useMediaQuery('(max-width: 640px)')

const loading = ref(true)
const loadError = ref('')
const assignment = ref(null)

const deadline = computed(() => {
  const item = assignment.value
  if (!item) return ''
  if (item.status === 'not_started') return `作业将于 ${formatDateTime(item.start_time)} 开始，届时可查看题目`
  const left = timeLeft(item.end_time)
  return left ? `距截止还有 ${left}` : '已截止'
})

watch(
  () => route.params.id,
  async (id) => {
    if (!id) return
    loading.value = true
    loadError.value = ''
    try {
      assignment.value = await assignmentApi.detail(id, { silent: true })
      document.title = `${assignment.value.title} - YGU OJ`
    } catch (err) {
      loadError.value = err?.code === 404 ? '作业不存在，或你不在该班级中' : err?.message || '加载失败'
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

function openProblem(row) {
  router.push({ name: 'problem-detail', params: { id: row.problem_id }, query: { assignment: assignment.value.id } })
}
</script>

<template>
  <el-result v-if="loadError" icon="warning" :title="loadError">
    <template #extra>
      <el-button type="primary" @click="router.push({ name: 'my-assignments' })">返回我的作业</el-button>
    </template>
  </el-result>

  <div v-else v-loading="loading" class="page">
    <template v-if="assignment">
      <el-card shadow="never">
        <h1 class="title">
          {{ assignment.title }}
          <el-tag :type="ASSIGNMENT_STATUS[assignment.status].type">{{ ASSIGNMENT_STATUS[assignment.status].label }}</el-tag>
        </h1>
        <div class="meta">
          <span>{{ assignment.class_name }}</span>
          <span>{{ formatDateTime(assignment.start_time) }} 至 {{ formatDateTime(assignment.end_time) }}</span>
          <span>{{ latePolicy(assignment) }}</span>
        </div>
        <el-alert :title="deadline" :type="assignment.status === 'in_progress' ? 'info' : 'warning'" :closable="false" show-icon class="deadline" />

        <div v-if="assignment.status !== 'not_started'" class="summary">
          <div class="summary__item">
            <div class="summary__value">{{ formatScore(assignment.my_score) }}</div>
            <div class="summary__label">我的得分 / {{ assignment.total_score }}</div>
          </div>
          <div class="summary__item">
            <div class="summary__value">{{ assignment.my_solved }} / {{ assignment.problem_count }}</div>
            <div class="summary__label">已通过</div>
          </div>
        </div>

        <MarkdownView v-if="assignment.description" :content="assignment.description" class="description" />
      </el-card>

      <el-card v-if="assignment.problems.length" shadow="never">
        <template #header>题目</template>
        <p class="hint">每题取最高得分，可多次提交；部分通过按通过的测试点比例得分。</p>
        <el-table :data="assignment.problems" class="problems" @row-click="openProblem">
          <el-table-column width="44" align="center">
            <template #default="{ row }">
              <el-icon v-if="row.accepted" class="accepted"><CircleCheckFilled /></el-icon>
            </template>
          </el-table-column>
          <el-table-column type="index" label="#" width="44" />
          <el-table-column label="题目" min-width="180">
            <template #default="{ row }">
              <router-link
                :to="{ name: 'problem-detail', params: { id: row.problem_id }, query: { assignment: assignment.id } }"
                class="link"
                @click.stop
              >
                {{ row.title }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column v-if="!isMobile" label="难度" width="80">
            <template #default="{ row }"><DifficultyTag :difficulty="row.difficulty" /></template>
          </el-table-column>
          <el-table-column label="得分" width="120" align="right">
            <template #default="{ row }">
              <span :class="{ full: row.my_score >= row.score }">{{ formatScore(row.my_score) }}</span>
              <span class="muted"> / {{ row.score }}</span>
              <sup v-if="row.late" class="late-mark">迟</sup>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 200px;
}

.title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 0 0 8px;
  font-size: 22px;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.deadline {
  margin-top: 12px;
}

.summary {
  display: flex;
  gap: 16px;
  margin-top: 16px;
}

.summary__item {
  padding: 10px 16px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
}

.summary__value {
  color: var(--oj-brand-navy);
  font-size: 22px;
  font-weight: 600;
}

.summary__label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.description {
  margin-top: 16px;
}

.hint {
  margin: 0 0 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.problems :deep(.el-table__row) {
  cursor: pointer;
}

.accepted {
  color: var(--el-color-success);
  font-size: 18px;
}

.link {
  color: var(--el-color-primary);
  text-decoration: none;
}

.full {
  color: var(--el-color-success);
  font-weight: 600;
}

.muted {
  color: var(--el-text-color-secondary);
}

.late-mark {
  color: var(--el-color-warning-dark-2);
  font-size: 10px;
}
</style>
