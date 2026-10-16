<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Document, EditPen, Trophy } from '@element-plus/icons-vue'

import { assignmentApi } from '@/api/assignment'
import { authApi } from '@/api/auth'
import { problemApi } from '@/api/problem'
import Countdown from '@/components/ui/Countdown.vue'
import DifficultyBadge from '@/components/ui/DifficultyBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ProgressRing from '@/components/ui/ProgressRing.vue'
import RateBar from '@/components/ui/RateBar.vue'
import StatCard from '@/components/ui/StatCard.vue'
import VerdictBadge from '@/components/ui/VerdictBadge.vue'
import { useExamStore } from '@/stores/exam'
import { useSiteStore } from '@/stores/site'
import { useUserStore } from '@/stores/user'
import { ROLES } from '@/utils/constants'
import { passRateValue, timeAgo } from '@/utils/judge'
import { timeLeft } from '@/utils/assignment'

const router = useRouter()
const userStore = useUserStore()
const examStore = useExamStore()
const site = useSiteStore()

const announcement = computed(() => site.settings.home_announcement?.trim() ?? '')
const isStudent = computed(() => userStore.role === ROLES.STUDENT)
const name = computed(() => userStore.user?.real_name || userStore.user?.username || '')

const stats = ref(null)
const todo = ref([])
const problems = ref([])
const loading = ref(true)

// 一天中的问候语
const greeting = computed(() => {
  const h = new Date().getHours()
  return h < 6 ? '夜深了' : h < 12 ? '上午好' : h < 18 ? '下午好' : '晚上好'
})

onMounted(async () => {
  const tasks = [
    problemApi.list({ page_size: 6 }).then((d) => (problems.value = d.results), () => {}),
  ]
  if (userStore.isLoggedIn) {
    tasks.push(authApi.profile({ silent: true }).then((d) => (stats.value = d.stats), () => {}))
    // 考试期间作业接口被锁定，不请求
    if (isStudent.value) await examStore.refresh()
    if (isStudent.value && !examStore.active) {
      tasks.push(assignmentApi.mine({ status: 'todo' }).then((d) => (todo.value = d.slice(0, 4)), () => {}))
    }
  }
  await Promise.all(tasks)
  loading.value = false
})

function deadline(item) {
  const left = timeLeft(item.end_time)
  return left ? `还剩 ${left}` : '已截止，可迟交'
}

const features = [
  { icon: EditPen, title: '在线编程，即时评测', text: '浏览器里写代码，提交后几秒内给出每个测试点的结果。' },
  { icon: Document, title: '作业与考试一体', text: '老师布置的作业、课堂考试和成绩统计，都在同一个平台。' },
  { icon: Trophy, title: '公开竞赛', text: '参加 ACM / OI 赛制的竞赛，实时排名，检验自己的水平。' },
]
</script>

