<script setup>
/** 我的成绩：每个班级的学习曲线（我的得分率与班级平均对照）与成绩明细。 */
import { onMounted, reactive, ref } from 'vue'

import { statsApi } from '@/api/stats'
import EChart from '@/components/EChart.vue'
import LearnTabs from '@/components/LearnTabs.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatCard from '@/components/ui/StatCard.vue'
import StudentKnowledge from '@/components/StudentKnowledge.vue'
import { formatScore } from '@/utils/assignment'
import { INK, baseOption, categoryAxis, lineSeries, shortLabel, valueAxis } from '@/utils/chart'
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

const lastPoint = (item) => item.points[item.points.length - 1]
// 最近一次得分率与班级平均的差，保留整数
const diff = (item) => Math.round(lastPoint(item).rate - lastPoint(item).class_average_rate)
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
      lineSeries({
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
  <div>
    <PageHeader title="我的成绩" subtitle="作业与考试的得分趋势，对比班级平均水平" />
    <LearnTabs />

    <el-skeleton v-if="loading" animated :rows="6" />
    <EmptyState v-else-if="!classes.length" title="你还没有加入班级" description="加入班级并完成作业后，成绩会显示在这里。" />

    <section v-for="item in classes" :key="item.class_id" class="class">
      <header class="class__head">
        <h2>
          {{ item.class_name }}
          <span v-if="item.course" class="muted class__course">{{ item.course }}</span>
        </h2>
        <el-switch v-if="item.points.length" v-model="tableView[item.class_id]" active-text="表格视图" />
      </header>

      <EmptyState
        v-if="!item.points.length"
        compact
        title="暂无成绩"
        description="还没有已截止的作业或已公布成绩的考试"
      />
      <template v-else>
        <div class="stats">
          <StatCard accent label="总得分率" :value="item.rate" unit="%" :hint="`共 ${item.points.length} 次作业与考试`" />
          <StatCard label="最近一次" :value="lastPoint(item).rate" unit="%" :hint="lastPoint(item).title" />
          <StatCard
            label="对比班级平均"
            :value="diff(item) >= 0 ? `+${diff(item)}` : `${diff(item)}`"
            unit="%"
            :hint="diff(item) >= 0 ? '高于班级平均水平' : '低于班级平均水平'"
          />
        </div>

        <el-card shadow="never" class="class__chart">
          <el-table v-if="tableView[item.class_id]" :data="item.points">
            <el-table-column label="名称" min-width="180">
              <template #default="{ row }">{{ kindLabel(row) }}：{{ row.title }}</template>
            </el-table-column>
            <el-table-column label="时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.time) }}</template>
            </el-table-column>
            <el-table-column label="得分" width="110" align="right" class-name="num">
              <template #default="{ row }">
                <span v-if="!row.submitted" class="missing">未提交</span>
                <span v-else>{{ formatScore(row.score) }} / {{ row.total_score }}</span>
              </template>
            </el-table-column>
            <el-table-column label="得分率" width="90" align="right" class-name="num">
              <template #default="{ row }">{{ row.rate }}%</template>
            </el-table-column>
            <el-table-column label="班级平均" width="100" align="right" class-name="num">
              <template #default="{ row }">{{ row.class_average_rate }}%</template>
            </el-table-column>
          </el-table>
          <EChart v-else :option="curveOption(item.points)" height="300px" :label="`${item.class_name} 学习曲线`" />
        </el-card>
      </template>
      <StudentKnowledge v-if="item.knowledge.length" :points="item.knowledge" />
    </section>
  </div>
</template>

<style scoped>
.class + .class {
  margin-top: var(--oj-space-6);
}

.class__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--oj-space-3);
}

.class__head h2 {
  margin: 0;
  font-size: var(--oj-fs-lg);
}

.class__course {
  margin-left: 8px;
  font-size: var(--oj-fs-sm);
  font-weight: 400;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--oj-space-4);
  margin-bottom: var(--oj-space-4);
}

.class__chart {
  margin-bottom: var(--oj-space-4);
}

.missing {
  color: var(--oj-v-wa-fg);
}
</style>
