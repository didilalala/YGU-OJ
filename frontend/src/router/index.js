import { createRouter, createWebHistory } from 'vue-router'

import { useExamStore } from '@/stores/exam'
import { useUserStore } from '@/stores/user'
import { ROLES, STAFF_ROLES } from '@/utils/constants'
import OjLayout from '@/components/layout/OjLayout.vue'

/**
 * meta 字段：
 *   title         浏览器标题，显示为「title - YGU OJ」
 *   requiresAuth  需要登录
 *   roles         允许访问的角色；子路由继承父路由的 meta
 */
const routes = [
  {
    path: '/',
    component: OjLayout,
    children: [
      { path: '', name: 'home', component: () => import('@/views/oj/HomeView.vue'), meta: { title: '首页' } },
      { path: 'login', name: 'login', component: () => import('@/views/oj/LoginView.vue'), meta: { title: '登录' } },
      {
        path: 'profile',
        name: 'profile',
        component: () => import('@/views/oj/ProfileView.vue'),
        meta: { title: '个人主页', requiresAuth: true },
      },
      {
        path: 'register',
        name: 'register',
        component: () => import('@/views/oj/RegisterView.vue'),
        meta: { title: '注册' },
      },
      {
        path: 'bind-student',
        name: 'bind-student',
        component: () => import('@/views/oj/BindStudentView.vue'),
        meta: { title: '绑定学号', requiresAuth: true },
      },
      {
        path: 'change-password',
        name: 'change-password',
        component: () => import('@/views/oj/ChangePasswordView.vue'),
        meta: { title: '修改密码', requiresAuth: true },
      },
      { path: '403', name: 'forbidden', component: () => import('@/views/oj/ForbiddenView.vue'), meta: { title: '无权访问' } },
      {
        path: 'problems',
        name: 'problems',
        component: () => import('@/views/oj/ProblemListView.vue'),
        meta: { title: '题目' },
      },
      {
        // 页面标题在加载题目后设为题目名
        path: 'problems/:id(\\d+)',
        name: 'problem-detail',
        component: () => import('@/views/oj/ProblemDetailView.vue'),
        meta: { title: '题目' },
      },
      {
        path: 'submissions',
        name: 'submissions',
        component: () => import('@/views/oj/SubmissionListView.vue'),
        meta: { title: '提交记录', requiresAuth: true },
      },
      {
        path: 'submissions/:id(\\d+)',
        name: 'submission-detail',
        component: () => import('@/views/oj/SubmissionDetailView.vue'),
        meta: { title: '提交详情', requiresAuth: true },
      },
      {
        path: 'classes',
        name: 'my-classes',
        component: () => import('@/views/oj/MyClassesView.vue'),
        meta: { title: '我的班级', requiresAuth: true },
      },
      {
        path: 'assignments',
        name: 'my-assignments',
        component: () => import('@/views/oj/MyAssignmentsView.vue'),
        meta: { title: '我的作业', requiresAuth: true },
      },
      {
        path: 'assignments/:id(\\d+)',
        name: 'assignment-detail',
        component: () => import('@/views/oj/AssignmentDetailView.vue'),
        meta: { title: '作业', requiresAuth: true },
      },
      {
        path: 'exams',
        name: 'my-exams',
        component: () => import('@/views/oj/MyExamsView.vue'),
        meta: { title: '我的考试', requiresAuth: true },
      },
      {
        // 页面标题在加载后设为考试名
        path: 'exams/:id(\\d+)',
        name: 'exam-detail',
        component: () => import('@/views/oj/ExamView.vue'),
        meta: { title: '考试', requiresAuth: true },
      },
      {
        path: 'scores',
        name: 'my-scores',
        component: () => import('@/views/oj/MyScoresView.vue'),
        meta: { title: '我的成绩', requiresAuth: true },
      },
      {
        path: 'contests',
        name: 'contests',
        component: () => import('@/views/oj/ContestListView.vue'),
        meta: { title: '竞赛' },
      },
      {
        // 公开竞赛：访客可浏览与看排名，登录后参加；页面复用考场
        path: 'contests/:id(\\d+)',
        name: 'contest-detail',
        component: () => import('@/views/oj/ExamView.vue'),
        meta: { title: '竞赛' },
      },
    ],
  },
  {
    path: '/admin',
    component: () => import('@/components/layout/AdminLayout.vue'),
    meta: { requiresAuth: true, roles: STAFF_ROLES },
    children: [
      {
        path: '',
        name: 'admin-dashboard',
        component: () => import('@/views/admin/DashboardView.vue'),
        meta: { title: '管理后台' },
      },
      {
        path: 'problems',
        name: 'admin-problems',
        component: () => import('@/views/admin/ProblemListView.vue'),
        meta: { title: '题库' },
      },
      {
        path: 'problems/new',
        name: 'admin-problem-create',
        component: () => import('@/views/admin/ProblemEditView.vue'),
        meta: { title: '新建题目' },
      },
      {
        // 页面标题在加载后设为「编辑：题目名」
        path: 'problems/:id(\\d+)/edit',
        name: 'admin-problem-edit',
        component: () => import('@/views/admin/ProblemEditView.vue'),
        meta: { title: '编辑题目' },
      },
      {
        path: 'classes',
        name: 'admin-classes',
        component: () => import('@/views/admin/ClassListView.vue'),
        meta: { title: '班级' },
      },
      {
        // 页面标题在加载后设为班级名
        path: 'classes/:id(\\d+)',
        name: 'admin-class-detail',
        component: () => import('@/views/admin/ClassDetailView.vue'),
        meta: { title: '班级' },
      },
      {
        path: 'assignments',
        name: 'admin-assignments',
        component: () => import('@/views/admin/AssignmentListView.vue'),
        meta: { title: '作业' },
      },
      {
        path: 'assignments/new',
        name: 'admin-assignment-create',
        component: () => import('@/views/admin/AssignmentEditView.vue'),
        meta: { title: '布置作业' },
      },
      {
        path: 'assignments/:id(\\d+)/edit',
        name: 'admin-assignment-edit',
        component: () => import('@/views/admin/AssignmentEditView.vue'),
        meta: { title: '编辑作业' },
      },
      {
        // 页面标题在加载后设为「作业名 成绩」
        path: 'assignments/:id(\\d+)',
        name: 'admin-assignment-results',
        component: () => import('@/views/admin/AssignmentResultView.vue'),
        meta: { title: '作业成绩' },
      },
      {
        path: 'exams',
        name: 'admin-exams',
        component: () => import('@/views/admin/ExamListView.vue'),
        meta: { title: '考试' },
      },
      {
        path: 'exams/new',
        name: 'admin-exam-create',
        component: () => import('@/views/admin/ExamEditView.vue'),
        meta: { title: '创建考试' },
      },
      {
        path: 'exams/:id(\\d+)/edit',
        name: 'admin-exam-edit',
        component: () => import('@/views/admin/ExamEditView.vue'),
        meta: { title: '编辑考试' },
      },
      {
        // 页面标题在加载后设为「考试名 监考」
        path: 'exams/:id(\\d+)',
        name: 'admin-exam-monitor',
        component: () => import('@/views/admin/ExamMonitorView.vue'),
        meta: { title: '监考' },
      },
      {
        path: 'stats',
        name: 'admin-stats',
        component: () => import('@/views/admin/ClassStatsView.vue'),
        meta: { title: '成绩统计' },
      },
      {
        path: 'stats/assignments/:id(\\d+)',
        name: 'admin-assignment-stats',
        component: () => import('@/views/admin/WorkStatsView.vue'),
        meta: { title: '作业统计', statsKind: 'assignment' },
      },
      {
        path: 'stats/exams/:id(\\d+)',
        name: 'admin-exam-stats',
        component: () => import('@/views/admin/WorkStatsView.vue'),
        meta: { title: '考试统计', statsKind: 'exam' },
      },
      {
        path: 'knowledge-points',
        name: 'admin-knowledge-points',
        component: () => import('@/views/admin/KnowledgePointView.vue'),
        meta: { title: '知识点' },
      },
      {
        path: 'judge-servers',
        name: 'admin-judge-servers',
        component: () => import('@/views/admin/JudgeServerView.vue'),
        meta: { title: '判题服务器', roles: [ROLES.ADMIN] },
      },
      {
        path: 'settings',
        name: 'admin-settings',
        component: () => import('@/views/admin/SiteSettingsView.vue'),
        meta: { title: '网站参数', roles: [ROLES.ADMIN] },
      },
      {
        path: 'languages',
        name: 'admin-languages',
        component: () => import('@/views/admin/LanguageListView.vue'),
        meta: { title: '支持语言', roles: [ROLES.ADMIN] },
      },
      // TODO: 系统配置
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/oj/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

// 考试期间不能访问的页面
const EXAM_LOCKED_ROUTES = ['problems', 'problem-detail', 'my-assignments', 'assignment-detail', 'my-scores']

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()

  if (userStore.isLoggedIn && !userStore.user) {
    try {
      await userStore.fetchMe()
    } catch {
      userStore.logout()
    }
  }

  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  // 在校学生首次登录必须先修改初始密码
  if (userStore.mustChangePassword && to.name !== 'change-password') {
    return { name: 'change-password' }
  }
  if (to.meta.roles && !to.meta.roles.includes(userStore.role)) {
    return { name: 'forbidden' }
  }
  // 考试期间学生只能访问考场与考试题目（后端同样会拒绝其他请求）
  if (userStore.role === ROLES.STUDENT && EXAM_LOCKED_ROUTES.includes(to.name)) {
    const exam = await useExamStore().refresh()
    const examProblem = to.name === 'problem-detail' && Number(to.query.exam) === exam?.id
    if (exam && !examProblem) return { name: 'exam-detail', params: { id: exam.id } }
  }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} - YGU OJ` : 'YGU OJ'
})

export default router