<template>
  <!-- 已登录：个人工作台 -->
  <div v-if="userStore.user" class="home">
    <header class="greet">
      <div>
        <h1>{{ greeting }}，{{ name }}</h1>
        <p class="muted">继续今天的练习吧。</p>
      </div>
      <div class="greet__actions">
        <el-button v-if="userStore.isStaff" @click="router.push({ name: 'admin-dashboard' })">进入管理后台</el-button>
        <el-button type="primary" @click="router.push({ name: 'problems' })">去刷题 <el-icon class="el-icon--right"><ArrowRight /></el-icon></el-button>
      </div>
    </header>

    <router-link
      v-if="examStore.active"
      :to="{ name: 'exam-detail', params: { id: examStore.active.id } }"
      class="exam-card"
    >
      <span class="exam-card__dot" />
      <div class="exam-card__main">
        <strong>考试进行中：{{ examStore.active.title }}</strong>
        <span>剩余 <Countdown :end="examStore.active.end_time" /></span>
      </div>
      <el-button type="primary" color="var(--oj-brand-orange-deep)">进入考场</el-button>
    </router-link>

    <div class="stats">
      <StatCard accent label="已通过题目" :value="stats?.solved_problems ?? '—'" :unit="stats ? `/ ${stats.visible_problems}` : ''" :loading="loading" :hint="stats ? `尝试过 ${stats.attempted_problems} 题` : ''" />
      <StatCard label="提交次数" :value="stats?.submitted ?? '—'" :loading="loading" hint="已完成评测的提交" />
      <StatCard label="通过率" :value="stats?.accept_rate ?? '—'" unit="%" :loading="loading" :hint="stats ? `通过 ${stats.accepted} 次` : ''" />
    </div>

    <div class="cols">
      <section class="col-main">
        <el-card v-if="isStudent && !examStore.active" shadow="never" class="panel">
          <template #header>
            <div class="panel__head">
              <span>待完成的作业</span>
              <router-link :to="{ name: 'my-assignments' }" class="text-link">全部作业</router-link>
            </div>
          </template>
          <EmptyState v-if="!loading && !todo.length" compact title="没有待完成的作业" description="去题库练练手吧。" />
          <ul v-else class="todo">
            <li v-for="item in todo" :key="item.id">
              <router-link :to="{ name: 'assignment-detail', params: { id: item.id } }" class="todo__item">
                <ProgressRing :done="item.my_solved" :total="item.problem_count" :size="44" />
                <div class="todo__main">
                  <div class="todo__title">{{ item.title }}</div>
                  <div class="muted todo__meta">{{ item.class_name }} · {{ deadline(item) }}</div>
                </div>
                <el-icon class="todo__arrow"><ArrowRight /></el-icon>
              </router-link>
            </li>
          </ul>
        </el-card>

        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel__head">
              <span>最近提交</span>
              <router-link :to="{ name: 'submissions' }" class="text-link">全部提交</router-link>
            </div>
          </template>
          <EmptyState v-if="!loading && !(stats?.recent?.length)" compact title="还没有提交" description="选一道题，提交你的第一份代码。" />
          <ul v-else class="recent">
            <li v-for="s in stats?.recent ?? []" :key="s.id">
              <router-link :to="{ name: 'submission-detail', params: { id: s.id } }" class="recent__item">
                <VerdictBadge :result="s.result" size="sm" />
                <span class="recent__title">{{ s.problem_title }}</span>
                <span class="muted">{{ timeAgo(s.created_at) }}</span>
              </router-link>
            </li>
          </ul>
        </el-card>
      </section>

      <aside class="col-side">
        <el-card shadow="never" class="panel">
          <template #header>公告</template>
          <p v-if="announcement" class="announcement">{{ announcement }}</p>
          <EmptyState v-else compact title="暂无公告" />
        </el-card>
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel__head">
              <span>推荐题目</span>
              <router-link :to="{ name: 'problems' }" class="text-link">更多</router-link>
            </div>
          </template>
          <ul class="picks">
            <li v-for="p in problems" :key="p.id">
              <router-link :to="{ name: 'problem-detail', params: { id: p.id } }" class="picks__item">
                <span class="muted num">{{ p.id }}</span>
                <span class="picks__title">{{ p.title }}</span>
                <DifficultyBadge :difficulty="p.difficulty" />
              </router-link>
            </li>
          </ul>
        </el-card>
      </aside>
    </div>
  </div>

  <!-- 未登录：品牌首页 -->
  <div v-else class="landing">
    <section class="hero">
      <div class="hero__text">
        <span class="hero__badge">YGU Online Judge</span>
        <h1>{{ site.settings.site_name }}</h1>
        <p>
          支持 {{ site.languages.map((lang) => lang.name).join('、') || 'C / C++ / Java / Python' }}
          在线提交与自动评测。作业、考试、竞赛，一个平台搞定。
        </p>
        <div class="hero__actions">
          <el-button type="primary" size="large" @click="router.push({ name: 'login' })">登录</el-button>
          <el-button v-if="site.settings.allow_registration" size="large" @click="router.push({ name: 'register' })">注册账号</el-button>
          <el-button size="large" text @click="router.push({ name: 'problems' })">先看看题库 →</el-button>
        </div>
      </div>
      <pre class="hero__code" aria-hidden="true"><span class="c">// 提交后几秒内得到结果</span>
<span class="k">#include</span> &lt;stdio.h&gt;

<span class="k">int</span> main(<span class="k">void</span>) {
    <span class="k">int</span> a, b;
    scanf(<span class="s">"%d %d"</span>, &amp;a, &amp;b);
    printf(<span class="s">"%d\n"</span>, a + b);
    <span class="k">return</span> <span class="n">0</span>;
}</pre>
    </section>

    <section class="features">
      <article v-for="f in features" :key="f.title" class="feature">
        <div class="feature__icon"><el-icon :size="20"><component :is="f.icon" /></el-icon></div>
        <h3>{{ f.title }}</h3>
        <p>{{ f.text }}</p>
      </article>
    </section>

    <div class="cols">
      <el-card shadow="never" class="panel col-main">
        <template #header>
          <div class="panel__head">
            <span>推荐题目</span>
            <router-link :to="{ name: 'problems' }" class="text-link">进入题库</router-link>
          </div>
        </template>
        <ul class="picks">
          <li v-for="p in problems" :key="p.id">
            <router-link :to="{ name: 'problem-detail', params: { id: p.id } }" class="picks__item">
              <span class="muted num">{{ p.id }}</span>
              <span class="picks__title">{{ p.title }}</span>
              <RateBar :value="passRateValue(p)" width="48px" />
              <DifficultyBadge :difficulty="p.difficulty" />
            </router-link>
          </li>
        </ul>
      </el-card>
      <el-card shadow="never" class="panel col-side">
        <template #header>公告</template>
        <p v-if="announcement" class="announcement">{{ announcement }}</p>
        <EmptyState v-else compact title="暂无公告" />
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.greet {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: var(--oj-space-5);
}

