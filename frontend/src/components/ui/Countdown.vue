<script setup>
/**
 * 倒计时。按剩余时间自动变色：> 1 小时常规，≤ 1 小时强调，≤ 10 分钟红色。
 * offset 为服务器时间 - 本地时间（毫秒），见 utils/exam.serverOffset。
 *
 *   <Countdown :end="exam.end_time" :offset="offset" @finish="onEnd" />
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { formatDuration } from '@/utils/exam'

const props = defineProps({
  end: { type: String, required: true },
  offset: { type: Number, default: 0 },
  // 只显示到「天/小时」的粗略形式，用于列表
  coarse: { type: Boolean, default: false },
})
const emit = defineEmits(['finish'])

const now = ref(Date.now())
let timer = null
let finished = false

const left = computed(() => Math.max(0, (new Date(props.end).getTime() - now.value - props.offset) / 1000))
const level = computed(() => (left.value <= 600 ? 'danger' : left.value <= 3600 ? 'warn' : 'normal'))
const text = computed(() => {
  if (!props.coarse) return formatDuration(left.value)
  const s = left.value
  if (s >= 86400) return `${Math.floor(s / 86400)} 天 ${Math.floor((s % 86400) / 3600)} 小时`
  if (s >= 3600) return `${Math.floor(s / 3600)} 小时 ${Math.floor((s % 3600) / 60)} 分钟`
  return `${Math.floor(s / 60)} 分钟`
})

function check() {
  if (!finished && left.value <= 0) {
    finished = true
    emit('finish')
  }
}

onMounted(() => {
  timer = setInterval(() => {
    now.value = Date.now()
    check()
  }, 1000)
  check()
})
onBeforeUnmount(() => clearInterval(timer))
watch(() => props.end, () => (finished = false))
</script>

<template>
  <span class="countdown num" :class="`countdown--${level}`">{{ text }}</span>
</template>

<style scoped>
.countdown {
  font-family: var(--oj-font-mono);
  font-weight: 600;
}

.countdown--warn {
  color: var(--oj-accent-text);
}

.countdown--danger {
  color: var(--oj-v-wa-fg);
}
</style>
