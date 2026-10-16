<script setup>
/**
 * 测试数据上传：上传 zip 后得到 test_case_id，随题目一起保存才生效。
 *
 *   <TestCaseUploader v-model="form.test_case_id" v-model:cases="testCases" />
 */
import { computed, ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'

import { adminProblemApi } from '@/api/adminProblem'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})
const testCaseId = defineModel({ type: String, default: '' })
const cases = defineModel('cases', { type: Array, default: () => [] })

const savedTestCaseId = ref(testCaseId.value)
const uploading = ref(false)
const progress = ref(0)

const replaced = computed(() => savedTestCaseId.value && testCaseId.value !== savedTestCaseId.value)

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function upload({ file }) {
  uploading.value = true
  progress.value = 0
  try {
    const data = await adminProblemApi.uploadTestCases(file, (value) => (progress.value = value))
    testCaseId.value = data.test_case_id
    cases.value = data.test_cases
  } finally {
    uploading.value = false
  }
}

// 题目保存后调用，之后再上传才算「替换」
function markSaved() {
  savedTestCaseId.value = testCaseId.value
}

defineExpose({ markSaved })
</script>

<template>
  <div class="test-cases">
    <el-upload
      drag
      accept=".zip"
      :show-file-list="false"
      :http-request="upload"
      :disabled="props.disabled || uploading"
      class="test-cases__upload"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div v-if="uploading" class="el-upload__text">正在上传 {{ progress }}%…</div>
      <div v-else class="el-upload__text">
        将 zip 拖到此处，或 <em>点击上传</em>{{ cases.length ? '（将替换现有数据）' : '' }}
      </div>
      <template #tip>
        <div class="el-upload__tip">
          压缩包中每组数据为同名的 .in 与 .out 文件（如 1.in / 1.out），可放在子目录中，按名称排序为 1、2、10……
        </div>
      </template>
    </el-upload>

    <el-alert
      v-if="!cases.length"
      type="warning"
      :closable="false"
      show-icon
      title="尚未上传测试数据，学生暂时无法提交此题。"
    />
    <template v-else>
      <el-alert
        v-if="replaced"
        type="info"
        :closable="false"
        show-icon
        title="已上传新的测试数据，保存题目后生效，旧数据随之删除。"
        class="test-cases__alert"
      />
      <el-table :data="cases" size="small" max-height="280" class="test-cases__table">
        <el-table-column prop="index" label="测试点" width="80" />
        <!-- 原文件名只在刚上传时可知，保存后的题目不记录 -->
        <el-table-column v-if="cases.some((c) => c.name)" label="原文件名" min-width="120">
          <template #default="{ row }">{{ row.name ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="输入大小" width="110">
          <template #default="{ row }">{{ formatSize(row.input_size) }}</template>
        </el-table-column>
        <el-table-column label="输出大小" width="110">
          <template #default="{ row }">{{ formatSize(row.output_size) }}</template>
        </el-table-column>
      </el-table>
    </template>
  </div>
</template>

<style scoped>
.test-cases {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.test-cases__upload :deep(.el-upload-dragger) {
  padding: 20px;
}

.test-cases__upload :deep(.el-icon--upload) {
  margin-bottom: 4px;
  font-size: 40px;
}
</style>
