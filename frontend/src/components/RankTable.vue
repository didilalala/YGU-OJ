<script setup>
/**
 * 考试排名表（学生端考场与教师监考共用）。
 * OI：各题得分与总分；ACM：通过标「+」及通过用时、错误次数，按通过题数与罚时排名。
 */
import { formatScore } from '@/utils/assignment'
import { formatDuration } from '@/utils/exam'

defineProps({
  rank: { type: Array, required: true },
  problems: { type: Array, required: true },
  ruleType: { type: String, required: true },
  highlightUserId: { type: Number, default: null },
  // 公开竞赛：显示账号（在校学生的学号已打码），不显示姓名
  isPublic: { type: Boolean, default: false },
})

function acmCell(entry) {
  if (!entry) return ''
  if (entry.accepted) return entry.attempts ? `+${entry.attempts}` : '+'
  return entry.attempts ? `-${entry.attempts}` : ''
}

function cellClass(entry, problem, ruleType) {
  if (!entry) return ''
  if (entry.accepted) return 'cell--ok'
  if (ruleType === 'OI' && entry.score > 0) return entry.score >= problem.score ? 'cell--ok' : 'cell--partial'
  return 'cell--bad'
}
</script>

<template>
  <el-table
    :data="rank"
    size="small"
    border
    class="num"
    empty-text="还没有人上榜"
    :row-class-name="({ row }) => (row.user_id === highlightUserId ? 'row--me' : '')"
  >
    <el-table-column prop="rank" label="名次" width="64" align="center" fixed />
    <el-table-column prop="student_no" :label="isPublic ? '账号' : '学号'" width="110" fixed />
    <el-table-column v-if="!isPublic" prop="real_name" label="姓名" width="80" fixed />
    <template v-if="ruleType === 'ACM'">
      <el-table-column prop="solved_count" label="通过" width="64" align="center" />
      <el-table-column label="罚时" width="90" align="center">
        <template #default="{ row }">{{ formatDuration(row.penalty) }}</template>
      </el-table-column>
    </template>
    <el-table-column v-else label="总分" width="80" align="center">
      <template #default="{ row }"><strong>{{ formatScore(row.score) }}</strong></template>
    </el-table-column>
    <el-table-column
      v-for="(problem, index) in problems"
      :key="problem.problem_id"
      :label="String.fromCharCode(65 + index)"
      min-width="80"
      align="center"
    >
      <template #header>
        <span :title="`${problem.title}（${problem.score} 分）`">{{ String.fromCharCode(65 + index) }}</span>
      </template>
      <template #default="{ row }">
        <div :class="['cell', cellClass(row.problems[problem.problem_id], problem, ruleType)]">
          <template v-if="ruleType === 'ACM'">
            <div>{{ acmCell(row.problems[problem.problem_id]) }}</div>
            <div v-if="row.problems[problem.problem_id]?.accepted" class="cell__time">
              {{ formatDuration(row.problems[problem.problem_id].ac_time) }}
            </div>
          </template>
          <template v-else-if="row.problems[problem.problem_id]">
            {{ formatScore(row.problems[problem.problem_id].score) }}
          </template>
        </div>
      </template>
    </el-table-column>
  </el-table>
</template>

<style scoped>
.cell {
  margin: -4px -8px;
  padding: 4px 0;
  line-height: 1.3;
}

.cell--ok {
  background: var(--oj-v-ac-bg);
  color: var(--oj-v-ac-fg);
  font-weight: 600;
}

.cell--partial {
  background: var(--oj-v-tle-bg);
  color: var(--oj-v-tle-fg);
}

.cell--bad {
  background: var(--oj-v-wa-bg);
  color: var(--oj-v-wa-fg);
}

.cell__time {
  font-size: 11px;
  font-weight: normal;
}

:deep(.row--me td) {
  background: var(--el-color-primary-light-9) !important;
}
</style>
