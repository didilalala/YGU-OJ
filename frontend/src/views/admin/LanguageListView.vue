<script setup>
/**
 * 支持语言（M6）：启用或停用语言，编辑名称、代码编辑器语言、初始代码与判题配置。
 * 语言不能删除：已有提交仍引用它，停用即可。
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

import { adminLanguageApi } from '@/api/system'
import { useSiteStore } from '@/stores/site'

const MB = 1024 * 1024
const KEY_PATTERN = /^[a-z][a-z0-9_]{0,31}$/
// 与后端 seccomp 规则名称一致；留空表示不使用系统调用白名单（如 Java）
const SECCOMP_RULES = [
  { value: '', label: '不限制（不使用白名单）' },
  { value: 'c_cpp', label: 'c_cpp（C / C++）' },
  { value: 'general', label: 'general（Python 等解释型语言）' },
]

const site = useSiteStore()
const loading = ref(false)
const languages = ref([])
const dialog = reactive({ visible: false, saving: false, editing: null })
const formRef = ref()
const form = reactive(emptyForm())
const rules = {
  key: [
    { required: true, message: '请输入标识', trigger: 'blur' },
    { pattern: KEY_PATTERN, message: '小写字母开头，只能包含小写字母、数字和下划线', trigger: 'blur' },
  ],
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  monaco_id: [{ required: true, message: '请输入编辑器语言', trigger: 'blur' }],
  run_command: [{ required: true, message: '请输入运行命令', trigger: 'blur' }],
  src_name: [{ required: true, message: '请输入源文件名', trigger: 'blur' }],
}
// 编译相关字段只在「需要编译」时必填，因此在保存时单独检查
const COMPILE_FIELDS = [
  ['exe_name', '请输入可执行文件名'],
  ['compile_command', '请输入编译命令'],
]

function emptyForm() {
  return {
    key: '',
    name: '',
    enabled: true,
    sort_order: 10,
    monaco_id: '',
    starter_code: '',
    compiled: true,
    src_name: '',
    exe_name: 'main',
    compile_command: '',
    max_cpu_time: 3000,
    max_real_time: 10000,
    max_memory_mb: 256,
    run_command: '',
    seccomp_rule: '',
    env_text: 'LANG=C.UTF-8',
    memory_limit_check_only: false,
  }
}

async function load() {
  loading.value = true
  try {
    languages.value = await adminLanguageApi.list()
  } finally {
    loading.value = false
  }
}

onMounted(load)

// 把表单转换为后端的判题配置格式
function buildPayload() {
  const compile_config = form.compiled
    ? {
        src_name: form.src_name.trim(),
        exe_name: form.exe_name.trim(),
        compile_command: form.compile_command.trim(),
        max_cpu_time: form.max_cpu_time,
        max_real_time: form.max_real_time,
        // -1 表示不限制（如 Java），其余换算为字节
        max_memory: form.max_memory_mb === -1 ? -1 : form.max_memory_mb * MB,
      }
    : null
  return {
    key: form.key.trim(),
    name: form.name.trim(),
    enabled: form.enabled,
    sort_order: form.sort_order,
    monaco_id: form.monaco_id.trim(),
    starter_code: form.starter_code,
    compile_config,
    run_config: {
      command: form.run_command.trim(),
      seccomp_rule: form.seccomp_rule || null,
      env: form.env_text.split('\n').map((line) => line.trim()).filter(Boolean),
      memory_limit_check_only: form.memory_limit_check_only ? 1 : 0,
      // 解释执行时源代码以该文件名保存后直接运行
      ...(form.compiled ? {} : { exe_name: form.src_name.trim() }),
    },
  }
}

function fillForm(lang) {
  const compile = lang.compile_config
  Object.assign(form, emptyForm(), {
    key: lang.key,
    name: lang.name,
    enabled: lang.enabled,
    sort_order: lang.sort_order,
    monaco_id: lang.monaco_id,
    starter_code: lang.starter_code,
    compiled: !!compile,
    src_name: compile?.src_name ?? lang.run_config.exe_name ?? '',
    exe_name: compile?.exe_name ?? 'main',
    compile_command: compile?.compile_command ?? '',
    max_cpu_time: compile?.max_cpu_time ?? 3000,
    max_real_time: compile?.max_real_time ?? 10000,
    max_memory_mb: compile ? (compile.max_memory === -1 ? -1 : Math.round(compile.max_memory / MB)) : 256,
    run_command: lang.run_config.command,
    seccomp_rule: lang.run_config.seccomp_rule ?? '',
    env_text: (lang.run_config.env ?? []).join('\n'),
    memory_limit_check_only: !!lang.run_config.memory_limit_check_only,
  })
}

function openCreate() {
  dialog.editing = null
  Object.assign(form, emptyForm())
  dialog.visible = true
}

function openEdit(lang) {
  dialog.editing = lang
  fillForm(lang)
  dialog.visible = true
}

async function toggle(lang, value) {
  try {
    const updated = await adminLanguageApi.update(lang.id, { enabled: value })
    Object.assign(lang, updated)
    ElMessage.success(value ? '已启用，学生可以选择该语言提交' : '已停用，学生不能再选择该语言')
    site.load()
  } catch {
    // 错误提示已由请求拦截器弹出
  }
}

async function save() {
  if (form.compiled) {
    const missing = COMPILE_FIELDS.find(([field]) => !form[field].trim())
    if (missing) {
      ElMessage.warning(missing[1])
      return
    }
  }
  if (!(await formRef.value.validate().catch(() => false))) return
  dialog.saving = true
  try {
    const payload = buildPayload()
    if (dialog.editing) {
      delete payload.key
      await adminLanguageApi.update(dialog.editing.id, payload)
    } else {
      await adminLanguageApi.create(payload)
    }
    ElMessage.success('已保存')
    dialog.visible = false
    await load()
    site.load()
  } catch {
    // 校验错误提示已由请求拦截器弹出
  } finally {
    dialog.saving = false
  }
}

const isEditing = computed(() => !!dialog.editing)
</script>

<template>
  <el-card v-loading="loading" shadow="never">
    <template #header>
      <div class="header">
        <span class="header__title">支持语言</span>
        <span class="header__spacer" />
        <el-button type="primary" :icon="Plus" @click="openCreate">新增语言</el-button>
      </div>
    </template>
    <p class="hint">
      停用的语言不再出现在提交与题目的语言选项中，已有提交与重判不受影响。编译配置留空则按解释语言处理，运行时直接执行源文件。
    </p>

    <el-table :data="languages" empty-text="还没有语言">
      <el-table-column prop="sort_order" label="排序" width="70" align="center" />
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="key" label="标识" width="110">
        <template #default="{ row }"><code>{{ row.key }}</code></template>
      </el-table-column>
      <el-table-column label="类型" width="90">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.compile_config ? '编译执行' : '解释执行' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="编辑器" width="110">
        <template #default="{ row }">{{ row.monaco_id }}</template>
      </el-table-column>
      <el-table-column label="启用" width="90" align="center">
        <template #default="{ row }">
          <el-switch :model-value="row.enabled" @update:model-value="(value) => toggle(row, value)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="dialog.visible"
      :title="isEditing ? `编辑语言：${dialog.editing.name}` : '新增语言'"
      width="680px"
      top="5vh"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px" class="lang-form">
        <h4 class="section">基本信息</h4>
        <el-form-item label="标识" prop="key">
          <el-input v-model="form.key" :disabled="isEditing" maxlength="32" placeholder="如 go、kotlin，创建后不可修改" />
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" maxlength="64" placeholder="显示给学生的名称，如 Go 1.22" />
        </el-form-item>
        <el-form-item label="编辑器语言" prop="monaco_id">
          <el-input v-model="form.monaco_id" maxlength="32" placeholder="语法高亮，如 go、kotlin、plaintext" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :max="999" controls-position="right" />
        </el-form-item>
        <el-form-item label="初始代码">
          <el-input v-model="form.starter_code" type="textarea" :rows="5" class="mono" placeholder="学生新建代码时看到的内容，留空则为空白" />
        </el-form-item>

        <h4 class="section">编译</h4>
        <el-form-item label="需要编译">
          <el-switch v-model="form.compiled" :active-text="form.compiled ? '是' : '否，解释执行'" />
        </el-form-item>
        <el-form-item label="源文件名" prop="src_name">
          <el-input v-model="form.src_name" maxlength="64" placeholder="如 main.go、solution.rb" />
        </el-form-item>
        <template v-if="form.compiled">
          <el-form-item label="可执行文件名" prop="exe_name">
            <el-input v-model="form.exe_name" maxlength="64" />
          </el-form-item>
          <el-form-item label="编译命令" prop="compile_command">
            <el-input
              v-model="form.compile_command"
              type="textarea"
              :rows="2"
              class="mono"
              placeholder="可用占位符 {src_path} {exe_path} {exe_dir}"
            />
          </el-form-item>
          <el-form-item label="编译时间上限（毫秒）">
            <el-input-number v-model="form.max_cpu_time" :min="100" :max="60000" :step="500" controls-position="right" />
          </el-form-item>
          <el-form-item label="编译内存上限（MB）">
            <el-input-number v-model="form.max_memory_mb" :min="-1" :max="4096" controls-position="right" />
            <span class="muted"> 填 -1 表示不限制</span>
          </el-form-item>
        </template>

        <h4 class="section">运行</h4>
        <el-form-item label="运行命令" prop="run_command">
          <el-input
            v-model="form.run_command"
            type="textarea"
            :rows="2"
            class="mono"
            placeholder="如 {exe_path} 或 /usr/bin/java -cp {exe_dir} Main"
          />
        </el-form-item>
        <el-form-item label="系统调用白名单">
          <el-select v-model="form.seccomp_rule" class="full">
            <el-option v-for="rule in SECCOMP_RULES" :key="rule.value" :label="rule.label" :value="rule.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="环境变量">
          <el-input v-model="form.env_text" type="textarea" :rows="3" class="mono" placeholder="每行一个，如 LANG=C.UTF-8" />
        </el-form-item>
        <el-form-item label="只按实际内存判断">
          <el-switch v-model="form.memory_limit_check_only" />
          <span class="muted"> 如 Java 预留的虚拟内存很大，开启后只按实际占用判断超内存</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header__title {
  font-size: 16px;
  font-weight: 600;
}

.header__spacer {
  flex: 1;
}

.hint {
  margin: 0 0 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.section {
  margin: 12px 0 8px;
  padding-left: 8px;
  border-left: 3px solid var(--oj-brand-orange);
  font-size: 14px;
}

.mono :deep(textarea),
.mono :deep(input) {
  font-family: Consolas, Menlo, monospace;
}

.full {
  width: 100%;
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
