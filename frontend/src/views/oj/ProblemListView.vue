<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CircleCheckFilled, Filter, Search, WarningFilled } from '@element-plus/icons-vue'

import { problemApi } from '@/api/problem'
import DifficultyBadge from '@/components/ui/DifficultyBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import RateBar from '@/components/ui/RateBar.vue'
import SkeletonTable from '@/components/ui/SkeletonTable.vue'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { DIFFICULTIES, passRateValue } from '@/utils/judge'
import { buildKnowledgeTree } from '@/utils/knowledgeTree'

const route = useRoute()
const router = useRouter()

const PAGE_SIZE = 20
const isMobile = useMediaQuery('(max-width: 640px)')
const isNarrow = useMediaQuery('(max-width: 900px)')
const drawer = ref(false)

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

// 已选中的筛选条件，以可移除的标签显示在列表上方
function findPoint(nodes, id) {
  for (const node of nodes) {
    if (node.value === id) return node
    const found = findPoint(node.children ?? [], id)
    if (found) return found
  }
  return null
}

const chips = computed(() => {
  const list = []
  if (query.value.keyword) list.push({ key: 'keyword', label: `关键词：${query.value.keyword}`, empty: '' })
  if (query.value.difficulty) list.push({ key: 'difficulty', label: `难度：${DIFFICULTIES[query.value.difficulty]?.label ?? query.value.difficulty}`, empty: '' })
  if (query.value.knowledge_point) {
    const node = findPoint(knowledgeTree.value, query.value.knowledge_point)
    list.push({ key: 'knowledge_point', label: `知识点：${node?.label ?? query.value.knowledge_point}`, empty: null })
  }
  return list
})

function clearAll() {
  keyword.value = ''
  router.push({ query: {} })
}

function openProblem(row) {
  router.push({ name: 'problem-detail', params: { id: row.id } })
}
</script>

