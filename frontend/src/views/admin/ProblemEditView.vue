<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus } from '@element-plus/icons-vue'

import { adminProblemApi } from '@/api/adminProblem'
import { problemApi } from '@/api/problem'
import MarkdownEditor from '@/components/admin/MarkdownEditor.vue'
import TemplateCodeEditor from '@/components/admin/TemplateCodeEditor.vue'
import TestCaseUploader from '@/components/admin/TestCaseUploader.vue'
import { useSiteStore } from '@/stores/site'
import { DIFFICULTIES } from '@/utils/judge'
import { buildKnowledgeTree } from '@/utils/knowledgeTree'

// 与后端 problem/serializers.py 的校验范围一致
const MAX_SAMPLES = 10

const route = useRoute()
const site = useSiteStore()
const router = useRouter()

const problemId = computed(() => (route.params.id ? Number(route.params.id) : null))
const isCreate = computed(() => problemId.value === null)

const formRef = ref()
const uploaderRef = ref()
const loading = ref(false)
const loaded = ref(false)
const loadError = ref('')
const saving = ref(false)
const canEdit = ref(true)
const knowledgePoints = ref([])
const testCases = ref([])
const knowledgeTree = computed(() => buildKnowledgeTree(knowledgePoints.value))

function emptyForm() {
  return {
    title: '',
    difficulty: 'easy',
    time_limit: site.settings.default_time_limit_ms,
    memory_limit: site.settings.default_memory_limit_mb,
    knowledge_point_ids: [],
    is_public: false,
    description: '',
    input_desc: '',
    output_desc: '',
    samples: [{ input: '', output: '' }],
    hint: '',
    source: '',
    is_template: false,
    template_code: {},
    test_case_id: '',
  }
}

const form = reactive(emptyForm())
// 上次保存（或加载）时的表单快照，用于判断是否有未保存的修改
let savedSnapshot = ''
const snapshot = () => JSON.stringify(form)
const dirty = computed(() => loaded.value && snapshot() !== savedSnapshot)

const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  description: [{ required: true, message: '请输入题目描述', trigger: 'blur' }],
}

function fillForm(problem) {
  Object.assign(form, emptyForm(), {
    ...Object.fromEntries(Object.keys(emptyForm()).map((key) => [key, problem[key] ?? emptyForm()[key]])),
    knowledge_point_ids: problem.knowledge_points.map((point) => point.id),
    template_code: problem.template_code ?? {},
  })
  testCases.value = problem.test_cases
  canEdit.value = problem.can_edit
}

