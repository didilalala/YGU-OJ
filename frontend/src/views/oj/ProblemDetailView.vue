<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowDown, ArrowUp, RefreshLeft, VideoPlay } from '@element-plus/icons-vue'

import { assignmentApi } from '@/api/assignment'
import { examApi } from '@/api/exam'
import { problemApi } from '@/api/problem'
import { submissionApi } from '@/api/submission'
import MarkdownView from '@/components/MarkdownView.vue'
import SubmissionResult from '@/components/SubmissionResult.vue'
import CodeBlock from '@/components/ui/CodeBlock.vue'
import Countdown from '@/components/ui/Countdown.vue'
import DifficultyBadge from '@/components/ui/DifficultyBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SplitPane from '@/components/ui/SplitPane.vue'
import VerdictBadge from '@/components/ui/VerdictBadge.vue'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { useSubmissionPolling } from '@/composables/useSubmissionPolling'
import { useSiteStore } from '@/stores/site'
import { useUserStore } from '@/stores/user'
import { formatScore, latePolicy, timeLeft } from '@/utils/assignment'
import { serverOffset } from '@/utils/exam'
import { formatDateTime, formatMemory, formatTime, passRate, timeAgo } from '@/utils/judge'
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
const examIndex = computed(() => exam.value?.problems.findIndex((p) => p.problem_id === problem.value?.id) ?? -1)
// 已交卷或不在考试时间内时不能提交
const examClosed = computed(() => !!exam.value && (exam.value.finished || exam.value.status !== 'in_progress'))
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

// Ctrl/⌘ + Enter 也走这里，需要与按钮相同的限制
function trySubmit() {
  if (!userStore.isLoggedIn) return goLogin()
  if (assignmentClosed.value || examClosed.value || !canSubmit.value) return
  submit()
}

function goLogin() {
  router.push({ name: 'login', query: { redirect: route.fullPath } })
}


const isNarrow = useMediaQuery('(max-width: 900px)')
// 窄屏下用标签页切换「题目 / 代码」
const mobileTab = ref('statement')
const sideTab = ref('statement')
const resultOpen = ref(true)

// 「我的提交」：当前题目的历史提交（登录后可见）
const history = ref([])
const historyLoading = ref(false)
async function loadHistory() {
  if (!userStore.isLoggedIn || !problem.value) return
  historyLoading.value = true
  try {
    const params = { problem_id: problem.value.id, page_size: 20 }
    const data = await submissionApi.list(params)
    history.value = data.results
  } catch {
    history.value = []
  } finally {
    historyLoading.value = false
  }
}
watch(sideTab, (value) => value === 'history' && loadHistory())
watch(
  () => problem.value?.id,
  () => {
    sideTab.value = 'statement'
    history.value = []
    resultOpen.value = true
  },
)
watch(
  () => submission.value?.is_finished,
  (finished) => {
    if (finished && sideTab.value === 'history') loadHistory()
  },
)
// 提交后自动展开结果面板；窄屏下也要能看到结果
watch(
  () => submission.value?.id,
  () => {
    resultOpen.value = true
  },
)

const letter = (index) => String.fromCharCode(65 + index)
const contextBanner = computed(() => !!exam.value || !!assignment.value)
const submitLabel = computed(() => (cooldown.value > 0 ? `提交（${cooldown.value}）` : '提交'))
const submitDisabledText = computed(() => {
  if (assignmentClosed.value) return '作业已截止'
  if (examClosed.value) return exam.value.finished ? '已交卷' : `不在${exam.value.is_public ? '竞赛' : '考试'}时间内`
  return ''
})

onBeforeUnmount(() => {
  flushDraft()
  clearInterval(cooldownTimer)
})
</script>

