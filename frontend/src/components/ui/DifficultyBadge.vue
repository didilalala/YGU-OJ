<script setup>
/** 难度：圆点 + 文字，比实色标签更轻 */
import { computed } from 'vue'

import { DIFFICULTIES } from '@/utils/judge'

const props = defineProps({
  difficulty: { type: String, required: true },
})

const meta = computed(() => DIFFICULTIES[props.difficulty] ?? { label: props.difficulty, tone: 'wait' })
</script>

<template>
  <span class="difficulty" :style="{ color: `var(--oj-v-${meta.tone}-fg)` }">
    <i class="difficulty__dot" />{{ meta.label }}
  </span>
</template>

<style scoped>
.difficulty {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--oj-fs-sm);
  font-weight: 500;
  white-space: nowrap;
}

.difficulty__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}
</style>
