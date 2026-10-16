<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, RefreshLeft } from '@element-plus/icons-vue'

import { assignmentApi } from '@/api/assignment'
import { examApi } from '@/api/exam'
import { problemApi } from '@/api/problem'
import { submissionApi } from '@/api/submission'
import DifficultyTag from '@/components/DifficultyTag.vue'
import MarkdownView from '@/components/MarkdownView.vue'
import SubmissionResult from '@/components/SubmissionResult.vue'
import { useSubmissionPolling } from '@/composables/useSubmissionPolling'
import { useSiteStore } from '@/stores/site'
import { useUserStore } from '@/stores/user'
import { copyText } from '@/utils/clipboard'
import { formatScore, latePolicy, timeLeft } from '@/utils/assignment'
import { formatDuration, serverOffset } from '@/utils/exam'
import { formatDateTime, passRate } from '@/utils/judge'
import { loadLocal, saveLocal } from '@/utils/storage'

// Monaco 体积较大，异步加载，先显示题面
const CodeEditor = defineAsyncComponent(() => import('@/components/CodeEditor.vue'))

// 与后端提交频率限制一致（同一用户 5 秒内只能提交一次）
const SUBMIT_COOLDOWN = 5
const LANGUAGE_KEY = 'oj_language'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const site = useSiteStore()
const { submission, error: pollError, start: startPolling, stop: stopPolling } = useSubmissionPolling()

const problem = ref(null)
const loading = ref(true)
const notFound = ref(false)
// 考试未开始、未进入考试等无法查看题目的原因
const loadMessage = ref('')
const language = ref('')
const code = ref('')
const submitting = ref(false)
const cooldown = ref(0)
let cooldownTimer = null
let draftTimer = null

// 从作业进入时（?assignment=），提交计入作业成绩
const assignmentId = computed(() => (route.query.assignment ? Number(route.query.assignment) : null))
const assignment = ref(null)
const assignmentItem = computed(() => assignment.value?.problems.find((p) => p.problem_id === problem.value?.id))
// 截止且不允许迟交时不能再提交
const assignmentClosed = computed(() => assignment.value?.status === 'ended')

// 从考场进入时（?exam=），提交计入考试成绩
const examId = computed(() => (route.query.exam ? Number(route.query.exam) : null))
const exam = ref(null)
const examOffset = ref(0)
const examNow = ref(Date.now())
const examIndex = computed(() => exam.value?.problems.findIndex((p) => p.problem_id === problem.value?.id) ?? -1)
const examLeft = computed(() =>
  exam.value?.status === 'in_progress'
    ? formatDuration((new Date(exam.value.end_time) - (examNow.value + examOffset.value)) / 1000)
    : '',
)
// 已交卷或不在考试时间内时不能提交
const examClosed = computed(() => !!exam.value && (exam.value.finished || exam.value.status !== 'in_progress'))
const examClock = setInterval(() => (examNow.value = Date.now()), 1000)
// 返回考场：公开竞赛回竞赛页，课堂考试回考场
const examRoute = computed(() => ({
  name: exam.value?.is_public ? 'contest-detail' : 'exam-detail',
  params: { id: examId.value },
}))

const draftKey = computed(() => `oj_draft_${problem.value?.id}_${language.value}`)
const canSubmit = computed(() => !submitting.value && cooldown.value === 0)

function initialCode(lang) {
  if (problem.value.is_template) return problem.value.template[lang] ?? ''
  return site.starterCode(lang)
}

function loadCode() {
  code.value = loadLocal(draftKey.value) ?? initialCode(language.value)
}

