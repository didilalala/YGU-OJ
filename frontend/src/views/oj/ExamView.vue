<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheckFilled, CircleCloseFilled, Lock } from '@element-plus/icons-vue'

import { examApi } from '@/api/exam'
import MarkdownView from '@/components/MarkdownView.vue'
import RankTable from '@/components/RankTable.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import StatCard from '@/components/ui/StatCard.vue'
import { useExamStore } from '@/stores/exam'
import { useUserStore } from '@/stores/user'
import { formatScore } from '@/utils/assignment'
import { EXAM_STATUS, RULE_LABELS, RULE_TIPS, formatDuration, serverOffset } from '@/utils/exam'
import { formatDateTime } from '@/utils/judge'

// 考场信息定时刷新（进入人数、交卷状态等），倒计时每秒更新
const REFRESH_INTERVAL = 30 * 1000

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const examStore = useExamStore()

const loading = ref(true)
const loadError = ref('')
const exam = ref(null)
const offset = ref(0)
const now = ref(Date.now())
const password = ref('')
const joining = ref(false)
const tab = ref('problems')
const rank = ref(null)
let clock = null
let poll = null

const serverNow = computed(() => now.value + offset.value)
const countdown = computed(() => {
  if (!exam.value) return ''
  if (exam.value.status === 'not_started') return formatDuration((new Date(exam.value.start_time) - serverNow.value) / 1000)
  if (exam.value.status === 'in_progress') return formatDuration((new Date(exam.value.end_time) - serverNow.value) / 1000)
  return ''
})
const secondsLeft = computed(() =>
  exam.value?.status === 'in_progress' ? (new Date(exam.value.end_time) - serverNow.value) / 1000 : Infinity,
)
const canFinish = computed(() => exam.value?.status === 'in_progress' && exam.value.joined && !exam.value.finished)
// 公开竞赛称「竞赛」，课堂考试称「考试」
const noun = computed(() => (exam.value?.is_public ? '竞赛' : '考试'))
// 课堂考试的排名只给已进入的学生看；公开竞赛的排名所有人都能看（学号打码）
const rankVisible = computed(
  () =>
    exam.value &&
    ((exam.value.status === 'in_progress' && exam.value.show_rank && (exam.value.joined || exam.value.is_public)) ||
      (exam.value.status === 'ended' && exam.value.is_score_published)),
)
// 未进入公开竞赛时，排名显示在报名区下方
const showStandaloneRank = computed(() => exam.value?.is_public && !exam.value.joined && rankVisible.value)

