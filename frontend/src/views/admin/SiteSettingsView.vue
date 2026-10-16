<script setup>
/** 网站参数（M6）：站点信息、开放策略、提交限制、题目默认值。 */
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { adminSettingsApi } from '@/api/system'
import { useSiteStore } from '@/stores/site'

const site = useSiteStore()
const loading = ref(true)
const saving = ref(false)
const definitions = ref([])
const form = reactive({})
const saved = reactive({})

// 按分组排列，保持后端定义的顺序
const groups = computed(() => {
  const map = new Map()
  for (const item of definitions.value) {
    if (!map.has(item.group)) map.set(item.group, [])
    map.get(item.group).push(item)
  }
  return [...map.entries()].map(([title, items]) => ({ title, items }))
})
const dirty = computed(() => Object.keys(form).some((key) => form[key] !== saved[key]))

function fill(items) {
  definitions.value = items
  for (const item of items) {
    form[item.key] = item.value
    saved[item.key] = item.value
  }
}

onMounted(async () => {
  try {
    fill((await adminSettingsApi.list()).items)
  } finally {
    loading.value = false
  }
})

async function save() {
  const changes = Object.fromEntries(Object.keys(form).filter((key) => form[key] !== saved[key]).map((key) => [key, form[key]]))
  saving.value = true
  try {
    fill((await adminSettingsApi.update(changes)).items)
    ElMessage.success('已保存')
    // 站点信息与语言列表在应用启动时加载，刷新后前台生效
    site.load()
  } catch {
    // 不合法的参数会列出原因，错误提示已由请求拦截器弹出
  } finally {
    saving.value = false
  }
}

function restoreDefault(item) {
  form[item.key] = item.default
}
</script>

<template>
  <el-card v-loading="loading" shadow="never" class="settings">
    <template #header>
      <div class="header">
        <span class="header__title">网站参数</span>
        <el-tag v-if="dirty" type="warning" effect="plain">有未保存的修改</el-tag>
        <span class="header__spacer" />
        <el-button type="primary" :loading="saving" :disabled="!dirty" @click="save">保存修改</el-button>
      </div>
    </template>
    <p class="hint">修改后，学生刷新页面即可生效。各项的取值范围在输入时会检查。</p>

    <section v-for="group in groups" :key="group.title" class="group">
      <h3 class="group__title">{{ group.title }}</h3>
      <el-form label-position="left" label-width="200px" class="group__form">
        <el-form-item v-for="item in group.items" :key="item.key">
          <template #label>
            <span class="label">
              {{ item.label }}
              <el-button
                v-if="form[item.key] !== item.default"
                link
                type="primary"
                size="small"
                @click="restoreDefault(item)"
              >
                恢复默认
              </el-button>
            </span>
          </template>
          <div class="control">
            <el-switch v-if="item.kind === 'bool'" v-model="form[item.key]" :active-text="form[item.key] ? '开启' : '关闭'" />
            <el-input-number
              v-else-if="item.kind === 'int'"
              v-model="form[item.key]"
              :min="item.min_value"
              :max="item.max_value"
              :step="1"
              controls-position="right"
            />
            <el-input
              v-else
              v-model="form[item.key]"
              :maxlength="item.max_length"
              :type="item.multiline ? 'textarea' : 'text'"
              :rows="item.multiline ? 4 : 1"
              show-word-limit
              class="control__text"
            />
            <div v-if="item.description" class="description">{{ item.description }}</div>
          </div>
        </el-form-item>
      </el-form>
    </section>
  </el-card>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header__title {
  font-size: 16px;
  font-weight: 600;
}

.header__spacer {
  flex: 1;
}

.hint {
  margin: 0 0 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.group + .group {
  margin-top: 24px;
}

.group__title {
  margin: 0 0 8px;
  padding-left: 8px;
  border-left: 3px solid var(--oj-brand-orange);
  font-size: 15px;
}

.label {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.control {
  width: 100%;
}

.control__text {
  max-width: 560px;
}

.description {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

@media (max-width: 760px) {
  .group__form :deep(.el-form-item) {
    flex-direction: column;
    align-items: flex-start;
  }

  .group__form :deep(.el-form-item__label) {
    width: auto !important;
    margin-bottom: 4px;
  }
}
</style>
