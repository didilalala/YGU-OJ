<script setup>
/** 公开竞赛列表：所有人可浏览，登录后参加。 */
import { computed, onMounted, ref } from 'vue'
import { Lock } from '@element-plus/icons-vue'

import { examApi } from '@/api/exam'
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
  <el-card v-loading="loading" shadow="never">
    <template #header><span class="title">竞赛</span></template>
    <el-empty v-if="!loading && !contests.length" description="暂无公开竞赛" />

    <template v-for="group in groups" :key="group.key">
      <section v-if="group.items.length" class="group">
        <h3 class="group__title">{{ group.title }}</h3>
        <router-link
          v-for="contest in group.items"
          :key="contest.id"
          :to="{ name: 'contest-detail', params: { id: contest.id } }"
          :class="['contest', `contest--${contest.status}`]"
        >
          <div class="contest__main">
            <div class="contest__title">
              {{ contest.title }}
              <el-tag :type="EXAM_STATUS[contest.status].type" size="small">{{ EXAM_STATUS[contest.status].label }}</el-tag>
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
          <div v-if="myState(contest)" class="contest__state">{{ myState(contest) }}</div>
        </router-link>
      </section>
    </template>
  </el-card>
</template>

<style scoped>
.title {
  font-size: 16px;
  font-weight: 600;
}

.group + .group {
  margin-top: 20px;
}

.group__title {
  margin: 0 0 10px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.contest {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 24px;
  margin-bottom: 10px;
  padding: 14px 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-left: 3px solid var(--el-border-color);
  border-radius: 6px;
  background: #fff;
  color: inherit;
  text-decoration: none;
}

.contest:hover {
  box-shadow: var(--el-box-shadow-light);
}

.contest--in_progress {
  border-left-color: var(--el-color-danger);
}

.contest--not_started {
  border-left-color: var(--oj-brand-navy);
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
  font-size: 16px;
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
  gap: 4px 16px;
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.contest__state {
  color: var(--el-text-color-regular);
  font-size: 13px;
}
</style>
