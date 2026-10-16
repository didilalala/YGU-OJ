<script setup>
import { defineAsyncComponent, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'

import SubmissionResult from '@/components/SubmissionResult.vue'
import { useSubmissionPolling } from '@/composables/useSubmissionPolling'
import { useSiteStore } from '@/stores/site'
import { useUserStore } from '@/stores/user'
import { copyText } from '@/utils/clipboard'
import { formatDateTime } from '@/utils/judge'

const CodeEditor = defineAsyncComponent(() => import('@/components/CodeEditor.vue'))

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const site = useSiteStore()
const { submission, error, start } = useSubmissionPolling()
const loading = ref(true)

watch(
  () => route.params.id,
  async (id) => {
    if (!id) return
    loading.value = true
    submission.value = null
    await start(id)
    loading.value = false
  },
  { immediate: true },
)

async function copyCode() {
  try {
    await copyText(submission.value.code)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}
</script>

<template>
  <div v-loading="loading" class="submission-page">
    <el-result v-if="error" icon="warning" title="无法查看该提交" :sub-title="error">
      <template #extra>
        <el-button type="primary" @click="router.push({ name: 'submissions' })">返回提交记录</el-button>
      </template>
    </el-result>

    <template v-else-if="submission">
      <el-card shadow="never">
        <template #header>
          <div class="header">
            <span class="header__title">提交 #{{ submission.id }}</span>
            <router-link :to="{ name: 'problem-detail', params: { id: submission.problem } }" class="link">
              {{ submission.problem }}. {{ submission.problem_title }}
            </router-link>
          </div>
        </template>
        <el-descriptions :column="3" size="small" class="meta">
          <el-descriptions-item v-if="userStore.isStaff" label="用户">{{ submission.username }}</el-descriptions-item>
          <el-descriptions-item label="语言">{{ site.languageName(submission.language) }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ formatDateTime(submission.created_at) }}</el-descriptions-item>
        </el-descriptions>
        <SubmissionResult :submission="submission" />
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="header">
            <span class="header__title">代码</span>
            <el-button link type="primary" :icon="CopyDocument" @click="copyCode">复制</el-button>
          </div>
        </template>
        <CodeEditor
          :model-value="submission.code"
          :language="site.languageMonaco(submission.language)"
          read-only
          height="480px"
        />
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.submission-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 300px;
}

.header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.header__title {
  font-weight: 600;
}

.link {
  color: var(--el-color-primary);
  text-decoration: none;
}

.meta {
  margin-bottom: 12px;
}
</style>