<template>
  <div v-loading="loading" class="ws">
    <div v-if="notFound || loadMessage" class="ws__center">
      <el-result v-if="notFound" icon="warning" title="题目不存在" sub-title="题目可能已删除，或你没有权限查看">
        <template #extra>
          <el-button type="primary" @click="router.push({ name: 'problems' })">返回题库</el-button>
        </template>
      </el-result>
      <el-result v-else icon="warning" :title="loadMessage">
        <template #extra>
          <el-button v-if="examId" type="primary" @click="router.push(examRoute)">返回考场</el-button>
          <el-button v-else type="primary" @click="router.push({ name: 'problems' })">返回题库</el-button>
        </template>
      </el-result>
    </div>

    <template v-else-if="problem">
      <!-- 考试 / 作业上下文条 -->
      <div v-if="exam" class="ctx ctx--exam">
        <router-link :to="examRoute" class="ctx__back"><el-icon><ArrowLeft /></el-icon>{{ exam.is_public ? '竞赛' : '考试' }}：{{ exam.title }}</router-link>
        <nav class="ctx__strip" aria-label="试卷题目">
          <router-link
            v-for="(p, index) in exam.problems"
            :key="p.problem_id"
            :to="{ name: 'problem-detail', params: { id: p.problem_id }, query: { exam: exam.id } }"
            class="chip"
            :class="{
              'is-current': p.problem_id === problem.id,
              'is-ac': p.accepted,
              'is-tried': !p.accepted && p.attempted,
            }"
            :title="`${letter(index)}. ${p.title}（${p.score} 分）`"
          >
            {{ letter(index) }}
          </router-link>
        </nav>
        <span v-if="examIndex >= 0" class="ctx__item">第 {{ letter(examIndex) }} 题 · {{ exam.problems[examIndex].score }} 分</span>
        <span class="ctx__spacer" />
        <span v-if="exam.status === 'in_progress'" class="ctx__item">
          剩余 <Countdown :end="exam.end_time" :offset="examOffset" />
        </span>
        <span v-if="exam.finished" class="ctx__warn">你已交卷，不能再提交</span>
        <span v-else-if="exam.status === 'ended'" class="ctx__warn">{{ exam.is_public ? '竞赛' : '考试' }}已结束</span>
      </div>
      <div v-else-if="assignment" class="ctx">
        <router-link :to="{ name: 'assignment-detail', params: { id: assignment.id } }" class="ctx__back">
          <el-icon><ArrowLeft /></el-icon>作业：{{ assignment.title }}
        </router-link>
        <span v-if="assignmentItem" class="ctx__item">本题 {{ assignmentItem.score }} 分 · 我的得分 {{ formatScore(assignmentItem.my_score) }}</span>
        <span class="ctx__spacer" />
        <span v-if="timeLeft(assignment.end_time)" class="ctx__item">
          截止 {{ formatDateTime(assignment.end_time) }}（还剩 {{ timeLeft(assignment.end_time) }}）
        </span>
        <span v-else-if="assignment.status === 'late'" class="ctx__warn">已截止，{{ latePolicy(assignment) }}</span>
        <span v-else class="ctx__warn">作业已截止，不能再提交</span>
      </div>

      <div v-if="isNarrow" class="seg" role="tablist">
        <button role="tab" :aria-selected="mobileTab === 'statement'" :class="{ 'is-on': mobileTab === 'statement' }" @click="mobileTab = 'statement'">题目</button>
        <button role="tab" :aria-selected="mobileTab === 'code'" :class="{ 'is-on': mobileTab === 'code' }" @click="mobileTab = 'code'">代码与结果</button>
      </div>

      <SplitPane
        class="ws__split"
        storage-key="problem"
        :single="isNarrow"
        :active="mobileTab === 'code' ? 'right' : 'left'"
      >
        <!-- 左：题面 -->
        <template #left>
          <section class="pane statement">
            <el-tabs v-model="sideTab" class="statement__tabs">
              <el-tab-pane label="题目描述" name="statement" />
              <el-tab-pane v-if="userStore.isLoggedIn && !exam" label="我的提交" name="history" />
            </el-tabs>

            <div v-show="sideTab === 'statement'" class="pane__scroll">
              <h1 class="statement__title">{{ problem.id }}. {{ problem.title }}</h1>
              <div class="statement__meta">
                <DifficultyBadge :difficulty="problem.difficulty" />
                <span>时间 <b class="num">{{ problem.time_limit }} ms</b></span>
                <span>内存 <b class="num">{{ problem.memory_limit }} MB</b></span>
                <span v-if="!exam">通过率 <b class="num">{{ passRate(problem) }}</b></span>
                <el-tag v-if="problem.my_status === 'AC'" type="success" size="small" effect="light">已通过</el-tag>
                <el-tag v-else-if="problem.my_status === 'TRIED'" type="warning" size="small" effect="light">尝试过</el-tag>
              </div>
              <div v-if="problem.knowledge_points.length && !exam" class="statement__points">
                <el-tag
                  v-for="point in problem.knowledge_points"
                  :key="point.id"
                  size="small"
                  effect="plain"
                  class="point"
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
                <h2>样例{{ problem.samples.length > 1 ? ` ${index + 1}` : '' }}</h2>
                <div class="sample__pair">
                  <CodeBlock title="输入" :text="sample.input" />
                  <CodeBlock title="输出" :text="sample.output" />
                </div>
              </section>
              <section v-if="problem.hint">
                <h2>提示</h2>
                <MarkdownView :content="problem.hint" />
              </section>
              <section v-if="problem.source" class="statement__source">来源：{{ problem.source }}</section>
            </div>

            <div v-show="sideTab === 'history'" class="pane__scroll">
              <el-table v-loading="historyLoading" :data="history" size="small" empty-text="" class="history">
                <el-table-column label="结果" width="120">
                  <template #default="{ row }">
                    <router-link :to="{ name: 'submission-detail', params: { id: row.id } }">
                      <VerdictBadge :result="row.result" size="sm" />
                    </router-link>
                  </template>
                </el-table-column>
                <el-table-column label="耗时" width="80" class-name="num">
                  <template #default="{ row }">{{ formatTime(row.time_cost) }}</template>
                </el-table-column>
                <el-table-column label="内存" width="90" class-name="num">
                  <template #default="{ row }">{{ formatMemory(row.memory_cost) }}</template>
                </el-table-column>
                <el-table-column label="语言" min-width="80">
                  <template #default="{ row }">{{ site.languageName(row.language) }}</template>
                </el-table-column>
                <el-table-column label="时间" min-width="90">
                  <template #default="{ row }"><span class="muted">{{ timeAgo(row.created_at) }}</span></template>
                </el-table-column>
              </el-table>
              <EmptyState v-if="!historyLoading && !history.length" compact title="还没有提交" description="提交代码后，历史记录会显示在这里" />
              <router-link
                v-if="history.length"
                :to="{ name: 'submissions', query: { problem_id: problem.id } }"
                class="text-link history__more"
              >
                查看全部提交记录 →
              </router-link>
            </div>
          </section>
        </template>

        <!-- 右：代码 + 结果 -->
        <template #right>
          <section class="pane code">
            <div class="code__toolbar">
              <el-select :model-value="language" class="code__lang" @update:model-value="onLanguageChange">
                <el-option v-for="lang in problem.languages" :key="lang" :label="site.languageName(lang)" :value="lang" />
              </el-select>
              <el-button :icon="RefreshLeft" text @click="resetCode">重置</el-button>
              <span class="ctx__spacer" />
              <el-button v-if="!userStore.isLoggedIn" type="primary" @click="goLogin">登录后提交</el-button>
              <el-button v-else-if="submitDisabledText" type="primary" disabled>{{ submitDisabledText }}</el-button>
              <el-button v-else type="primary" :icon="VideoPlay" :loading="submitting" :disabled="!canSubmit" @click="submit">
                {{ submitLabel }}
                <kbd v-if="!isNarrow && cooldown === 0" class="code__kbd">Ctrl ↵</kbd>
              </el-button>
            </div>

            <div class="code__editor">
              <CodeEditor v-model="code" :language="site.languageMonaco(language)" height="100%" :bordered="false" @submit="trySubmit" />
            </div>

            <div class="result" :class="{ 'result--open': resultOpen && (submission || pollError) }">
              <button class="result__bar" type="button" @click="resultOpen = !resultOpen">
                <span class="result__title">评测结果</span>
                <template v-if="submission">
                  <VerdictBadge :result="submission.result" size="sm" />
                  <router-link
                    :to="{ name: 'submission-detail', params: { id: submission.id } }"
                    class="text-link"
                    @click.stop
                  >
                    提交 #{{ submission.id }}
                  </router-link>
                </template>
                <span v-else class="muted result__hint">提交代码后在这里查看结果</span>
                <span class="ctx__spacer" />
                <el-icon v-if="submission || pollError"><component :is="resultOpen ? ArrowDown : ArrowUp" /></el-icon>
              </button>
              <div v-if="resultOpen && (submission || pollError)" class="result__body">
                <el-alert v-if="pollError" type="error" :closable="false" :title="pollError" />
                <SubmissionResult v-else :submission="submission" />
              </div>
            </div>
          </section>
        </template>
      </SplitPane>
    </template>
  </div>
