import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { authApi } from '@/api/auth'
import { useExamStore } from '@/stores/exam'
import { STAFF_ROLES } from '@/utils/constants'
import { tokenStorage } from '@/utils/token'

export const useUserStore = defineStore('user', () => {
  const user = ref(null)
  const token = ref(tokenStorage.access)

  const isLoggedIn = computed(() => !!token.value)
  const role = computed(() => user.value?.role ?? null)
  const isStaff = computed(() => STAFF_ROLES.includes(role.value))
  const mustChangePassword = computed(() => !!user.value?.is_initial_password)

  async function login(form) {
    const data = await authApi.login(form)
    tokenStorage.set(data.access, data.refresh)
    token.value = data.access
    user.value = data.user
  }

  // 注册成功后直接以返回的令牌登录
  function setSession(data) {
    tokenStorage.set(data.access, data.refresh)
    token.value = data.access
    user.value = data.user
  }

  async function fetchMe() {
    user.value = await authApi.me({ silent: true })
  }

  function logout() {
    // 换人登录时不能沿用上一位学生的考试状态
    useExamStore().clear()
    tokenStorage.clear()
    token.value = null
    user.value = null
  }

  return { user, isLoggedIn, role, isStaff, mustChangePassword, login, setSession, fetchMe, logout }
})
