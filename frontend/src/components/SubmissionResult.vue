<script setup>
/** 评测结果面板：总体结果、耗时与内存、编译错误信息、各测试点详情。 */
import { computed } from 'vue'

import ResultTag from '@/components/ResultTag.vue'
import { formatMemory, formatTime } from '@/utils/judge'

const props = defineProps({
  submission: { type: Object, required: true },
})

const passed = computed(() => props.submission.case_info.filter((c) => c.result === 'AC').length)
</script>

<template>
  <div class="submission-result">
    <div class="summary">
      <ResultTag :result="submission.result" size="large" />
      <template v-if="submission.is_finished && submission.case_info.length">
        <span>通过 {{ passed }} / {{ submission.case_info.length }} 个测试点</span>
        <span>耗时 {{ formatTime(submission.time_cost) }}</span>
        <span>内存 {{ formatMemory(submission.memory_cost) }}</span>
      </template>
      <span v-else-if="!submission.is_finished" class="muted">正在评测，请稍候…</span>
    </div>

    <template v-if="submission.result === 'CE'">
      <div class="section-title">编译信息</div>
      <pre class="error-info">{{ submission.error_info || '（无）' }}</pre>
    </template>
    <el-alert
      v-else-if="submission.result === 'SE'"
      type="info"
      :closable="false"
      title="判题服务暂时异常，请稍后重新提交或联系老师重判。"
    />
    <pre v-if="submission.result === 'SE' && submission.error_info" class="error-info">{{ submission.error_info }}</pre>

    <div v-if="submission.case_info.length" class="cases">
      <div
        v-for="item in submission.case_info"
        :key="item.case"
        class="case"
        :class="`case--${item.result === 'AC' ? 'ok' : 'bad'}`"
      >
        <div class="case__index">#{{ item.case }}</div>
        <ResultTag :result="item.result" size="small" />
        <div class="case__meta">{{ formatTime(item.time) }} · {{ formatMemory(item.memory) }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 20px;
  margin-bottom: 12px;
  color: var(--el-text-color-regular);
}

.muted {
  color: var(--el-text-color-secondary);
}

.section-title {
  margin: 12px 0 6px;
  font-weight: 600;
}

.error-info {
  max-height: 320px;
  margin: 8px 0 0;
  padding: 12px;
  overflow: auto;
  border-radius: 4px;
  background: #1f2329;
  color: #f2f3f5;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

.cases {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
  margin-top: 12px;
}

.case {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 8px 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-left-width: 3px;
  border-radius: 4px;
  background: #fff;
}

.case--ok {
  border-left-color: var(--el-color-success);
}

.case--bad {
  border-left-color: var(--el-color-danger);
}

.case__index {
  font-weight: 600;
}

.case__meta {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
