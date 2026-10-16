<script setup>
import { onMounted, ref } from 'vue'
import { School } from '@element-plus/icons-vue'

import { classroomApi } from '@/api/classroom'

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
  <el-card v-loading="loading" shadow="never">
    <template #header><span class="title">我的班级</span></template>

    <el-empty v-if="!loading && !classes.length" description="你还没有加入任何班级。班级由任课教师导入，如有疑问请联系老师。" />

    <div class="class-grid">
      <div v-for="item in classes" :key="item.id" class="class-card">
        <el-icon class="class-card__icon"><School /></el-icon>
        <div>
          <div class="class-card__name">{{ item.name }}</div>
          <div class="class-card__meta">
            <span v-if="item.course">{{ item.course }}</span>
            <span v-if="item.semester">{{ item.semester }}</span>
          </div>
          <div class="class-card__teacher">任课教师：{{ item.teacher_name }}</div>
          <!-- TODO(M10)：待完成作业与完成进度 -->
        </div>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.title {
  font-size: 16px;
  font-weight: 600;
}

.class-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.class-card {
  display: flex;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-top: 3px solid var(--oj-brand-navy);
  border-radius: 6px;
  background: #fff;
}

.class-card__icon {
  flex-shrink: 0;
  color: var(--oj-brand-navy);
  font-size: 28px;
}

.class-card__name {
  font-size: 16px;
  font-weight: 600;
}

.class-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.class-card__teacher {
  margin-top: 8px;
  font-size: 13px;
}
</style>
