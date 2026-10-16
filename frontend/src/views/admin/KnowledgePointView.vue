<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import { adminKnowledgePointApi } from '@/api/adminProblem'
import { problemApi } from '@/api/problem'
import { buildKnowledgeTree, courseNames } from '@/utils/knowledgeTree'
import PageHeader from '@/components/ui/PageHeader.vue'

const loading = ref(false)
const points = ref([])
const course = ref('')

const courses = computed(() => courseNames(points.value))
const tree = computed(() =>
  buildKnowledgeTree(course.value ? points.value.filter((p) => p.course === course.value) : points.value),
)

async function load() {
  loading.value = true
  try {
    points.value = await problemApi.knowledgePoints()
  } finally {
    loading.value = false
  }
}

onMounted(load)

// ---------------------------------------------------------------- 新增与编辑

const dialog = reactive({ visible: false, saving: false, editingId: null })
const formRef = ref()
const form = reactive({ name: '', course: '', parent: null })
const rules = { name: [{ required: true, message: '请输入名称', trigger: 'blur' }] }

// 上级知识点候选：编辑时排除自身及其下级，避免形成环
const parentOptions = computed(() => {
  if (!dialog.editingId) return buildKnowledgeTree(points.value)
  const excluded = new Set([dialog.editingId])
  let changed = true
  while (changed) {
    changed = false
    for (const p of points.value) {
      if (p.parent && excluded.has(p.parent) && !excluded.has(p.id)) {
        excluded.add(p.id)
        changed = true
      }
    }
  }
  return buildKnowledgeTree(points.value.filter((p) => !excluded.has(p.id)))
})

function openCreate(parent = null) {
  Object.assign(form, { name: '', course: parent?.course ?? course.value, parent: parent?.id ?? null })
  dialog.editingId = null
  dialog.visible = true
}

function openEdit(point) {
  Object.assign(form, { name: point.name, course: point.course, parent: point.parent })
  dialog.editingId = point.id
  dialog.visible = true
}

function onParentChange(parentId) {
  // 下级知识点默认与上级同属一门课程
  const parent = points.value.find((p) => p.id === parentId)
  if (parent) form.course = parent.course
}

function suggestCourses(keyword, callback) {
  callback(courses.value.filter((name) => name.includes(keyword)).map((value) => ({ value })))
}

async function save() {
  if (!(await formRef.value.validate().catch(() => false))) return
  dialog.saving = true
  try {
    const data = { name: form.name.trim(), course: form.course.trim(), parent: form.parent ?? null }
    if (dialog.editingId) await adminKnowledgePointApi.update(dialog.editingId, data)
    else await adminKnowledgePointApi.create(data)
    ElMessage.success('已保存')
    dialog.visible = false
    load()
  } catch {
    // 重名等错误提示已由请求拦截器弹出
  } finally {
    dialog.saving = false
  }
}

async function remove(point) {
  try {
    await ElMessageBox.confirm(`确定删除知识点「${point.name}」吗？题目上的该标签会一并移除。`, '删除知识点', {
      type: 'warning',
      confirmButtonText: '删除',
    })
  } catch {
    return
  }
  try {
    await adminKnowledgePointApi.remove(point.id)
    ElMessage.success('已删除')
    load()
  } catch {
    // 有下级知识点时后端拒绝删除，提示已由请求拦截器弹出
  }
}
</script>

<template>
  <div>
    <PageHeader title="知识点" subtitle="用于给题目打标签、按知识点筛选，以及统计学生的掌握情况">
      <el-select v-model="course" placeholder="全部课程" clearable class="header__course">
        <el-option v-for="name in courses" :key="name" :label="name" :value="name" />
      </el-select>
      <el-button type="primary" :icon="Plus" @click="openCreate()">新增知识点</el-button>
    </PageHeader>
    <el-card shadow="never">
      <p class="muted">知识点用于给题目打标签、按知识点筛选题目，以及统计学生的知识点掌握情况。</p>

      <el-tree
        v-loading="loading"
        :data="tree"
        node-key="id"
        default-expand-all
        :expand-on-click-node="false"
        empty-text="暂无知识点"
        class="tree"
      >
        <template #default="{ data }">
          <div class="node">
            <span class="node__name">{{ data.name }}</span>
            <el-tag v-if="data.course && !course" size="small" type="info" effect="plain">{{ data.course }}</el-tag>
            <span class="node__actions">
              <el-button link type="primary" size="small" @click="openCreate(data)">添加下级</el-button>
              <el-button link type="primary" size="small" @click="openEdit(data)">编辑</el-button>
              <el-button link type="danger" size="small" @click="remove(data)">删除</el-button>
            </span>
          </div>
        </template>
      </el-tree>

      <el-dialog v-model="dialog.visible" :title="dialog.editingId ? '编辑知识点' : '新增知识点'" width="460px">
        <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" @submit.prevent="save">
          <el-form-item label="名称" prop="name">
            <el-input v-model="form.name" maxlength="64" placeholder="如：循环、数组、指针" />
          </el-form-item>
          <el-form-item label="上级">
            <el-tree-select
              v-model="form.parent"
              :data="parentOptions"
              check-strictly
              clearable
              filterable
              :render-after-expand="false"
              placeholder="无（作为顶层知识点）"
              class="full-width"
              @update:model-value="onParentChange"
            />
          </el-form-item>
          <el-form-item label="课程">
            <el-autocomplete
              v-model="form.course"
              :fetch-suggestions="suggestCourses"
              maxlength="64"
              placeholder="如：C 语言程序设计"
              class="full-width"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialog.visible = false">取消</el-button>
          <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<style scoped>


.header__course {
  width: 200px;
}

.muted {
  margin: 0 0 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.tree :deep(.el-tree-node__content) {
  height: 36px;
}

.node {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 8px;
  padding-right: 8px;
}

.node__actions {
  margin-left: auto;
  opacity: 0.85;
}

.full-width {
  width: 100%;
}
</style>