async function load({ silent = false } = {}) {
  if (!silent) loading.value = true
  try {
    const data = await examApi.detail(route.params.id, { silent: true })
    offset.value = serverOffset(data.server_time)
    exam.value = data
    document.title = `${data.title} - YGU OJ`
    if (rankVisible.value && (tab.value === 'rank' || showStandaloneRank.value)) loadRank()
  } catch (err) {
    if (!silent) loadError.value = err?.code === 404 ? '考试或竞赛不存在，或你没有权限参加' : err?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadRank() {
  try {
    rank.value = await examApi.rank(exam.value.id, { silent: true })
  } catch {
    rank.value = null
  }
}

watch(
  () => route.params.id,
  (id) => {
    if (!id) return
    exam.value = null
    rank.value = null
    tab.value = 'problems'
    load()
  },
  { immediate: true },
)
watch(tab, (value) => value === 'rank' && loadRank())

clock = setInterval(() => {
  now.value = Date.now()
  // 到开考或结束时间时刷新状态
  const item = exam.value
  if (!item) return
  const boundary = item.status === 'not_started' ? item.start_time : item.status === 'in_progress' ? item.end_time : null
  if (boundary && new Date(boundary) <= serverNow.value) {
    load({ silent: true })
    examStore.refresh({ force: true })
  }
}, 1000)
poll = setInterval(() => load({ silent: true }), REFRESH_INTERVAL)
onBeforeUnmount(() => {
  clearInterval(clock)
  clearInterval(poll)
})

async function join() {
  joining.value = true
  try {
    await examApi.join(exam.value.id, password.value)
    ElMessage.success(`已进入${noun.value}，祝你顺利`)
    await load({ silent: true })
    examStore.refresh({ force: true })
  } catch {
    // 口令错误、IP 不在范围内等提示已由请求拦截器弹出
  } finally {
    joining.value = false
  }
}

async function finish() {
  // 列出还没通过的题号，交卷前再看一眼
  const unsolved = exam.value.problems.map((p, i) => (p.accepted ? '' : letter(i))).filter(Boolean)
  try {
    await ElMessageBox.confirm(
      `${unsolved.length ? `还有 ${unsolved.length} 道题未通过：${unsolved.join('、')}。` : ''}交卷后不能再提交，确定交卷吗？`,
      '交卷',
      { type: 'warning', confirmButtonText: '交卷', cancelButtonText: '继续作答' },
    )
  } catch {
    return
  }
  try {
    await examApi.finish(exam.value.id)
    ElMessage.success('已交卷')
    load({ silent: true })
  } catch {
    // 错误提示已由请求拦截器弹出
  }
}

function openProblem(row) {
  router.push({ name: 'problem-detail', params: { id: row.problem_id }, query: { exam: exam.value.id } })
}

// 公开竞赛使用 /contests/:id 地址（访客也能打开）
watch(exam, (value) => {
  if (value?.is_public && route.name === 'exam-detail') router.replace({ name: 'contest-detail', params: { id: value.id } })
})

const letter = (index) => String.fromCharCode(65 + index)
</script>

<template>
  <el-result v-if="loadError" icon="warning" :title="loadError">
    <template #extra>
      <el-button type="primary" @click="router.push({ name: route.name === 'contest-detail' ? 'contests' : 'my-exams' })">
        {{ route.name === 'contest-detail' ? '返回竞赛列表' : '返回我的考试' }}
      </el-button>
    </template>
  </el-result>

  <div v-else class="exam-page">
    <el-skeleton v-if="loading && !exam" animated :rows="8" />
    <template v-if="exam">
      <section class="hero" :class="`hero--${exam.status}`">
        <div class="hero__main">
          <div class="hero__tags">
            <el-tag :type="EXAM_STATUS[exam.status].type" effect="dark" size="small">{{ EXAM_STATUS[exam.status].label }}</el-tag>
            <span>{{ exam.is_public ? '公开竞赛' : exam.class_name }}</span>
          </div>
          <h1 class="hero__title">{{ exam.title }}</h1>
          <div class="hero__meta">
            <span>{{ RULE_LABELS[exam.rule_type] }} · {{ exam.problem_count }} 题 · 满分 {{ exam.total_score }}</span>
            <span v-if="exam.is_public && exam.participant_count !== null">{{ exam.participant_count }} 人参加</span>
            <span>{{ formatDateTime(exam.start_time) }} 至 {{ formatDateTime(exam.end_time) }}</span>
          </div>
        </div>
        <div v-if="countdown" class="clock" :class="{ 'clock--danger': exam.status === 'in_progress' && secondsLeft <= 600 }">
          <div class="clock__label">{{ exam.status === 'not_started' ? '距开考' : '剩余时间' }}</div>
          <div class="clock__value">{{ countdown }}</div>
        </div>
      </section>

      <el-card shadow="never" class="block">
        <p class="rule-tip">{{ RULE_TIPS[exam.rule_type] }}</p>
        <MarkdownView v-if="exam.description" :content="exam.description" />
      </el-card>

      <!-- 未开始 -->
      <el-card v-if="exam.status === 'not_started'" shadow="never" class="block">
        <EmptyState
          :title="`${noun}尚未开始`"
          :description="
            exam.is_public
              ? '开始后在此页面报名参加。'
              : '开考后在此页面进入考试；考试期间只能访问考试题目，不能浏览题库和历史代码。'
          "
        />
      </el-card>

      <!-- 进行中，尚未进入 -->
      <el-card v-else-if="exam.status === 'in_progress' && !exam.joined" shadow="never" class="block join">
        <h2>{{ exam.is_public ? '参加竞赛' : '进入考试' }}</h2>
        <template v-if="!userStore.isLoggedIn">
          <p class="muted">登录后即可参加，普通用户与在校学生都可以参加公开竞赛。</p>
          <el-button type="primary" size="large" @click="router.push({ name: 'login', query: { redirect: route.fullPath } })">
            登录后参加
          </el-button>
        </template>
        <template v-else>
          <p class="join__ip">
            当前 IP：<code>{{ exam.ip }}</code>
            <el-tag v-if="exam.ip_allowed" type="success" size="small" effect="plain">
              <el-icon><CircleCheckFilled /></el-icon> 在允许范围内
            </el-tag>
            <el-tag v-else type="danger" size="small">
              <el-icon><CircleCloseFilled /></el-icon> 不在允许范围内，请在指定机房参加考试
            </el-tag>
          </p>
          <el-form class="join__form" @submit.prevent="join">
            <el-form-item v-if="exam.need_password">
              <el-input
                v-model="password"
                type="password"
                show-password
                size="large"
                :placeholder="exam.is_public ? '请输入竞赛口令' : '请输入监考老师公布的考试口令'"
                :prefix-icon="Lock"
              />
            </el-form-item>
            <el-button type="primary" size="large" :loading="joining" :disabled="!exam.ip_allowed" native-type="submit">
              {{ exam.is_public ? '参加竞赛' : '进入考试' }}
            </el-button>
          </el-form>
        </template>

        <template v-if="showStandaloneRank">
          <h2 class="rank-title">实时排名</h2>
          <RankTable v-if="rank" :rank="rank.rank" :problems="rank.problems" :rule-type="rank.rule_type" is-public />
        </template>
      </el-card>

      <!-- 已进入或已结束 -->
      <el-card v-else shadow="never" class="block">
        <el-alert
          v-if="exam.finished && exam.status === 'in_progress'"
          type="success"
          :closable="false"
          show-icon
          :title="`你已交卷，${noun}结束并公布成绩后可查看成绩。如误交卷请联系${exam.is_public ? '出题老师' : '监考老师'}。`"
          class="alert"
        />
        <el-alert
          v-if="exam.status === 'ended' && !exam.is_score_published"
          type="info"
          :closable="false"
          show-icon
          :title="`${noun}已结束，成绩尚未公布。`"
          class="alert"
        />
        <div v-if="exam.status === 'ended' && exam.is_score_published" class="score">
          <StatCard accent label="我的成绩" :value="formatScore(exam.my_score)" :unit="`/ ${exam.total_score}`" />
        </div>

        <el-tabs v-if="exam.problems.length" v-model="tab">
          <el-tab-pane label="题目" name="problems">
            <ul class="problems">
              <li v-for="(row, index) in exam.problems" :key="row.problem_id">
                <router-link
                  :to="{ name: 'problem-detail', params: { id: row.problem_id }, query: { exam: exam.id } }"
                  class="problem"
                  :class="{ 'is-ac': row.accepted, 'is-tried': !row.accepted && row.attempted }"
                >
                  <span class="problem__letter">{{ letter(index) }}</span>
                  <span class="problem__title">{{ row.title }}</span>
                  <span class="problem__score num">{{ row.score }} 分</span>
                  <span class="problem__state">
                    <el-tag v-if="row.accepted" type="success" size="small">已通过</el-tag>
                    <el-tag v-else-if="row.attempted" type="warning" size="small" effect="plain">已提交</el-tag>
                    <span v-else class="muted">未提交</span>
                  </span>
                  <span v-if="exam.is_score_published" class="problem__got num">{{ formatScore(row.my_score) }}</span>
                </router-link>
              </li>
            </ul>
          </el-tab-pane>
          <el-tab-pane v-if="rankVisible" label="排名" name="rank">
            <RankTable
              v-if="rank"
              :rank="rank.rank"
              :problems="rank.problems"
              :rule-type="rank.rule_type"
              :is-public="rank.is_public"
              :highlight-user-id="userStore.user?.id"
            />
          </el-tab-pane>
        </el-tabs>

        <div v-if="canFinish" class="finish">
          <el-button type="danger" plain @click="finish">交卷</el-button>
          <span class="muted">{{ noun }}结束时自动收卷，提前交卷后不能再提交</span>
        </div>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.exam-page {
  min-height: 200px;
}

.hero {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 20px;
  margin-bottom: var(--oj-space-4);
  padding: 28px 32px;
  border-radius: var(--oj-radius-md);
  background: linear-gradient(150deg, var(--oj-navy-700), var(--oj-navy-900));
  color: #fff;
}

.hero--in_progress {
  background:
    radial-gradient(circle at 100% 0%, rgba(236, 106, 12, 0.3), transparent 45%),
    linear-gradient(150deg, var(--oj-navy-700), var(--oj-navy-900));
}

.hero__main {
  flex: 1;
  min-width: 240px;
}

.hero__tags {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.75);
  font-size: var(--oj-fs-sm);
}

.hero__title {
  margin: 8px 0;
  color: #fff;
  font-size: 26px;
  letter-spacing: -0.01em;
}

.hero__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 20px;
  color: rgba(255, 255, 255, 0.75);
  font-size: var(--oj-fs-sm);
}

