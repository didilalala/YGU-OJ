<script setup>
/** 个人主页：个人信息与做题统计。 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { authApi } from '@/api/auth'
import EChart from '@/components/EChart.vue'
import { ROLE_LABELS } from '@/utils/constants'
import { INK, PRIMARY_SERIES, barSeries, baseOption, categoryAxis, valueAxis } from '@/utils/chart'
import { RESULTS, formatDateTime } from '@/utils/judge'

const router = useRouter()
const loading = ref(true)
const loadError = ref('')
const data = ref(null)
const tableView = ref({ results: false, activity: false })

onMounted(async () => {
  try {
    data.value = await authApi.profile({ silent: true })
    document.title = `${data.value.profile.real_name || data.value.profile.username} - YGU OJ`
  } catch (err) {
    loadError.value = err?.message || '加载失败'
  } finally {
    loading.value = false
  }
})

const displayName = computed(() => data.value?.profile.real_name || data.value?.profile.username || '')
const avatarLetter = computed(() => displayName.value.slice(0, 1).toUpperCase())
const profileRows = computed(() => {
  const p = data.value.profile
  const rows = [
    { label: '角色', value: ROLE_LABELS[p.role] },
    { label: '用户名', value: p.username },
  ]
  if (p.student_no) rows.push({ label: '学号', value: p.student_no })
  if (p.staff_no) rows.push({ label: '工号', value: p.staff_no })
  if (p.email) rows.push({ label: '邮箱', value: p.email })
  if (p.college) rows.push({ label: '学院', value: p.college })
  if (p.major) rows.push({ label: '专业', value: p.major })
  if (p.grade) rows.push({ label: '年级', value: p.grade })
  rows.push({ label: '所在班级', value: `${p.class_count} 个` })
  rows.push({ label: '注册时间', value: formatDateTime(p.created_at) })
  return rows
})

// 提交结果分布：状态色 + 文字标签（颜色不单独承载含义）
const RESULT_COLORS = {
  AC: '#67C23A',
  WA: '#F56C6C',
  RE: '#F56C6C',
  CE: '#F56C6C',
  TLE: '#E6A23C',
  MLE: '#E6A23C',
  PAC: '#ec835a',
}
const resultOption = computed(() => {
  const rows = data.value.stats.distribution
  return {
    ...baseOption(),
    tooltip: {
      ...baseOption().tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(30,42,102,0.06)' } },
      formatter: ([item]) => `${RESULTS[rows[item.dataIndex].result].label}：<b>${item.value}</b> 次`,
    },
    xAxis: categoryAxis(rows.map((r) => RESULTS[r.result].label)),
    yAxis: valueAxis({ minInterval: 1 }),
    series: [
      barSeries({
        data: rows.map((r) => ({ value: r.count, itemStyle: { color: RESULT_COLORS[r.result], borderRadius: [4, 4, 0, 0] } })),
        label: { show: true, position: 'top', color: INK.secondary, formatter: ({ value }) => (value ? value : '') },
      }),
    ],
  }
})

const activityOption = computed(() => {
  const days = data.value.stats.activity
  return {
    ...baseOption(),
    tooltip: {
      ...baseOption().tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(30,42,102,0.06)' } },
      formatter: ([item]) => `${days[item.dataIndex].date}：<b>${item.value}</b> 次提交`,
    },
    xAxis: categoryAxis(days.map((d) => d.date.slice(5)), { axisLabel: { color: INK.muted, fontSize: 11, interval: 4 } }),
    yAxis: valueAxis({ minInterval: 1 }),
    series: [barSeries({ data: days.map((d) => d.count), itemStyle: { color: PRIMARY_SERIES, borderRadius: [4, 4, 0, 0] } })],
  }
})

function percentFor(item) {
  return item.total ? Math.round((item.solved / item.total) * 100) : 0
}

function openSubmission(row) {
  router.push({ name: 'submission-detail', params: { id: row.id } })
}
</script>

<template>
  <div v-loading="loading" class="profile-page">
    <el-result v-if="loadError" icon="warning" :title="loadError" />

    <template v-else-if="data">
      <el-card shadow="never" class="identity">
        <div class="identity__avatar">{{ avatarLetter }}</div>
        <div class="identity__main">
          <h1 class="identity__name">
            {{ displayName }}
            <el-tag size="small" effect="plain">{{ ROLE_LABELS[data.profile.role] }}</el-tag>
          </h1>
          <dl class="identity__facts">
            <template v-for="row in profileRows" :key="row.label">
              <dt>{{ row.label }}</dt>
              <dd>{{ row.value }}</dd>
            </template>
          </dl>
        </div>
        <div class="identity__actions">
          <el-button @click="router.push({ name: 'submissions' })">提交记录</el-button>
          <el-button v-if="data.profile.role === 'student'" @click="router.push({ name: 'my-scores' })">我的成绩</el-button>
        </div>
      </el-card>

      <div class="tiles">
        <div class="tile">
          <div class="tile__label">已通过题目</div>
          <div class="tile__value">{{ data.stats.solved_problems }} <span class="tile__of">/ {{ data.stats.visible_problems }}</span></div>
          <div class="tile__sub">尝试过 {{ data.stats.attempted_problems }} 题</div>
        </div>
        <div class="tile">
          <div class="tile__label">提交次数</div>
          <div class="tile__value">{{ data.stats.submitted }}</div>
          <div class="tile__sub">已完成评测的提交</div>
        </div>
        <div class="tile">
          <div class="tile__label">通过率</div>
          <div class="tile__value">{{ data.stats.accept_rate }}%</div>
          <div class="tile__sub">通过 {{ data.stats.accepted }} 次</div>
        </div>
      </div>

      <div class="grid">
        <el-card shadow="never">
          <template #header>各难度完成情况</template>
          <div v-for="level in data.stats.by_difficulty" :key="level.difficulty" class="level">
            <div class="level__head">
              <span>{{ level.label }}</span>
              <span class="muted">{{ level.solved }} / {{ level.total }}</span>
            </div>
            <el-progress
              :percentage="percentFor(level)"
              :stroke-width="10"
              :show-text="false"
              :color="PRIMARY_SERIES"
            />
          </div>
        </el-card>

        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>提交结果分布</span>
              <el-switch v-model="tableView.results" size="small" active-text="表格" />
            </div>
          </template>
          <el-table v-if="tableView.results" :data="data.stats.distribution" size="small">
            <el-table-column label="结果">
              <template #default="{ row }">{{ RESULTS[row.result].label }}</template>
            </el-table-column>
            <el-table-column prop="count" label="次数" align="right" />
          </el-table>
          <EChart
            v-else
            :option="resultOption"
            height="240px"
            label="提交结果分布柱状图，按评测结果分类计数"
          />
        </el-card>
      </div>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>近 30 天每日提交</span>
            <el-switch v-model="tableView.activity" size="small" active-text="表格" />
          </div>
        </template>
        <el-table v-if="tableView.activity" :data="data.stats.activity" size="small" max-height="260">
          <el-table-column prop="date" label="日期" />
          <el-table-column prop="count" label="提交次数" align="right" />
        </el-table>
        <EChart v-else :option="activityOption" height="220px" label="近 30 天每日提交次数柱状图" />
      </el-card>

      <el-card shadow="never">
        <template #header>最近提交</template>
        <el-empty v-if="!data.stats.recent.length" description="还没有提交记录" :image-size="60" />
        <el-table v-else :data="data.stats.recent" size="small" class="recent" @row-click="openSubmission">
          <el-table-column label="题目" min-width="180">
            <template #default="{ row }">{{ row.problem_title }}</template>
          </el-table-column>
          <el-table-column label="结果" width="120">
            <template #default="{ row }">{{ RESULTS[row.result].label }}</template>
          </el-table-column>
          <el-table-column label="提交时间" width="170">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.profile-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 200px;
}

.identity {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  align-items: flex-start;
}

.identity__avatar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--oj-brand-navy);
  color: #fff;
  font-size: 30px;
  font-weight: 600;
}

.identity__main {
  flex: 1;
  min-width: 240px;
}

.identity__name {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 8px;
  font-size: 22px;
}

.identity__facts {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 16px;
  margin: 0;
  font-size: 14px;
}

.identity__facts dt {
  color: var(--el-text-color-secondary);
}

.identity__facts dd {
  margin: 0;
  color: var(--el-text-color-primary);
}

.identity__actions {
  display: flex;
  gap: 8px;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.tile {
  padding: 12px 16px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
}

.tile__label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.tile__value {
  margin-top: 4px;
  font-size: 24px;
  font-weight: 600;
}

.tile__of {
  color: var(--el-text-color-secondary);
  font-size: 16px;
  font-weight: normal;
}

.tile__sub {
  margin-top: 2px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.level + .level {
  margin-top: 14px;
}

.level__head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 14px;
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.recent :deep(.el-table__row) {
  cursor: pointer;
}

@media (max-width: 640px) {
  .identity__actions {
    width: 100%;
  }
}
</style>