</template>

<style scoped>
.ws {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--oj-bg);
}

.ws__center {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
}

.ws__split {
  flex: 1;
  padding: 0 12px 12px;
}

/* 上下文条 */
.ctx {
  display: flex;
  flex-shrink: 0;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 16px;
  min-height: 44px;
  padding: 6px 16px;
  border-bottom: 1px solid var(--oj-border);
  background: var(--el-color-primary-light-9);
  font-size: var(--oj-fs-sm);
}

.ctx--exam {
  background: var(--oj-accent-bg);
  border-bottom-color: var(--oj-accent-border);
}

.ctx__back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--oj-link);
  font-weight: 600;
  text-decoration: none;
}

.ctx--exam .ctx__back {
  color: var(--oj-accent-text);
}

.ctx__spacer {
  flex: 1;
}

.ctx__item {
  color: var(--oj-text-2);
}

.ctx__warn {
  color: var(--oj-v-wa-fg);
  font-weight: 600;
}

.ctx__strip {
  display: flex;
  gap: 6px;
}

.chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--oj-border-strong);
  border-radius: var(--oj-radius-sm);
  background: var(--oj-surface);
  color: var(--oj-text-2);
  font-weight: 600;
  text-decoration: none;
}

.chip.is-tried {
  border-color: var(--oj-v-tle-bd);
  background: var(--oj-v-tle-bg);
  color: var(--oj-v-tle-fg);
}

