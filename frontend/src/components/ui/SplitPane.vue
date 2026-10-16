<script setup>
/**
 * 可拖拽的左右分栏。比例保存在 localStorage（storageKey），窄屏（< breakpoint）退化为上下堆叠。
 *
 *   <SplitPane storage-key="problem-split">
 *     <template #left>…</template>
 *     <template #right>…</template>
 *   </SplitPane>
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { loadLocal, saveLocal } from '@/utils/storage'

const props = defineProps({
  storageKey: { type: String, default: '' },
  initial: { type: Number, default: 46 },
  min: { type: Number, default: 28 },
  max: { type: Number, default: 72 },
  // 窄屏：一次只显示一个面板，active 取 left | right
  single: { type: Boolean, default: false },
  active: { type: String, default: 'left' },
})

const root = ref()
const ratio = ref(props.initial)
const dragging = ref(false)

onMounted(() => {
  if (!props.storageKey) return
  const saved = Number(loadLocal(`split:${props.storageKey}`))
  if (saved >= props.min && saved <= props.max) ratio.value = saved
})

function clamp(value) {
  return Math.min(props.max, Math.max(props.min, value))
}

function onMove(event) {
  const rect = root.value.getBoundingClientRect()
  ratio.value = clamp(((event.clientX - rect.left) / rect.width) * 100)
}

function stop() {
  dragging.value = false
  window.removeEventListener('pointermove', onMove)
  window.removeEventListener('pointerup', stop)
  if (props.storageKey) saveLocal(`split:${props.storageKey}`, String(Math.round(ratio.value)))
}

function start() {
  dragging.value = true
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', stop)
}

function onKey(event) {
  if (event.key === 'ArrowLeft') ratio.value = clamp(ratio.value - 2)
  else if (event.key === 'ArrowRight') ratio.value = clamp(ratio.value + 2)
  else return
  if (props.storageKey) saveLocal(`split:${props.storageKey}`, String(Math.round(ratio.value)))
}

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onMove)
  window.removeEventListener('pointerup', stop)
})
</script>

<template>
  <div
    ref="root"
    class="split"
    :class="{ 'split--dragging': dragging, 'split--single': single }"
    :style="{ '--split-left': `${ratio}%` }"
  >
    <div v-show="!single || active === 'left'" class="split__pane split__left"><slot name="left" /></div>
    <div
      v-if="!single"
      class="split__handle"
      role="separator"
      aria-orientation="vertical"
      tabindex="0"
      :aria-valuenow="Math.round(ratio)"
      @pointerdown.prevent="start"
      @keydown="onKey"
    />
    <div v-show="!single || active === 'right'" class="split__pane split__right"><slot name="right" /></div>
  </div>
</template>

<style scoped>
.split {
  display: flex;
  height: 100%;
  min-height: 0;
}

.split__pane {
  min-width: 0;
  min-height: 0;
}

.split__left {
  flex: 0 0 calc(var(--split-left) - 4px);
}

.split__right {
  flex: 1;
}

.split--single .split__left {
  flex: 1;
}

.split__handle {
  position: relative;
  flex: 0 0 8px;
  cursor: col-resize;
}

.split__handle::after {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 4px;
  height: 40px;
  border-radius: 2px;
  background: var(--oj-border-strong);
  transform: translate(-50%, -50%);
  content: '';
  transition: background 0.15s;
}

.split__handle:hover::after,
.split__handle:focus-visible::after,
.split--dragging .split__handle::after {
  background: var(--el-color-primary);
}

.split--dragging {
  user-select: none;
}
</style>
