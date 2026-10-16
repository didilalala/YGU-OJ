<script setup>
import { onMounted, ref } from 'vue'
import { School } from '@element-plus/icons-vue'

import { classroomApi } from '@/api/classroom'
import LearnTabs from '@/components/LearnTabs.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const loading = ref(true)
const classes = ref([])

onMounted(async () => {
  try {
    classes.value = await classroomApi.mine()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <PageHeader title="我的班级" subtitle="你所在的教学班" />
    <LearnTabs />

    <el-skeleton v-if="loading" animated :rows="3" />
    <EmptyState
      v-else-if="!classes.length"
      title="你还没有加入任何班级"
      description="班级由任课教师导入名单后自动加入，如有疑问请联系老师。"
    />

    <div class="class-grid">
      <article v-for="item in classes" :key="item.id" class="class-card">
        <div class="class-card__icon"><el-icon :size="22"><School /></el-icon></div>
        <h2 class="class-card__name">{{ item.name }}</h2>
        <div class="class-card__tags">
          <el-tag v-if="item.course" size="small" effect="plain">{{ item.course }}</el-tag>
          <el-tag v-if="item.semester" size="small" effect="plain" type="info">{{ item.semester }}</el-tag>
        </div>
        <div class="class-card__teacher">任课教师 · {{ item.teacher_name }}</div>
      </article>
    </div>
  </div>
</template>

<style scoped>
.class-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--oj-space-4);
}

.class-card {
  padding: 20px;
  border: 1px solid var(--oj-border);
  border-radius: var(--oj-radius-md);
  background: var(--oj-surface);
}

.class-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: var(--oj-radius-sm);
  background: var(--el-color-primary-light-9);
  color: var(--oj-link);
}

.class-card__name {
  margin: 12px 0 8px;
  font-size: var(--oj-fs-md);
}

.class-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.class-card__teacher {
  margin-top: 12px;
  color: var(--oj-text-3);
  font-size: var(--oj-fs-sm);
}
</style>