.chip.is-ac {
  border-color: var(--oj-v-ac-bd);
  background: var(--oj-v-ac-bg);
  color: var(--oj-v-ac-fg);
}

.chip.is-current {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 1px;
}

/* 窄屏分段切换 */
.seg {
  display: flex;
  flex-shrink: 0;
  margin: 8px 12px;
  padding: 3px;
  border-radius: var(--oj-radius-sm);
  background: var(--oj-surface-hover);
}

.seg button {
  flex: 1;
  height: 32px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--oj-text-2);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.seg button.is-on {
  background: var(--oj-surface);
  box-shadow: var(--oj-shadow-sm);
  color: var(--oj-text);
}

/* 面板 */
.pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  margin-top: 12px;
  overflow: hidden;
  border: 1px solid var(--oj-border);
  border-radius: var(--oj-radius-md);
  background: var(--oj-surface);
}

.pane__scroll {
  flex: 1;
  min-height: 0;
  padding: 4px 24px 32px;
  overflow-y: auto;
}

.statement__tabs {
  flex-shrink: 0;
  padding: 0 24px;
}

.statement__tabs :deep(.el-tabs__header) {
  margin: 0;
}

.statement__title {
  margin: 16px 0 12px;
  font-size: 22px;
  letter-spacing: -0.01em;
}

.statement__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 20px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-sm);
}

.statement__meta b {
  color: var(--oj-text-2);
  font-weight: 600;
}

.statement__points {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.point {
  cursor: pointer;
}

.statement__alert {
  margin-top: 16px;
}

.statement h2 {
  margin: 24px 0 8px;
  font-size: var(--oj-fs-md);
}

.sample__pair {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.statement__source {
  margin-top: 24px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-sm);
}

.history__more {
  display: inline-block;
  margin-top: 12px;
  font-size: var(--oj-fs-sm);
}

/* 代码区 */
.code__toolbar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--oj-border);
}

.code__lang {
  width: 140px;
}

.code__kbd {
  margin-left: 6px;
  padding: 0 4px;
  border-color: rgba(255, 255, 255, 0.35);
  background: rgba(255, 255, 255, 0.15);
  color: inherit;
  font-size: 11px;
}

.code__editor {
  flex: 1;
  min-height: 160px;
}

/* 结果面板：收起时只留一条标题栏 */
.result {
  flex-shrink: 0;
  border-top: 1px solid var(--oj-border);
  background: var(--oj-surface);
}

.result__bar {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  height: 40px;
  padding: 0 16px;
  border: none;
  background: var(--oj-surface-2);
  color: var(--oj-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.result__title {
  font-weight: 600;
}

.result__hint {
  font-size: var(--oj-fs-sm);
}

.result__body {
  max-height: 42vh;
  padding: 12px 16px 16px;
  overflow-y: auto;
}

@media (max-width: 900px) {
  .ws__split {
    padding: 0 8px 8px;
  }

  .pane__scroll {
    padding: 4px 16px 24px;
  }

  .sample__pair {
    grid-template-columns: minmax(0, 1fr);
  }

  .result__body {
    max-height: 50vh;
  }
}
</style>
