/**
 * 图表配色与基础样式（数据可视化规范，详见各项注释）。
 *
 * - 单系列图（成绩分布、各题满分率）用品牌藏青（设计说明书 12.2：图表主系列）；
 * - 多系列图的配色经色觉障碍校验（validate_palette.js，相邻色 CVD ΔE ≥ 8、正常视觉 ΔE ≥ 15），
 *   顺序固定，颜色跟随类别而不随排名变化；
 * - 部分颜色与白底对比度低于 3:1，因此每个图表都配有表格视图；
 * - 线 2px、标记点 8px 带 2px 白环、柱宽 ≤ 24px 顶端 4px 圆角，网格线为实线细线。
 */

export const INK = {
  primary: '#303133',
  secondary: '#606266',
  muted: '#909399',
  grid: '#ebeef5',
  axis: '#dcdfe6',
  surface: '#ffffff',
}

// 单系列主色：品牌藏青
export const PRIMARY_SERIES = '#1e2a66'

// 两条趋势线（平均得分率、提交率）：已校验
export const TREND_COLORS = ['#2a78d6', '#1baf7a']

// 错误类型（不含通过），顺序与后端 stats.service.ERROR_TYPES 一致；已校验相邻色
export const ERROR_TYPES = ['WA', 'CE', 'TLE', 'MLE', 'RE', 'PAC']
export const ERROR_COLORS = {
  WA: '#2a78d6',
  CE: '#e34948',
  TLE: '#eda100',
  MLE: '#e87ba4',
  RE: '#6250d6',
  PAC: '#1baf7a',
}

const axisLabel = { color: INK.muted, fontSize: 12 }

export function baseOption() {
  return {
    textStyle: { fontFamily: 'inherit', color: INK.secondary },
    grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
    tooltip: {
      backgroundColor: INK.surface,
      borderColor: INK.axis,
      textStyle: { color: INK.primary, fontSize: 13 },
      extraCssText: 'box-shadow: 0 2px 8px rgba(0,0,0,0.08);',
    },
  }
}

export function categoryAxis(data, extra = {}) {
  return {
    type: 'category',
    data,
    axisLine: { lineStyle: { color: INK.axis } },
    axisTick: { show: false },
    axisLabel: { ...axisLabel, interval: 0, hideOverlap: true },
    ...extra,
  }
}

export function valueAxis(extra = {}) {
  return {
    type: 'value',
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel,
    splitLine: { lineStyle: { color: INK.grid, type: 'solid', width: 1 } },
    ...extra,
  }
}

export function barSeries(extra = {}) {
  return {
    type: 'bar',
    barMaxWidth: 24,
    itemStyle: { borderRadius: [4, 4, 0, 0] },
    emphasis: { focus: 'series' },
    ...extra,
  }
}

export function lineSeries(color, extra = {}) {
  return {
    type: 'line',
    lineStyle: { width: 2, color, cap: 'round', join: 'round' },
    itemStyle: { color, borderColor: INK.surface, borderWidth: 2 },
    symbol: 'circle',
    symbolSize: 8,
    emphasis: { scale: 1.4 },
    ...extra,
  }
}

// 掌握度矩阵的单色顺序色阶（浅 → 深，蓝色），按 0–20–40–60–80–100% 分 5 档。
// 格内文字与底色的对比度均 ≥ 5:1（浅色三档用深色字，深色两档用白字）
export const MASTERY_STEPS = [
  { min: 0, color: '#cde2fb', text: INK.primary },
  { min: 20, color: '#9ec5f4', text: INK.primary },
  { min: 40, color: '#6da7ec', text: INK.primary },
  { min: 60, color: '#256abf', text: '#ffffff' },
  { min: 80, color: '#184f95', text: '#ffffff' },
]

export function masteryStep(value) {
  return [...MASTERY_STEPS].reverse().find((step) => value >= step.min) ?? MASTERY_STEPS[0]
}

// 低于此掌握度视为需要加强
export const MASTERY_THRESHOLD = 60

/** 截断过长的类别名（图上），完整名称在提示框与表格中显示 */
export function shortLabel(text, max = 8) {
  return text.length > max ? `${text.slice(0, max)}…` : text
}
