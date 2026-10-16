<script setup>
/**
 * 在线代码编辑器（Monaco）。
 *
 * 只加载编辑器核心与 C/C++/Java/Python 语法高亮，不加载语言服务，
 * 体积更小；Worker 由 Vite 打包到本地，机房断网时也能使用。
 *
 *   <CodeEditor v-model="code" language="cpp" />
 */
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as monaco from 'monaco-editor/editor/editor.api'
import 'monaco-editor/languages/definitions/cpp/register'
import 'monaco-editor/languages/definitions/java/register'
import 'monaco-editor/languages/definitions/python/register'
import EditorWorker from 'monaco-editor/editor/editor.worker?worker'

import { useTheme } from '@/composables/useTheme'

self.MonacoEnvironment = {
  getWorker: () => new EditorWorker(),
}

// 与站点配色统一的编辑器主题：背景用卡片色，选中色用品牌藏青系
monaco.editor.defineTheme('ygu-light', {
  base: 'vs',
  inherit: true,
  rules: [],
  colors: {
    'editor.background': '#ffffff',
    'editor.lineHighlightBackground': '#f4f5fa',
    'editorLineNumber.foreground': '#9aa0b4',
    'editorLineNumber.activeForeground': '#1e2a66',
    'editor.selectionBackground': '#d9ddef',
    'editorCursor.foreground': '#1e2a66',
  },
})
monaco.editor.defineTheme('ygu-dark', {
  base: 'vs-dark',
  inherit: true,
  rules: [],
  colors: {
    'editor.background': '#11152a',
    'editor.lineHighlightBackground': '#1a2040',
    'editorLineNumber.foreground': '#5b6384',
    'editorLineNumber.activeForeground': '#a5b0ff',
    'editor.selectionBackground': '#2f3a78',
    'editorCursor.foreground': '#a5b0ff',
  },
})

const props = defineProps({
  modelValue: { type: String, default: '' },
  // c | cpp | java | python
  language: { type: String, default: 'cpp' },
  readOnly: { type: Boolean, default: false },
  height: { type: String, default: '420px' },
  // 铺满父容器时去掉外框和圆角
  bordered: { type: Boolean, default: true },
})
// submit：Ctrl/⌘ + Enter
const emit = defineEmits(['update:modelValue', 'submit'])
const { isDark } = useTheme()

const container = ref()
const editor = shallowRef()

onMounted(() => {
  editor.value = monaco.editor.create(container.value, {
    value: props.modelValue,
    language: props.language,
    readOnly: props.readOnly,
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 14,
    fontFamily: "'JetBrains Mono', 'Cascadia Code', Consolas, monospace",
    fontLigatures: false,
    lineHeight: 22,
    padding: { top: 12, bottom: 12 },
    tabSize: 4,
    scrollBeyondLastLine: false,
    renderLineHighlight: 'line',
    theme: isDark.value ? 'ygu-dark' : 'ygu-light',
  })
  editor.value.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => emit('submit'))
  editor.value.onDidChangeModelContent(() => {
    emit('update:modelValue', editor.value.getValue())
  })
})

watch(
  () => props.modelValue,
  (value) => {
    if (editor.value && value !== editor.value.getValue()) editor.value.setValue(value)
  },
)
watch(
  () => props.language,
  (language) => monaco.editor.setModelLanguage(editor.value.getModel(), language),
)
watch(isDark, (dark) => monaco.editor.setTheme(dark ? 'ygu-dark' : 'ygu-light'))
watch(
  () => props.readOnly,
  (readOnly) => editor.value.updateOptions({ readOnly }),
)

onBeforeUnmount(() => {
  editor.value?.dispose()
})
</script>

<template>
  <div ref="container" class="code-editor" :class="{ 'code-editor--bordered': bordered }" :style="{ height }" />
</template>

<style scoped>
.code-editor {
  overflow: hidden;
}

.code-editor--bordered {
  border: 1px solid var(--oj-border);
  border-radius: var(--oj-radius-sm);
}
</style>
