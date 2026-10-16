<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { submissionApi } from '@/api/submission'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SkeletonTable from '@/components/ui/SkeletonTable.vue'
import VerdictBadge from '@/components/ui/VerdictBadge.vue'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { useSiteStore } from '@/stores/site'
import { useUserStore } from '@/stores/user'
import { RESULTS, formatDateTime, formatMemory, formatTime, timeAgo } from '@/utils/judge'

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
  <div>
    <PageHeader :title="userStore.isStaff ? '提交记录' : '我的提交'" :subtitle="total ? `共 ${total} 条` : ''" />

    <div class="filters">
      <el-input
        v-model="problemId"
        class="filters__item"
        placeholder="题号"
        clearable
        @keyup.enter="applyProblemId"
        @clear="updateQuery({ problem_id: '' })"
      />
      <el-select
        class="filters__item"
        :model-value="query.result"
        placeholder="评测结果"
        clearable
        @update:model-value="(v) => updateQuery({ result: v || '' })"
      >
        <el-option v-for="(meta, value) in RESULTS" :key="value" :label="meta.label" :value="value" />
      </el-select>
      <el-select
        class="filters__item"
        :model-value="query.language"
        placeholder="语言"
        clearable
        @update:model-value="(v) => updateQuery({ language: v || '' })"
      >
        <el-option v-for="lang in site.languages" :key="lang.key" :label="lang.name" :value="lang.key" />
      </el-select>
    </div>

    <div class="surface">
      <SkeletonTable v-if="loading && !submissions.length" :columns="[8, 30, 14, 10, 10, 18]" />
      <el-table v-else :data="submissions" @row-click="(row) => router.push({ name: 'submission-detail', params: { id: row.id } })">
        <el-table-column label="编号" :width="isMobile ? 70 : 90" class-name="num">
          <template #default="{ row }">
            <router-link :to="{ name: 'submission-detail', params: { id: row.id } }" class="text-link" @click.stop>#{{ row.id }}</router-link>
          </template>
        </el-table-column>
        <el-table-column label="题目" :min-width="isMobile ? 140 : 200">
          <template #default="{ row }">
            <router-link :to="{ name: 'problem-detail', params: { id: row.problem } }" class="text-link" @click.stop>
              {{ row.problem }}. {{ row.problem_title }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column v-if="userStore.isStaff && !isMobile" prop="username" label="用户" width="120" />
        <el-table-column label="结果" :width="isMobile ? 130 : 150">
          <template #default="{ row }"><VerdictBadge :result="row.result" size="sm" /></template>
        </el-table-column>
        <el-table-column v-if="!isMobile" label="语言" width="90">
          <template #default="{ row }">{{ site.languageName(row.language) }}</template>
        </el-table-column>
        <el-table-column v-if="!isMobile" label="耗时" width="90" align="right" class-name="num">
          <template #default="{ row }">{{ formatTime(row.time_cost) }}</template>
        </el-table-column>
        <el-table-column v-if="!isMobile" label="内存" width="100" align="right" class-name="num">
          <template #default="{ row }">{{ formatMemory(row.memory_cost) }}</template>
        </el-table-column>
        <el-table-column v-if="!isMobile" label="提交时间" width="170">
          <template #default="{ row }">
            <el-tooltip :content="formatDateTime(row.created_at)"><span class="muted">{{ timeAgo(row.created_at) }}</span></el-tooltip>
          </template>
        </el-table-column>
        <template #empty>
          <EmptyState title="暂无提交记录" description="去题库选一道题，提交你的第一份代码。">
            <el-button type="primary" @click="router.push({ name: 'problems' })">去题库</el-button>
          </EmptyState>
        </template>
      </el-table>

      <el-pagination
        v-if="total > PAGE_SIZE"
        class="pagination"
        layout="prev, pager, next"
        background
        :total="total"
        :page-size="PAGE_SIZE"
        :current-page="query.page"
        @current-change="(page) => updateQuery({ page })"
      />
    </div>
  </div>
</template>

<style scoped>
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--oj-space-3);
  margin-bottom: var(--oj-space-4);
}

.filters__item {
  width: 160px;
}

:deep(.el-table__row) {
  cursor: pointer;
}

.pagination {
  justify-content: center;
  padding: var(--oj-space-4) 0;
}

@media (max-width: 640px) {
  .filters__item {
    width: 100%;
  }
}
</style>
