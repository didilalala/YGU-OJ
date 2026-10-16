<script setup>
/** FPS 导入对话框（HUSTOJ 等系统导出的题目 XML）。导入成功后触发 imported 事件。 */
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'

import { adminProblemApi } from '@/api/adminProblem'

const visible = defineModel({ type: Boolean, default: false })
const emit = defineEmits(['imported'])

const uploading = ref(false)
const progress = ref(0)
const result = ref(null)

async function upload({ file }) {
  uploading.value = true
  progress.value = 0
  result.value = null
  try {
    result.value = await adminProblemApi.importFps(file, (value) => (progress.value = value))
    if (result.value.created.length) emit('imported')
  } finally {
    uploading.value = false
  }
}

function onClosed() {
  result.value = null
}
</script>

<template>
  <el-dialog v-model="visible" title="导入 FPS 题目" width="640px" @closed="onClosed">
    <el-upload
      v-if="!result"
      drag
      accept=".xml,.fps"
      :show-file-list="false"
      :http-request="upload"
      :disabled="uploading"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div v-if="uploading" class="el-upload__text">正在导入 {{ progress }}%…</div>
      <div v-else class="el-upload__text">将 FPS 文件（.xml）拖到此处，或 <em>点击上传</em></div>
      <template #tip>
        <div class="el-upload__tip">
          导入的题目为私有，创建者为你，可在题库中修改后设为公开。特判题暂不支持，会被跳过。
        </div>
      </template>
    </el-upload>

    <template v-else>
      <el-alert
        :type="result.created.length ? 'success' : 'warning'"
        :closable="false"
        show-icon
        :title="`导入 ${result.created.length} 道题目${result.skipped.length ? `，跳过 ${result.skipped.length} 道` : ''}`"
      />
      <el-table v-if="result.created.length" :data="result.created" size="small" class="result-table">
        <el-table-column prop="id" label="题号" width="70" />
        <el-table-column prop="title" label="标题" min-width="160" />
        <el-table-column prop="test_case_count" label="测试点" width="70" />
        <el-table-column label="提示" min-width="180">
          <template #default="{ row }">
            <div v-for="warning in row.warnings" :key="warning" class="warning">{{ warning }}</div>
          </template>
        </el-table-column>
      </el-table>
      <el-table v-if="result.skipped.length" :data="result.skipped" size="small" class="result-table">
        <el-table-column prop="title" label="跳过的题目" min-width="160" />
        <el-table-column prop="reason" label="原因" min-width="180" />
      </el-table>
    </template>

    <template #footer>
      <el-button v-if="result" @click="result = null">继续导入</el-button>
      <el-button type="primary" @click="visible = false">完成</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.result-table {
  margin-top: 12px;
}

.warning {
  color: var(--el-color-warning-dark-2);
  font-size: 12px;
}
</style>
