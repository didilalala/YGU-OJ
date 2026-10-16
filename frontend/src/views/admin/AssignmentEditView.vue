<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, ArrowUp, Delete, Plus } from '@element-plus/icons-vue'

import { adminAssignmentApi } from '@/api/assignment'
import { adminClassApi } from '@/api/classroom'
import MarkdownEditor from '@/components/admin/MarkdownEditor.vue'
import ProblemPicker from '@/components/admin/ProblemPicker.vue'
import DifficultyTag from '@/components/DifficultyTag.vue'

const DEFAULT_SCORE = 100

const route = useRoute()
const router = useRouter()

const assignmentId = computed(() => (route.params.id ? Number(route.params.id) : null))
const isCreate = computed(() => assignmentId.value === null)

const formRef = ref()
const loading = ref(false)
const loaded = ref(false)
const loadError = ref('')
const saving = ref(false)
const pickerVisible = ref(false)
const classes = ref([])

function defaultTimes() {
  // 默认现在开始、一周后 23:59 截止
  const start = new Date()
  start.setSeconds(0, 0)
  const end = new Date(start.getTime() + 7 * 24 * 3600 * 1000)
  end.setHours(23, 59, 0, 0)
  return [start, end]
}

function emptyForm() {
  return {
    class_group: route.query.class_id ? Number(route.query.class_id) : null,
    title: '',
    description: '',
    times: defaultTimes(),
    allow_late: false,
    late_penalty_percent: 20,
    is_published: true,
    // [{ problem_id, title, difficulty, score }]
    items: [],
  }
}

const form = reactive(emptyForm())
let savedSnapshot = ''
const snapshot = () => JSON.stringify(form)
const dirty = computed(() => loaded.value && snapshot() !== savedSnapshot)
const totalScore = computed(() => form.items.reduce((sum, item) => sum + (item.score || 0), 0))

const rules = {
  class_group: [{ required: true, message: '请选择班级', trigger: 'change' }],
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  times: [{ required: true, message: '请选择起止时间', trigger: 'change' }],
}

function fillForm(assignment) {
  Object.assign(form, {
    class_group: assignment.class_group,
    title: assignment.title,
    description: assignment.description,
    times: [new Date(assignment.start_time), new Date(assignment.end_time)],
    allow_late: assignment.allow_late,
    late_penalty_percent: Math.round(assignment.late_penalty * 100),
    is_published: assignment.is_published,
    items: assignment.items.map((item) => ({ ...item })),
  })
}

async function load() {
  loading.value = true
  loaded.value = false
  try {
    const [classPage, assignment] = await Promise.all([
      adminClassApi.list({ page_size: 100 }),
      isCreate.value ? null : adminAssignmentApi.detail(assignmentId.value, { silent: true }),
    ])
    classes.value = classPage.results
    if (assignment) {
      fillForm(assignment)
      document.title = `编辑：${assignment.title} - YGU OJ`
    } else {
      Object.assign(form, emptyForm())
    }
    savedSnapshot = snapshot()
    loaded.value = true
  } catch (err) {
    loadError.value = err?.code === 404 ? '作业不存在，或你没有权限管理' : err?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

watch(assignmentId, load)
onMounted(load)

// ---------------------------------------------------------------- 题目

function addProblems(problems) {
  for (const problem of problems) {
    form.items.push({ problem_id: problem.id, title: problem.title, difficulty: problem.difficulty, score: DEFAULT_SCORE })
  }
  const missing = problems.filter((p) => !p.has_test_cases)
  if (missing.length) ElMessage.warning(`有 ${missing.length} 道题目尚未上传测试数据，学生暂时无法提交`)
}

function move(index, offset) {
  const [item] = form.items.splice(index, 1)
  form.items.splice(index + offset, 0, item)
}

function removeItem(index) {
  form.items.splice(index, 1)
}

// ---------------------------------------------------------------- 保存

async function save() {
  if (!(await formRef.value.validate().catch(() => false))) {
    ElMessage.warning('请检查标红的必填项')
    return
  }
  if (!form.items.length) {
    ElMessage.warning('请至少添加一道题目')
    return
  }
  saving.value = true
  try {
    const [start, end] = form.times
    const payload = {
      title: form.title.trim(),
      description: form.description,
      start_time: start,
      end_time: end,
      allow_late: form.allow_late,
      late_penalty: form.allow_late ? form.late_penalty_percent / 100 : 0,
      is_published: form.is_published,
      problems: form.items.map(({ problem_id, score }) => ({ problem_id, score })),
    }
    if (isCreate.value) payload.class_group = form.class_group
    const assignment = isCreate.value
      ? await adminAssignmentApi.create(payload)
      : await adminAssignmentApi.update(assignmentId.value, payload)
    fillForm(assignment)
    savedSnapshot = snapshot()
    ElMessage.success(isCreate.value ? '作业已布置' : '已保存，成绩已按新设置重新计算')
    if (isCreate.value) router.replace({ name: 'admin-assignment-edit', params: { id: assignment.id } })
  } catch {
    // 校验错误提示已由请求拦截器弹出
  } finally {
    saving.value = false
  }
}

onBeforeRouteLeave(async (to) => {
  if (!dirty.value || to.name === 'admin-assignment-edit') return true
  try {
    await ElMessageBox.confirm('有未保存的修改，确定离开吗？', '离开页面', {
      type: 'warning',
      confirmButtonText: '离开',
      cancelButtonText: '留下',
    })
    return true
  } catch {
    return false
  }
})

function onBeforeUnload(event) {
  if (dirty.value) event.preventDefault()
}
window.addEventListener('beforeunload', onBeforeUnload)
onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))
</script>

