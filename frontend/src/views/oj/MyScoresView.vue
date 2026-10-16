<script setup>
/** 我的成绩：每个班级的学习曲线（我的得分率与班级平均对照）与成绩明细。 */
import { onMounted, reactive, ref } from 'vue'

import { statsApi } from '@/api/stats'
import EChart from '@/components/EChart.vue'
import StudentKnowledge from '@/components/StudentKnowledge.vue'
import { formatScore } from '@/utils/assignment'
import { INK, PRIMARY_SERIES, baseOption, categoryAxis, lineSeries, shortLabel, valueAxis } from '@/utils/chart'
import { formatDateTime } from '@/utils/judge'

const loading = ref(true)
const classes = ref([])
// 每个班级可切换为表格视图
const tableView = reactive({})

onMounted(async () => {
  try {
    classes.value = (await statsApi.mine()).classes
  } finally {
    loading.value = false
  }
})

const kindLabel = (point) => (point.kind === 'exam' ? '考试' : '作业')

function curveOption(points) {
  return {
    ...baseOption(),
    grid: { ...baseOption().grid, top: 40 },
    legend: { top: 0, itemWidth: 16, itemHeight: 8, textStyle: { color: INK.secondary } },
    tooltip: {
      ...baseOption().tooltip,
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: INK.axis } },
      formatter: (items) => {
        const p = points[items[0].dataIndex]
        return (
          `${kindLabel(p)}：${p.title}<br/>` +
          `我的得分 <b>${formatScore(p.score)}</b> / ${p.total_score}（${p.rate}%）${p.submitted ? '' : '，未提交'}<br/>` +
          `班级平均得分率 ${p.class_average_rate}%`
        )
      },
    },
    xAxis: categoryAxis(points.map((p) => shortLabel(p.title)), { boundaryGap: false }),
    yAxis: valueAxis({ max: 100, axisLabel: { color: INK.muted, formatter: '{value}%' } }),
    series: [
      // 突出「我的」，班级平均用灰色作参照
      lineSeries(PRIMARY_SERIES, {
        name: '我的得分率',
        data: points.map((p) => p.rate),
        endLabel: { show: true, color: INK.primary, formatter: '{c}%' },
        z: 3,
      }),
      lineSeries(INK.muted, { name: '班级平均', data: points.map((p) => p.class_average_rate), z: 2 }),
    ],
  }
}
</script>

<template>
  <div v-loading="loading" class="page">
    <el-card v-if="!loading && !classes.length" shadow="never">
      <el-empty description="你还没有加入班级，暂无成绩" />
    </el-card>

    <el-card v-for="item in classes" :key="item.class_id" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ item.class_name }}<span v-if="item.course" class="muted"> · {{ item.course }}</span></span>
          <el-switch v-model="tableView[item.class_id]" size="small" active-text="表格" />
        </div>
      </template>

      <el-empty v-if="!item.points.length" description="还没有已截止的作业或已公布成绩的考试" :image-size="60" />
      <template v-else>
        <div class="tile">
          <div class="tile__label">总得分率</div>
          <div class="tile__value">{{ item.rate }}%</div>
          <div class="tile__sub">共 {{ item.points.length }} 次作业与考试</div>
        </div>

        <el-table v-if="tableView[item.class_id]" :data="item.points" size="small">
          <el-table-column label="名称" min-width="180">
            <template #default="{ row }">{{ kindLabel(row) }}：{{ row.title }}</template>
          </el-table-column>
          <el-table-column label="时间" width="170">
            <template #default="{ row }">{{ formatDateTime(row.time) }}</template>
          </el-table-column>
          <el-table-column label="得分" width="100" align="right">
            <template #default="{ row }">
              <span v-if="!row.submitted" class="missing">未提交</span>
              <span v-else>{{ formatScore(row.score) }} / {{ row.total_score }}</span>
            </template>
          </el-table-column>
          <el-table-column label="得分率" width="80" align="right">
            <template #default="{ row }">{{ row.rate }}%</template>
          </el-table-column>
          <el-table-column label="班级平均" width="90" align="right">
            <template #default="{ row }">{{ row.class_average_rate }}%</template>
          </el-table-column>
        </el-table>
        <EChart v-else :option="curveOption(item.points)" height="280px" :label="`${item.class_name} 学习曲线`" />
      </template>
      <StudentKnowledge v-if="item.knowledge.length" :points="item.knowledge" />
    </el-card>
  </div>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 200px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.tile {
  display: inline-block;
  margin-bottom: 12px;
  padding: 10px 16px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
}

.tile__label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.tile__value {
  font-size: 24px;
  font-weight: 600;
}

.tile__sub {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.missing {
  color: var(--el-color-danger);
}
</style>
