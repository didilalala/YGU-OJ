<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { submissionApi } from '@/api/submission'
import ResultTag from '@/components/ResultTag.vue'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { useSiteStore } from '@/stores/site'
import { useUserStore } from '@/stores/user'
import { RESULTS, formatDateTime, formatMemory, formatTime } from '@/utils/judge'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const site = useSiteStore()

const PAGE_SIZE = 20
const isMobile = useMediaQuery('(max-width: 640px)')
// 列表中有未完成的评测时定时刷新
const REFRESH_INTERVAL = 3000

const loading = ref(false)
const submissions = ref([])
const total = ref(0)
let refreshTimer = null

const query = computed(() => ({
  page: Number(route.query.page) || 1,
  problem_id: route.query.problem_id || '',
  result: route.query.result || '',
  language: route.query.language || '',
}))
const problemId = ref(query.value.problem_id)

function updateQuery(patch) {
  const next = { ...query.value, ...patch }
  if (!('page' in patch)) next.page = 1
  const entries = Object.entries(next).filter(([k, v]) => v !== '' && v !== null && !(k === 'page' && v === 1))
  router.push({ query: Object.fromEntries(entries) })
}

async function load({ silent = false } = {}) {
  clearTimeout(refreshTimer)
  if (!silent) loading.value = true
  try {
    const params = { ...query.value, page_size: PAGE_SIZE }
    Object.keys(params).forEach((key) => params[key] === '' && delete params[key])
    const data = await submissionApi.list(params)
    submissions.value = data.results
    total.value = data.total
    if (data.results.some((s) => !s.is_finished)) {
      refreshTimer = setTimeout(() => load({ silent: true }), REFRESH_INTERVAL)
    }
  } catch {
    if (!silent) {
      submissions.value = []
      total.value = 0
    }
  } finally {
    loading.value = false
  }
}

watch(query, () => load())
watch(
  () => route.query.problem_id,
  (value) => (problemId.value = value || ''),
)
onMounted(load)
onBeforeUnmount(() => clearTimeout(refreshTimer))

function applyProblemId() {
  const value = String(problemId.value).trim()
  if (value && !/^\d+$/.test(value)) return
  updateQuery({ problem_id: value })
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="toolbar">
        <span class="title">{{ userStore.isStaff ? '提交记录' : '我的提交' }}</span>
        <el-input
          v-model="problemId"
          class="toolbar__item"
          placeholder="题号"
          clearable
          @keyup.enter="applyProblemId"
          @clear="updateQuery({ problem_id: '' })"
        />
        <el-select
          class="toolbar__item"
          :model-value="query.result"
          placeholder="评测结果"
          clearable
          @update:model-value="(v) => updateQuery({ result: v || '' })"
        >
          <el-option v-for="(meta, value) in RESULTS" :key="value" :label="meta.label" :value="value" />
        </el-select>
        <el-select
          class="toolbar__item"
          :model-value="query.language"
          placeholder="语言"
          clearable
          @update:model-value="(v) => updateQuery({ language: v || '' })"
        >
          <el-option v-for="lang in site.languages" :key="lang.key" :label="lang.name" :value="lang.key" />
        </el-select>
      </div>
    </template>

    <el-table v-loading="loading" :data="submissions" empty-text="暂无提交记录">
      <el-table-column label="编号" :width="isMobile ? 70 : 90">
        <template #default="{ row }">
          <router-link :to="{ name: 'submission-detail', params: { id: row.id } }" class="link">#{{ row.id }}</router-link>
        </template>
      </el-table-column>
      <el-table-column label="题目" :min-width="isMobile ? 140 : 200">
        <template #default="{ row }">
          <router-link :to="{ name: 'problem-detail', params: { id: row.problem } }" class="link">
            {{ row.problem }}. {{ row.problem_title }}
          </router-link>
        </template>
      </el-table-column>
      <el-table-column v-if="userStore.isStaff && !isMobile" prop="username" label="用户" width="120" />
      <el-table-column label="结果" :width="isMobile ? 110 : 140">
        <template #default="{ row }">
          <router-link :to="{ name: 'submission-detail', params: { id: row.id } }">
            <ResultTag :result="row.result" size="small" />
          </router-link>
        </template>
      </el-table-column>
      <el-table-column v-if="!isMobile" label="语言" width="90">
        <template #default="{ row }">{{ site.languageName(row.language) }}</template>
      </el-table-column>
      <el-table-column v-if="!isMobile" label="耗时" width="90">
        <template #default="{ row }">{{ formatTime(row.time_cost) }}</template>
      </el-table-column>
      <el-table-column v-if="!isMobile" label="内存" width="100">
        <template #default="{ row }">{{ formatMemory(row.memory_cost) }}</template>
      </el-table-column>
      <el-table-column v-if="!isMobile" label="提交时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > PAGE_SIZE"
      class="pagination"
      layout="prev, pager, next, total"
      :total="total"
      :page-size="PAGE_SIZE"
      :current-page="query.page"
      @current-change="(page) => updateQuery({ page })"
    />
  </el-card>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.title {
  margin-right: auto;
  font-size: 16px;
  font-weight: 600;
}

.toolbar__item {
  width: 150px;
}

.link {
  color: var(--el-color-primary);
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.pagination {
  justify-content: center;
  margin-top: 16px;
}

@media (max-width: 640px) {
  .toolbar__item {
    width: 100%;
  }
}
</style>
