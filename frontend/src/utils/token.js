const ACCESS_KEY = 'oj_access_token'
const REFRESH_KEY = 'oj_refresh_token'

function read(key) {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key, value) {
  try {
    if (value) localStorage.setItem(key, value)
    else localStorage.removeItem(key)
  } catch {
    // 隐私模式等情况下 localStorage 不可用，令牌只在本次页面内有效
  }
}

export const tokenStorage = {
  get access() {
    return read(ACCESS_KEY)
  },
  set access(value) {
    write(ACCESS_KEY, value)
  },
  get refresh() {
    return read(REFRESH_KEY)
  },
  set(access, refresh) {
    write(ACCESS_KEY, access)
    write(REFRESH_KEY, refresh)
  },
  clear() {
    write(ACCESS_KEY, null)
    write(REFRESH_KEY, null)
  },
}
