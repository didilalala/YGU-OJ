<script setup>
import { computed } from 'vue'

import { DIFFICULTIES } from '@/utils/judge'

const props = defineProps({
  difficulty: { type: String, required: true },
})

const meta = computed(() => DIFFICULTIES[props.difficulty] ?? { label: props.difficulty, type: 'info' })
</script>

<template>
  <el-tag :type="meta.type" effect="plain" size="small">{{ meta.label }}</el-tag>
</template>