<template>
  <div v-loading="loading" class="edit-page">
    <el-result v-if="loadError" icon="warning" :title="loadError">
      <template #extra>
        <el-button type="primary" @click="router.push({ name: 'admin-assignments' })">返回作业列表</el-button>
      </template>
    </el-result>

    <template v-else-if="loaded">
      <div class="page-header">
        <h2>{{ isCreate ? '布置作业' : `编辑作业 #${assignmentId}` }}</h2>
        <el-tag v-if="dirty" type="warning" effect="plain">未保存</el-tag>
        <span class="page-header__spacer" />
        <el-button
          v-if="!isCreate"
          @click="router.push({ name: 'admin-assignment-results', params: { id: assignmentId } })"
        >
          查看成绩
        </el-button>
        <el-button @click="router.push({ name: 'admin-assignments' })">返回列表</el-button>
        <el-button type="primary" :loading="saving" @click="save">{{ isCreate ? '布置' : '保存' }}</el-button>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-card shadow="never" class="block">
          <template #header>基本信息</template>
          <div class="row">
            <el-form-item label="班级" prop="class_group" class="row__class">
              <el-select
                v-model="form.class_group"
                :disabled="!isCreate"
                placeholder="选择班级"
                filterable
                class="full-width"
              >
                <el-option
                  v-for="item in classes"
                  :key="item.id"
                  :label="`${item.name}（${item.member_count} 人）`"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="标题" prop="title" class="row__title">
              <el-input v-model="form.title" maxlength="128" placeholder="如：第 3 周 循环练习" />
            </el-form-item>
          </div>
          <div class="row">
            <el-form-item label="起止时间" prop="times">
              <el-date-picker
                v-model="form.times"
                type="datetimerange"
                start-placeholder="开始时间"
                end-placeholder="截止时间"
                format="YYYY-MM-DD HH:mm"
                :clearable="false"
              />
            </el-form-item>
            <el-form-item label="迟交">
              <div class="late">
                <el-switch v-model="form.allow_late" active-text="允许迟交" inactive-text="截止后不能提交" />
                <template v-if="form.allow_late">
                  <span>迟交得分扣</span>
                  <el-input-number v-model="form.late_penalty_percent" :min="0" :max="100" :step="10" size="small" />
                  <span>%</span>
                </template>
              </div>
            </el-form-item>
            <el-form-item label="发布">
              <el-switch v-model="form.is_published" active-text="班级学生可见" inactive-text="草稿" />
            </el-form-item>
          </div>
          <el-form-item label="说明（可选）">
            <MarkdownEditor v-model="form.description" height="200px" placeholder="作业要求、注意事项等" />
          </el-form-item>
        </el-card>

        <el-card shadow="never" class="block">
          <template #header>
            <div class="card-header">
              <span>题目（{{ form.items.length }} 道，共 {{ totalScore }} 分）</span>
              <el-button type="primary" plain :icon="Plus" @click="pickerVisible = true">从题库选题</el-button>
            </div>
          </template>
          <p class="muted">学生每题取最高得分；部分通过按通过测试点的比例给分。</p>
          <el-table :data="form.items" empty-text="还没有题目，点击「从题库选题」添加">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column label="题目" min-width="220">
              <template #default="{ row }">{{ row.problem_id }}. {{ row.title }}</template>
            </el-table-column>
            <el-table-column label="难度" width="80">
              <template #default="{ row }"><DifficultyTag :difficulty="row.difficulty" /></template>
            </el-table-column>
            <el-table-column label="分值" width="150">
              <template #default="{ row }">
                <el-input-number v-model="row.score" :min="1" :max="1000" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="130">
              <template #default="{ $index }">
                <el-button :icon="ArrowUp" circle text size="small" :disabled="$index === 0" @click="move($index, -1)" />
                <el-button
                  :icon="ArrowDown"
                  circle
                  text
                  size="small"
                  :disabled="$index === form.items.length - 1"
                  @click="move($index, 1)"
                />
                <el-button :icon="Delete" circle text size="small" @click="removeItem($index)" />
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-form>

      <ProblemPicker
        v-model="pickerVisible"
        :selected-ids="form.items.map((item) => item.problem_id)"
        @pick="addProblems"
      />
    </template>
  </div>
</template>

<style scoped>
.edit-page {
  min-height: 300px;
}

.page-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: -20px -20px 16px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--el-border-color-light);
  background: #f5f7fa;
}

.page-header h2 {
  margin: 0;
  font-size: 18px;
}

.page-header__spacer {
  flex: 1;
}

.block {
  margin-bottom: 16px;
}

.row {
  display: flex;
  flex-wrap: wrap;
  gap: 0 32px;
}

.row__class {
  width: 280px;
}

.row__title {
  flex: 1;
  min-width: 280px;
}

.late {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.full-width {
  width: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.muted {
  margin: 0 0 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
