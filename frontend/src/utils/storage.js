// localStorage 在隐私模式等情况下可能不可用，读写失败时静默忽略

export function loadLocal(key, fallback = null) {
  try {
    const value = localStorage.getItem(key)
    return value === null ? fallback : value
  } catch {
    return fallback
  }
}

export function saveLocal(key, value) {
  try {
    if (value === null || value === undefined) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    // 忽略
  }
}