async function load() {
  loading.value = true
  loaded.value = false
  loadError.value = ''
  try {
    const [points, problem] = await Promise.all([
      problemApi.knowledgePoints(),
      isCreate.value ? null : adminProblemApi.detail(problemId.value, { silent: true }),
    ])
    knowledgePoints.value = points
    if (problem) {
      fillForm(problem)
      document.title = `编辑：${problem.title} - YGU OJ`
    } else {
      Object.assign(form, emptyForm())
      testCases.value = []
      canEdit.value = true
    }
    savedSnapshot = snapshot()
    loaded.value = true
  } catch (err) {
    loadError.value = err?.code === 404 ? '题目不存在，或你没有权限查看' : err?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

watch(problemId, load)
onMounted(load)

function addSample() {
  form.samples.push({ input: '', output: '' })
}

function removeSample(index) {
  form.samples.splice(index, 1)
}

async function save() {
  if (!(await formRef.value.validate().catch(() => false))) {
    ElMessage.warning('请检查标红的必填项')
    return
  }
  if (form.is_template && !Object.keys(form.template_code).length) {
    ElMessage.warning('模板题至少需要配置一种语言的模板')
    return
  }
  saving.value = true
  try {
    const payload = { ...form, samples: form.samples.filter((s) => s.input || s.output) }
    const problem = isCreate.value
      ? await adminProblemApi.create(payload)
      : await adminProblemApi.update(problemId.value, payload)
    fillForm(problem)
    savedSnapshot = snapshot()
    uploaderRef.value?.markSaved()
    ElMessage.success('已保存')
    if (isCreate.value) router.replace({ name: 'admin-problem-edit', params: { id: problem.id } })
  } catch {
    // 校验错误等提示已由请求拦截器弹出
  } finally {
    saving.value = false
  }
}

// 离开页面前确认未保存的修改
onBeforeRouteLeave(async (to) => {
  // 新建保存后跳转到编辑页时已无未保存修改
  if (!dirty.value || to.name === 'admin-problem-edit') return true
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
        <el-button type="primary" @click="router.push({ name: 'admin-problems' })">返回题库</el-button>
      </template>
    </el-result>

    <template v-else-if="loaded">
      <div class="page-header">
        <h2>{{ isCreate ? '新建题目' : `编辑题目 #${problemId}` }}</h2>
        <el-tag v-if="dirty" type="warning" effect="plain">未保存</el-tag>
        <span class="page-header__spacer" />
        <el-button
          v-if="!isCreate"
          @click="router.push({ name: 'problem-detail', params: { id: problemId } })"
        >
          前台预览
        </el-button>
        <el-button @click="router.push({ name: 'admin-problems' })">返回题库</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </div>
      <el-alert
        v-if="!canEdit"
        type="info"
        :closable="false"
        show-icon
        title="这是其他教师创建的题目，你只能查看，不能修改。"
        class="block"
      />

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        :disabled="!canEdit"
        label-position="top"
        class="edit-form"
      >
        <el-card shadow="never" class="block">
          <template #header>基本信息</template>
          <el-form-item label="标题" prop="title">
            <el-input v-model="form.title" maxlength="128" show-word-limit />
          </el-form-item>
          <div class="row">
            <el-form-item label="难度">
              <el-radio-group v-model="form.difficulty">
                <el-radio-button v-for="(meta, value) in DIFFICULTIES" :key="value" :value="value">
                  {{ meta.label }}
                </el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="时间限制（毫秒）">
              <el-input-number v-model="form.time_limit" :min="100" :max="10000" :step="100" />
            </el-form-item>
            <el-form-item label="内存限制（MB）">
              <el-input-number v-model="form.memory_limit" :min="16" :max="1024" :step="16" />
            </el-form-item>
            <el-form-item label="公开">
              <el-switch v-model="form.is_public" active-text="所有人可见" inactive-text="仅自己可见" />
            </el-form-item>
          </div>
          <el-form-item label="知识点">
            <el-tree-select
              v-model="form.knowledge_point_ids"
              :data="knowledgeTree"
              multiple
              check-strictly
              filterable
              show-checkbox
              :render-after-expand="false"
              default-expand-all
              placeholder="选择本题考查的知识点"
              class="full-width"
            />
          </el-form-item>
          <el-form-item label="来源">
            <el-input v-model="form.source" maxlength="128" placeholder="如：2026 秋季期中考试" />
          </el-form-item>
        </el-card>

        <el-card shadow="never" class="block">
          <template #header>题面（Markdown，支持 $公式$）</template>
          <el-form-item label="题目描述" prop="description">
            <MarkdownEditor v-model="form.description" height="360px" :read-only="!canEdit" />
          </el-form-item>
          <el-form-item label="输入格式">
            <MarkdownEditor v-model="form.input_desc" height="200px" :read-only="!canEdit" />
          </el-form-item>
          <el-form-item label="输出格式">
            <MarkdownEditor v-model="form.output_desc" height="200px" :read-only="!canEdit" />
          </el-form-item>
          <el-form-item label="提示">
            <MarkdownEditor v-model="form.hint" height="200px" :read-only="!canEdit" />
          </el-form-item>
        </el-card>

        <el-card shadow="never" class="block">
          <template #header>
            <div class="card-header">
              <span>样例（显示在题面中，不参与评测）</span>
              <el-button
                size="small"
                :icon="Plus"
                :disabled="!canEdit || form.samples.length >= MAX_SAMPLES"
                @click="addSample"
              >
                添加样例
              </el-button>
            </div>
          </template>
          <p v-if="!form.samples.length" class="muted">暂无样例</p>
          <div v-for="(sample, index) in form.samples" :key="index" class="sample">
            <el-form-item :label="`输入样例 ${index + 1}`">
              <el-input v-model="sample.input" type="textarea" :rows="4" class="mono" />
            </el-form-item>
            <el-form-item :label="`输出样例 ${index + 1}`">
              <el-input v-model="sample.output" type="textarea" :rows="4" class="mono" />
            </el-form-item>
            <el-button class="sample__remove" :icon="Delete" circle text @click="removeSample(index)" />
          </div>
        </el-card>

        <el-card shadow="never" class="block">
          <template #header>测试数据</template>
          <TestCaseUploader
            ref="uploaderRef"
            v-model="form.test_case_id"
            v-model:cases="testCases"
            :disabled="!canEdit"
          />
        </el-card>

        <el-card shadow="never" class="block">
          <template #header>
            <div class="card-header">
              <span>模板题</span>
              <el-switch v-model="form.is_template" />
            </div>
          </template>
          <p v-if="!form.is_template" class="muted">
            开启后学生只需补全函数体，系统评测时拼接为「前置代码 + 学生代码 + 后置代码」，适合低年级专项练习。
          </p>
          <TemplateCodeEditor v-else v-model="form.template_code" :disabled="!canEdit" />
        </el-card>
      </el-form>
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

.full-width {
  width: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sample {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
  padding-right: 40px;
}

.sample__remove {
  position: absolute;
  top: 28px;
  right: 0;
}

.mono :deep(textarea) {
  font-family: Consolas, Menlo, monospace;
}

.muted {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

@media (max-width: 760px) {
  .sample {
    grid-template-columns: 1fr;
  }
}
</style>
