<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, ArrowUp, Delete, Plus } from '@element-plus/icons-vue'

import { adminClassApi } from '@/api/classroom'
import { adminExamApi } from '@/api/exam'
import MarkdownEditor from '@/components/admin/MarkdownEditor.vue'
import ProblemPicker from '@/components/admin/ProblemPicker.vue'
import DifficultyTag from '@/components/DifficultyTag.vue'
import { RULE_LABELS, RULE_TIPS } from '@/utils/exam'

const DEFAULT_SCORE = 100
const PUBLIC = 'public'

const route = useRoute()
const router = useRouter()

const examId = computed(() => (route.params.id ? Number(route.params.id) : null))
const isCreate = computed(() => examId.value === null)

const formRef = ref()
const loading = ref(false)
const loaded = ref(false)
const loadError = ref('')
const saving = ref(false)
const pickerVisible = ref(false)
const classes = ref([])

function defaultTimes() {
  // 默认下一个整点开始，考试 2 小时
  const start = new Date()
  start.setHours(start.getHours() + 1, 0, 0, 0)
  return [start, new Date(start.getTime() + 2 * 3600 * 1000)]
}

function emptyForm() {
  return {
    // 'public' 表示公开竞赛（不限班级），保存时转为 null
    class_group: route.query.class_id === 'public' ? PUBLIC : route.query.class_id ? Number(route.query.class_id) : null,
    title: '',
    description: '',
    rule_type: 'OI',
    times: defaultTimes(),
    ip_ranges_text: '',
    password: '',
    is_published: true,
    show_rank: route.query.class_id === 'public',
    lock_problem_bank: route.query.class_id !== 'public',
    // [{ problem_id, title, difficulty, score }]
    items: [],
  }
}

const form = reactive(emptyForm())
let savedSnapshot = ''
const snapshot = () => JSON.stringify(form)
const dirty = computed(() => loaded.value && snapshot() !== savedSnapshot)
// 公开竞赛：所有登录用户可参加，不锁定题库
const isPublic = computed(() => form.class_group === PUBLIC)
watch(isPublic, (value) => {
  if (!isCreate.value) return
  form.show_rank = value
  form.lock_problem_bank = !value
})
const totalScore = computed(() => form.items.reduce((sum, item) => sum + (item.score || 0), 0))

const rules = {
  class_group: [{ required: true, message: '请选择参加范围', trigger: 'change' }],
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  times: [{ required: true, message: '请选择起止时间', trigger: 'change' }],
}

function fillForm(exam) {
  Object.assign(form, {
    class_group: exam.class_group ?? PUBLIC,
    title: exam.title,
    description: exam.description,
    rule_type: exam.rule_type,
    times: [new Date(exam.start_time), new Date(exam.end_time)],
    ip_ranges_text: exam.allowed_ip_ranges.join('\n'),
    password: exam.password,
    is_published: exam.is_published,
    show_rank: exam.show_rank,
    lock_problem_bank: exam.lock_problem_bank,
    items: exam.items.map((item) => ({ ...item })),
  })
}

async function load() {
  loading.value = true
  loaded.value = false
  try {
    const [classPage, exam] = await Promise.all([
      adminClassApi.list({ page_size: 100 }),
      isCreate.value ? null : adminExamApi.detail(examId.value, { silent: true }),
    ])
    classes.value = classPage.results
    if (exam) {
      fillForm(exam)
      document.title = `编辑：${exam.title} - YGU OJ`
    } else {
      Object.assign(form, emptyForm())
    }
    savedSnapshot = snapshot()
    loaded.value = true
  } catch (err) {
    loadError.value = err?.code === 404 ? '考试不存在，或你没有权限管理' : err?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

watch(examId, load)
onMounted(load)

function addProblems(problems) {
  for (const problem of problems) {
    form.items.push({ problem_id: problem.id, title: problem.title, difficulty: problem.difficulty, score: DEFAULT_SCORE })
  }
  const missing = problems.filter((p) => !p.has_test_cases)
  if (missing.length) ElMessage.warning(`有 ${missing.length} 道题目尚未上传测试数据，学生将无法提交`)
}

function move(index, offset) {
  const [item] = form.items.splice(index, 1)
  form.items.splice(index + offset, 0, item)
}

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
      rule_type: form.rule_type,
      start_time: start,
      end_time: end,
      allowed_ip_ranges: form.ip_ranges_text.split(/[\s,，]+/).filter(Boolean),
      password: form.password.trim(),
      is_published: form.is_published,
      show_rank: form.show_rank,
      lock_problem_bank: form.lock_problem_bank,
      problems: form.items.map(({ problem_id, score }) => ({ problem_id, score })),
    }
    if (isCreate.value) payload.class_group = isPublic.value ? null : form.class_group
    const exam = isCreate.value ? await adminExamApi.create(payload) : await adminExamApi.update(examId.value, payload)
    fillForm(exam)
    savedSnapshot = snapshot()
    ElMessage.success(isCreate.value ? '考试已创建' : '已保存')
    if (isCreate.value) router.replace({ name: 'admin-exam-edit', params: { id: exam.id } })
  } catch {
    // 校验错误提示已由请求拦截器弹出
  } finally {
    saving.value = false
  }
}

