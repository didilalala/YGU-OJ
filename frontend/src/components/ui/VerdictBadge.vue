<script setup>
/**
 * 评测结果徽标：图标 + 底色 + 文字，不只靠颜色区分状态。
 *
 *   <VerdictBadge result="WA" size="lg" />
 *   size: sm | md | lg；short 时只显示缩写（AC / WA …）
 */
import { computed } from 'vue'
import { CircleCheckFilled, CircleCloseFilled, Clock, Loading, WarningFilled } from '@element-plus/icons-vue'

import { RESULTS } from '@/utils/judge'

const props = defineProps({
  result: { type: String, required: true },
  size: { type: String, default: 'md' },
  short: { type: Boolean, default: false },
})

const meta = computed(() => RESULTS[props.result] ?? { label: props.result, short: props.result, tone: 'wait' })
const running = computed(() => props.result === 'PENDING' || props.result === 'JUDGING')
const icon = computed(() => {
  if (props.result === 'JUDGING') return Loading
  if (props.result === 'PENDING') return Clock
  if (props.result === 'AC') return CircleCheckFilled
  if (['WA', 'RE', 'CE'].includes(props.result)) return CircleCloseFilled
  return WarningFilled
})
</script>

<template>
  <span class="verdict" :class="[`verdict--${meta.tone}`, `verdict--${size}`]">
    <el-icon :class="{ 'is-loading': props.result === 'JUDGING' }" class="verdict__icon"><component :is="icon" /></el-icon>
    <span>{{ short ? meta.short : meta.label }}</span>
    <span v-if="running" class="sr-only">…</span>
  </span>
</template>

<style scoped>
.verdict {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  border: 1px solid var(--vd-bd);
  border-radius: var(--oj-radius-pill);
  background: var(--vd-bg);
  color: var(--vd-fg);
  font-size: var(--oj-fs-sm);
  font-weight: 600;
  line-height: 22px;
  white-space: nowrap;
}

.verdict--sm {
  padding: 0 6px;
  font-size: var(--oj-fs-xs);
  line-height: 18px;
}

.verdict--lg {
  gap: 8px;
  padding: 2px 16px;
  font-size: var(--oj-fs-md);
  line-height: 28px;
}

.verdict--lg .verdict__icon {
  font-size: 20px;
}

.verdict__icon {
  font-size: 1.1em;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}

.verdict--ac { --vd-fg: var(--oj-v-ac-fg); --vd-bg: var(--oj-v-ac-bg); --vd-bd: var(--oj-v-ac-bd); }
.verdict--wa { --vd-fg: var(--oj-v-wa-fg); --vd-bg: var(--oj-v-wa-bg); --vd-bd: var(--oj-v-wa-bd); }
.verdict--ce { --vd-fg: var(--oj-v-ce-fg); --vd-bg: var(--oj-v-ce-bg); --vd-bd: var(--oj-v-ce-bd); }
.verdict--re { --vd-fg: var(--oj-v-re-fg); --vd-bg: var(--oj-v-re-bg); --vd-bd: var(--oj-v-re-bd); }
.verdict--tle { --vd-fg: var(--oj-v-tle-fg); --vd-bg: var(--oj-v-tle-bg); --vd-bd: var(--oj-v-tle-bd); }
.verdict--mle { --vd-fg: var(--oj-v-mle-fg); --vd-bg: var(--oj-v-mle-bg); --vd-bd: var(--oj-v-mle-bd); }
.verdict--pac { --vd-fg: var(--oj-v-pac-fg); --vd-bg: var(--oj-v-pac-bg); --vd-bd: var(--oj-v-pac-bd); }
.verdict--wait { --vd-fg: var(--oj-v-wait-fg); --vd-bg: var(--oj-v-wait-bg); --vd-bd: var(--oj-v-wait-bd); }
.verdict--se { --vd-fg: var(--oj-v-se-fg); --vd-bg: var(--oj-v-se-bg); --vd-bd: var(--oj-v-se-bd); }
</style>
