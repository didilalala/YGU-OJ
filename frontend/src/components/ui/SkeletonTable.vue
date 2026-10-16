<script setup>
/** 表格加载占位。列数按 columns 数组的相对宽度渲染 */
defineProps({
  rows: { type: Number, default: 6 },
  columns: { type: Array, default: () => [8, 40, 20, 12, 12] },
})
</script>

<template>
  <div class="sk" aria-busy="true" aria-label="加载中">
    <div v-for="r in rows" :key="r" class="sk__row">
      <span v-for="(w, c) in columns" :key="c" class="sk__cell" :style="{ flex: w }" />
    </div>
  </div>
</template>

<style scoped>
.sk__row {
  display: flex;
  gap: var(--oj-space-4);
  align-items: center;
  height: 52px;
  padding: 0 var(--oj-space-3);
  border-bottom: 1px solid var(--oj-border);
}

.sk__cell {
  height: 12px;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--oj-border) 25%, var(--oj-surface-hover) 50%, var(--oj-border) 75%);
  background-size: 200% 100%;
  animation: sk-shimmer 1.4s infinite linear;
}

@keyframes sk-shimmer {
  to {
    background-position: -200% 0;
  }
}
</style>
