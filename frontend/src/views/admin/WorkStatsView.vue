<script setup>
/** 作业 / 考试统计：成绩分布、各题满分率、错误类型分布、未提交名单（设计说明书 9.4 班级视角）。 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { statsApi } from '@/api/stats'
import EChart from '@/components/EChart.vue'
import { formatScore } from '@/utils/assignment'
import {
  ERROR_COLORS,
  ERROR_TYPES,
  INK,
  barSeries,
  baseOption,
  categoryAxis,
  shortLabel,
  valueAxis,
} from '@/utils/chart'
import { RESULTS } from '@/utils/judge'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const kind = computed(() => route.meta.statsKind)
const kindLabel = computed(() => (kind.value === 'exam' ? '考试' : '作业'))

const loading = ref(true)
const loadError = ref('')
const data = ref(null)
// 每个图表可切换为表格视图
const tableView = ref({ distribution: false, problems: false, errors: false })

onMounted(async () => {
  try {
    const load = kind.value === 'exam' ? statsApi.exam : statsApi.assignment
    data.value = await load(route.params.id, { silent: true })
    document.title = `${data.value.title} 统计 - YGU OJ`
  } catch (err) {
    loadError.value = err?.code === 404 ? `${kindLabel.value}不存在，或你没有权限查看` : err?.message || '加载失败'
  } finally {
    loading.value = false
  }
})

const problemNames = computed(() => data.value?.problems.map((p) => `${p.index + 1}. ${p.title}`) ?? [])
const totalErrors = computed(() => (data.value ? ERROR_TYPES.reduce((sum, t) => sum + data.value.errors[t], 0) : 0))

const distributionOption = computed(() => {
  const buckets = data.value.distribution
  return {
    ...baseOption(),
    tooltip: {
      ...baseOption().tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(30,42,102,0.06)' } },
      formatter: ([item]) => `${buckets[item.dataIndex].label}（得分率 ${buckets[item.dataIndex].range}）<br/><b>${item.value}</b> 人`,
    },
    xAxis: categoryAxis(buckets.map((b) => b.label)),
    yAxis: valueAxis({ minInterval: 1 }),
    series: [
      barSeries({
        data: buckets.map((b) => b.count),
        itemStyle: { color: INK.series, borderRadius: [4, 4, 0, 0] },
        // 只有 5 根柱，柱顶标注人数
        label: { show: true, position: 'top', color: INK.secondary, formatter: ({ value }) => (value ? `${value} 人` : '') },
      }),
    ],
  }
})

const problemOption = computed(() => {
  const problems = data.value.problems
  return {
    ...baseOption(),
    tooltip: {
      ...baseOption().tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(30,42,102,0.06)' } },
      formatter: ([item]) => {
        const p = problems[item.dataIndex]
        return `${problemNames.value[item.dataIndex]}<br/>满分率 <b>${p.accepted_rate}%</b>（${p.accepted_count}/${data.value.summary.member_count} 人）<br/>平均得分 ${formatScore(p.average_score)} / ${p.score}`
      },
    },
    xAxis: categoryAxis(problemNames.value.map((name) => shortLabel(name))),
    yAxis: valueAxis({ max: 100, axisLabel: { color: INK.muted, formatter: '{value}%' } }),
    series: [
      barSeries({
        data: problems.map((p) => p.accepted_rate),
        itemStyle: { color: INK.series, borderRadius: [4, 4, 0, 0] },
        label: { show: problems.length <= 10, position: 'top', color: INK.secondary, formatter: '{c}%' },
      }),
    ],
  }
})

const errorOption = computed(() => {
  const problems = data.value.problems
  return {
    ...baseOption(),
    grid: { ...baseOption().grid, top: 40 },
    legend: {
      top: 0,
      itemWidth: 12,
      itemHeight: 12,
      textStyle: { color: INK.secondary },
      data: ERROR_TYPES.map((t) => ({ name: RESULTS[t].label, itemStyle: { color: ERROR_COLORS[t] } })),
    },
    tooltip: { ...baseOption().tooltip, trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(30,42,102,0.06)' } } },
    xAxis: categoryAxis(problemNames.value.map((name) => shortLabel(name))),
    yAxis: valueAxis({ minInterval: 1, name: '提交次数', nameTextStyle: { color: INK.muted, align: 'left' } }),
    series: ERROR_TYPES.map((t, index) =>
      barSeries({
        name: RESULTS[t].label,
        stack: 'errors',
        data: problems.map((p) => p.errors[t]),
        // 堆叠段之间用 2px 白色间隔分开；只有最上面一段圆角
        itemStyle: {
          color: ERROR_COLORS[t],
          borderColor: INK.surface,
          borderWidth: 2,
          borderRadius: index === ERROR_TYPES.length - 1 ? [4, 4, 0, 0] : 0,
        },
      }),
    ),
  }
})

function errorShare(count) {
  return totalErrors.value ? `${((count / totalErrors.value) * 100).toFixed(1)}%` : '—'
}
</script>

<template>
  <el-result v-if="loadError" icon="warning" :title="loadError">
    <template #extra>
      <el-button type="primary" @click="router.back()">返回</el-button>
    </template>
  </el-result>

  <div v-else v-loading="loading" class="stats-page">
    <template v-if="data">
      <PageHeader :title="`${data.title} · 统计分析`">
        <template #meta>
          <div class="head-meta muted">
            {{ data.class_name }} · {{ kindLabel }} · 满分 {{ data.total_score }} · 只统计在班学生
          </div>
        </template>
        <el-button
          @click="
            router.push(
              kind === 'exam'
                ? { name: 'admin-exam-monitor', params: { id: data.id } }
                : { name: 'admin-assignment-results', params: { id: data.id } },
            )
          "
        >
          {{ kind === 'exam' ? '监考与排名' : '成绩表' }}
        </el-button>
        <el-button v-if="data.class_id" @click="router.push({ name: 'admin-stats', query: { class_id: data.class_id } })">
          班级统计
        </el-button>
      </PageHeader>
      <el-card shadow="never">

        <div class="tiles">
          <div class="tile">
            <div class="tile__label">提交人数</div>
            <div class="tile__value">{{ data.summary.submitted_count }} / {{ data.summary.member_count }}</div>
            <div class="tile__sub">提交率 {{ data.summary.submission_rate }}%</div>
          </div>
          <div class="tile">
            <div class="tile__label">平均分（全班）</div>
            <div class="tile__value">{{ formatScore(data.summary.average_score) }}</div>
            <div class="tile__sub">未提交计 0 分</div>
          </div>
          <div class="tile">
            <div class="tile__label">已提交平均 / 中位数</div>
            <div class="tile__value">{{ formatScore(data.summary.average_submitted) }} / {{ formatScore(data.summary.median_submitted) }}</div>
            <div class="tile__sub">最高 {{ formatScore(data.summary.max_score) }} · 最低 {{ formatScore(data.summary.min_score) }}</div>
          </div>
          <div class="tile">
            <div class="tile__label">满分人数</div>
            <div class="tile__value">{{ data.summary.full_score_count }}</div>
            <div class="tile__sub">及格率 {{ data.summary.pass_rate }}%（全班）</div>
          </div>
        </div>
      </el-card>

      <div class="grid">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>成绩分布（已提交 {{ data.summary.submitted_count }} 人）</span>
              <el-switch v-model="tableView.distribution" size="small" active-text="表格" />
            </div>
          </template>
          <el-table v-if="tableView.distribution" :data="data.distribution" size="small">
            <el-table-column prop="label" label="等级" />
            <el-table-column prop="range" label="得分率" />
            <el-table-column prop="count" label="人数" align="right" />
          </el-table>
          <EChart v-else :option="distributionOption" height="260px" label="成绩分布柱状图，按得分率分为五个等级" />
        </el-card>

        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>各题满分率（按全班）</span>
              <el-switch v-model="tableView.problems" size="small" active-text="表格" />
            </div>
          </template>
          <el-table v-if="tableView.problems" :data="data.problems" size="small">
            <el-table-column label="题目" min-width="140">
              <template #default="{ row }">{{ row.index + 1 }}. {{ row.title }}</template>
            </el-table-column>
            <el-table-column label="满分率" width="80" align="right">
              <template #default="{ row }">{{ row.accepted_rate }}%</template>
            </el-table-column>
            <el-table-column label="平均得分" width="90" align="right">
              <template #default="{ row }">{{ formatScore(row.average_score) }} / {{ row.score }}</template>
            </el-table-column>
            <el-table-column label="尝试人数" prop="attempted_count" width="80" align="right" />
          </el-table>
          <EChart v-else :option="problemOption" height="260px" label="各题满分率柱状图" />
        </el-card>
      </div>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>错误类型分布（共 {{ totalErrors }} 次未通过的提交）</span>
            <el-switch v-model="tableView.errors" size="small" active-text="表格" />
          </div>
        </template>
        <el-empty v-if="!totalErrors" description="还没有未通过的提交" :image-size="60" />
        <el-table v-else-if="tableView.errors" :data="data.problems" size="small">
          <el-table-column label="题目" min-width="140">
            <template #default="{ row }">{{ row.index + 1 }}. {{ row.title }}</template>
          </el-table-column>
          <el-table-column v-for="type in ERROR_TYPES" :key="type" :label="RESULTS[type].label" align="right" min-width="90">
            <template #default="{ row }">{{ row.errors[type] }}</template>
          </el-table-column>
          <el-table-column label="提交 / 通过" align="right" width="100">
            <template #default="{ row }">{{ row.submission_count }} / {{ row.ac_submission_count }}</template>
          </el-table-column>
        </el-table>
        <template v-else>
          <EChart :option="errorOption" height="300px" label="各题错误类型堆叠柱状图" />
          <div class="error-summary">
            <span v-for="type in ERROR_TYPES" :key="type" class="error-summary__item">
              <i class="swatch" :style="{ background: ERROR_COLORS[type] }" />
              {{ RESULTS[type].label }} {{ data.errors[type] }}（{{ errorShare(data.errors[type]) }}）
            </span>
          </div>
        </template>
      </el-card>

      <el-card shadow="never">
        <template #header>未提交名单（{{ data.not_submitted.length }} 人）</template>
        <p v-if="!data.not_submitted.length" class="muted">全班都已提交。</p>
        <div class="names">
          <el-tag v-for="student in data.not_submitted" :key="student.user_id" type="info" effect="plain">
            {{ student.real_name }} {{ student.student_no }}
          </el-tag>
        </div>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.stats-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 300px;
}




.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 16px;
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
  color: var(--el-text-color-primary);
  font-size: 24px;
  font-weight: 600;
}

.tile__sub {
  margin-top: 2px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.error-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 20px;
  margin-top: 8px;
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.error-summary__item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.names {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