async function load(id) {
  // 在题目之间跳转时，先保存上一题尚未写入的草稿
  flushDraft()
  loading.value = true
  notFound.value = false
  loadMessage.value = ''
  stopPolling()
  submission.value = null
  try {
    // 不存在时页面自行显示提示，不再弹出错误消息
    let params
    if (examId.value) params = { exam_id: examId.value }
    else if (assignmentId.value) params = { assignment_id: assignmentId.value }
    const [detail, assignmentDetail, examDetail] = await Promise.all([
      problemApi.detail(id, { silent: true, params }),
      assignmentId.value ? assignmentApi.detail(assignmentId.value, { silent: true }).catch(() => null) : null,
      examId.value ? examApi.detail(examId.value, { silent: true }).catch(() => null) : null,
    ])
    problem.value = detail
    assignment.value = assignmentDetail
    exam.value = examDetail
    examOffset.value = serverOffset(examDetail?.server_time)
    document.title = `${problem.value.title} - YGU OJ`
    const preferred = loadLocal(LANGUAGE_KEY)
    language.value = problem.value.languages.includes(preferred) ? preferred : problem.value.languages[0]
    loadCode()
  } catch (err) {
    problem.value = null
    notFound.value = err?.code === 404
    loadMessage.value = notFound.value ? '' : err?.message || '题目加载失败，请刷新重试'
  } finally {
    loading.value = false
  }
}

watch(
  () => [route.params.id, route.query.assignment],
  ([id]) => id && load(id),
  { immediate: true },
)

function onLanguageChange(lang) {
  flushDraft()
  language.value = lang
  saveLocal(LANGUAGE_KEY, lang)
  loadCode()
}

// 代码草稿自动保存到浏览器，防止刷新或误关页面丢失
function flushDraft() {
  clearTimeout(draftTimer)
  if (!problem.value) return
  saveLocal(draftKey.value, code.value === initialCode(language.value) ? null : code.value)
}

watch(code, () => {
  clearTimeout(draftTimer)
  draftTimer = setTimeout(flushDraft, 500)
})

async function resetCode() {
  try {
    await ElMessageBox.confirm('将丢弃当前代码并恢复为初始代码，确定吗？', '重置代码', { type: 'warning' })
  } catch {
    return
  }
  code.value = initialCode(language.value)
  saveLocal(draftKey.value, null)
}

function startCooldown() {
  cooldown.value = SUBMIT_COOLDOWN
  clearInterval(cooldownTimer)
  cooldownTimer = setInterval(() => {
    cooldown.value -= 1
    if (cooldown.value <= 0) clearInterval(cooldownTimer)
  }, 1000)
}

async function submit() {
  if (!code.value.trim()) {
    ElMessage.warning('代码不能为空')
    return
  }
  submitting.value = true
  try {
    const { id } = await submissionApi.submit({
      problem_id: problem.value.id,
      assignment_id: assignmentId.value ?? undefined,
      exam_id: examId.value ?? undefined,
      language: language.value,
      code: code.value,
    })
    startCooldown()
    flushDraft()
    await startPolling(id)
  } catch {
    // 错误提示已由请求拦截器弹出
  } finally {
    submitting.value = false
  }
}

// 评测结束后就地更新做题状态与通过率，不必重新加载题目
watch(
  () => submission.value?.is_finished,
  (finished) => {
    if (!finished) return
    // 刷新考场中的题目状态
    if (examId.value) {
      examApi.detail(examId.value, { silent: true }).then((data) => (exam.value = data), () => {})
    }
    // 刷新作业得分
    if (assignmentId.value) {
      assignmentApi.detail(assignmentId.value, { silent: true }).then((data) => (assignment.value = data), () => {})
    }
    const accepted = submission.value.result === 'AC'
    problem.value.submission_count += 1
    if (accepted) {
      problem.value.accepted_count += 1
      problem.value.my_status = 'AC'
    } else if (!problem.value.my_status) {
      problem.value.my_status = 'TRIED'
    }
  },
)

async function copySample(text) {
  try {
    await copyText(text)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败，请手动选择文本复制')
  }
}

function goLogin() {
  router.push({ name: 'login', query: { redirect: route.fullPath } })
}

onBeforeUnmount(() => {
  clearInterval(examClock)
  flushDraft()
  clearInterval(cooldownTimer)
})
</script>

