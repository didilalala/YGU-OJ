import axios from 'axios'
import { ElMessage } from 'element-plus'

import { EXAM_LOCKED_CODE } from '@/utils/exam'
import { tokenStorage } from '@/utils/token'

/**
 * 统一请求实例。
 *
 * 后端响应格式为 { code, message, data }：成功时直接返回 data；
 * 失败时弹出 message 并 reject。传入 { silent: true } 可不弹提示。
 * 访问令牌过期（401）时自动用刷新令牌换新令牌并重发一次请求。
 */
const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

request.interceptors.request.use((config) => {
  const token = tokenStorage.access
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing = null

function refreshAccessToken() {
  if (!refreshing) {
    refreshing = axios
      .post('/api/auth/refresh', { refresh: tokenStorage.refresh })
      .then((res) => {
        tokenStorage.access = res.data.data.access
      })
      .finally(() => {
        refreshing = null
      })
  }
  return refreshing
}

function redirectToLogin() {
  tokenStorage.clear()
  const redirect = encodeURIComponent(location.pathname + location.search)
  if (location.pathname !== '/login') location.href = `/login?redirect=${redirect}`
}

request.interceptors.response.use(
  (res) => {
    // 删除等接口返回 204，没有响应体
    if (res.status === 204) return null
    // 文件下载直接返回 Blob
    if (res.config.responseType === 'blob') return res.data
    const body = res.data
    if (body && body.code !== 0) {
      ElMessage.error(body.message)
      return Promise.reject(body)
    }
    return body.data
  },
  async (error) => {
    const { response, config = {} } = error
    const isAuthRequest = config.url?.startsWith('/auth/')

    if (response?.status === 401 && !isAuthRequest && !config._retried && tokenStorage.refresh) {
      config._retried = true
      try {
        await refreshAccessToken()
        return request(config)
      } catch {
        redirectToLogin()
      }
    }

    // 考试期间访问考试以外的内容：回到考场
    if (response?.status === 403 && response.data?.code === EXAM_LOCKED_CODE) {
      const examPath = `/exams/${response.data.data.exam_id}`
      if (location.pathname !== examPath) {
        ElMessage.warning(response.data.message)
        location.href = examPath
      }
      return Promise.reject(response.data)
    }

    const message =
      response?.data?.message ?? (response ? `请求失败（${response.status}）` : '网络错误，请稍后重试')
    if (!config.silent) ElMessage.error(message)
    return Promise.reject(response?.data ?? { code: -1, message })
  },
)

export default request
