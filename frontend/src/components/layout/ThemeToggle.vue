<script setup>
import { Moon, Sunny } from '@element-plus/icons-vue'

import { useTheme } from '@/composables/useTheme'

const { isDark, toggle } = useTheme()
</script>

<template>
  <el-tooltip :content="isDark ? '切换到亮色' : '切换到暗色'" placement="bottom">
    <button class="theme-toggle" type="button" :aria-label="isDark ? '切换到亮色模式' : '切换到暗色模式'" @click="toggle">
      <el-icon :size="18"><component :is="isDark ? Sunny : Moon" /></el-icon>
    </button>
  </el-tooltip>
</template>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: var(--oj-radius-sm);
  background: transparent;
  color: var(--oj-text-2);
  cursor: pointer;
}

.theme-toggle:hover {
  background: var(--oj-surface-hover);
  color: var(--oj-text);
}
</style>
