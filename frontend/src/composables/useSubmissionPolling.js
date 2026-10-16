import { onBeforeUnmount, ref } from 'vue'

import { submissionApi } from '@/api/submission'

/**
 * 轮询评测结果，直到评测结束（设计说明书 8.1 第 9 步：每秒一次）。
 * 等待超过 30 秒后（判题机繁忙或重启）放慢到每 3 秒一次，减轻服务器压力。
 * 组件卸载或开始新的轮询时自动停止上一次。
 */
export function useSubmissionPolling() {
  const submission = ref(null)
  const error = ref('')
  let timer = null
  let generation = 0

  function stop() {
    clearTimeout(timer)
    timer = null
    generation += 1
  }

  async function start(id) {
    stop()
    const current = generation
    const startedAt = Date.now()
    error.value = ''

    const tick = async () => {
      try {
        const data = await submissionApi.detail(id, { silent: true })
        if (current !== generation) return
        submission.value = data
        if (data.is_finished) return
      } catch (err) {
        if (current !== generation) return
        // 404 等错误不会自行恢复，停止轮询；网络抖动则继续重试
        if (err?.code && err.code !== -1) {
          error.value = err.message || '获取评测结果失败'
          return
        }
      }
      const delay = Date.now() - startedAt > 30000 ? 3000 : 1000
      timer = setTimeout(tick, delay)
    }
    await tick()
  }

  onBeforeUnmount(stop)

  return { submission, error, start, stop }
}
