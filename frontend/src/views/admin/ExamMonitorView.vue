<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Refresh } from '@element-plus/icons-vue'

import { adminExamApi } from '@/api/exam'
import RankTable from '@/components/RankTable.vue'
import { formatScore } from '@/utils/assignment'
import { EXAM_STATUS, RULE_LABELS, formatDuration } from '@/utils/exam'
import { formatDateTime } from '@/utils/judge'
import PageHeader from '@/components/ui/PageHeader.vue'

// 监考数据自动刷新间隔
const REFRESH_INTERVAL = 15 * 1000

const STATES = {
  in_exam: { label: '考试中', type: 'primary' },
  finished: { label: '已交卷', type: 'success' },
  absent: { label: '未进入', type: 'info' },
}

const route = useRoute()
const router = useRouter()
const examId = computed(() => Number(route.params.id))

const loading = ref(false)
const loadError = ref('')
const data = ref(null)
const tab = ref('students')
const stateFilter = ref('')
const autoRefresh = ref(true)
const now = ref(Date.now())
let poll = null
let clock = null

const exam = computed(() => data.value?.exam)
// 公开竞赛没有班级名单，只列出已进入的参加者
const isPublic = computed(() => exam.value && exam.value.class_group === null)
const stateOptions = computed(() =>
  Object.fromEntries(Object.entries(STATES).filter(([key]) => !(isPublic.value && key === 'absent'))),
)
const students = computed(() =>
  (data.value?.students ?? []).filter((s) => !stateFilter.value || s.state === stateFilter.value),
)
const timeText = computed(() => {
  if (!exam.value) return ''
  if (exam.value.status === 'not_started') return `距开考 ${formatDuration((new Date(exam.value.start_time) - now.value) / 1000)}`
  if (exam.value.status === 'in_progress') return `剩余 ${formatDuration((new Date(exam.value.end_time) - now.value) / 1000)}`
  return '已结束'
})

async function load({ silent = false } = {}) {
  if (!silent) loading.value = true
  try {
    data.value = await adminExamApi.monitor(examId.value, { silent: true })
    document.title = `${data.value.exam.title} 监考 - YGU OJ`
  } catch (err) {
    if (!silent) loadError.value = err?.code === 404 ? '考试不存在，或你没有权限管理' : err?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  poll = setInterval(() => autoRefresh.value && load({ silent: true }), REFRESH_INTERVAL)
  clock = setInterval(() => (now.value = Date.now()), 1000)
})
onBeforeUnmount(() => {
  clearInterval(poll)
  clearInterval(clock)
})

async function toggleScorePublished(value) {
  try {
    await adminExamApi.update(examId.value, { is_score_published: value })
    exam.value.is_score_published = value
    ElMessage.success(value ? '已公布成绩，学生可查看成绩与排名' : '已撤回成绩')
  } catch {
    // 错误提示已由请求拦截器弹出
  }
}