<template>
  <div v-loading="loading" class="problem-page">
    <el-result v-if="notFound" icon="warning" title="题目不存在" sub-title="题目可能已删除，或你没有权限查看">
      <template #extra>
        <el-button type="primary" @click="router.push({ name: 'problems' })">返回题目列表</el-button>
      </template>
    </el-result>

    <el-result v-else-if="loadMessage" icon="warning" :title="loadMessage">
      <template #extra>
        <el-button v-if="examId" type="primary" @click="router.push(examRoute)">
          返回考场
        </el-button>
        <el-button v-else type="primary" @click="router.push({ name: 'problems' })">返回题目列表</el-button>
      </template>
    </el-result>

    <template v-else-if="problem">
      <el-card shadow="never" class="statement">
        <div v-if="exam" class="assignment-banner exam-banner">
          <router-link :to="examRoute" class="assignment-banner__title">
            ← {{ exam.is_public ? '竞赛' : '考试' }}：{{ exam.title }}
          </router-link>
          <div class="assignment-banner__meta">
            <span v-if="examIndex >= 0">第 {{ String.fromCharCode(65 + examIndex) }} 题，{{ exam.problems[examIndex].score }} 分</span>
            <span v-if="examLeft">剩余时间 <strong>{{ examLeft }}</strong></span>
            <span v-if="exam.finished" class="warn">你已交卷，不能再提交</span>
            <span v-else-if="exam.status === 'ended'" class="warn">{{ exam.is_public ? '竞赛' : '考试' }}已结束</span>
          </div>
        </div>
        <div v-if="assignment" class="assignment-banner">
          <router-link :to="{ name: 'assignment-detail', params: { id: assignment.id } }" class="assignment-banner__title">
            ← 作业：{{ assignment.title }}
          </router-link>
          <div class="assignment-banner__meta">
            <span v-if="assignmentItem">本题 {{ assignmentItem.score }} 分，我的得分 {{ formatScore(assignmentItem.my_score) }}</span>
            <span v-if="timeLeft(assignment.end_time)">截止 {{ formatDateTime(assignment.end_time) }}（还剩 {{ timeLeft(assignment.end_time) }}）</span>
            <span v-else-if="assignment.status === 'late'" class="warn">已截止，{{ latePolicy(assignment) }}</span>
            <span v-else class="warn">作业已截止，不能再提交</span>
          </div>
        </div>
        <h1 class="statement__title">{{ problem.id }}. {{ problem.title }}</h1>
        <div class="statement__meta">
          <DifficultyTag :difficulty="problem.difficulty" />
          <span>时间限制 {{ problem.time_limit }} ms</span>
          <span>内存限制 {{ problem.memory_limit }} MB</span>
          <span v-if="!exam">通过率 {{ passRate(problem) }}</span>
          <el-tag v-if="problem.my_status === 'AC'" type="success" size="small">已通过</el-tag>
        </div>
        <div v-if="problem.knowledge_points.length && !exam" class="statement__points">
          <el-tag
            v-for="point in problem.knowledge_points"
            :key="point.id"
            size="small"
            effect="plain"
            @click="router.push({ name: 'problems', query: { knowledge_point: point.id } })"
          >
            {{ point.name }}
          </el-tag>
        </div>
        <el-alert
          v-if="problem.is_template"
          type="info"
          :closable="false"
          show-icon
          title="本题为模板题：只需补全给出的函数，main 函数等其余代码由系统提供。"
          class="statement__alert"
        />

        <section>
          <h2>题目描述</h2>
          <MarkdownView :content="problem.description" />
        </section>
        <section v-if="problem.input_desc">
          <h2>输入格式</h2>
          <MarkdownView :content="problem.input_desc" />
        </section>
        <section v-if="problem.output_desc">
          <h2>输出格式</h2>
          <MarkdownView :content="problem.output_desc" />
        </section>
        <section v-for="(sample, index) in problem.samples" :key="index" class="sample">
          <div v-for="part in ['input', 'output']" :key="part" class="sample__part">
            <div class="sample__head">
              <h2>{{ part === 'input' ? '输入' : '输出' }}样例 {{ problem.samples.length > 1 ? index + 1 : '' }}</h2>
              <el-button link type="primary" :icon="CopyDocument" @click="copySample(sample[part])">复制</el-button>
            </div>
            <pre>{{ sample[part] }}</pre>
          </div>
        </section>
        <section v-if="problem.hint">
          <h2>提示</h2>
          <MarkdownView :content="problem.hint" />
        </section>
        <section v-if="problem.source" class="statement__source">来源：{{ problem.source }}</section>
      </el-card>

      <div class="workspace">
        <el-card shadow="never" class="editor-card">
          <div class="editor-toolbar">
            <el-select :model-value="language" class="editor-toolbar__lang" @update:model-value="onLanguageChange">
              <el-option v-for="lang in problem.languages" :key="lang" :label="site.languageName(lang)" :value="lang" />
            </el-select>
            <el-button :icon="RefreshLeft" @click="resetCode">重置代码</el-button>
            <span class="editor-toolbar__spacer" />
            <el-button v-if="!userStore.isLoggedIn" type="primary" @click="goLogin">登录后提交</el-button>
            <el-button v-else-if="assignmentClosed" type="primary" disabled>作业已截止</el-button>
            <el-button v-else-if="examClosed" type="primary" disabled>{{ exam.finished ? '已交卷' : `不在${exam.is_public ? '竞赛' : '考试'}时间内` }}</el-button>
            <el-button v-else type="primary" :loading="submitting" :disabled="!canSubmit" @click="submit">
              {{ cooldown > 0 ? `提交（${cooldown}）` : '提交' }}
            </el-button>
          </div>
          <CodeEditor v-model="code" :language="site.languageMonaco(language)" height="460px" />
        </el-card>

        <el-card v-if="submission || pollError" shadow="never" class="result-card">
          <template #header>
            <div class="result-card__header">
              <span>评测结果</span>
              <router-link
                v-if="submission"
                :to="{ name: 'submission-detail', params: { id: submission.id } }"
                class="result-card__link"
              >
                提交 #{{ submission.id }}
              </router-link>
            </div>
          </template>
          <el-alert v-if="pollError" type="error" :closable="false" :title="pollError" />
          <SubmissionResult v-else :submission="submission" />
        </el-card>
      </div>
    </template>
  </div>
