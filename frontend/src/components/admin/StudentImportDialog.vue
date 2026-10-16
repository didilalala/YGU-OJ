<script setup>
/** 导入学生名单：下载模板 → 上传 Excel → 查看导入报告。导入后触发 imported 事件。 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, UploadFilled } from '@element-plus/icons-vue'

import { adminClassApi } from '@/api/classroom'
import { saveBlob } from '@/utils/download'

const props = defineProps({
  classId: { type: Number, required: true },
})
const visible = defineModel({ type: Boolean, default: false })
const emit = defineEmits(['imported'])

const uploading = ref(false)
const downloading = ref(false)
const report = ref(null)

const summary = computed(() => {
  if (!report.value) return ''
  const r = report.value
  const parts = [`新建账号 ${r.created} 人`, `加入已有账号 ${r.joined} 人`]
  if (r.already_in_class) parts.push(`已在班级 ${r.already_in_class} 人`)
  if (r.failed.length) parts.push(`失败 ${r.failed.length} 行`)
  return parts.join('，')
})

async function downloadTemplate() {
  downloading.value = true
  try {
    saveBlob(await adminClassApi.downloadTemplate(), '学生名单导入模板.xlsx')
  } catch {
    ElMessage.error('模板下载失败')
  } finally {
    downloading.value = false
  }
}

async function upload({ file }) {
  uploading.value = true
  try {
    report.value = await adminClassApi.importStudents(props.classId, file)
    if (report.value.created || report.value.joined) emit('imported')
  } finally {
    uploading.value = false
  }
}

function onClosed() {
  report.value = null
}
</script>

<template>
  <el-dialog v-model="visible" title="导入学生名单" width="680px" @closed="onClosed">
    <template v-if="!report">
      <ol class="steps">
        <li>
          下载模板，按表头填写学号、姓名（必填）及学院、专业、年级。
          <el-button link type="primary" :icon="Download" :loading="downloading" @click="downloadTemplate">
            下载模板
          </el-button>
        </li>
        <li>上传填好的 .xlsx 文件。新学号自动创建账号，初始密码为学号后六位，首次登录须修改密码。</li>
      </ol>
      <el-upload drag accept=".xlsx" :show-file-list="false" :http-request="upload" :disabled="uploading">
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">{{ uploading ? '正在导入…' : '将名单拖到此处，或点击上传' }}</div>
      </el-upload>
    </template>

    <template v-else>
      <el-alert
        :type="report.failed.length ? 'warning' : 'success'"
        :closable="false"
        show-icon
        :title="summary"
      />
      <template v-if="report.failed.length">
        <h4 class="section-title">未导入的行（请修改后重新上传，已导入的不会重复）</h4>
        <el-table :data="report.failed" size="small" max-height="260">
          <el-table-column label="行号" width="70">
            <template #default="{ row }">{{ row.row ?? '—' }}</template>
          </el-table-column>
          <el-table-column prop="student_no" label="学号" width="140" />
          <el-table-column prop="reason" label="原因" min-width="200" />
        </el-table>
      </template>
      <template v-if="report.notes.length">
        <h4 class="section-title">提示</h4>
        <el-table :data="report.notes" size="small" max-height="200">
          <el-table-column prop="row" label="行号" width="70" />
          <el-table-column prop="student_no" label="学号" width="140" />
          <el-table-column prop="message" label="说明" min-width="200" />
        </el-table>
      </template>
    </template>

    <template #footer>
      <el-button v-if="report" @click="report = null">继续导入</el-button>
      <el-button type="primary" @click="visible = false">完成</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.steps {
  margin: 0 0 16px;
  padding-left: 20px;
  line-height: 2;
  color: var(--el-text-color-regular);
}

.section-title {
  margin: 16px 0 8px;
  font-size: 14px;
}
</style>
