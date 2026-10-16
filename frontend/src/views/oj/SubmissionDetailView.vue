<script setup>
import { defineAsyncComponent, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'

import SubmissionResult from '@/components/SubmissionResult.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
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
  <div class="submission-page">
    <el-result v-if="error" icon="warning" title="无法查看该提交" :sub-title="error">
      <template #extra>
        <el-button type="primary" @click="router.push({ name: 'submissions' })">返回提交记录</el-button>
      </template>
    </el-result>

    <el-skeleton v-else-if="loading" animated :rows="8" />

    <template v-else-if="submission">
      <PageHeader
        :title="`提交 #${submission.id}`"
        :crumbs="[{ text: '提交记录', to: '/submissions' }]"
      >
        <template #meta>
          <router-link :to="{ name: 'problem-detail', params: { id: submission.problem } }" class="text-link problem">
            {{ submission.problem }}. {{ submission.problem_title }}
          </router-link>
        </template>
        <el-button @click="router.push({ name: 'problem-detail', params: { id: submission.problem } })">再做一次</el-button>
      </PageHeader>

      <div class="meta">
        <div v-if="userStore.isStaff" class="meta__item"><span>用户</span><b>{{ submission.username }}</b></div>
        <div class="meta__item"><span>语言</span><b>{{ site.languageName(submission.language) }}</b></div>
        <div class="meta__item"><span>提交时间</span><b>{{ formatDateTime(submission.created_at) }}</b></div>
      </div>

      <el-card shadow="never" class="block">
        <SubmissionResult :submission="submission" />
      </el-card>

      <el-card shadow="never" class="block">
        <template #header>
          <div class="header">
            <span>代码</span>
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
.problem {
  display: inline-block;
  margin-top: 4px;
  font-weight: 500;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 32px;
  margin-bottom: var(--oj-space-4);
  color: var(--oj-text-3);
  font-size: var(--oj-fs-sm);
}

.meta__item b {
  margin-left: 8px;
  color: var(--oj-text);
  font-weight: 500;
}

.block {
  margin-bottom: var(--oj-space-4);
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
