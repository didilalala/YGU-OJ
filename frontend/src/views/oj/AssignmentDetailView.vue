<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CircleCheckFilled } from '@element-plus/icons-vue'

import { assignmentApi } from '@/api/assignment'
import MarkdownView from '@/components/MarkdownView.vue'
import DifficultyBadge from '@/components/ui/DifficultyBadge.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatCard from '@/components/ui/StatCard.vue'
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

  <div v-else>
    <el-skeleton v-if="loading" animated :rows="6" />
    <template v-else-if="assignment">
      <PageHeader
        :title="assignment.title"
        :subtitle="`${assignment.class_name} · ${formatDateTime(assignment.start_time)} 至 ${formatDateTime(assignment.end_time)}`"
        :crumbs="[{ text: '我的作业', to: '/assignments' }]"
      >
        <el-tag :type="ASSIGNMENT_STATUS[assignment.status].type" effect="plain">{{ ASSIGNMENT_STATUS[assignment.status].label }}</el-tag>
      </PageHeader>

      <el-alert :title="deadline" :type="assignment.status === 'in_progress' ? 'info' : 'warning'" :closable="false" show-icon class="deadline" />
      <p class="muted policy">{{ latePolicy(assignment) }}</p>

      <div v-if="assignment.status !== 'not_started'" class="stats">
        <StatCard accent label="我的得分" :value="formatScore(assignment.my_score)" :unit="`/ ${assignment.total_score}`" />
        <StatCard label="已通过" :value="assignment.my_solved" :unit="`/ ${assignment.problem_count} 题`" />
      </div>

      <el-card v-if="assignment.description" shadow="never" class="block">
        <MarkdownView :content="assignment.description" />
      </el-card>

      <el-card v-if="assignment.problems.length" shadow="never" class="block">
        <template #header>题目</template>
        <p class="muted hint">每题取最高得分，可多次提交；部分通过按通过的测试点比例得分。</p>
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
                class="text-link"
                @click.stop
              >
                {{ row.title }}
              </router-link>
            </template>
          </el-table-column>
          <el-table-column v-if="!isMobile" label="难度" width="90">
            <template #default="{ row }"><DifficultyBadge :difficulty="row.difficulty" /></template>
          </el-table-column>
          <el-table-column label="得分" width="130" align="right" class-name="num">
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
.deadline {
  margin-bottom: 4px;
}

.policy {
  margin: 4px 0 var(--oj-space-4);
  font-size: var(--oj-fs-sm);
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 240px));
  gap: var(--oj-space-4);
  margin-bottom: var(--oj-space-4);
}

.block {
  margin-bottom: var(--oj-space-4);
}

.hint {
  margin: 0 0 8px;
  font-size: var(--oj-fs-sm);
}

.problems :deep(.el-table__row) {
  cursor: pointer;
}

.accepted {
  color: var(--oj-v-ac-fg);
  font-size: 18px;
}

.full {
  color: var(--oj-v-ac-fg);
  font-weight: 600;
}

.late-mark {
  color: var(--oj-v-tle-fg);
  font-size: 10px;
}
</style>
