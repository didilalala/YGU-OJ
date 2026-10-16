<script setup>
/** 环形进度，中间显示 done/total */
import { computed } from 'vue'

const props = defineProps({
  done: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  size: { type: Number, default: 56 },
})

const R = 20
const C = 2 * Math.PI * R
const ratio = computed(() => (props.total ? Math.min(1, props.done / props.total) : 0))
</script>

<template>
  <span class="ring" :style="{ width: `${size}px`, height: `${size}px` }" role="img" :aria-label="`完成 ${done} / ${total}`">
    <svg viewBox="0 0 48 48" :width="size" :height="size">
      <circle cx="24" cy="24" :r="R" fill="none" stroke="var(--oj-border)" stroke-width="5" />
      <circle
        cx="24"
        cy="24"
        :r="R"
        fill="none"
        :stroke="ratio >= 1 ? 'var(--oj-v-ac-fg)' : 'var(--el-color-primary)'"
        stroke-width="5"
        stroke-linecap="round"
        :stroke-dasharray="C"
        :stroke-dashoffset="C * (1 - ratio)"
        transform="rotate(-90 24 24)"
      />
    </svg>
    <span class="ring__text num">{{ done }}/{{ total }}</span>
  </span>
</template>

<style scoped>
.ring {
  position: relative;
  display: inline-block;
  flex-shrink: 0;
}

.ring__text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
}
</style>
