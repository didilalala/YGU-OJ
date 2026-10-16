<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { judgeServerApi } from '@/api/judgeServer'
import PageHeader from '@/components/ui/PageHeader.vue'

// 判题服务器每 5 秒上报一次心跳，页面按同样频率刷新
const REFRESH_INTERVAL = 5000

const servers = ref([])
const loading = ref(true)
const now = ref(Date.now())
let timer = null

async function load() {
  try {
    servers.value = await judgeServerApi.list({ silent: servers.value.length > 0 })
    now.value = Date.now()
  } catch {
    // 首次加载失败已弹出提示；自动刷新失败时保留上次数据
  } finally {
    loading.value = false
  }
}

function statusOf(server) {
  if (!server.is_enabled) return { text: '已停用', type: 'info' }
  if (!server.is_alive) return { text: '心跳异常', type: 'danger' }
  return { text: '正常', type: 'success' }
}

function heartbeatAgo(time) {
  const seconds = Math.max(0, Math.round((now.value - new Date(time).getTime()) / 1000))
  if (seconds < 60) return `${seconds} 秒前`
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`
  return new Date(time).toLocaleString('zh-CN')
}

async function toggle(server, isEnabled) {
  try {
    await judgeServerApi.setEnabled(server.id, isEnabled)
    server.is_enabled = isEnabled
    ElMessage.success(isEnabled ? '已启用' : '已停用，不再分配新的评测任务')
  } catch {
    // 错误提示已由请求拦截器弹出
  }
}

async function remove(server) {
  const hint = server.is_alive ? '该服务器仍在发送心跳，删除后会在下次心跳时重新注册。' : ''
  try {
    await ElMessageBox.confirm(`${hint}确定删除 ${server.hostname}（${server.url}）吗？`, '删除判题服务器', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await judgeServerApi.remove(server.id)
    ElMessage.success('已删除')
    load()
  } catch {
    // 错误提示已由请求拦截器弹出
  }
}

onMounted(() => {
  load()
  timer = setInterval(load, REFRESH_INTERVAL)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <div>
    <PageHeader title="判题服务器" subtitle="页面每 5 秒刷新一次状态，服务器启动后会自动注册" />
    <el-card shadow="never">
      <el-table v-loading="loading" :data="servers" empty-text="暂无判题服务器，启动 judge-server 后会自动注册">
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusOf(row).type">{{ statusOf(row).text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="主机名 / 地址" min-width="200">
          <template #default="{ row }">
            <div>{{ row.hostname }}</div>
            <div class="muted">{{ row.url }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP" width="130" />
        <el-table-column prop="judger_version" label="Judger" width="90" />
        <el-table-column label="任务数" width="90">
          <template #default="{ row }">{{ row.task_count }} / {{ row.max_task_count }}</template>
        </el-table-column>
        <el-table-column label="CPU" width="120">
          <template #default="{ row }">{{ row.cpu_core }} 核 · {{ row.cpu_usage.toFixed(0) }}%</template>
        </el-table-column>
        <el-table-column label="内存" width="80">
          <template #default="{ row }">{{ row.memory_usage.toFixed(0) }}%</template>
        </el-table-column>
        <el-table-column label="最近心跳" width="120">
          <template #default="{ row }">{{ heartbeatAgo(row.last_heartbeat) }}</template>
        </el-table-column>
        <el-table-column label="启用" width="80">
          <template #default="{ row }">
            <el-switch :model-value="row.is_enabled" @change="(value) => toggle(row, value)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
