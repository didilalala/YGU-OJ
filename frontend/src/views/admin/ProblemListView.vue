<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Upload } from '@element-plus/icons-vue'

import { adminProblemApi } from '@/api/adminProblem'
import { problemApi } from '@/api/problem'
import FpsImportDialog from '@/components/admin/FpsImportDialog.vue'
import DifficultyTag from '@/components/DifficultyTag.vue'
import { DIFFICULTIES, formatDateTime, passRate } from '@/utils/judge'
import { buildKnowledgeTree } from '@/utils/knowledgeTree'

const route = useRoute()
const router = useRouter()

const PAGE_SIZE = 20

const loading = ref(false)
const problems = ref([])
const total = ref(0)
const knowledgePoints = ref([])
const fpsVisible = ref(false)

const query = computed(() => ({
  page: Number(route.query.page) || 1,
  keyword: route.query.keyword || '',
  difficulty: route.query.difficulty || '',
  knowledge_point: route.query.knowledge_point ? Number(route.query.knowledge_point) : null,
  mine: route.query.mine || '',
  is_public: route.query.is_public ?? '',
}))
const keyword = ref(query.value.keyword)
const knowledgeTree = computed(() => buildKnowledgeTree(knowledgePoints.value))

function updateQuery(patch) {
  const next = { ...query.value, ...patch }
  if (!('page' in patch)) next.page = 1
  const entries = Object.entries(next).filter(([k, v]) => v !== '' && v !== null && !(k === 'page' && v === 1))
  router.push({ query: Object.fromEntries(entries) })
}

async function load() {
  loading.value = true
  try {
    const params = { ...query.value, page_size: PAGE_SIZE }
    Object.keys(params).forEach((key) => (params[key] === '' || params[key] === null) && delete params[key])
    const data = await adminProblemApi.list(params)
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
    // 知识点加载失败不影响列表
  }
})

async function togglePublic(row, value) {
  try {
    await adminProblemApi.update(row.id, { is_public: value })
    row.is_public = value
    ElMessage.success(value ? '已公开，所有人可见' : '已设为私有')
  } catch {
    // 错误提示已由请求拦截器弹出
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定删除题目「${row.id}. ${row.title}」吗？测试数据将一并删除。`, '删除题目', {
      type: 'warning',
      confirmButtonText: '删除',
    })
  } catch {
    return
  }
  try {
    await adminProblemApi.remove(row.id)
    ElMessage.success('已删除')
    load()
  } catch {
    // 有提交记录时后端拒绝删除，提示已由请求拦截器弹出
  }
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="header">
        <span class="header__title">题库</span>
        <el-button :icon="Upload" @click="fpsVisible = true">导入 FPS</el-button>
        <el-button type="primary" :icon="Plus" @click="router.push({ name: 'admin-problem-create' })">
          新建题目
        </el-button>
      </div>
    </template>

    <div class="filters">
      <el-input
        v-model="keyword"
        class="filters__keyword"
        placeholder="题号或标题"
        clearable
        :prefix-icon="Search"
        @keyup.enter="updateQuery({ keyword: keyword.trim() })"
        @clear="updateQuery({ keyword: '' })"
      />
      <el-select
        class="filters__item"
        :model-value="query.mine"
        @update:model-value="(v) => updateQuery({ mine: v })"
      >
        <el-option label="全部可见题目" value="" />
        <el-option label="我创建的" value="1" />
      </el-select>
      <el-select
        class="filters__item"
        :model-value="query.is_public"
        placeholder="公开状态"
        clearable
        @update:model-value="(v) => updateQuery({ is_public: v ?? '' })"
      >
        <el-option label="公开" value="1" />
        <el-option label="私有" value="0" />
      </el-select>
      <el-select
        class="filters__item"
        :model-value="query.difficulty"
        placeholder="难度"
        clearable
        @update:model-value="(v) => updateQuery({ difficulty: v || '' })"
      >
        <el-option v-for="(meta, value) in DIFFICULTIES" :key="value" :label="meta.label" :value="value" />
      </el-select>
      <el-tree-select
        class="filters__item"
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

    <el-table v-loading="loading" :data="problems" empty-text="没有符合条件的题目">
      <el-table-column prop="id" label="题号" width="70" />
      <el-table-column label="标题" min-width="200">
        <template #default="{ row }">
          <router-link
            v-if="row.can_edit"
            :to="{ name: 'admin-problem-edit', params: { id: row.id } }"
            class="link"
          >
            {{ row.title }}
          </router-link>
          <span v-else>{{ row.title }}</span>
          <el-tag v-if="row.is_template" size="small" type="info" class="tag">模板题</el-tag>
          <div class="points">
            <el-tag v-for="point in row.knowledge_points" :key="point.id" size="small" effect="plain">
              {{ point.name }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="难度" width="80">
        <template #default="{ row }"><DifficultyTag :difficulty="row.difficulty" /></template>
      </el-table-column>
      <el-table-column label="测试数据" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.has_test_cases" type="success" size="small" effect="plain">已上传</el-tag>
          <el-tag v-else type="warning" size="small">未上传</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="通过率" width="140">
        <template #default="{ row }">
          {{ passRate(row) }}
          <span class="muted">（{{ row.accepted_count }}/{{ row.submission_count }}）</span>
        </template>
      </el-table-column>
      <el-table-column label="公开" width="70">
        <template #default="{ row }">
          <el-switch
            :model-value="row.is_public"
            :disabled="!row.can_edit"
            @update:model-value="(value) => togglePublic(row, value)"
          />
        </template>
      </el-table-column>
      <el-table-column label="创建者" width="110">
        <template #default="{ row }">{{ row.created_by_name ?? '—' }}</template>
      </el-table-column>
      <el-table-column label="更新时间" width="160">
        <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.can_edit"
            link
            type="primary"
            @click="router.push({ name: 'admin-problem-edit', params: { id: row.id } })"
          >
            编辑
          </el-button>
          <el-button link type="primary" @click="router.push({ name: 'problem-detail', params: { id: row.id } })">
            预览
          </el-button>
          <el-button v-if="row.can_edit" link type="danger" @click="remove(row)">删除</el-button>
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

    <FpsImportDialog v-model="fpsVisible" @imported="load" />
  </el-card>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header__title {
  margin-right: auto;
  font-size: 16px;
  font-weight: 600;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.filters__keyword {
  width: 200px;
}

.filters__item {
  width: 150px;
}

.link {
  color: var(--el-color-primary);
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.tag {
  margin-left: 6px;
}

.points {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.pagination {
  justify-content: center;
  margin-top: 16px;
}
</style>
