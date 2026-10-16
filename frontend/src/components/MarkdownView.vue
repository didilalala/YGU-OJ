<script setup>
/**
 * 题面渲染（Markdown + KaTeX，兼容 FPS 导入的 HTML 题面），输出经 DOMPurify 过滤。
 *
 *   <MarkdownView :content="problem.description" />
 */
import { useId } from 'vue'
import { MdPreview } from 'md-editor-v3'

import { sanitizeHtml } from '@/utils/markdown'

defineProps({
  content: { type: String, default: '' },
})

const id = `md-${useId()}`
</script>

<template>
  <MdPreview
    :id="id"
    class="markdown-view"
    :model-value="content"
    :sanitize="sanitizeHtml"
    preview-theme="default"
    no-highlight
    no-mermaid
    no-echarts
    :show-code-row-number="false"
  />
</template>

<style scoped>
.markdown-view {
  background: transparent;
}

.markdown-view :deep(.md-editor-preview-wrapper) {
  padding: 0;
}

.markdown-view :deep(.md-editor-preview) {
  font-size: 15px;
  line-height: 1.75;
  color: var(--el-text-color-primary);
}

.markdown-view :deep(img) {
  max-width: 100%;
}
</style>
