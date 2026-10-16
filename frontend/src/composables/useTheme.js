import { ref } from 'vue'

const STORAGE_KEY = 'oj-theme'

// light | dark | auto（跟随系统）
const mode = ref('auto')
const isDark = ref(false)
let media = null

function apply() {
  const dark = mode.value === 'dark' || (mode.value === 'auto' && media?.matches)
  isDark.value = dark
  document.documentElement.classList.toggle('dark', dark)
}

/** 应用启动时调用一次，在页面渲染前设置好主题，避免闪烁 */
export function initTheme() {
  try {
    mode.value = localStorage.getItem(STORAGE_KEY) || 'auto'
  } catch {
    // 隐私模式下读不到存储，使用默认值
  }
  media = window.matchMedia('(prefers-color-scheme: dark)')
  media.addEventListener('change', apply)
  apply()
}

export function useTheme() {
  function setMode(value) {
    mode.value = value
    try {
      localStorage.setItem(STORAGE_KEY, value)
    } catch {
      // 忽略
    }
    apply()
  }

  function toggle() {
    setMode(isDark.value ? 'light' : 'dark')
  }

  return { mode, isDark, setMode, toggle }
}
