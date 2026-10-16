<script setup>
/**
 * 测试点结果色块网格。悬停（或键盘聚焦）显示耗时与内存。
 *
 *   <TestcaseGrid :cases="submission.case_info" />
 */
import { RESULTS, formatMemory, formatTime } from '@/utils/judge'

defineProps({
  cases: { type: Array, required: true },
})

function tone(result) {
  return RESULTS[result]?.tone ?? 'wait'
}
</script>

<template>
  <div class="grid" role="list">
    <el-tooltip v-for="item in cases" :key="item.case" placement="top" :show-after="100">
      <template #content>
        #{{ item.case }} · {{ RESULTS[item.result]?.label ?? item.result }}<br />
        {{ formatTime(item.time) }} · {{ formatMemory(item.memory) }}
      </template>
      <div class="cell" :class="`cell--${tone(item.result)}`" role="listitem" tabindex="0">
        <span class="cell__index num">#{{ item.case }}</span>
        <span class="cell__result">{{ RESULTS[item.result]?.short ?? item.result }}</span>
        <span class="cell__meta num">{{ formatTime(item.time) }}</span>
      </div>
    </el-tooltip>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
  gap: 6px;
}

.cell {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 6px 8px;
  border: 1px solid var(--cl-bd);
  border-radius: var(--oj-radius-sm);
  background: var(--cl-bg);
  color: var(--cl-fg);
  font-size: var(--oj-fs-xs);
  cursor: default;
}

.cell__index {
  opacity: 0.75;
}

.cell__result {
  font-size: var(--oj-fs-sm);
  font-weight: 700;
}

.cell__meta {
  opacity: 0.75;
}

.cell--ac { --cl-fg: var(--oj-v-ac-fg); --cl-bg: var(--oj-v-ac-bg); --cl-bd: var(--oj-v-ac-bd); }
.cell--wa { --cl-fg: var(--oj-v-wa-fg); --cl-bg: var(--oj-v-wa-bg); --cl-bd: var(--oj-v-wa-bd); }
.cell--ce { --cl-fg: var(--oj-v-ce-fg); --cl-bg: var(--oj-v-ce-bg); --cl-bd: var(--oj-v-ce-bd); }
.cell--re { --cl-fg: var(--oj-v-re-fg); --cl-bg: var(--oj-v-re-bg); --cl-bd: var(--oj-v-re-bd); }
.cell--tle { --cl-fg: var(--oj-v-tle-fg); --cl-bg: var(--oj-v-tle-bg); --cl-bd: var(--oj-v-tle-bd); }
.cell--mle { --cl-fg: var(--oj-v-mle-fg); --cl-bg: var(--oj-v-mle-bg); --cl-bd: var(--oj-v-mle-bd); }
.cell--pac { --cl-fg: var(--oj-v-pac-fg); --cl-bg: var(--oj-v-pac-bg); --cl-bd: var(--oj-v-pac-bd); }
.cell--wait { --cl-fg: var(--oj-v-wait-fg); --cl-bg: var(--oj-v-wait-bg); --cl-bd: var(--oj-v-wait-bd); }
.cell--se { --cl-fg: var(--oj-v-se-fg); --cl-bg: var(--oj-v-se-bg); --cl-bd: var(--oj-v-se-bd); }
</style>
