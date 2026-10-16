import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { authApi } from '@/api/auth'

// 加载失败时使用的默认值，与后端 options.site.SETTINGS 一致
const FALLBACK_SETTINGS = {
  site_name: '阳光学院在线评测平台',
  home_announcement: '',
  allow_registration: true,
  submit_interval_seconds: 5,
  max_code_kb: 64,
  default_time_limit_ms: 1000,
  default_memory_limit_mb: 256,
}

/**
 * 网站参数与已启用的编程语言（M6）。应用启动时加载一次，之后各页面从这里读取，
 * 管理员修改后刷新页面即可生效。
 */
export const useSiteStore = defineStore('site', () => {
  const settings = ref({ ...FALLBACK_SETTINGS })
  const languages = ref([])
  const loaded = ref(false)

  async function load() {
    try {
      const data = await authApi.site({ silent: true })
      settings.value = { ...FALLBACK_SETTINGS, ...data.settings }
      languages.value = data.languages
    } catch {
      // 网络不通时使用默认值，页面仍可浏览
    } finally {
      loaded.value = true
    }
  }

  const byKey = computed(() => new Map(languages.value.map((lang) => [lang.key, lang])))

  function languageName(key) {
    return byKey.value.get(key)?.name ?? key
  }

  function languageMonaco(key) {
    return byKey.value.get(key)?.monaco_id ?? 'plaintext'
  }

  function starterCode(key) {
    return byKey.value.get(key)?.starter_code ?? ''
  }

  return { settings, languages, loaded, load, languageName, languageMonaco, starterCode }
})
