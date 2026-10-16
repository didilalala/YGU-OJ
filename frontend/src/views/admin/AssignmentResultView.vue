<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Edit, Refresh } from '@element-plus/icons-vue'

import { adminAssignmentApi } from '@/api/assignment'
import { ASSIGNMENT_STATUS, formatScore, latePolicy } from '@/utils/assignment'
import { formatDateTime } from '@/utils/judge'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const assignmentId = computed(() => Number(route.params.id))

const loading = ref(false)
const loadError = ref('')
const data = ref(null)
const onlyUnsubmitted = ref(false)

const totalScore = computed(() => data.value?.problems.reduce((sum, p) => sum + p.score, 0) ?? 0)
const rows = computed(() => (data.value?.rows ?? []).filter((row) => !onlyUnsubmitted.value || !row.submitted))

async function load() {
  loading.value = true
  try {
    data.value = await adminAssignmentApi.results(assignmentId.value, { silent: true })
    document.title = `${data.value.assignment.title} 成绩 - YGU OJ`
  } catch (err) {
    loadError.value = err?.code === 404 ? '作业不存在，或你没有权限查看' : err?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function cellClass(entry, problem) {
  if (!entry) return 'cell--none'
  if (entry.score >= problem.score) return 'cell--full'
  return entry.score > 0 ? 'cell--partial' : 'cell--zero'
}
</script>

<template>
  <el-result v-if="loadError" icon="warning" :title="loadError">
    <template #extra>
      <el-button type="primary" @click="router.push({ name: 'admin-assignments' })">返回作业列表</el-button>
    </template>
  </el-result>

  <div v-else v-loading="loading" class="result-page">
    <template v-if="data">
      <PageHeader :title="data.assignment.title">
        <template #meta>
          <div class="head-meta">
            <el-tag :type="ASSIGNMENT_STATUS[data.assignment.status].type" size="small" effect="plain">
              {{ ASSIGNMENT_STATUS[data.assignment.status].label }}
            </el-tag>
            <el-tag v-if="!data.assignment.is_published" type="info" size="small" effect="plain">未发布</el-tag>
            <span class="muted">
              {{ data.assignment.class_name }} · {{ formatDateTime(data.assignment.start_time) }} 至
              {{ formatDateTime(data.assignment.end_time) }} · {{ latePolicy(data.assignment) }}
            </span>
          </div>
        </template>
        <el-button :icon="Refresh" @click="load">刷新</el-button>
        <el-button @click="router.push({ name: 'admin-assignment-stats', params: { id: assignmentId } })">统计分析</el-button>
        <el-button :icon="Edit" @click="router.push({ name: 'admin-assignment-edit', params: { id: assignmentId } })">
          编辑作业
        </el-button>
      </PageHeader>
      <el-card shadow="never">

        <div class="stats">
          <div class="stat">
            <div class="stat__value">{{ data.summary.submitted_count }} / {{ data.summary.member_count }}</div>
            <div class="stat__label">已提交 / 班级人数</div>
          </div>
          <div class="stat">
            <div class="stat__value">{{ formatScore(data.summary.average_score) }}</div>
            <div class="stat__label">平均分（满分 {{ totalScore }}，未提交计 0 分）</div>
          </div>
          <div class="stat">
            <div class="stat__value">{{ data.summary.full_score_count }}</div>
            <div class="stat__label">满分人数</div>
          </div>
        </div>
      </el-card>

      <el-card shadow="never">
        <div class="toolbar">
          <el-checkbox v-model="onlyUnsubmitted">只看未提交的学生</el-checkbox>
          <span class="muted legend">
            <span class="dot cell--full" />满分 <span class="dot cell--partial" />部分得分
            <span class="dot cell--zero" />0 分 · 「迟」为迟交得分
          </span>
        </div>
        <el-table :data="rows" border size="small" :default-sort="{ prop: 'student_no', order: 'ascending' }">
          <el-table-column prop="student_no" label="学号" width="120" fixed sortable />
          <el-table-column prop="real_name" label="姓名" width="90" fixed />
          <el-table-column
            v-for="(problem, index) in data.problems"
            :key="problem.problem_id"
            :label="`${index + 1}. ${problem.title}（${problem.score}）`"
            min-width="120"
            align="center"
          >
            <template #default="{ row }">
              <span :class="['cell', cellClass(row.problems[problem.problem_id], problem)]">
                <template v-if="row.problems[problem.problem_id]">
                  {{ formatScore(row.problems[problem.problem_id].score) }}
                  <sup v-if="row.problems[problem.problem_id].late" class="late-mark">迟</sup>
                </template>
                <template v-else>—</template>
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="score" label="总分" width="90" align="center" fixed="right" sortable>
            <template #default="{ row }">
              <strong v-if="row.submitted">{{ formatScore(row.score) }}</strong>
              <el-tag v-else type="danger" size="small" effect="plain">未提交</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="solved_count" label="通过" width="70" align="center" fixed="right" sortable />
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.result-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 300px;
}




.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.stat {
  padding: 12px 16px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
}

.stat__value {
  color: var(--oj-brand-navy);
  font-size: 24px;
  font-weight: 600;
}

.stat__label {
  margin-top: 2px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}

.legend {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  margin-left: 8px;
  border-radius: 2px;
}

.cell {
  display: inline-block;
  min-width: 40px;
  padding: 2px 6px;
  border-radius: 4px;
}

.cell--full {
  background: var(--el-color-success-light-8);
  color: var(--el-color-success-dark-2);
}

.cell--partial {
  background: var(--el-color-warning-light-8);
  color: var(--el-color-warning-dark-2);
}

.cell--zero {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}

.cell--none {
  color: var(--el-text-color-placeholder);
}

.dot.cell--full {
  background: var(--el-color-success-light-5);
}

.dot.cell--partial {
  background: var(--el-color-warning-light-5);
}

.dot.cell--zero {
  background: var(--el-color-danger-light-7);
}

.late-mark {
  color: var(--el-color-warning-dark-2);
  font-size: 10px;
}
</style>
