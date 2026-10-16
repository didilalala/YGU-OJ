/**
 * 评测相关的展示常量，与后端 submission.models.Submission 保持一致。
 *
 * 状态色遵循设计说明书 12.2：通过为绿、错误为红、超时与超内存为黄、等待与评测中为灰；
 * 品牌橙不用于任何状态。
 */

// tone 对应 tokens.css 中的 --oj-v-<tone>-fg/bg/bd；short 用于测试点色块等窄位置
export const RESULTS = {
  PENDING: { label: '等待评测', short: '等待', type: 'info', tone: 'wait' },
  JUDGING: { label: '评测中', short: '评测中', type: 'info', tone: 'wait' },
  AC: { label: '通过', short: 'AC', type: 'success', tone: 'ac' },
  WA: { label: '答案错误', short: 'WA', type: 'danger', tone: 'wa' },
  TLE: { label: '超出时间限制', short: 'TLE', type: 'warning', tone: 'tle' },
  MLE: { label: '超出内存限制', short: 'MLE', type: 'warning', tone: 'mle' },
  RE: { label: '运行错误', short: 'RE', type: 'danger', tone: 're' },
  CE: { label: '编译错误', short: 'CE', type: 'danger', tone: 'ce' },
  PAC: { label: '部分正确', short: 'PAC', type: 'warning', tone: 'pac' },
  SE: { label: '系统错误', short: 'SE', type: 'info', tone: 'se' },
}

export const FINISHED_RESULTS = Object.keys(RESULTS).filter((key) => !['PENDING', 'JUDGING'].includes(key))

export const DIFFICULTIES = {
  easy: { label: '简单', type: 'success', tone: 'ac' },
  medium: { label: '中等', type: 'warning', tone: 'tle' },
  hard: { label: '困难', type: 'danger', tone: 'wa' },
}

export function formatMemory(kb) {
  if (kb == null) return '—'
  return kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb} KB`
}

export function formatTime(ms) {
  return ms == null ? '—' : `${ms} ms`
}

export function passRate(problem) {
  if (!problem.submission_count) return '—'
  return `${((problem.accepted_count / problem.submission_count) * 100).toFixed(1)}%`
}

export function formatDateTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
}

/** 通过率的数值（0–100），无提交时为 null */
export function passRateValue(problem) {
  if (!problem.submission_count) return null
  return (problem.accepted_count / problem.submission_count) * 100
}

/** 相对时间：刚刚 / 5 分钟前 / 3 小时前 / 2 天前，超过 30 天显示日期 */
export function timeAgo(value) {
  if (!value) return '—'
  const diff = (Date.now() - new Date(value).getTime()) / 1000
  if (diff < 45) return '刚刚'
  if (diff < 3600) return `${Math.round(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.round(diff / 3600)} 小时前`
  if (diff < 86400 * 30) return `${Math.round(diff / 86400)} 天前`
  return new Date(value).toLocaleDateString('zh-CN')
}
