<script setup>
import { computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'

import { RESULTS } from '@/utils/judge'

const props = defineProps({
  result: { type: String, required: true },
  size: { type: String, default: 'default' },
})

const meta = computed(() => RESULTS[props.result] ?? { label: props.result, type: 'info' })
const running = computed(() => props.result === 'PENDING' || props.result === 'JUDGING')
</script>

<template>
  <el-tag :type="meta.type" :size="size" :effect="running ? 'plain' : 'light'" class="result-tag">
    <el-icon v-if="running" class="is-loading"><Loading /></el-icon>
    {{ meta.label }}
  </el-tag>
</template>

<style scoped>
.result-tag :deep(.el-tag__content) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>