.clock {
  padding: 12px 24px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: var(--oj-radius-md);
  background: rgba(255, 255, 255, 0.08);
  text-align: center;
}

.clock--danger {
  border-color: var(--oj-v-wa-fg);
  background: rgba(201, 48, 44, 0.3);
  animation: blink 1.2s infinite;
}

@keyframes blink {
  50% {
    background: rgba(201, 48, 44, 0.12);
  }
}

.clock__label {
  font-size: var(--oj-fs-xs);
  opacity: 0.8;
}

.clock__value {
  font-family: var(--oj-font-mono);
  font-size: 32px;
  font-weight: 600;
  letter-spacing: 1px;
}

.block {
  margin-bottom: var(--oj-space-4);
}

.rule-tip {
  margin: 0 0 12px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-sm);
}

.join h2 {
  margin: 0 0 12px;
  font-size: var(--oj-fs-lg);
}

.join__ip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.join__form {
  max-width: 360px;
}

.rank-title {
  margin: 32px 0 12px;
}

.alert {
  margin-bottom: 12px;
}

.score {
  max-width: 260px;
  margin-bottom: 16px;
}

.problems {
  margin: 0;
  padding: 0;
  list-style: none;
}

.problem {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 8px;
  border-bottom: 1px solid var(--oj-border);
  color: inherit;
  text-decoration: none;
}

.problem:hover {
  background: var(--oj-surface-hover);
}

.problem__letter {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--oj-border-strong);
  border-radius: var(--oj-radius-sm);
  font-weight: 700;
}

.is-ac .problem__letter {
  border-color: var(--oj-v-ac-bd);
  background: var(--oj-v-ac-bg);
  color: var(--oj-v-ac-fg);
}

.is-tried .problem__letter {
  border-color: var(--oj-v-tle-bd);
  background: var(--oj-v-tle-bg);
  color: var(--oj-v-tle-fg);
}

.problem__title {
  flex: 1;
  min-width: 0;
  font-weight: 500;
}

.problem__score {
  color: var(--oj-text-3);
}

.problem__state {
  min-width: 64px;
  text-align: center;
}

.problem__got {
  min-width: 40px;
  font-weight: 600;
  text-align: right;
}

.finish {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}
</style>
