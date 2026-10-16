<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CircleCheckFilled, Search, WarningFilled } from '@element-plus/icons-vue'

import { problemApi } from '@/api/problem'
import DifficultyTag from '@/components/DifficultyTag.vue'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { DIFFICULTIES, passRate } from '@/utils/judge'
import { buildKnowledgeTree } from '@/utils/knowledgeTree'

const route = useRoute()
const router = useRouter()

const PAGE_SIZE = 20
const isMobile = useMediaQuery('(max-width: 640px)')

const loading = ref(false)
const problems = ref([])
const total = ref(0)
const knowledgePoints = ref([])

// 筛选条件保存在地址栏，返回、刷新、分享链接时保持不变
const query = computed(() => ({
  page: Number(route.query.page) || 1,
  keyword: route.query.keyword || '',
  difficulty: route.query.difficulty || '',
  knowledge_point: route.query.knowledge_point ? Number(route.query.knowledge_point) : null,
}))
const keyword = ref(query.value.keyword)

const knowledgeTree = computed(() => buildKnowledgeTree(knowledgePoints.value))

function updateQuery(patch) {
  const next = { ...query.value, ...patch }
  // 修改筛选条件时回到第一页
  if (!('page' in patch)) next.page = 1
  // 地址栏只保留有值的条件，第 1 页不写 page
  const entries = Object.entries(next).filter(([k, v]) => v !== '' && v !== null && !(k === 'page' && v === 1))
  router.push({ query: Object.fromEntries(entries) })
}

async function load() {
  loading.value = true
  try {
    const params = { ...query.value, page_size: PAGE_SIZE }
    Object.keys(params).forEach((key) => (params[key] === '' || params[key] === null) && delete params[key])
    const data = await problemApi.list(params)
    problems.value = data.results
    total.value = data.total
  } catch {
    problems.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

watch(query, load)
watch(
  () => route.query.keyword,
  (value) => (keyword.value = value || ''),
)

onMounted(async () => {
  load()
  try {
    knowledgePoints.value = await problemApi.knowledgePoints()
  } catch {
    // 知识点加载失败不影响题目列表
  }
})

function openProblem(row) {
  router.push({ name: 'problem-detail', params: { id: row.id } })
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="toolbar">
        <span class="title">题目</span>
        <el-input
          v-model="keyword"
          class="toolbar__keyword"
          placeholder="题号或标题"
          clearable
          :prefix-icon="Search"
          @keyup.enter="updateQuery({ keyword: keyword.trim() })"
          @clear="updateQuery({ keyword: '' })"
        />
        <el-select
          class="toolbar__select"
          :model-value="query.difficulty"
          placeholder="难度"
          clearable
          @update:model-value="(v) => updateQuery({ difficulty: v || '' })"
        >
          <el-option v-for="(meta, value) in DIFFICULTIES" :key="value" :label="meta.label" :value="value" />
        </el-select>
        <el-tree-select
          class="toolbar__select"
          :model-value="query.knowledge_point"
          :data="knowledgeTree"
          placeholder="知识点"
          check-strictly
          clearable
          filterable
          :render-after-expand="false"
          default-expand-all
          @update:model-value="(v) => updateQuery({ knowledge_point: v ?? null })"
        />
      </div>
    </template>

    <el-table v-loading="loading" :data="problems" class="problem-table" @row-click="openProblem">
      <el-table-column :width="isMobile ? 36 : 48" align="center">
        <template #default="{ row }">
          <el-icon v-if="row.my_status === 'AC'" class="status status--ac" title="已通过"><CircleCheckFilled /></el-icon>
          <el-icon v-else-if="row.my_status === 'TRIED'" class="status status--tried" title="尝试过"><WarningFilled /></el-icon>
        </template>
      </el-table-column>
      <el-table-column prop="id" label="题号" :width="isMobile ? 56 : 80" />
      <el-table-column label="标题" :min-width="isMobile ? 160 : 220">
        <template #default="{ row }">
          <router-link :to="{ name: 'problem-detail', params: { id: row.id } }" class="problem-link" @click.stop>
            {{ row.title }}
          </router-link>
          <el-tag v-if="row.is_template" size="small" type="info" class="title-tag">模板题</el-tag>
          <DifficultyTag v-if="isMobile" :difficulty="row.difficulty" class="title-tag" />
        </template>
      </el-table-column>
      <el-table-column v-if="!isMobile" label="知识点" min-width="180">
        <template #default="{ row }">
          <el-tag
            v-for="point in row.knowledge_points"
            :key="point.id"
            size="small"
            effect="plain"
            class="point-tag"
            @click.stop="updateQuery({ knowledge_point: point.id })"
          >
            {{ point.name }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="!isMobile" label="难度" width="80">
        <template #default="{ row }"><DifficultyTag :difficulty="row.difficulty" /></template>
      </el-table-column>
      <el-table-column v-if="!isMobile" label="通过率" width="140">
        <template #default="{ row }">
          {{ passRate(row) }}
          <span class="muted">（{{ row.accepted_count }}/{{ row.submission_count }}）</span>
        </template>
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

.toolbar__keyword {
  width: 200px;
}

.toolbar__select {
  width: 160px;
}

.problem-table :deep(.el-table__row) {
  cursor: pointer;
}

.problem-link {
  color: var(--el-color-primary);
  text-decoration: none;
}

.problem-link:hover {
  text-decoration: underline;
}

.title-tag {
  margin-left: 8px;
}

.point-tag {
  margin: 2px 4px 2px 0;
  cursor: pointer;
}

.status {
  font-size: 18px;
}

.status--ac {
  color: var(--el-color-success);
}

.status--tried {
  color: var(--el-color-warning);
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.pagination {
  justify-content: center;
  margin-top: 16px;
}

@media (max-width: 640px) {
  .toolbar__keyword,
  .toolbar__select {
    width: 100%;
  }
}
</style>
