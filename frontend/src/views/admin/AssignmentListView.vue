<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import { adminAssignmentApi } from '@/api/assignment'
import { adminClassApi } from '@/api/classroom'
import { ASSIGNMENT_STATUS } from '@/utils/assignment'
import { formatDateTime } from '@/utils/judge'

const route = useRoute()
const router = useRouter()

const PAGE_SIZE = 20

const loading = ref(false)
const assignments = ref([])
const total = ref(0)
const classes = ref([])
const classId = computed(() => (route.query.class_id ? Number(route.query.class_id) : null))
const page = computed(() => Number(route.query.page) || 1)

function updateQuery(patch) {
  const next = { class_id: classId.value, page: page.value, ...patch }
  if (!('page' in patch)) next.page = 1
  const entries = Object.entries(next).filter(([k, v]) => v !== null && v !== '' && !(k === 'page' && v === 1))
  router.push({ query: Object.fromEntries(entries) })
}

async function load() {
  loading.value = true
  try {
    const data = await adminAssignmentApi.list({
      class_id: classId.value ?? undefined,
      page: page.value,
      page_size: PAGE_SIZE,
    })
    assignments.value = data.results
    total.value = data.total
  } finally {
    loading.value = false
  }
}

watch(() => route.query, load)
onMounted(async () => {
  load()
  classes.value = (await adminClassApi.list({ page_size: 100 })).results
})

async function togglePublished(row, value) {
  try {
    await adminAssignmentApi.update(row.id, { is_published: value })
    row.is_published = value
    ElMessage.success(value ? '已发布，班级学生可见' : '已取消发布，学生不再可见')
  } catch {
    // 错误提示已由请求拦截器弹出
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定删除作业「${row.title}」吗？`, '删除作业', {
      type: 'warning',
      confirmButtonText: '删除',
    })
  } catch {
    return
  }
  try {
    await adminAssignmentApi.remove(row.id)
    ElMessage.success('已删除')
    load()
  } catch {
    // 已有提交时后端拒绝删除，提示已由请求拦截器弹出
  }
}
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="header">
        <span class="header__title">作业</span>
        <el-select
          :model-value="classId"
          placeholder="全部班级"
          clearable
          class="header__class"
          @update:model-value="(v) => updateQuery({ class_id: v ?? null })"
        >
          <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-button
          type="primary"
          :icon="Plus"
          @click="router.push({ name: 'admin-assignment-create', query: classId ? { class_id: classId } : {} })"
        >
          布置作业
        </el-button>
      </div>
    </template>

    <el-table v-loading="loading" :data="assignments" empty-text="还没有作业">
      <el-table-column label="作业" min-width="200">
        <template #default="{ row }">
          <router-link :to="{ name: 'admin-assignment-results', params: { id: row.id } }" class="link">
            {{ row.title }}
          </router-link>
          <div class="muted">{{ row.class_name }} · {{ row.items.length }} 题 · 共 {{ row.total_score }} 分</div>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="200">
        <template #default="{ row }">
          <div class="muted">开始 {{ formatDateTime(row.start_time) }}</div>
          <div class="muted">截止 {{ formatDateTime(row.end_time) }}</div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="ASSIGNMENT_STATUS[row.status].type" size="small">{{ ASSIGNMENT_STATUS[row.status].label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="已提交" width="100">
        <template #default="{ row }">{{ row.submitted_count }} / {{ row.member_count }}</template>
      </el-table-column>
      <el-table-column label="发布" width="70">
        <template #default="{ row }">
          <el-switch :model-value="row.is_published" @update:model-value="(v) => togglePublished(row, v)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push({ name: 'admin-assignment-results', params: { id: row.id } })">
            成绩
          </el-button>
          <el-button link type="primary" @click="router.push({ name: 'admin-assignment-edit', params: { id: row.id } })">
            编辑
          </el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > PAGE_SIZE"
      class="pagination"
      layout="prev, pager, next, total"
      :total="total"
      :page-size="PAGE_SIZE"
      :current-page="page"
      @current-change="(p) => updateQuery({ page: p })"
    />
  </el-card>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header__title {
  margin-right: auto;
  font-size: 16px;
  font-weight: 600;
}

.header__class {
  width: 200px;
}

.link {
  color: var(--el-color-primary);
  font-weight: 600;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
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
