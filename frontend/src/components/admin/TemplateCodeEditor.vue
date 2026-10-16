<script setup>
/**
 * 模板题代码（M8）：按语言分别编辑前置代码、学生初始代码、后置代码。
 * 评测时拼接为 前置 + 学生代码 + 后置；学生只能看到初始代码。
 *
 *   <TemplateCodeEditor v-model="form.template_code" />
 *   template_code: {"c": {"prepend": "...", "template": "...", "append": "..."}}
 */
import { computed, defineAsyncComponent, ref, watch } from 'vue'

import { useSiteStore } from '@/stores/site'

const CodeEditor = defineAsyncComponent(() => import('@/components/CodeEditor.vue'))

const props = defineProps({
  disabled: { type: Boolean, default: false },
})
const model = defineModel({ type: Object, default: () => ({}) })
const site = useSiteStore()

// 可选语言：已启用的语言，加上模板中已配置但现已停用的语言（保存时不丢失）
const options = computed(() => {
  const enabled = site.languages.map((lang) => ({ key: lang.key, name: lang.name, monaco: lang.monaco_id }))
  const known = new Set(enabled.map((lang) => lang.key))
  const extra = Object.keys(model.value)
    .filter((key) => !known.has(key))
    .map((key) => ({ key, name: `${key}（已停用）`, monaco: 'plaintext' }))
  return [...enabled, ...extra]
})
const optionByKey = computed(() => new Map(options.value.map((opt) => [opt.key, opt])))

const PARTS = [
  { key: 'prepend', label: '前置代码', tip: '放在学生代码之前，如 #include、辅助函数', height: '140px' },
  { key: 'template', label: '学生初始代码', tip: '学生看到并补全的部分，如函数签名', height: '180px' },
  { key: 'append', label: '后置代码', tip: '放在学生代码之后，如调用学生函数的 main', height: '180px' },
]

const languages = computed({
  get: () => options.value.map((opt) => opt.key).filter((lang) => lang in model.value),
  set: (selected) => {
    const next = {}
    for (const lang of selected) next[lang] = model.value[lang] ?? { prepend: '', template: '', append: '' }
    model.value = next
  },
})

const activeLanguage = ref(languages.value[0] ?? '')
watch(languages, (value) => {
  if (!value.includes(activeLanguage.value)) activeLanguage.value = value[0] ?? ''
})

function updatePart(lang, key, value) {
  model.value = { ...model.value, [lang]: { ...model.value[lang], [key]: value } }
}
</script>

<template>
  <div class="template-editor">
    <el-checkbox-group v-model="languages" :disabled="props.disabled">
      <el-checkbox v-for="opt in options" :key="opt.key" :value="opt.key">{{ opt.name }}</el-checkbox>
    </el-checkbox-group>
    <p v-if="!languages.length" class="muted">请选择至少一种语言，学生只能使用已配置模板的语言提交。</p>

    <el-tabs v-else v-model="activeLanguage" type="border-card">
      <el-tab-pane v-for="lang in languages" :key="lang" :label="optionByKey.get(lang)?.name ?? lang" :name="lang" lazy>
        <div v-for="part in PARTS" :key="part.key" class="template-editor__part">
          <div class="template-editor__label">
            {{ part.label }}<span class="muted">：{{ part.tip }}</span>
          </div>
          <CodeEditor
            :model-value="model[lang]?.[part.key] ?? ''"
            :language="optionByKey.get(lang)?.monaco ?? 'plaintext'"
            :height="part.height"
            :read-only="props.disabled"
            @update:model-value="(value) => updatePart(lang, part.key, value)"
          />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.template-editor {
  width: 100%;
}

.template-editor__part + .template-editor__part {
  margin-top: 12px;
}

.template-editor__label {
  margin-bottom: 4px;
  font-size: 13px;
  font-weight: 600;
}

.muted {
  color: var(--el-text-color-secondary);
  font-weight: normal;
}
</style>
