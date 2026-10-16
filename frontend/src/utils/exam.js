// 与后端 contest.access.EXAM_LOCKED_CODE 一致：考试期间访问考试以外的内容
export const EXAM_LOCKED_CODE = 40301

export const EXAM_STATUS = {
  not_started: { label: '未开始', type: 'info' },
  in_progress: { label: '进行中', type: 'danger' },
  ended: { label: '已结束', type: 'info' },
}

export const RULE_LABELS = {
  ACM: 'ACM 赛制',
  OI: 'OI 赛制',
}

export const RULE_TIPS = {
  ACM: '每题只有通过才得分；按通过题数排名，同题数按罚时（通过用时 + 每次错误提交 20 分钟）',
  OI: '每题按通过测试点的比例得分，取最高分；按总分排名',
}

/** 秒数格式化为 h:mm:ss */
export function formatDuration(seconds) {
  const s = Math.max(0, Math.floor(seconds))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${h}:${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

/**
 * 服务器时间校准：学生电脑的时钟可能不准，倒计时以服务器时间为准。
 * offset = 服务器时间 - 本地时间（毫秒）
 */
export function serverOffset(serverTime) {
  return serverTime ? new Date(serverTime).getTime() - Date.now() : 0
}
