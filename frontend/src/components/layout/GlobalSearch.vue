<script setup>
/** 全局题目搜索（Ctrl/⌘ + K）：输入题号或标题，方向键选择，回车打开 */
import { nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'

import { problemApi } from '@/api/problem'
import DifficultyBadge from '@/components/ui/DifficultyBadge.vue'

const visible = defineModel({ type: Boolean, default: false })
const router = useRouter()

const keyword = ref('')
const results = ref([])
const active = ref(0)
const loading = ref(false)
const input = ref()
let timer = null
let seq = 0

watch(visible, async (value) => {
  if (!value) return
  keyword.value = ''
  results.value = []
  active.value = 0
  await nextTick()
  input.value?.focus()
})

watch(keyword, (value) => {
  clearTimeout(timer)
  if (!value.trim()) {
    results.value = []
    return
  }
  timer = setTimeout(search, 200)
})

async function search() {
  const current = ++seq
  loading.value = true
  try {
    const data = await problemApi.list({ keyword: keyword.value.trim(), page_size: 8 })
    if (current === seq) {
      results.value = data.results
      active.value = 0
    }
  } catch {
    if (current === seq) results.value = []
  } finally {
    if (current === seq) loading.value = false
  }
}

function open(problem) {
  visible.value = false
  router.push({ name: 'problem-detail', params: { id: problem.id } })
}

function onKey(event) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    active.value = Math.min(results.value.length - 1, active.value + 1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    active.value = Math.max(0, active.value - 1)
  } else if (event.key === 'Enter') {
    if (results.value[active.value]) open(results.value[active.value])
    else if (keyword.value.trim()) {
      visible.value = false
      router.push({ name: 'problems', query: { keyword: keyword.value.trim() } })
    }
  }
}
</script>

<template>
  <el-dialog v-model="visible" width="560px" :show-close="false" class="gs-dialog" align-center append-to-body>
    <el-input ref="input" v-model="keyword" size="large" placeholder="搜索题号或标题…" :prefix-icon="Search" @keydown="onKey" />
    <ul v-if="results.length" class="gs-list" role="listbox">
      <li
        v-for="(item, index) in results"
        :key="item.id"
        class="gs-item"
        :class="{ 'gs-item--active': index === active }"
        role="option"
        :aria-selected="index === active"
        @mouseenter="active = index"
        @click="open(item)"
      >
        <span class="gs-item__id num">{{ item.id }}</span>
        <span class="gs-item__title">{{ item.title }}</span>
        <DifficultyBadge :difficulty="item.difficulty" />
      </li>
    </ul>
    <p v-else-if="keyword.trim() && !loading" class="gs-empty">没有找到匹配的题目，按回车在题库中搜索</p>
    <p v-else-if="!keyword.trim()" class="gs-empty">输入关键词开始搜索 · <kbd>↑</kbd> <kbd>↓</kbd> 选择 · <kbd>Enter</kbd> 打开 · <kbd>Esc</kbd> 关闭</p>
  </el-dialog>
</template>

<style scoped>
.gs-list {
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}

.gs-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--oj-radius-sm);
  cursor: pointer;
}

.gs-item--active {
  background: var(--el-color-primary-light-9);
}

.gs-item__id {
  min-width: 40px;
  color: var(--oj-text-3);
}

.gs-item__title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gs-empty {
  margin: 16px 0 4px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-sm);
  text-align: center;
}
</style>

<style>
.gs-dialog .el-dialog__header {
  display: none;
}
</style>
