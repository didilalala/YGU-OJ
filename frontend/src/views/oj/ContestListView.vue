<script setup>
/** 公开竞赛列表：所有人可浏览，登录后参加。 */
import { computed, onMounted, ref } from 'vue'
import { Lock } from '@element-plus/icons-vue'

import { examApi } from '@/api/exam'
import Countdown from '@/components/ui/Countdown.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { EXAM_STATUS, RULE_LABELS } from '@/utils/exam'
import { formatDateTime } from '@/utils/judge'

const loading = ref(true)
const contests = ref([])

const groups = computed(() => [
  { key: 'in_progress', title: '进行中', items: contests.value.filter((c) => c.status === 'in_progress') },
  // 即将开始的按开始时间正序
  { key: 'not_started', title: '即将开始', items: contests.value.filter((c) => c.status === 'not_started').reverse() },
  { key: 'ended', title: '已结束', items: contests.value.filter((c) => c.status === 'ended') },
])

onMounted(async () => {
  try {
    contests.value = await examApi.contests()
  } finally {
    loading.value = false
  }
})

function myState(contest) {
  if (contest.finished) return '已交卷'
  if (contest.joined) return '已参加'
  return ''
}
</script>

<template>
  <div>
    <PageHeader title="竞赛" subtitle="公开竞赛所有人可浏览，登录后参加" />

    <el-skeleton v-if="loading" animated :rows="4" />
    <EmptyState v-else-if="!contests.length" title="暂无公开竞赛" description="有新的竞赛时会显示在这里。" />

    <template v-for="group in groups" :key="group.key">
      <section v-if="group.items.length" class="group">
        <h2 class="group__title">{{ group.title }} <span class="num">{{ group.items.length }}</span></h2>
        <router-link
          v-for="contest in group.items"
          :key="contest.id"
          :to="{ name: 'contest-detail', params: { id: contest.id } }"
          :class="['contest', `contest--${contest.status}`]"
        >
          <div class="contest__main">
            <div class="contest__title">
              {{ contest.title }}
              <el-tag :type="EXAM_STATUS[contest.status].type" size="small" effect="plain">{{ EXAM_STATUS[contest.status].label }}</el-tag>
              <el-tag v-if="contest.need_password" size="small" effect="plain" type="info">
                <el-icon><Lock /></el-icon> 需口令
              </el-tag>
            </div>
            <div class="contest__meta">
              <span>{{ RULE_LABELS[contest.rule_type] }} · {{ contest.problem_count }} 题</span>
              <span>{{ formatDateTime(contest.start_time) }} 至 {{ formatDateTime(contest.end_time) }}</span>
              <span>{{ contest.participant_count }} 人参加</span>
            </div>
          </div>
          <div class="contest__state">
            <Countdown v-if="contest.status === 'in_progress'" :end="contest.end_time" />
            <span v-if="myState(contest)">{{ myState(contest) }}</span>
          </div>
        </router-link>
      </section>
    </template>
  </div>
</template>

<style scoped>
.group + .group {
  margin-top: var(--oj-space-5);
}

.group__title {
  margin: 0 0 var(--oj-space-3);
  color: var(--oj-text-3);
  font-size: var(--oj-fs-sm);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.contest {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 24px;
  margin-bottom: 12px;
  padding: 16px 20px;
  border: 1px solid var(--oj-border);
  border-left: 3px solid var(--oj-border-strong);
  border-radius: var(--oj-radius-md);
  background: var(--oj-surface);
  color: inherit;
  text-decoration: none;
  transition: box-shadow 0.15s;
}

.contest:hover {
  box-shadow: var(--oj-shadow-sm);
}

.contest--in_progress {
  border-left-color: var(--oj-v-wa-fg);
}

.contest--not_started {
  border-left-color: var(--el-color-primary);
}

.contest__main {
  flex: 1;
  min-width: 220px;
}

.contest__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: var(--oj-fs-md);
  font-weight: 600;
}

.contest__title .el-tag :deep(.el-tag__content) {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.contest__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 16px;
  margin-top: 4px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-sm);
}

.contest__state {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  color: var(--oj-text-2);
  font-size: var(--oj-fs-sm);
}
</style>
