<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheckFilled, CircleCloseFilled, Lock } from '@element-plus/icons-vue'

import { examApi } from '@/api/exam'
import MarkdownView from '@/components/MarkdownView.vue'
import RankTable from '@/components/RankTable.vue'
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
  const unsolved = exam.value.problems.filter((p) => !p.accepted).length
  try {
    await ElMessageBox.confirm(
      `${unsolved ? `还有 ${unsolved} 道题未通过。` : ''}交卷后不能再提交，确定交卷吗？`,
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

  <div v-else v-loading="loading" class="exam-page">
    <template v-if="exam">
      <el-card shadow="never">
        <div class="exam-header">
          <div class="exam-header__main">
            <h1 class="exam-header__title">
              {{ exam.title }}
              <el-tag :type="EXAM_STATUS[exam.status].type">{{ EXAM_STATUS[exam.status].label }}</el-tag>
            </h1>
            <div class="exam-header__meta">
              <span>{{ exam.is_public ? '公开竞赛' : exam.class_name }}</span>
              <span v-if="exam.is_public && exam.participant_count !== null">{{ exam.participant_count }} 人参加</span>
              <span>{{ RULE_LABELS[exam.rule_type] }} · {{ exam.problem_count }} 题 · 满分 {{ exam.total_score }}</span>
              <span>{{ formatDateTime(exam.start_time) }} 至 {{ formatDateTime(exam.end_time) }}</span>
            </div>
          </div>
          <div v-if="countdown" class="countdown">
            <div class="countdown__label">{{ exam.status === 'not_started' ? '距开考' : '剩余时间' }}</div>
            <div class="countdown__value">{{ countdown }}</div>
          </div>
        </div>
        <p class="rule-tip">{{ RULE_TIPS[exam.rule_type] }}</p>
        <MarkdownView v-if="exam.description" :content="exam.description" />
      </el-card>

      <!-- 未开始 -->
      <el-card v-if="exam.status === 'not_started'" shadow="never">
        <el-result
          icon="info"
          :title="`${noun}尚未开始`"
          :sub-title="
            exam.is_public
              ? '开始后在此页面报名参加。'
              : '开考后在此页面进入考试；考试期间只能访问考试题目，不能浏览题库和历史代码。'
          "
        />
      </el-card>

      <!-- 进行中，尚未进入 -->
      <el-card v-else-if="exam.status === 'in_progress' && !exam.joined" shadow="never" class="join">
        <h3>{{ exam.is_public ? '参加竞赛' : '进入考试' }}</h3>
        <template v-if="!userStore.isLoggedIn">
          <p class="muted">登录后即可参加，普通用户与在校学生都可以参加公开竞赛。</p>
          <el-button type="primary" size="large" @click="router.push({ name: 'login', query: { redirect: route.fullPath } })">
            登录后参加
          </el-button>
        </template>
        <template v-else>
        <p class="join__ip">
          当前 IP：{{ exam.ip }}
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
          <h3 class="rank-title">实时排名</h3>
          <RankTable v-if="rank" :rank="rank.rank" :problems="rank.problems" :rule-type="rank.rule_type" is-public />
        </template>
      </el-card>

      <!-- 已进入或已结束 -->
      <el-card v-else shadow="never">
        <el-alert
          v-if="exam.finished && exam.status === 'in_progress'"
          type="success"
          :closable="false"
          show-icon
          :title="`你已交卷，${noun}结束并公布成绩后可查看成绩。如误交卷请联系${exam.is_public ? '出题老师' : '监考老师'}。`"
          class="block"
        />
        <el-alert
          v-if="exam.status === 'ended' && !exam.is_score_published"
          type="info"
          :closable="false"
          show-icon
          :title="`${noun}已结束，成绩尚未公布。`"
        />
        <div v-if="exam.status === 'ended' && exam.is_score_published" class="score">
          <div class="score__value">{{ formatScore(exam.my_score) }}</div>
          <div class="score__label">我的成绩 / {{ exam.total_score }}</div>
        </div>

        <el-tabs v-if="exam.problems.length" v-model="tab">
          <el-tab-pane label="题目" name="problems">
            <el-table :data="exam.problems" class="problems" @row-click="openProblem">
              <el-table-column label="题号" width="64" align="center">
                <template #default="{ $index }"><strong>{{ letter($index) }}</strong></template>
              </el-table-column>
              <el-table-column label="题目" min-width="200">
                <template #default="{ row }">
                  <router-link
                    :to="{ name: 'problem-detail', params: { id: row.problem_id }, query: { exam: exam.id } }"
                    class="link"
                    @click.stop
                  >
                    {{ row.title }}
                  </router-link>
                </template>
              </el-table-column>
              <el-table-column prop="score" label="分值" width="70" align="center" />
              <el-table-column label="状态" width="110" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.accepted" type="success" size="small">已通过</el-tag>
                  <el-tag v-else-if="row.attempted" type="warning" size="small" effect="plain">已提交</el-tag>
                  <span v-else class="muted">未提交</span>
                </template>
              </el-table-column>
              <el-table-column v-if="exam.is_score_published" label="得分" width="80" align="center">
                <template #default="{ row }">{{ formatScore(row.my_score) }}</template>
              </el-table-column>
            </el-table>
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
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 200px;
}

.exam-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
}

.exam-header__main {
  flex: 1;
  min-width: 240px;
}

.exam-header__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin: 0 0 8px;
  font-size: 22px;
}

.exam-header__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.countdown {
  padding: 10px 20px;
  border-radius: 6px;
  background: var(--oj-brand-navy);
  color: #fff;
  text-align: center;
}

.countdown__label {
  font-size: 12px;
  opacity: 0.8;
}

.countdown__value {
  font-family: Consolas, Menlo, monospace;
  font-size: 28px;
  font-weight: 600;
  letter-spacing: 1px;
}

.rule-tip {
  margin: 12px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.join h3 {
  margin-top: 0;
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

.block {
  margin-bottom: 12px;
}

.score {
  display: inline-block;
  margin: 8px 0 12px;
  padding: 10px 20px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
}

.score__value {
  color: var(--oj-brand-navy);
  font-size: 28px;
  font-weight: 600;
}

.score__label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.problems :deep(.el-table__row) {
  cursor: pointer;
}

.link {
  color: var(--el-color-primary);
  text-decoration: none;
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.rank-title {
  margin: 24px 0 12px;
}

.finish {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}
</style>
