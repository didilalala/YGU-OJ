<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'

import { adminClassApi } from '@/api/classroom'
import { useUserStore } from '@/stores/user'
import { formatDateTime } from '@/utils/judge'
import PageHeader from '@/components/ui/PageHeader.vue'

const router = useRouter()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.role === 'admin')

const PAGE_SIZE = 20

const loading = ref(false)
const classes = ref([])
const total = ref(0)
const page = ref(1)
const keyword = ref('')

async function load() {
  loading.value = true
  try {
    const data = await adminClassApi.list({ page: page.value, page_size: PAGE_SIZE, keyword: keyword.value.trim() || undefined })
    classes.value = data.results
    total.value = data.total
  } finally {
    loading.value = false
  }
}

onMounted(load)

function search() {
  page.value = 1
  load()
}

// ---------------------------------------------------------------- 新建与编辑

/** 当前学期，如 2026 年 10 月为 2026-2027-1，2027 年 3 月为 2026-2027-2 */
function currentSemester(now = new Date()) {
  const year = now.getFullYear()
  const month = now.getMonth() + 1
  if (month >= 8) return `${year}-${year + 1}-1`
  if (month >= 2) return `${year - 1}-${year}-2`
  return `${year - 1}-${year}-1`
}

const dialog = reactive({ visible: false, saving: false, editingId: null })
const formRef = ref()
const form = reactive({ name: '', course: '', semester: '' })
const rules = { name: [{ required: true, message: '请输入班级名称', trigger: 'blur' }] }

const semesterOptions = computed(() => {
  const current = currentSemester()
  const [start] = current.split('-').map(Number)
  return [`${start - 1}-${start}-2`, `${start}-${start + 1}-1`, `${start}-${start + 1}-2`, `${start + 1}-${start + 2}-1`]
})

function openCreate() {
  Object.assign(form, { name: '', course: '', semester: currentSemester() })
  dialog.editingId = null
  dialog.visible = true
}

function openEdit(row) {
  Object.assign(form, { name: row.name, course: row.course, semester: row.semester })
  dialog.editingId = row.id
  dialog.visible = true
}

async function save() {
  if (!(await formRef.value.validate().catch(() => false))) return
  dialog.saving = true
  try {
    const data = { name: form.name.trim(), course: form.course.trim(), semester: form.semester.trim() }
    if (dialog.editingId) {
      await adminClassApi.update(dialog.editingId, data)
      ElMessage.success('已保存')
      dialog.visible = false
      load()
    } else {
      const created = await adminClassApi.create(data)
      ElMessage.success('班级已创建，接下来导入学生名单')
      dialog.visible = false
      router.push({ name: 'admin-class-detail', params: { id: created.id }, query: { import: '1' } })
    }
  } catch {
    // 错误提示已由请求拦截器弹出
  } finally {
    dialog.saving = false
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除班级「${row.name}」吗？班级中的 ${row.member_count} 名学生将移出该班级，学生账号保留。`,
      '删除班级',
      { type: 'warning', confirmButtonText: '删除' },
    )
  } catch {
    return
  }
  try {
    await adminClassApi.remove(row.id)
    ElMessage.success('已删除')
    load()
  } catch {
    // 错误提示已由请求拦截器弹出
  }
}
</script>

<template>
  <div>
    <PageHeader title="班级" :subtitle="total ? `共 ${total} 个班级` : ''">
      <el-input
        v-model="keyword"
        class="header__search"
        placeholder="班级名称或课程"
        clearable
        :prefix-icon="Search"
        @keyup.enter="search"
        @clear="search"
      />
      <el-button type="primary" :icon="Plus" @click="openCreate">新建班级</el-button>
    </PageHeader>
    <el-card shadow="never">
      <el-table v-loading="loading" :data="classes" empty-text="还没有班级，点击「新建班级」开始">
        <el-table-column label="班级" min-width="180">
          <template #default="{ row }">
            <router-link :to="{ name: 'admin-class-detail', params: { id: row.id } }" class="link">{{ row.name }}</router-link>
          </template>
        </el-table-column>
        <el-table-column prop="course" label="课程" min-width="140" />
        <el-table-column prop="semester" label="学期" width="130" />
        <el-table-column prop="member_count" label="学生数" width="90" />
        <el-table-column v-if="isAdmin" prop="teacher_name" label="教师" width="110" />
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <el-button link type="primary" @click="router.push({ name: 'admin-class-detail', params: { id: row.id } })">
              学生
            </el-button>
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > PAGE_SIZE"
        v-model:current-page="page"
        class="pagination"
        layout="prev, pager, next, total"
        :total="total"
        :page-size="PAGE_SIZE"
        @current-change="load"
      />

      <el-dialog v-model="dialog.visible" :title="dialog.editingId ? '编辑班级' : '新建班级'" width="460px">
        <el-form ref="formRef" :model="form" :rules="rules" label-width="80px" @submit.prevent="save">
          <el-form-item label="班级名称" prop="name">
            <el-input v-model="form.name" maxlength="64" placeholder="如：软件工程 2601 班" />
          </el-form-item>
          <el-form-item label="课程">
            <el-input v-model="form.course" maxlength="64" placeholder="如：C 语言程序设计" />
          </el-form-item>
          <el-form-item label="学期">
            <el-select v-model="form.semester" filterable allow-create default-first-option class="full-width">
              <el-option v-for="option in semesterOptions" :key="option" :label="option" :value="option" />
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialog.visible = false">取消</el-button>
          <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<style scoped>


.header__search {
  width: 220px;
}

.link {
  color: var(--el-color-primary);
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.pagination {
  justify-content: center;
  margin-top: 16px;
}

.full-width {
  width: 100%;
}
</style>
