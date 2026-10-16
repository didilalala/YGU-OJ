// 作业状态，与后端 classroom.models.Assignment.status_at 一致；品牌橙不用于状态
export const ASSIGNMENT_STATUS = {
  not_started: { label: '未开始', type: 'info' },
  in_progress: { label: '进行中', type: 'primary' },
  late: { label: '可迟交', type: 'warning' },
  ended: { label: '已截止', type: 'info' },
}

/** 距离某时刻还有多久，如「2 天 3 小时」「45 分钟」；已过去返回空串 */
export function timeLeft(value, now = Date.now()) {
  const minutes = Math.floor((new Date(value).getTime() - now) / 60000)
  if (minutes < 0) return ''
  const days = Math.floor(minutes / 1440)
  const hours = Math.floor((minutes % 1440) / 60)
  if (days > 0) return `${days} 天 ${hours} 小时`
  if (hours > 0) return `${hours} 小时 ${minutes % 60} 分钟`
  return `${Math.max(minutes, 1)} 分钟`
}

export function latePolicy(assignment) {
  if (!assignment.allow_late) return '截止后不能提交'
  const penalty = Math.round(assignment.late_penalty * 100)
  return penalty ? `允许迟交，迟交得分扣 ${penalty}%` : '允许迟交，不扣分'
}

export function formatScore(value) {
  if (value === null || value === undefined) return '—'
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}