onBeforeRouteLeave(async (to) => {
  if (!dirty.value || to.name === 'admin-exam-edit') return true
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
        <el-button type="primary" @click="router.push({ name: 'admin-exams' })">返回考试列表</el-button>
      </template>
    </el-result>

    <template v-else-if="loaded">
      <div class="page-header">
        <h2>{{ isCreate ? '创建考试' : `编辑考试 #${examId}` }}</h2>
        <el-tag v-if="dirty" type="warning" effect="plain">未保存</el-tag>
        <span class="page-header__spacer" />
        <el-button v-if="!isCreate" @click="router.push({ name: 'admin-exam-monitor', params: { id: examId } })">监考</el-button>
        <el-button @click="router.push({ name: 'admin-exams' })">返回列表</el-button>
        <el-button type="primary" :loading="saving" @click="save">{{ isCreate ? '创建' : '保存' }}</el-button>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-card shadow="never" class="block">
          <template #header>基本信息</template>
          <div class="row">
            <el-form-item label="参加范围" prop="class_group" class="row__class">
              <el-select v-model="form.class_group" :disabled="!isCreate" placeholder="选择班级或公开竞赛" filterable class="full-width">
                <el-option label="公开竞赛（所有登录用户可参加）" :value="PUBLIC" />
                <el-option
                  v-for="item in classes"
                  :key="item.id"
                  :label="`${item.name}（${item.member_count} 人）`"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="标题" prop="title" class="row__title">
              <el-input v-model="form.title" maxlength="128" placeholder="如：C 语言期中上机考试" />
            </el-form-item>
          </div>
          <div class="row">
            <el-form-item label="起止时间" prop="times">
              <el-date-picker
                v-model="form.times"
                type="datetimerange"
                start-placeholder="开始时间"
                end-placeholder="结束时间"
                format="YYYY-MM-DD HH:mm"
                :clearable="false"
              />
            </el-form-item>
            <el-form-item label="赛制">
              <el-radio-group v-model="form.rule_type">
                <el-radio-button v-for="(label, value) in RULE_LABELS" :key="value" :value="value">{{ label }}</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </div>
          <p class="muted">{{ RULE_TIPS[form.rule_type] }}</p>
          <el-form-item label="说明（可选）">
            <MarkdownEditor v-model="form.description" height="180px" placeholder="考试须知，如允许携带的资料等" />
          </el-form-item>
        </el-card>

        <el-card shadow="never" class="block">
          <template #header>考场设置</template>
          <div class="row">
            <el-form-item label="允许的 IP 段（每行一个，留空不限制）" class="row__ip">
              <el-input
                v-model="form.ip_ranges_text"
                type="textarea"
                :rows="4"
                placeholder="如机房网段：&#10;10.1.0.0/16&#10;202.1.2.3"
                class="mono"
              />
            </el-form-item>
            <el-form-item label="考试口令（可选）" class="row__password">
              <el-input v-model="form.password" maxlength="32" placeholder="开考时在机房公布，学生进入考试时输入" />
            </el-form-item>
          </div>
          <div class="switches">
            <el-switch
              v-if="!isPublic"
              v-model="form.lock_problem_bank"
              active-text="考试期间锁定题库（学生只能访问考试题目，不能查看题库、作业与历史代码）"
            />
            <el-switch
              v-model="form.show_rank"
              :active-text="isPublic ? '进行中公开实时排名（访客也能看，学号打码、不显示姓名）' : '考试中学生可查看实时排名'"
            />
            <el-switch v-model="form.is_published" :active-text="isPublic ? '发布（所有人可见）' : '发布（班级学生可见）'" />
          </div>
        </el-card>

        <el-card shadow="never" class="block">
          <template #header>
            <div class="card-header">
              <span>题目（{{ form.items.length }} 道，共 {{ totalScore }} 分）</span>
              <el-button type="primary" plain :icon="Plus" @click="pickerVisible = true">从题库选题</el-button>
            </div>
          </template>
          <el-table :data="form.items" empty-text="还没有题目，点击「从题库选题」添加">
            <el-table-column label="题号" width="64">
              <template #default="{ $index }">{{ String.fromCharCode(65 + $index) }}</template>
            </el-table-column>
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
                <el-button :icon="ArrowDown" circle text size="small" :disabled="$index === form.items.length - 1" @click="move($index, 1)" />
                <el-button :icon="Delete" circle text size="small" @click="form.items.splice($index, 1)" />
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-form>

      <ProblemPicker v-model="pickerVisible" :selected-ids="form.items.map((item) => item.problem_id)" @pick="addProblems" />
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

.row__ip {
  width: 320px;
}

.row__password {
  width: 320px;
}

.switches {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.full-width {
  width: 100%;
}

.mono :deep(textarea) {
  font-family: Consolas, Menlo, monospace;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.muted {
  margin: -8px 0 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
