/**
 * 图表配色与基础样式（数据可视化规范，详见各项注释；亮色与暗色两套）。
 *
 * - 单系列图（成绩分布、各题满分率）用品牌藏青（设计说明书 12.2：图表主系列）；
 * - 多系列图的配色经色觉障碍校验（validate_palette.js，相邻色 CVD ΔE ≥ 8、正常视觉 ΔE ≥ 15），
 *   顺序固定，颜色跟随类别而不随排名变化；
 * - 部分颜色与白底对比度低于 3:1，因此每个图表都配有表格视图；
 * - 线 2px、标记点 8px 带 2px 白环、柱宽 ≤ 24px 顶端 4px 圆角，网格线为实线细线。
 */
import { useTheme } from '@/composables/useTheme'

// 图表画在 canvas 上，读不到 CSS 变量，所以按当前主题取色。
// 这些属性在构建图表配置时读取 isDark，页面因此会在切换主题时重新生成配置。
const LIGHT_INK = {
  primary: '#1f2433',
  secondary: '#4a5165',
  muted: '#6b7185',
  grid: '#e9ebf2',
  axis: '#cfd4e2',
  surface: '#ffffff',
  // 单系列主色：品牌藏青
  series: '#1e2a66',
}
const DARK_INK = {
  primary: '#e7e9f3',
  secondary: '#b6bbd0',
  muted: '#8d93ab',
  grid: '#2a3049',
  axis: '#3a4263',
  surface: '#1c2134',
  series: '#8c99ee',
}
const { isDark } = useTheme()

export const INK = {
  get primary() {
    return (isDark.value ? DARK_INK : LIGHT_INK).primary
  },
  get secondary() {
    return (isDark.value ? DARK_INK : LIGHT_INK).secondary
  },
  get muted() {
    return (isDark.value ? DARK_INK : LIGHT_INK).muted
  },
  get grid() {
    return (isDark.value ? DARK_INK : LIGHT_INK).grid
  },
  get axis() {
    return (isDark.value ? DARK_INK : LIGHT_INK).axis
  },
  get surface() {
    return (isDark.value ? DARK_INK : LIGHT_INK).surface
  },
  get series() {
    return (isDark.value ? DARK_INK : LIGHT_INK).series
  },
}

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


export function baseOption() {
  return {
    textStyle: { fontFamily: 'inherit', color: INK.secondary },
    grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
    tooltip: {
      backgroundColor: INK.surface,
      borderColor: INK.axis,
      textStyle: { color: INK.primary, fontSize: 13 },
      extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.16);',
    },
  }
}

export function categoryAxis(data, extra = {}) {
  return {
    type: 'category',
    data,
    axisLine: { lineStyle: { color: INK.axis } },
    axisTick: { show: false },
    axisLabel: { color: INK.muted, fontSize: 12, interval: 0, hideOverlap: true },
    ...extra,
  }
}

export function valueAxis(extra = {}) {
  return {
    type: 'value',
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: INK.muted, fontSize: 12 },
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

// 评测结果的图表配色，与 tokens.css 中的 --oj-v-*-fg 一致（图表读不到 CSS 变量）
const VERDICT_LIGHT = { AC: '#17803d', WA: '#c9302c', CE: '#9a2a7a', RE: '#b4351f', TLE: '#8a5a00', MLE: '#7a5a00', PAC: '#8a5a00', SE: '#566074' }
const VERDICT_DARK = { AC: '#5fd38a', WA: '#ff8b87', CE: '#f08fd0', RE: '#ff9d85', TLE: '#f0c25a', MLE: '#e6c150', PAC: '#f0c25a', SE: '#a9b0c6' }

export function verdictColor(result) {
  return (isDark.value ? VERDICT_DARK : VERDICT_LIGHT)[result] ?? INK.muted
}
