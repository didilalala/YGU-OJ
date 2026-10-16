<script setup>
/**
 * 统一页面头：面包屑 → 标题 + 副标题 → 右侧操作区。
 *
 *   <PageHeader title="题库" subtitle="共 120 道题" :crumbs="[{ text: '后台', to: '/admin' }]">
 *     <el-button type="primary">新建</el-button>
 *   </PageHeader>
 */
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  crumbs: { type: Array, default: () => [] },
})
</script>

<template>
  <header class="page-header">
    <el-breadcrumb v-if="crumbs.length" separator="/" class="page-header__crumbs">
      <el-breadcrumb-item v-for="crumb in crumbs" :key="crumb.text" :to="crumb.to">{{ crumb.text }}</el-breadcrumb-item>
      <el-breadcrumb-item>{{ title }}</el-breadcrumb-item>
    </el-breadcrumb>
    <div class="page-header__row">
      <div class="page-header__text">
        <h1 class="page-header__title">{{ title }}</h1>
        <p v-if="subtitle" class="page-header__subtitle">{{ subtitle }}</p>
        <slot name="meta" />
      </div>
      <div class="page-header__actions"><slot /></div>
    </div>
  </header>
</template>

<style scoped>
.page-header {
  margin-bottom: var(--oj-space-5);
}

.page-header__crumbs {
  margin-bottom: var(--oj-space-2);
  font-size: var(--oj-fs-sm);
}

.page-header__row {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--oj-space-3) var(--oj-space-4);
}

.page-header__title {
  margin: 0;
  font-size: var(--oj-fs-xl);
  font-weight: 600;
  letter-spacing: -0.01em;
}

.page-header__subtitle {
  margin: 4px 0 0;
  color: var(--oj-text-3);
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--oj-space-2);
}
</style>