</template>

<style scoped>
.problem-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
  min-height: 300px;
}

.problem-page > .el-result {
  grid-column: 1 / -1;
}

.assignment-banner {
  margin: -4px 0 16px;
  padding: 10px 14px;
  border-left: 3px solid var(--oj-brand-navy);
  border-radius: 4px;
  background: var(--el-color-primary-light-9);
}

.exam-banner {
  border-left-color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
}

.assignment-banner__title {
  color: var(--el-color-primary);
  font-weight: 600;
  text-decoration: none;
}

.assignment-banner__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin-top: 4px;
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.assignment-banner__meta .warn {
  color: var(--el-color-warning-dark-2);
}

.statement__title {
  margin: 0 0 12px;
  font-size: 22px;
}

.statement__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.statement__points {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.statement__points .el-tag {
  cursor: pointer;
}

.statement__alert {
  margin-top: 12px;
}

.statement section {
  margin-top: 20px;
}

.statement h2 {
  margin: 0 0 8px;
  padding-left: 8px;
  border-left: 3px solid var(--oj-brand-orange);
  font-size: 16px;
}

.sample {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.sample__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sample pre {
  margin: 0;
  padding: 10px 12px;
  overflow-x: auto;
  border-radius: 4px;
  background: var(--el-fill-color-light);
  font-family: Consolas, Menlo, monospace;
  font-size: 14px;
  white-space: pre;
}

.statement__source {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

/* 编辑器跟随页面滚动固定在视口内，长题面时也能边看边写 */
.workspace {
  position: sticky;
  top: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.editor-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.editor-toolbar__lang {
  width: 130px;
}

.editor-toolbar__spacer {
  flex: 1;
}

.result-card__header {
  display: flex;
  justify-content: space-between;
}

.result-card__link {
  color: var(--el-color-primary);
  font-size: 13px;
  text-decoration: none;
}

@media (max-width: 1000px) {
  .problem-page {
    grid-template-columns: minmax(0, 1fr);
  }

  .workspace {
    position: static;
  }

  .sample {
    grid-template-columns: 1fr;
  }
}
</style>
