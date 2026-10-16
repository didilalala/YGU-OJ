<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import { adminClassApi } from '@/api/classroom'
import { adminExamApi } from '@/api/exam'
import { EXAM_STATUS, RULE_LABELS } from '@/utils/exam'
import { formatDateTime } from '@/utils/judge'

const route = useRoute()
const router = useRouter()

const PAGE_SIZE = 20

const loading = ref(false)
const exams = ref([])
const total = ref(0)
const classes = ref([])
// class_id=public 表示只看公开竞赛
const classId = computed(() => {
  const value = route.query.class_id
  if (!value) return null
  return value === 'public' ? 'public' : Number(value)
})
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
    const filter = classId.value === 'public' ? { scope: 'public' } : { class_id: classId.value ?? undefined }
    const data = await adminExamApi.list({ ...filter, page: page.value, page_size: PAGE_SIZE })
    exams.value = data.results
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

async function toggle(row, field, value, message) {
  try {
    await adminExamApi.update(row.id, { [field]: value })
    row[field] = value
    ElMessage.success(message)
  } catch {
    // 错误提示已由请求拦截器弹出
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确定删除考试「${row.title}」吗？`, '删除考试', { type: 'warning', confirmButtonText: '删除' })
  } catch {
    return
  }
  try {
    await adminExamApi.remove(row.id)
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
        <span class="header__title">考试</span>
        <el-select
          :model-value="classId"
          placeholder="全部班级"
          clearable
          class="header__class"
          @update:model-value="(v) => updateQuery({ class_id: v ?? null })"
        >
          <el-option label="公开竞赛" value="public" />
          <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-button
          type="primary"
          :icon="Plus"
          @click="router.push({ name: 'admin-exam-create', query: classId ? { class_id: classId } : {} })"
        >
          创建考试
        </el-button>
      </div>
    </template>

    <el-table v-loading="loading" :data="exams" empty-text="还没有考试">
      <el-table-column label="考试" min-width="200">
        <template #default="{ row }">
          <router-link :to="{ name: 'admin-exam-monitor', params: { id: row.id } }" class="link">{{ row.title }}</router-link>
          <div class="muted">
            {{ row.class_name ?? '公开竞赛' }} · {{ RULE_LABELS[row.rule_type] }} · {{ row.items.length }} 题
            <template v-if="row.allowed_ip_ranges.length"> · 限 IP</template>
            <template v-if="row.password"> · 有口令</template>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="200">
        <template #default="{ row }">
          <div class="muted">开始 {{ formatDateTime(row.start_time) }}</div>
          <div class="muted">结束 {{ formatDateTime(row.end_time) }}</div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="EXAM_STATUS[row.status].type" size="small">{{ EXAM_STATUS[row.status].label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="参加" width="90">
        <template #default="{ row }">{{ row.participant_count }} / {{ row.member_count }}</template>
      </el-table-column>
      <el-table-column label="发布" width="70">
        <template #default="{ row }">
          <el-switch
            :model-value="row.is_published"
            @update:model-value="(v) => toggle(row, 'is_published', v, v ? '已发布，班级学生可见' : '已取消发布')"
          />
        </template>
      </el-table-column>
      <el-table-column label="公布成绩" width="90">
        <template #default="{ row }">
          <el-switch
            :model-value="row.is_score_published"
            @update:model-value="(v) => toggle(row, 'is_score_published', v, v ? '已公布成绩' : '已撤回成绩')"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push({ name: 'admin-exam-monitor', params: { id: row.id } })">
            监考
          </el-button>
          <el-button link type="primary" @click="router.push({ name: 'admin-exam-edit', params: { id: row.id } })">
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
