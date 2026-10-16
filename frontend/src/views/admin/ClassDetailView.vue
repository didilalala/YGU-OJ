<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Plus, Search, Upload } from '@element-plus/icons-vue'

import { adminClassApi } from '@/api/classroom'
import StudentImportDialog from '@/components/admin/StudentImportDialog.vue'
import { formatDateTime } from '@/utils/judge'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const classId = computed(() => Number(route.params.id))

const klass = ref(null)
const loadError = ref('')
const loading = ref(false)
const students = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const keyword = ref('')
const includeRemoved = ref(false)
const selected = ref([])
const tableRef = ref()
const importVisible = ref(route.query.import === '1')

async function loadClass() {
  try {
    klass.value = await adminClassApi.detail(classId.value, { silent: true })
    document.title = `${klass.value.name} - YGU OJ`
  } catch (err) {
    loadError.value = err?.code === 404 ? '班级不存在，或你没有权限管理' : err?.message || '加载失败'
  }
}

async function loadStudents() {
  loading.value = true
  try {
    const data = await adminClassApi.students(classId.value, {
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value.trim() || undefined,
      include_removed: includeRemoved.value ? 1 : undefined,
    })
    students.value = data.results
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function refresh() {
  await Promise.all([loadClass(), loadStudents()])
}

onMounted(async () => {
  await loadClass()
  if (klass.value) loadStudents()
})

function search() {
  page.value = 1
  loadStudents()
}

// ---------------------------------------------------------------- 单个添加

const addDialog = reactive({ visible: false, saving: false })
const addFormRef = ref()
const addForm = reactive({ student_no: '', real_name: '', college: '', major: '', grade: '' })
const addRules = {
  student_no: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
}

function openAdd() {
  Object.assign(addForm, { student_no: '', real_name: '', college: '', major: '', grade: '' })
  addDialog.visible = true
}

async function addStudent() {
  if (!(await addFormRef.value.validate().catch(() => false))) return
  addDialog.saving = true
  try {
    const report = await adminClassApi.addStudent(classId.value, { ...addForm })
    ElMessage.success(report.created ? '已创建账号并加入班级，初始密码为学号后六位' : '已有账号，已加入班级')
    if (report.notes.length) ElMessage.warning(report.notes[0].message)
    addDialog.visible = false
    refresh()
  } catch {
    // 错误提示已由请求拦截器弹出
  } finally {
    addDialog.saving = false
  }
}

// ---------------------------------------------------------------- 移出与重置密码

function describe(rows) {
  return rows.length === 1 ? `${rows[0].real_name}（${rows[0].student_no}）` : `选中的 ${rows.length} 名学生`
}

async function removeStudents(rows) {
  try {
    await ElMessageBox.confirm(
      `确定将${describe(rows)}移出班级吗？历史成绩保留，但不再计入本班后续统计；之后重新导入即可恢复。`,
      '移出学生',
      { type: 'warning', confirmButtonText: '移出' },
    )
  } catch {
    return
  }
  try {
    const { count } = await adminClassApi.removeStudents(classId.value, rows.map((r) => r.user_id))
    ElMessage.success(`已移出 ${count} 名学生`)
    tableRef.value?.clearSelection()
    refresh()
  } catch {
    // 错误提示已由请求拦截器弹出
  }
}

async function resetPasswords(rows) {
  try {
    await ElMessageBox.confirm(
      `确定将${describe(rows)}的密码重置为初始密码（学号后六位）吗？学生下次登录后须重新修改密码。`,
      '重置密码',
      { type: 'warning', confirmButtonText: '重置' },
    )
  } catch {
    return
  }
  try {
    const { count } = await adminClassApi.resetPasswords(classId.value, rows.map((r) => r.user_id))
    ElMessage.success(`已重置 ${count} 名学生的密码`)
    tableRef.value?.clearSelection()
    loadStudents()
  } catch {
    // 错误提示已由请求拦截器弹出
  }
}
</script>

<template>
  <el-result v-if="loadError" icon="warning" :title="loadError">
    <template #extra>
      <el-button type="primary" @click="router.push({ name: 'admin-classes' })">返回班级列表</el-button>
    </template>
  </el-result>

  <div v-else-if="klass" class="class-page">
    <PageHeader :title="klass.name">
      <template #meta>
        <div class="head-meta muted">
          <span v-if="klass.course">{{ klass.course }}</span>
          <span v-if="klass.semester">{{ klass.semester }}</span>
          <span>在班学生 {{ klass.member_count }} 人</span>
          <span v-if="klass.teacher_name">教师：{{ klass.teacher_name }}</span>
        </div>
      </template>
      <el-button @click="router.push({ name: 'admin-stats', query: { class_id: classId } })">成绩统计</el-button>
      <el-button @click="router.push({ name: 'admin-assignments', query: { class_id: classId } })">作业列表</el-button>
      <el-button type="primary" plain @click="router.push({ name: 'admin-assignment-create', query: { class_id: classId } })">
        布置作业
      </el-button>
      <el-button type="primary" plain @click="router.push({ name: 'admin-exam-create', query: { class_id: classId } })">
        创建考试
      </el-button>
    </PageHeader>
    <el-card shadow="never">
      <div class="toolbar">
        <el-input
          v-model="keyword"
          class="toolbar__search"
          placeholder="学号或姓名"
          clearable
          :prefix-icon="Search"
          @keyup.enter="search"
          @clear="search"
        />
        <el-checkbox v-model="includeRemoved" @change="search">显示已移出的学生</el-checkbox>
        <span class="toolbar__spacer" />
        <template v-if="selected.length">
          <span class="muted">已选 {{ selected.length }} 人</span>
          <el-button @click="resetPasswords(selected)">重置密码</el-button>
          <el-button type="danger" plain @click="removeStudents(selected)">移出班级</el-button>
        </template>
        <el-button :icon="Plus" @click="openAdd">添加学生</el-button>
        <el-button type="primary" :icon="Upload" @click="importVisible = true">导入名单</el-button>
      </div>

      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="students"
        row-key="id"
        class="student-table"
        @selection-change="(rows) => (selected = rows.filter((r) => !r.is_removed))"
      >
        <template #empty>
          <div class="empty">
            <p>班级里还没有学生</p>
            <el-button type="primary" @click="importVisible = true">导入学生名单</el-button>
          </div>
        </template>
        <el-table-column type="selection" width="44" :selectable="(row) => !row.is_removed" />
        <el-table-column prop="student_no" label="学号" width="130" />
        <el-table-column prop="real_name" label="姓名" width="100" />
        <el-table-column prop="college" label="学院" min-width="120" />
        <el-table-column prop="major" label="专业" min-width="120" />
        <el-table-column prop="grade" label="年级" width="70" />
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-tag v-if="row.is_removed" type="info" size="small">已移出</el-tag>
            <el-tag v-else-if="row.is_initial_password" type="warning" size="small" effect="plain">未修改初始密码</el-tag>
            <el-tag v-else type="success" size="small" effect="plain">正常</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最近登录" width="160">
          <template #default="{ row }">{{ row.last_login ? formatDateTime(row.last_login) : '从未登录' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <template v-if="!row.is_removed">
              <el-button link type="primary" @click="resetPasswords([row])">重置密码</el-button>
              <el-button link type="danger" @click="removeStudents([row])">移出</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > 20"
        v-model:current-page="page"
        v-model:page-size="pageSize"
        class="pagination"
        layout="total, sizes, prev, pager, next"
        :page-sizes="[20, 50, 100]"
        :total="total"
        @current-change="loadStudents"
        @size-change="search"
      />
    </el-card>

    <StudentImportDialog v-model="importVisible" :class-id="classId" @imported="refresh" />

    <el-dialog v-model="addDialog.visible" title="添加学生" width="460px">
      <el-form ref="addFormRef" :model="addForm" :rules="addRules" label-width="60px" @submit.prevent="addStudent">
        <el-form-item label="学号" prop="student_no">
          <el-input v-model="addForm.student_no" maxlength="32" />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="addForm.real_name" maxlength="32" />
        </el-form-item>
        <el-form-item label="学院">
          <el-input v-model="addForm.college" maxlength="64" />
        </el-form-item>
        <el-form-item label="专业">
          <el-input v-model="addForm.major" maxlength="64" />
        </el-form-item>
        <el-form-item label="年级">
          <el-input v-model="addForm.grade" maxlength="16" placeholder="如：2026" />
        </el-form-item>
      </el-form>
      <p class="muted">学号已有账号的直接加入班级；否则创建账号，初始密码为学号后六位。</p>
      <template #footer>
        <el-button @click="addDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="addDialog.saving" @click="addStudent">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.class-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}





.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.toolbar__search {
  width: 200px;
}

.toolbar__spacer {
  flex: 1;
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.empty {
  padding: 16px 0;
  line-height: 1.6;
}

.empty p {
  margin: 0 0 8px;
}

.pagination {
  justify-content: center;
  margin-top: 16px;
}
</style>
