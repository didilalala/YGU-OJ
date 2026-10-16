<script setup>
/**
 * 从题库选题：按关键字、难度、知识点筛选，多选后加入。已选的题目不可重复选择。
 *
 *   <ProblemPicker v-model="visible" :selected-ids="[1, 2]" @pick="(problems) => ..." />
 */
import { computed, ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'

import { adminProblemApi } from '@/api/adminProblem'
import { problemApi } from '@/api/problem'
import DifficultyTag from '@/components/DifficultyTag.vue'
import { DIFFICULTIES, passRate } from '@/utils/judge'
import { buildKnowledgeTree } from '@/utils/knowledgeTree'

const props = defineProps({
  selectedIds: { type: Array, default: () => [] },
})
const visible = defineModel({ type: Boolean, default: false })
const emit = defineEmits(['pick'])

const PAGE_SIZE = 10

const loading = ref(false)
const problems = ref([])
const total = ref(0)
const knowledgePoints = ref([])
const filters = ref({ keyword: '', difficulty: '', knowledge_point: null, page: 1 })
const picked = ref([])
const tableRef = ref()
const knowledgeTree = computed(() => buildKnowledgeTree(knowledgePoints.value))

async function load() {
  loading.value = true
  try {
    const params = { ...filters.value, page_size: PAGE_SIZE }
    Object.keys(params).forEach((key) => (params[key] === '' || params[key] === null) && delete params[key])
    const data = await adminProblemApi.list(params)
    problems.value = data.results
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  filters.value.page = 1
  load()
}

watch(visible, async (open) => {
  if (!open) return
  picked.value = []
  tableRef.value?.clearSelection()
  load()
  if (!knowledgePoints.value.length) {
    try {
      knowledgePoints.value = await problemApi.knowledgePoints()
    } catch {
      // 知识点加载失败不影响选题
    }
  }
})

// reserve-selection 使选择跨页保留，rows 即全部已选
function onSelectionChange(rows) {
  picked.value = rows
}

function confirm() {
  emit('pick', picked.value)
  visible.value = false
}
</script>

<template>
  <el-dialog v-model="visible" title="从题库选题" width="860px" top="6vh">
    <div class="filters">
      <el-input
        v-model="filters.keyword"
        placeholder="题号或标题"
        clearable
        :prefix-icon="Search"
        class="filters__keyword"
        @keyup.enter="search"
        @clear="search"
      />
      <el-select v-model="filters.difficulty" placeholder="难度" clearable class="filters__item" @change="search">
        <el-option v-for="(meta, value) in DIFFICULTIES" :key="value" :label="meta.label" :value="value" />
      </el-select>
      <el-tree-select
        v-model="filters.knowledge_point"
        :data="knowledgeTree"
        placeholder="知识点"
        check-strictly
        clearable
        filterable
        :render-after-expand="false"
        default-expand-all
        class="filters__item"
        @change="search"
      />
    </div>

    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="problems"
      row-key="id"
      size="small"
      max-height="420"
      class="picker-table"
      @selection-change="onSelectionChange"
    >
      <el-table-column type="selection" width="40" reserve-selection :selectable="(row) => !props.selectedIds.includes(row.id)" />
      <el-table-column prop="id" label="题号" width="64" />
      <el-table-column label="标题" min-width="200">
        <template #default="{ row }">
          {{ row.title }}
          <el-tag v-if="props.selectedIds.includes(row.id)" size="small" type="info">已在作业中</el-tag>
          <el-tag v-if="!row.has_test_cases" size="small" type="warning">无测试数据</el-tag>
          <el-tag v-if="!row.is_public" size="small" effect="plain">私有</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="知识点" min-width="140">
        <template #default="{ row }">{{ row.knowledge_points.map((p) => p.name).join('、') || '—' }}</template>
      </el-table-column>
      <el-table-column label="难度" width="70">
        <template #default="{ row }"><DifficultyTag :difficulty="row.difficulty" /></template>
      </el-table-column>
      <el-table-column label="通过率" width="80">
        <template #default="{ row }">{{ passRate(row) }}</template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > PAGE_SIZE"
      v-model:current-page="filters.page"
      class="pagination"
      layout="prev, pager, next, total"
      :total="total"
      :page-size="PAGE_SIZE"
      small
      @current-change="load"
    />

    <template #footer>
      <span class="picked">已选 {{ picked.length }} 道</span>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :disabled="!picked.length" @click="confirm">加入作业</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
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
  width: 160px;
}

.picker-table .el-tag {
  margin-left: 4px;
}

.pagination {
  justify-content: center;
  margin-top: 12px;
}

.picked {
  margin-right: 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
