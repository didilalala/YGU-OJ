<script setup>
/**
 * 学生的知识点掌握度（设计说明书 9.4 学生视角：知识点掌握雷达图）。
 *
 * 雷达图只在 3–8 个维度时清晰，且各维度应属同一层级（上级已包含下级的题目，混在一起会重复计入）：
 * 顶层知识点有 3–8 个时只画顶层；否则全部知识点不超过 8 个时全画，再否则取题目最多的 8 个；
 * 少于 3 个时改用横向柱状图。「我的」用藏青突出，班级平均用灰色作参照；全部数据见表格视图。
 */
import { computed, ref } from 'vue'

import EChart from '@/components/EChart.vue'
import { INK, MASTERY_THRESHOLD, PRIMARY_SERIES, baseOption, barSeries, valueAxis } from '@/utils/chart'

const MAX_AXES = 8
const MIN_AXES = 3

const props = defineProps({
  points: { type: Array, required: true },
})

const tableView = ref(false)

const byId = computed(() => new Map(props.points.map((p) => [p.id, p])))
const fullName = (point) => {
  const parent = byId.value.get(point.parent)
  return parent ? `${parent.name} / ${point.name}` : point.name
}

const chartPoints = computed(() => {
  const roots = props.points.filter((p) => p.depth === 0)
  if (roots.length >= MIN_AXES && roots.length <= MAX_AXES) return roots
  if (props.points.length <= MAX_AXES) return props.points
  return [...props.points].sort((a, b) => b.problem_count - a.problem_count).slice(0, MAX_AXES)
})
const useRadar = computed(() => chartPoints.value.length >= MIN_AXES)
const omitted = computed(() => props.points.length - chartPoints.value.length)

// 需要加强的知识点：下级已列出时不再列出上级（上级的掌握度由下级汇总而来，重复列出没有新信息）
const weak = computed(() => {
  const below = props.points.filter((p) => p.mastery < MASTERY_THRESHOLD)
  const parentsWithWeakChildren = new Set(below.map((p) => p.parent).filter(Boolean))
  return below.filter((p) => !parentsWithWeakChildren.has(p.id)).sort((a, b) => a.mastery - b.mastery)
})

const radarOption = computed(() => {
  const points = chartPoints.value
  return {
    ...baseOption(),
    legend: { bottom: 0, itemWidth: 16, itemHeight: 8, textStyle: { color: INK.secondary } },
    tooltip: {
      ...baseOption().tooltip,
      trigger: 'item',
      formatter: () =>
        points.map((p) => `${fullName(p)}：我的 <b>${p.mastery}%</b> · 班级 ${p.class_average}%`).join('<br/>'),
    },
    radar: {
      center: ['50%', '48%'],
      radius: '62%',
      indicator: points.map((p) => ({ name: p.name, max: 100 })),
      axisName: { color: INK.secondary, fontSize: 12 },
      splitLine: { lineStyle: { color: INK.grid, width: 1 } },
      axisLine: { lineStyle: { color: INK.grid } },
      splitArea: { show: false },
    },
    series: [
      {
        type: 'radar',
        symbol: 'circle',
        symbolSize: 8,
        data: [
          {
            name: '我的掌握度',
            value: points.map((p) => p.mastery),
            lineStyle: { color: PRIMARY_SERIES, width: 2 },
            itemStyle: { color: PRIMARY_SERIES, borderColor: INK.surface, borderWidth: 2 },
            areaStyle: { color: PRIMARY_SERIES, opacity: 0.1 },
            z: 3,
          },
          {
            name: '班级平均',
            value: points.map((p) => p.class_average),
            lineStyle: { color: INK.muted, width: 2 },
            itemStyle: { color: INK.muted, borderColor: INK.surface, borderWidth: 2 },
          },
        ],
      },
    ],
  }
})

const barOption = computed(() => {
  const points = chartPoints.value
  return {
    ...baseOption(),
    grid: { ...baseOption().grid, right: 48 },
    tooltip: {
      ...baseOption().tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(30,42,102,0.06)' } },
      formatter: ([item]) => {
        const p = points[item.dataIndex]
        return `${fullName(p)}<br/>我的 <b>${p.mastery}%</b> · 班级 ${p.class_average}%`
      },
    },
    xAxis: valueAxis({ max: 100, axisLabel: { color: INK.muted, formatter: '{value}%' } }),
    yAxis: {
      type: 'category',
      data: points.map((p) => p.name),
      axisLine: { lineStyle: { color: INK.axis } },
      axisTick: { show: false },
      axisLabel: { color: INK.secondary },
    },
    series: [
      barSeries({
        data: points.map((p) => p.mastery),
        itemStyle: { color: PRIMARY_SERIES, borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', color: INK.secondary, formatter: '{c}%' },
      }),
    ],
  }
})
</script>

<template>
  <section class="knowledge">
    <div class="knowledge__header">
      <h4>知识点掌握度</h4>
      <el-switch v-model="tableView" size="small" active-text="表格" />
    </div>
    <p class="hint">按作业与考试中各知识点题目的最佳得分计算，平时练习的提交也算。</p>

    <el-alert v-if="weak.length" type="warning" :closable="false" show-icon class="weak">
      <template #title>
        需要加强：<span v-for="(p, i) in weak" :key="p.id">{{ i ? '、' : '' }}{{ fullName(p) }}（{{ p.mastery }}%）</span>
      </template>
    </el-alert>

    <el-table v-if="tableView" :data="points" size="small">
      <el-table-column label="知识点" min-width="160">
        <template #default="{ row }">{{ fullName(row) }}</template>
      </el-table-column>
      <el-table-column label="我的掌握度" width="100" align="right">
        <template #default="{ row }">{{ row.mastery }}%</template>
      </el-table-column>
      <el-table-column label="已通过" width="90" align="right">
        <template #default="{ row }">{{ row.accepted_count }} / {{ row.problem_count }}</template>
      </el-table-column>
      <el-table-column label="班级平均" width="90" align="right">
        <template #default="{ row }">{{ row.class_average }}%</template>
      </el-table-column>
    </el-table>
    <template v-else>
      <EChart
        v-if="useRadar"
        :option="radarOption"
        height="340px"
        label="知识点掌握度雷达图，我的掌握度与班级平均对照"
      />
      <EChart
        v-else
        :option="barOption"
        :height="`${chartPoints.length * 44 + 48}px`"
        label="知识点掌握度横向柱状图"
      />
      <p v-if="omitted > 0" class="hint">图中显示 {{ chartPoints.length }} 个知识点，全部 {{ points.length }} 个（含下级知识点）见表格。</p>
    </template>
  </section>
</template>

<style scoped>
.knowledge {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.knowledge__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.knowledge__header h4 {
  margin: 0;
  font-size: 15px;
}

.hint {
  margin: 4px 0 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.weak {
  margin-bottom: 12px;
}
</style>
