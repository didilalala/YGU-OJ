<script setup>
/** 等宽代码块：样例、编译输出等。带标题与复制按钮 */
import { CopyDocument } from '@element-plus/icons-vue'

import { ElMessage } from 'element-plus'

import { copyText } from '@/utils/clipboard'

const props = defineProps({
  text: { type: String, default: '' },
  title: { type: String, default: '' },
  // light：跟随主题；terminal：终端深色（编译错误）
  variant: { type: String, default: 'light' },
  maxHeight: { type: String, default: '' },
})

async function copy() {
  try {
    await copyText(props.text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败，请手动选择文本')
  }
}
</script>

<template>
  <div class="code-block" :class="`code-block--${variant}`">
    <div v-if="title || text" class="code-block__head">
      <span>{{ title }}</span>
      <el-button v-if="text" link size="small" :icon="CopyDocument" @click="copy">复制</el-button>
    </div>
    <pre :style="{ maxHeight: maxHeight || undefined }">{{ text }}</pre>
  </div>
</template>

<style scoped>
.code-block {
  overflow: hidden;
  border: 1px solid var(--oj-border);
  border-radius: var(--oj-radius-sm);
  background: var(--oj-code-bg);
}

.code-block__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 2px 8px 2px 12px;
  border-bottom: 1px solid var(--oj-border);
  color: var(--oj-text-3);
  font-size: var(--oj-fs-xs);
  font-weight: 600;
}

pre {
  margin: 0;
  padding: 10px 12px;
  overflow: auto;
  color: var(--oj-text);
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.code-block--terminal {
  border-color: transparent;
  background: var(--oj-terminal-bg);
}

.code-block--terminal .code-block__head {
  border-bottom-color: rgba(255, 255, 255, 0.1);
  color: #9aa1b8;
}

.code-block--terminal pre {
  color: var(--oj-terminal-text);
}
</style>