async function reopen(row) {
  try {
    await ElMessageBox.confirm(`确定让 ${row.real_name}（${row.student_no}）撤销交卷、继续作答吗？`, '撤销交卷', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await adminExamApi.reopen(examId.value, row.user_id)
    ElMessage.success('已撤销交卷')
    load({ silent: true })
  } catch {
    // 错误提示已由请求拦截器弹出
  }
}
</script>

<template>
  <el-result v-if="loadError" icon="warning" :title="loadError">
    <template #extra>
      <el-button type="primary" @click="router.push({ name: 'admin-exams' })">返回考试列表</el-button>
    </template>
  </el-result>

  <div v-else v-loading="loading" class="monitor">
    <template v-if="data">
      <PageHeader :title="exam.title">
        <template #meta>
          <div class="head-meta">
            <el-tag :type="EXAM_STATUS[exam.status].type" size="small" effect="plain">{{ EXAM_STATUS[exam.status].label }}</el-tag>
            <el-tag v-if="!exam.is_published" type="info" size="small" effect="plain">未发布</el-tag>
            <span class="muted">
              {{ exam.class_name ?? '公开竞赛' }} · {{ RULE_LABELS[exam.rule_type] }} ·
              {{ formatDateTime(exam.start_time) }} 至 {{ formatDateTime(exam.end_time) }}
              <template v-if="exam.allowed_ip_ranges.length"> · 允许 IP：{{ exam.allowed_ip_ranges.join('、') }}</template>
              <template v-if="exam.password"> · 口令：{{ exam.password }}</template>
            </span>
          </div>
        </template>
        <span class="time">{{ timeText }}</span>
        <el-button :icon="Refresh" @click="load()">刷新</el-button>
        <el-button @click="router.push({ name: 'admin-exam-stats', params: { id: examId } })">统计分析</el-button>
        <el-button :icon="Edit" @click="router.push({ name: 'admin-exam-edit', params: { id: examId } })">编辑</el-button>
      </PageHeader>
      <el-card shadow="never">

        <div class="stats">
          <div class="stat">
            <div class="stat__value">{{ data.summary.in_exam }}</div>
            <div class="stat__label">考试中</div>
          </div>
          <div class="stat">
            <div class="stat__value">{{ data.summary.finished }}</div>
            <div class="stat__label">已交卷</div>
          </div>
          <div class="stat">
            <template v-if="isPublic">
              <div class="stat__value">{{ data.summary.member_count }}</div>
              <div class="stat__label">参加人数</div>
            </template>
            <template v-else>
              <div class="stat__value">{{ data.summary.absent }}</div>
              <div class="stat__label">未进入 / 共 {{ data.summary.member_count }} 人</div>
            </template>
          </div>
          <div class="stat stat--switch">
            <el-switch
              :model-value="exam.is_score_published"
              active-text="公布成绩"
              @update:model-value="toggleScorePublished"
            />
            <div class="stat__label">公布后学生可在考试结束后查看成绩、题目与排名</div>
          </div>
        </div>
      </el-card>

      <el-card shadow="never">
        <el-tabs v-model="tab">
          <el-tab-pane label="考生" name="students">
            <div class="toolbar">
              <el-radio-group v-model="stateFilter" size="small">
                <el-radio-button value="">全部</el-radio-button>
                <el-radio-button v-for="(meta, key) in stateOptions" :key="key" :value="key">{{ meta.label }}</el-radio-button>
              </el-radio-group>
              <el-checkbox v-model="autoRefresh">每 15 秒自动刷新</el-checkbox>
            </div>
            <el-table :data="students" size="small">
              <el-table-column prop="student_no" :label="isPublic ? '账号' : '学号'" width="120" />
              <el-table-column prop="real_name" label="姓名" width="90" />
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="STATES[row.state].type" size="small">{{ STATES[row.state].label }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="进入 IP" width="140">
                <template #default="{ row }">{{ row.join_ip ?? '—' }}</template>
              </el-table-column>
              <el-table-column label="进入时间" width="160">
                <template #default="{ row }">{{ row.joined_at ? formatDateTime(row.joined_at) : '—' }}</template>
              </el-table-column>
              <el-table-column label="交卷时间" width="160">
                <template #default="{ row }">{{ row.finished_at ? formatDateTime(row.finished_at) : '—' }}</template>
              </el-table-column>
              <el-table-column prop="submission_count" label="提交" width="70" align="center" />
              <el-table-column label="通过" width="70" align="center" prop="solved_count" />
              <el-table-column label="得分" width="80" align="center">
                <template #default="{ row }">{{ formatScore(row.score) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button
                    v-if="row.state === 'finished' && exam.status === 'in_progress'"
                    link
                    type="primary"
                    @click="reopen(row)"
                  >
                    撤销交卷
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="排名" name="rank">
            <RankTable :rank="data.rank" :problems="data.problems" :rule-type="exam.rule_type" />
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.monitor {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 300px;
}




.time {
  margin-right: 8px;
  color: var(--oj-brand-navy);
  font-family: Consolas, Menlo, monospace;
  font-size: 18px;
  font-weight: 600;
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.stat {
  padding: 12px 16px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
}

.stat--switch {
  grid-column: span 2;
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
</style>