.greet h1 {
  margin: 0;
  font-size: var(--oj-fs-xl);
  letter-spacing: -0.01em;
}

.greet p {
  margin: 4px 0 0;
}

.greet__actions {
  display: flex;
  gap: 8px;
}

.exam-card {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: var(--oj-space-4);
  padding: 16px 20px;
  border: 1px solid var(--oj-accent-border);
  border-radius: var(--oj-radius-md);
  background: var(--oj-accent-bg);
  color: var(--oj-accent-text);
  text-decoration: none;
}

.exam-card__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--oj-brand-orange);
  animation: pulse 1.6s infinite;
}

@keyframes pulse {
  50% {
    opacity: 0.3;
  }
}

.exam-card__main {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--oj-space-4);
  margin-bottom: var(--oj-space-4);
}

.cols {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: var(--oj-space-4);
  align-items: start;
}

.col-main,
.col-side {
  display: flex;
  flex-direction: column;
  gap: var(--oj-space-4);
}

.panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel__head .text-link {
  font-size: var(--oj-fs-sm);
  font-weight: 400;
}

ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.todo__item,
.recent__item,
.picks__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 8px;
  border-radius: var(--oj-radius-sm);
  color: inherit;
  text-decoration: none;
}

.todo__item:hover,
.recent__item:hover,
.picks__item:hover {
  background: var(--oj-surface-hover);
}

.todo__main {
  flex: 1;
  min-width: 0;
}

.todo__title {
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.todo__meta {
  font-size: var(--oj-fs-sm);
}

.todo__arrow {
  color: var(--oj-text-3);
}

.recent__title,
.picks__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.announcement {
  margin: 0;
  line-height: 1.7;
  white-space: pre-wrap;
}

/* 未登录首页 */
.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: var(--oj-space-6);
  align-items: center;
  margin-bottom: var(--oj-space-5);
  padding: 56px 48px;
  overflow: hidden;
  border-radius: var(--oj-radius-md);
  background:
    radial-gradient(circle at 90% 0%, rgba(236, 106, 12, 0.25), transparent 40%),
    linear-gradient(150deg, var(--oj-navy-700), var(--oj-navy-900));
  color: #fff;
}

.hero__badge {
  display: inline-block;
  margin-bottom: 16px;
  padding: 2px 12px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: var(--oj-radius-pill);
  font-size: var(--oj-fs-sm);
}

.hero h1 {
  margin: 0 0 12px;
  color: #fff;
  font-size: 36px;
  letter-spacing: -0.02em;
}

.hero p {
  max-width: 480px;
  margin: 0 0 28px;
  color: rgba(255, 255, 255, 0.8);
  font-size: var(--oj-fs-md);
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero__actions .el-button--primary {
  --el-button-bg-color: var(--oj-brand-orange-deep);
  --el-button-border-color: var(--oj-brand-orange-deep);
  --el-button-hover-bg-color: var(--oj-brand-orange);
  --el-button-hover-border-color: var(--oj-brand-orange);
}

.hero__actions .el-button:not(.el-button--primary) {
  --el-button-bg-color: rgba(255, 255, 255, 0.1);
  --el-button-text-color: #fff;
  --el-button-border-color: rgba(255, 255, 255, 0.3);
  --el-button-hover-bg-color: rgba(255, 255, 255, 0.2);
  --el-button-hover-text-color: #fff;
  --el-button-hover-border-color: rgba(255, 255, 255, 0.5);
}

.hero__actions .el-button.is-text {
  --el-button-bg-color: transparent;
  --el-button-border-color: transparent;
}

.hero__code {
  margin: 0;
  padding: 20px 24px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: var(--oj-radius-md);
  background: rgba(0, 0, 0, 0.28);
  color: #d5d9ee;
  font-size: 13px;
  line-height: 1.7;
}

.hero__code .k {
  color: #f2a468;
}

.hero__code .s {
  color: #8fd6a9;
}

.hero__code .n {
  color: #9db4ff;
}

.hero__code .c {
  color: #8a91b3;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--oj-space-4);
  margin-bottom: var(--oj-space-5);
}

.feature {
  padding: 20px;
  border: 1px solid var(--oj-border);
  border-radius: var(--oj-radius-md);
  background: var(--oj-surface);
}

.feature__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--oj-radius-sm);
  background: var(--oj-accent-bg);
  color: var(--oj-brand-orange-deep);
}

.feature h3 {
  margin: 12px 0 4px;
  font-size: var(--oj-fs-md);
}

.feature p {
  margin: 0;
  color: var(--oj-text-3);
}

@media (max-width: 900px) {
  .cols,
  .hero {
    grid-template-columns: minmax(0, 1fr);
  }

  .hero {
    padding: 32px 24px;
  }

  .hero h1 {
    font-size: 28px;
  }

  .hero__code {
    display: none;
  }
}
</style>
