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

self.MonacoEnvironment = {
  getWorker: () => new EditorWorker(),
}

const props = defineProps({
  modelValue: { type: String, default: '' },
  // c | cpp | java | python
  language: { type: String, default: 'cpp' },
  readOnly: { type: Boolean, default: false },
  height: { type: String, default: '420px' },
})
const emit = defineEmits(['update:modelValue'])

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
    tabSize: 4,
    scrollBeyondLastLine: false,
  })
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
watch(
  () => props.readOnly,
  (readOnly) => editor.value.updateOptions({ readOnly }),
)

onBeforeUnmount(() => {
  editor.value?.dispose()
})
</script>

<template>
  <div ref="container" class="code-editor" :style="{ height }" />
</template>

<style scoped>
.code-editor {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  overflow: hidden;
}
</style>
