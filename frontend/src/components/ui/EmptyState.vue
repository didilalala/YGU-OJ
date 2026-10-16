<script setup>
/** 统一的空状态：线性插画（单色） + 标题 + 说明 + 操作 */
defineProps({
  title: { type: String, default: '暂无数据' },
  description: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})
</script>

<template>
  <div class="empty" :class="{ 'empty--compact': compact }">
    <svg class="empty__art" viewBox="0 0 120 96" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <rect x="20" y="14" width="80" height="62" rx="8" />
      <path d="M20 30h80" />
      <circle cx="30" cy="22" r="1.5" fill="currentColor" />
      <circle cx="37" cy="22" r="1.5" fill="currentColor" />
      <path d="M44 48l-8 8 8 8M76 48l8 8-8 8M65 44l-10 24" />
      <path d="M30 84h60" opacity=".4" />
    </svg>
    <div class="empty__title">{{ title }}</div>
    <p v-if="description" class="empty__desc">{{ description }}</p>
    <div v-if="$slots.default" class="empty__actions"><slot /></div>
  </div>
</template>

<style scoped>
.empty {
  padding: var(--oj-space-7) var(--oj-space-4);
  color: var(--oj-navy-300);
  text-align: center;
}

.empty--compact {
  padding: var(--oj-space-5) var(--oj-space-4);
}

.empty__art {
  width: 96px;
  height: 77px;
}

.empty--compact .empty__art {
  width: 64px;
  height: 51px;
}

.empty__title {
  margin-top: var(--oj-space-3);
  color: var(--oj-text-2);
  font-size: var(--oj-fs-md);
  font-weight: 600;
}

.empty__desc {
  margin: 4px 0 0;
  color: var(--oj-text-3);
}

.empty__actions {
  margin-top: var(--oj-space-4);
}

html.dark .empty {
  color: var(--oj-navy-400);
}
</style>
