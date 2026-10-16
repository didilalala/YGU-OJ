<script setup>
/** 评测结果面板：总体结果、耗时与内存、编译错误信息、各测试点详情。 */
import { computed } from 'vue'

import CodeBlock from '@/components/ui/CodeBlock.vue'
import TestcaseGrid from '@/components/ui/TestcaseGrid.vue'
import VerdictBadge from '@/components/ui/VerdictBadge.vue'
import { formatMemory, formatTime } from '@/utils/judge'

const props = defineProps({
  submission: { type: Object, required: true },
})

const passed = computed(() => props.submission.case_info.filter((c) => c.result === 'AC').length)
const hasCases = computed(() => props.submission.is_finished && props.submission.case_info.length > 0)
</script>

<template>
  <div class="result">
    <div class="result__summary">
      <VerdictBadge :result="submission.result" size="lg" />
      <dl v-if="hasCases" class="result__stats">
        <div>
          <dt>通过</dt>
          <dd class="num">{{ passed }} / {{ submission.case_info.length }}</dd>
        </div>
        <div>
          <dt>耗时</dt>
          <dd class="num">{{ formatTime(submission.time_cost) }}</dd>
        </div>
        <div>
          <dt>内存</dt>
          <dd class="num">{{ formatMemory(submission.memory_cost) }}</dd>
        </div>
      </dl>
      <span v-else-if="!submission.is_finished" class="muted">正在评测，请稍候…</span>
    </div>

    <CodeBlock
      v-if="submission.result === 'CE'"
      title="编译信息"
      variant="terminal"
      max-height="320px"
      :text="submission.error_info || '（无）'"
    />
    <template v-else-if="submission.result === 'SE'">
      <el-alert type="info" :closable="false" title="判题服务暂时异常，请稍后重新提交或联系老师重判。" />
      <CodeBlock v-if="submission.error_info" variant="terminal" max-height="240px" :text="submission.error_info" class="result__gap" />
    </template>

    <TestcaseGrid v-if="submission.case_info.length" :cases="submission.case_info" class="result__gap" />
  </div>
</template>

<style scoped>
.result__summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 24px;
  margin-bottom: 12px;
}

.result__stats {
  display: flex;
  gap: 24px;
  margin: 0;
}

.result__stats dt {
  color: var(--oj-text-3);
  font-size: var(--oj-fs-xs);
}

.result__stats dd {
  margin: 0;
  font-size: var(--oj-fs-md);
  font-weight: 600;
}

.result__gap {
  margin-top: 12px;
}
</style>
