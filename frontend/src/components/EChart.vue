<script setup>
/**
 * ECharts 容器。按需引入用到的图表类型与组件，避免打包整个 ECharts。
 *
 *   <EChart :option="option" height="280px" label="成绩分布柱状图" />
 */
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, RadarChart } from 'echarts/charts'
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  RadarComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart,
  LineChart,
  RadarChart,
  AriaComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  RadarComponent,
  TooltipComponent,
  CanvasRenderer,
])

const props = defineProps({
  option: { type: Object, required: true },
  // 包含坐标轴标签在内的总高度
  height: { type: String, default: '280px' },
  // 屏幕阅读器读出的图表说明
  label: { type: String, default: '' },
})

const container = ref()
const chart = shallowRef()
let observer = null

function render() {
  chart.value?.setOption({ ...props.option, aria: { enabled: true, label: { description: props.label || undefined } } }, true)
}

onMounted(() => {
  chart.value = echarts.init(container.value)
  render()
  observer = new ResizeObserver(() => chart.value?.resize())
  observer.observe(container.value)
})

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  observer?.disconnect()
  chart.value?.dispose()
})
</script>

<template>
  <div ref="container" class="echart" :style="{ height }" role="img" :aria-label="label" />
</template>

<style scoped>
.echart {
  width: 100%;
}
</style>
