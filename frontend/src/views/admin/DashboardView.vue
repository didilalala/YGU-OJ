<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { EditPen, Notebook, Plus } from '@element-plus/icons-vue'

import { statsApi } from '@/api/stats'
import EChart from '@/components/EChart.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import RateBar from '@/components/ui/RateBar.vue'
import StatCard from '@/components/ui/StatCard.vue'
import { useUserStore } from '@/stores/user'
import { INK, barSeries, baseOption, categoryAxis, lineSeries, valueAxis } from '@/utils/chart'
import { formatDateTime } from '@/utils/judge'
import { timeLeft } from '@/utils/assignment'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(true)
const data = ref(null)

onMounted(async () => {
  try {
    data.value = await statsApi.overview()
  } finally {
    loading.value = false
  }
})

const name = computed(() => userStore.user?.real_name || userStore.user?.username)
const summary = computed(() => data.value?.summary)

// 提交趋势：柱为提交数，线为通过数
const trendOption = computed(() => {
  const days = data.value?.trend ?? []
  return {
    ...baseOption(),
    legend: { top: 0, right: 0, itemWidth: 14, itemHeight: 8, textStyle: { color: INK.secondary } },
    grid: { ...baseOption().grid, top: 36 },
    tooltip: { ...baseOption().tooltip, trigger: 'axis' },
    xAxis: categoryAxis(days.map((d) => d.date.slice(5)), { axisLabel: { color: INK.muted, fontSize: 11, interval: 1 } }),
    yAxis: valueAxis({ minInterval: 1 }),
    series: [
      barSeries({ name: '提交', data: days.map((d) => d.count), itemStyle: { color: INK.series, borderRadius: [4, 4, 0, 0] } }),
      lineSeries('#1baf7a', { name: '通过', data: days.map((d) => d.accepted) }),
    ],
  }
})

function deadline(item) {
  const left = timeLeft(item.end_time)
  return left ? `还剩 ${left}` : '已截止'
}

const actions = [
  { icon: Plus, text: '新建题目', to: { name: 'admin-problem-create' } },
  { icon: Notebook, text: '布置作业', to: { name: 'admin-assignment-create' } },
  { icon: EditPen, text: '创建考试', to: { name: 'admin-exam-create' } },
]
</script>

<template>
  <div>
    <PageHeader :title="`你好，${name}`" subtitle="这是你的教学概况" />

    <div class="stats">
      <StatCard accent label="我的班级" :value="summary?.class_count" unit="个" :loading="loading" />
      <StatCard label="在班学生" :value="summary?.student_count" unit="人" :loading="loading" />
      <StatCard label="进行中的作业" :value="summary?.active_assignments" :loading="loading" />
      <StatCard label="进行中的考试" :value="summary?.active_exams" :loading="loading" />
      <StatCard label="今日提交" :value="summary?.today_submissions" :loading="loading" />
      <StatCard label="判题队列" :value="summary?.queue_size" :loading="loading" :hint="summary?.queue_size ? '正在等待或评测中的提交' : '空闲'" />
    </div>

    <div class="cols">
      <el-card shadow="never">
        <template #header>近 14 天提交趋势</template>
        <el-skeleton v-if="loading" animated :rows="5" />
        <EChart v-else :option="trendOption" height="280px" label="近 14 天每日提交与通过次数" />
      </el-card>

      <el-card shadow="never">
        <template #header>需要关注</template>
        <el-skeleton v-if="loading" animated :rows="4" />
        <EmptyState v-else-if="!data?.attention.length" compact title="一切正常" description="没有提交率偏低的作业。" />
        <ul v-else class="attention">
          <li v-for="item in data.attention" :key="`${item.kind}-${item.id}`">
            <router-link :to="{ name: 'admin-assignment-results', params: { id: item.id } }" class="attention__item">
              <div class="attention__main">
                <div class="attention__title">{{ item.title }}</div>
                <div class="muted attention__meta">{{ item.class_name }} · {{ deadline(item) }}</div>
              </div>
              <div class="attention__rate">
                <RateBar :value="item.rate" width="56px" />
                <span class="muted num">{{ item.submitted }}/{{ item.member_count }} 人已提交</span>
              </div>
            </router-link>
          </li>
        </ul>
      </el-card>
    </div>

    <div class="cols cols--even">
      <el-card shadow="never">
        <template #header>近期考试</template>
        <el-skeleton v-if="loading" animated :rows="3" />
        <EmptyState v-else-if="!data?.upcoming_exams.length" compact title="没有即将开始的考试" />
        <ul v-else class="exams">
          <li v-for="exam in data.upcoming_exams" :key="exam.id">
            <router-link :to="{ name: 'admin-exam-monitor', params: { id: exam.id } }" class="exam">
              <div>
                <div class="exam__title">{{ exam.title }}</div>
                <div class="muted exam__meta">{{ exam.class_name }} · {{ formatDateTime(exam.start_time) }}</div>
              </div>
              <el-tag v-if="exam.in_progress" type="danger" size="small" effect="plain">进行中</el-tag>
              <el-tag v-else type="info" size="small" effect="plain">即将开始</el-tag>
            </router-link>
          </li>
        </ul>
      </el-card>

      <el-card shadow="never">
        <template #header>快捷操作</template>
        <div class="actions">
          <button v-for="a in actions" :key="a.text" type="button" class="action" @click="router.push(a.to)">
            <el-icon :size="20"><component :is="a.icon" /></el-icon>
            <span>{{ a.text }}</span>
          </button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--oj-space-4);
  margin-bottom: var(--oj-space-4);
}

.cols {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
  gap: var(--oj-space-4);
  margin-bottom: var(--oj-space-4);
}

.cols--even {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.attention__item,
.exam {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 8px;
  border-radius: var(--oj-radius-sm);
  color: inherit;
  text-decoration: none;
}

.attention__item:hover,
.exam:hover {
  background: var(--oj-surface-hover);
}

.attention__title,
.exam__title {
  font-weight: 600;
}

.attention__meta,
.exam__meta {
  font-size: var(--oj-fs-sm);
}

.attention__rate {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  font-size: var(--oj-fs-xs);
}

.actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--oj-space-3);
}

.action {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 8px;
  border: 1px dashed var(--oj-border-strong);
  border-radius: var(--oj-radius-md);
  background: transparent;
  color: var(--oj-text-2);
  font: inherit;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}

.action:hover {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  color: var(--oj-link);
}

@media (max-width: 1000px) {
  .cols,
  .cols--even {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