<template>
  <div>
    <PageHeader title="题库" :subtitle="total ? `共 ${total} 道题` : ''" />

    <div class="layout">
      <!-- 知识点：宽屏为左侧树，窄屏为抽屉 -->
      <aside v-if="!isNarrow" class="kp surface">
        <div class="kp__title">知识点</div>
        <el-tree
          :data="knowledgeTree"
          node-key="value"
          :props="{ label: 'label', children: 'children' }"
          default-expand-all
          highlight-current
          :current-node-key="query.knowledge_point ?? undefined"
          :expand-on-click-node="false"
          @node-click="(node) => updateQuery({ knowledge_point: node.value === query.knowledge_point ? null : node.value })"
        />
        <el-empty v-if="!knowledgeTree.length" :image-size="40" description="暂无知识点" />
      </aside>

      <section class="main">
        <div class="filters">
          <el-input
            v-model="keyword"
            class="filters__keyword"
            placeholder="搜索题号或标题"
            clearable
            :prefix-icon="Search"
            @keyup.enter="updateQuery({ keyword: keyword.trim() })"
            @clear="updateQuery({ keyword: '' })"
          />
          <el-radio-group
            :model-value="query.difficulty"
            class="filters__diff"
            @update:model-value="(v) => updateQuery({ difficulty: v || '' })"
          >
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button v-for="(meta, value) in DIFFICULTIES" :key="value" :value="value">{{ meta.label }}</el-radio-button>
          </el-radio-group>
          <el-button v-if="isNarrow" :icon="Filter" @click="drawer = true">知识点</el-button>
        </div>

        <div v-if="chips.length" class="chips">
          <el-tag v-for="chip in chips" :key="chip.key" closable effect="light" @close="updateQuery({ [chip.key]: chip.empty })">
            {{ chip.label }}
          </el-tag>
          <el-button link type="primary" @click="clearAll">清空筛选</el-button>
        </div>

        <div class="surface table-wrap">
          <SkeletonTable v-if="loading && !problems.length" :columns="[6, 40, 24, 8, 16]" />
          <el-table v-else :data="problems" class="problem-table" :class="{ 'is-loading': loading }" @row-click="openProblem">
            <el-table-column :width="isMobile ? 36 : 56" align="center">
              <template #default="{ row }">
                <el-icon v-if="row.my_status === 'AC'" class="status status--ac" title="已通过"><CircleCheckFilled /></el-icon>
                <el-icon v-else-if="row.my_status === 'TRIED'" class="status status--tried" title="尝试过"><WarningFilled /></el-icon>
              </template>
            </el-table-column>
            <el-table-column prop="id" label="题号" :width="isMobile ? 56 : 80" class-name="num" />
            <el-table-column label="标题" :min-width="isMobile ? 160 : 240">
              <template #default="{ row }">
                <router-link :to="{ name: 'problem-detail', params: { id: row.id } }" class="problem-link" @click.stop>
                  {{ row.title }}
                </router-link>
                <el-tag v-if="row.is_template" size="small" type="info" effect="plain" class="title-tag">模板题</el-tag>
                <DifficultyBadge v-if="isMobile" :difficulty="row.difficulty" class="title-tag" />
              </template>
            </el-table-column>
            <el-table-column v-if="!isMobile" label="知识点" min-width="180">
              <template #default="{ row }">
                <el-tag
                  v-for="point in row.knowledge_points.slice(0, 2)"
                  :key="point.id"
                  size="small"
                  effect="plain"
                  class="point-tag"
                  @click.stop="updateQuery({ knowledge_point: point.id })"
                >
                  {{ point.name }}
                </el-tag>
                <el-tooltip v-if="row.knowledge_points.length > 2" :content="row.knowledge_points.slice(2).map((p) => p.name).join('、')">
                  <el-tag size="small" type="info" effect="plain" class="point-tag">+{{ row.knowledge_points.length - 2 }}</el-tag>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column v-if="!isMobile" label="难度" width="90">
              <template #default="{ row }"><DifficultyBadge :difficulty="row.difficulty" /></template>
            </el-table-column>
            <el-table-column v-if="!isMobile" label="通过率" width="170">
              <template #default="{ row }">
                <RateBar :value="passRateValue(row)" :title="`${row.accepted_count} / ${row.submission_count}`" />
              </template>
            </el-table-column>
            <template #empty>
              <EmptyState title="没有找到题目" description="换个关键词，或者清空筛选条件试试。">
                <el-button v-if="chips.length" @click="clearAll">清空筛选</el-button>
              </EmptyState>
            </template>
          </el-table>

          <el-pagination
            v-if="total > PAGE_SIZE"
            class="pagination"
            layout="prev, pager, next"
            :total="total"
            :page-size="PAGE_SIZE"
            :current-page="query.page"
            background
            @current-change="(page) => updateQuery({ page })"
          />
        </div>
      </section>
    </div>

    <el-drawer v-model="drawer" title="按知识点筛选" direction="ltr" size="280px">
      <el-tree
        :data="knowledgeTree"
        node-key="value"
        default-expand-all
        highlight-current
        :current-node-key="query.knowledge_point ?? undefined"
        @node-click="(node) => { updateQuery({ knowledge_point: node.value === query.knowledge_point ? null : node.value }); drawer = false }"
      />
    </el-drawer>
  </div>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: var(--oj-space-4);
  align-items: start;
}

.kp {
  position: sticky;
  top: calc(var(--oj-header-height) + 16px);
  max-height: calc(100vh - var(--oj-header-height) - 32px);
  padding: var(--oj-space-3);
  overflow-y: auto;
}

.kp__title {
  margin: 4px 8px 8px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-xs);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.kp :deep(.el-tree-node__content) {
  height: 34px;
  border-radius: var(--oj-radius-sm);
}

.kp :deep(.el-tree--highlight-current .el-tree-node.is-current > .el-tree-node__content) {
  background: var(--el-color-primary-light-9);
  color: var(--oj-link);
  font-weight: 600;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--oj-space-3);
  margin-bottom: var(--oj-space-3);
}

.filters__keyword {
  flex: 1;
  min-width: 200px;
  max-width: 360px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: var(--oj-space-3);
}

.table-wrap {
  overflow: hidden;
}

.problem-table.is-loading {
  opacity: 0.6;
  transition: opacity 0.15s;
}

.problem-table :deep(.el-table__row) {
  cursor: pointer;
}

.problem-link {
  color: var(--oj-text);
  font-weight: 500;
  text-decoration: none;
}

.problem-table :deep(.el-table__row:hover) .problem-link {
  color: var(--oj-link);
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
  color: var(--oj-v-ac-fg);
}

.status--tried {
  color: var(--oj-v-tle-fg);
}

.pagination {
  justify-content: center;
  padding: var(--oj-space-4) 0;
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 640px) {
  .filters__keyword {
    max-width: none;
  }
}
</style>
