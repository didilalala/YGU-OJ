import { onBeforeUnmount, ref } from 'vue'

/**
 * 响应式媒体查询。el-table 的列用 CSS 隐藏后仍占宽度，窄屏下需用 v-if 去掉列。
 *
 *   const isMobile = useMediaQuery('(max-width: 640px)')
 */
export function useMediaQuery(query) {
  const media = window.matchMedia(query)
  const matches = ref(media.matches)
  const update = (event) => (matches.value = event.matches)
  media.addEventListener('change', update)
  onBeforeUnmount(() => media.removeEventListener('change', update))
  return matches
}
