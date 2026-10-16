<script setup>
/**
 * 班级知识点掌握度（设计说明书 9.4 知识点视角）：
 * 各知识点班级平均掌握度（由低到高，定位薄弱环节）与学生 × 知识点掌握度矩阵。
 */
import { computed, ref, watch } from 'vue'

import { statsApi } from '@/api/stats'
import EChart from '@/components/EChart.vue'
import {
  INK,
  MASTERY_STEPS,
  MASTERY_THRESHOLD,
  baseOption,
  barSeries,
  masteryStep,
  valueAxis,
} from '@/utils/chart'

const props = defineProps({
  classId: { type: Number, required: true },
})

const loading = ref(false)
const data = ref(null)
const tableView = ref(false)

async function load() {
  loading.value = true
  try {
    data.value = await statsApi.classKnowledge(props.classId)
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
}

watch(() => props.classId, load, { immediate: true })

// 知识点全名：下级显示为「上级 / 下级」
const pointNames = computed(() => {
  const byId = new Map((data.value?.points ?? []).map((p) => [p.id, p]))
  const names = new Map()
  for (const point of byId.values()) {
    const parent = byId.get(point.parent)
    names.set(point.id, parent ? `${parent.name} / ${point.name}` : point.name)
  }
  return names
})

const weakest = computed(() =>
  (data.value?.weakest ?? []).map((id) => data.value.points.find((p) => p.id === id)).filter(Boolean),
)

// 由低到高排列，最薄弱的在最上面
const sortedPoints = computed(() => [...(data.value?.points ?? [])].sort((a, b) => a.average_mastery - b.average_mastery))

const barOption = computed(() => {
  // 横向柱状图自下而上绘制，倒序后最低的显示在顶部
  const points = [...sortedPoints.value].reverse()
  return {
    ...baseOption(),
    grid: { ...baseOption().grid, right: 48 },
    tooltip: {
      ...baseOption().tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(30,42,102,0.06)' } },
      formatter: ([item]) => {
        const p = points[item.dataIndex]
        return `${pointNames.value.get(p.id)}（${p.problem_count} 题）<br/>平均掌握度 <b>${p.average_mastery}%</b><br/>通过率 ${p.average_pass_rate}%`
      },
    },
    xAxis: valueAxis({ max: 100, axisLabel: { color: INK.muted, formatter: '{value}%' } }),
    yAxis: {
      type: 'category',
      data: points.map((p) => pointNames.value.get(p.id)),
      axisLine: { lineStyle: { color: INK.axis } },
      axisTick: { show: false },
      axisLabel: { color: INK.secondary, width: 140, overflow: 'truncate' },
    },
    series: [
      barSeries({
        data: points.map((p) => p.average_mastery),
        itemStyle: { color: INK.series, borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', color: INK.secondary, formatter: '{c}%' },
        markLine: {
          symbol: 'none',
          silent: true,
          lineStyle: { color: INK.muted, type: 'solid', width: 1 },
          label: { formatter: `${MASTERY_THRESHOLD}%`, color: INK.muted, position: 'end' },
          data: [{ xAxis: MASTERY_THRESHOLD }],
        },
      }),
    ],
  }
})

const chartHeight = computed(() => `${Math.max(160, sortedPoints.value.length * 36 + 48)}px`)
</script>

<template>
  <el-card v-loading="loading" shadow="never">
    <template #header>
      <div class="card-header">
        <span>知识点掌握度</span>
        <el-switch v-if="data?.points.length" v-model="tableView" size="small" active-text="表格" />
      </div>
    </template>

    <el-empty
      v-if="data && !data.points.length"
      description="作业与考试中的题目还没有标注知识点，可在题库中为题目添加知识点"
      :image-size="60"
    />

    <template v-else-if="data">
      <p class="hint">
        掌握度 = 该知识点（含下级）各题最佳得分比例的平均，作业、考试与平时练习的提交都计入；共
        {{ data.problem_count }} 道题<template v-if="data.untagged_problem_count">，其中 {{ data.untagged_problem_count }} 道未标注知识点、未计入</template>。
      </p>
      <el-alert v-if="weakest.length" type="warning" :closable="false" show-icon class="weakest">
        <template #title>
          薄弱知识点：
          <span v-for="(point, index) in weakest" :key="point.id">
            {{ index ? '、' : '' }}{{ pointNames.get(point.id) }}（{{ point.average_mastery }}%）
          </span>
        </template>
      </el-alert>

      <el-table v-if="tableView" :data="sortedPoints" size="small">
        <el-table-column label="知识点" min-width="180">
          <template #default="{ row }">{{ pointNames.get(row.id) }}</template>
        </el-table-column>
        <el-table-column prop="problem_count" label="题数" width="70" align="right" />
        <el-table-column label="平均掌握度" width="110" align="right">
          <template #default="{ row }">{{ row.average_mastery }}%</template>
        </el-table-column>
        <el-table-column label="通过率" width="90" align="right">
          <template #default="{ row }">{{ row.average_pass_rate }}%</template>
        </el-table-column>
        <el-table-column label="题目" min-width="200">
          <template #default="{ row }">{{ row.problems.map((p) => p.title).join('、') }}</template>
        </el-table-column>
      </el-table>
      <EChart v-else :option="barOption" :height="chartHeight" label="各知识点班级平均掌握度横向柱状图，由低到高排列" />

      <h4 class="section-title">学生 × 知识点</h4>
      <div class="legend">
        <span v-for="(step, index) in MASTERY_STEPS" :key="step.min" class="legend__item">
          <i :style="{ background: step.color }" />
          {{ step.min }}–{{ MASTERY_STEPS[index + 1]?.min ?? 100 }}%
        </span>
      </div>
      <el-table :data="data.students" size="small" border max-height="520" class="matrix">
        <el-table-column prop="student_no" label="学号" width="110" fixed />
        <el-table-column prop="real_name" label="姓名" width="80" fixed />
        <el-table-column
          v-for="point in data.points"
          :key="point.id"
          :label="point.name"
          min-width="88"
          align="center"
        >
          <template #header>
            <span :title="pointNames.get(point.id)">{{ point.depth ? '└ ' : '' }}{{ point.name }}</span>
          </template>
          <template #default="{ row }">
            <span
              class="cell"
              :style="{
                background: masteryStep(row.mastery[point.id]).color,
                color: masteryStep(row.mastery[point.id]).text,
              }"
              :title="`${row.real_name}：${pointNames.get(point.id)} 掌握度 ${row.mastery[point.id]}%，通过 ${row.accepted[point.id]}/${point.problem_count} 题`"
            >
              {{ Math.round(row.mastery[point.id]) }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </template>
  </el-card>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.hint {
  margin: 0 0 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.weakest {
  margin-bottom: 12px;
}

.section-title {
  margin: 20px 0 8px;
  font-size: 14px;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin-bottom: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.legend__item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.legend__item i {
  display: inline-block;
  width: 14px;
  height: 10px;
  border-radius: 2px;
}

.matrix :deep(.el-table__cell) {
  padding: 2px 0;
}

.cell {
  display: block;
  margin: 0 2px;
  padding: 4px 0;
  border-radius: 3px;
  font-variant-numeric: tabular-nums;
}
</style>
