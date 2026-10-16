/**
 * 评测相关的展示常量，与后端 submission.models.Submission 保持一致。
 *
 * 状态色遵循设计说明书 12.2：通过为绿、错误为红、超时与超内存为黄、等待与评测中为灰；
 * 品牌橙不用于任何状态。
 */

export const RESULTS = {
  PENDING: { label: '等待评测', type: 'info' },
  JUDGING: { label: '评测中', type: 'info' },
  AC: { label: '通过', type: 'success' },
  WA: { label: '答案错误', type: 'danger' },
  TLE: { label: '超出时间限制', type: 'warning' },
  MLE: { label: '超出内存限制', type: 'warning' },
  RE: { label: '运行错误', type: 'danger' },
  CE: { label: '编译错误', type: 'danger' },
  PAC: { label: '部分正确', type: 'warning' },
  SE: { label: '系统错误', type: 'info' },
}

export const FINISHED_RESULTS = Object.keys(RESULTS).filter((key) => !['PENDING', 'JUDGING'].includes(key))

export const DIFFICULTIES = {
  easy: { label: '简单', type: 'success' },
  medium: { label: '中等', type: 'warning' },
  hard: { label: '困难', type: 'danger' },
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
