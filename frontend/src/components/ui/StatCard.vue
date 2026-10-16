<script setup>
/**
 * 统计卡：标签 + 大数字 + 说明。accent 时左侧加橙色竖条（品牌点缀，非状态）。
 *
 *   <StatCard label="本周通过" :value="7" unit="题" hint="比上周多 2 题" />
 */
defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: '—' },
  unit: { type: String, default: '' },
  hint: { type: String, default: '' },
  accent: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})
</script>

<template>
  <div class="stat" :class="{ 'stat--accent': accent }">
    <div class="stat__label">{{ label }}</div>
    <el-skeleton v-if="loading" animated :rows="1" class="stat__skeleton" />
    <div v-else class="stat__value num">
      {{ value }}<span v-if="unit" class="stat__unit">{{ unit }}</span>
    </div>
    <div v-if="hint || $slots.default" class="stat__hint"><slot>{{ hint }}</slot></div>
  </div>
</template>

<style scoped>
.stat {
  position: relative;
  padding: var(--oj-space-4) var(--oj-space-5);
  border: 1px solid var(--oj-border);
  border-radius: var(--oj-radius-md);
  background: var(--oj-surface);
}

.stat--accent::before {
  position: absolute;
  top: 16px;
  bottom: 16px;
  left: 0;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--oj-brand-orange);
  content: '';
}

.stat__label {
  color: var(--oj-text-3);
  font-size: var(--oj-fs-sm);
}

.stat__value {
  margin-top: 4px;
  color: var(--oj-text);
  font-size: var(--oj-fs-2xl);
  font-weight: 600;
  line-height: 1.2;
}

.stat__unit {
  margin-left: 4px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-base);
  font-weight: 400;
}

.stat__hint {
  margin-top: 4px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-xs);
}

.stat__skeleton {
  margin-top: 8px;
}
</style>
