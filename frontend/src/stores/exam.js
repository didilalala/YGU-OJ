import { ref } from 'vue'
import { defineStore } from 'pinia'

import { examApi } from '@/api/exam'

// 进行中考试的缓存时间：路由跳转时不必每次都请求
const CACHE_MS = 30 * 1000

/**
 * 学生当前进行中、且锁定题库的考试。考试期间前端把题库、作业等页面重定向到考场，
 * 后端同样会拒绝这些请求（见 contest.access）。
 */
export const useExamStore = defineStore('exam', () => {
  const active = ref(null)
  let fetchedAt = 0

  async function refresh({ force = false } = {}) {
    if (!force && Date.now() - fetchedAt < CACHE_MS) return active.value
    try {
      active.value = await examApi.active({ silent: true })
    } catch {
      // 网络错误时保留上次的结果
    }
    fetchedAt = Date.now()
    return active.value
  }

  function clear() {
    active.value = null
    fetchedAt = 0
  }

  return { active, refresh, clear }
})
