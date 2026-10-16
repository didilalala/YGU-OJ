<script setup>
/** 迷你进度条 + 百分比，用于通过率、完成率。value 为 0–100，null 显示 — */
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: null },
  width: { type: String, default: '64px' },
  title: { type: String, default: '' },
})

const percent = computed(() => (props.value == null ? null : Math.max(0, Math.min(100, props.value))))
</script>

<template>
  <span class="rate" :title="title">
    <template v-if="percent != null">
      <span class="rate__track" :style="{ width }"><span class="rate__fill" :style="{ width: `${percent}%` }" /></span>
      <span class="rate__text num">{{ percent.toFixed(1) }}%</span>
    </template>
    <span v-else class="muted">—</span>
  </span>
</template>

<style scoped>
.rate {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.rate__track {
  display: inline-block;
  height: 6px;
  overflow: hidden;
  border-radius: 3px;
  background: var(--oj-border);
}

.rate__fill {
  display: block;
  height: 100%;
  border-radius: 3px;
  background: var(--el-color-primary);
}

.rate__text {
  min-width: 44px;
  color: var(--oj-text-2);
  font-size: var(--oj-fs-sm);
}
</style>
