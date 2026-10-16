<script setup>
/** 班级统计：各次作业与考试的趋势、学生排名、成绩单导出。 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'

import { adminClassApi } from '@/api/classroom'
import { statsApi } from '@/api/stats'
import KnowledgeMastery from '@/components/admin/KnowledgeMastery.vue'
import EChart from '@/components/EChart.vue'
import { formatScore } from '@/utils/assignment'
import { INK, TREND_COLORS, baseOption, categoryAxis, lineSeries, shortLabel, valueAxis } from '@/utils/chart'
import { saveBlob } from '@/utils/download'
import { formatDateTime } from '@/utils/judge'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()

const classes = ref([])
const loading = ref(false)
const exporting = ref(false)
const data = ref(null)
const trendTable = ref(false)
const classId = computed(() => (route.query.class_id ? Number(route.query.class_id) : null))

async function load() {
  if (!classId.value) {
    data.value = null
    return
  }
  loading.value = true
  try {
    data.value = await statsApi.classOverview(classId.value)
    document.title = `${data.value.class_name} 统计 - YGU OJ`
  } catch {
    data.value = null
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  classes.value = (await adminClassApi.list({ page_size: 100 })).results
  // 未指定班级时默认第一个
  if (!classId.value && classes.value.length) router.replace({ query: { class_id: classes.value[0].id } })
})
watch(classId, load, { immediate: true })

const workLabel = (work) => `${work.kind === 'exam' ? '考试' : '作业'}：${work.title}`

const trendOption = computed(() => {
  const works = data.value.works
  return {
    ...baseOption(),
    grid: { ...baseOption().grid, top: 40 },
    legend: { top: 0, itemWidth: 16, itemHeight: 8, textStyle: { color: INK.secondary } },
    tooltip: {
      ...baseOption().tooltip,
      trigger: 'axis',
      axisPointer: { type: 'line', lineStyle: { color: INK.axis } },
      formatter: (items) =>
        `${workLabel(works[items[0].dataIndex])}<br/>` +
        items.map((item) => `${item.marker}${item.seriesName} <b>${item.value}%</b>`).join('<br/>'),
    },
    xAxis: categoryAxis(works.map((w) => shortLabel(w.title)), { boundaryGap: false }),
    yAxis: valueAxis({ max: 100, axisLabel: { color: INK.muted, formatter: '{value}%' } }),
    series: [
      lineSeries(TREND_COLORS[0], {
        name: '平均得分率',
        data: works.map((w) => w.average_rate),
        // 只在最后一个点标注数值
        endLabel: { show: true, color: INK.secondary, formatter: '{c}%' },
      }),
      lineSeries(TREND_COLORS[1], { name: '提交率', data: works.map((w) => w.submission_rate) }),
    ],
  }
})

function openWork(work) {
  router.push({ name: work.kind === 'exam' ? 'admin-exam-stats' : 'admin-assignment-stats', params: { id: work.id } })
}

async function exportScores() {
  exporting.value = true
  try {
    const blob = await statsApi.exportClass(classId.value)
    const date = new Date().toISOString().slice(0, 10).replaceAll('-', '')
    saveBlob(blob, `${data.value.class_name}成绩单_${date}.xlsx`)
  } catch {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <div v-loading="loading" class="stats-page">
    <PageHeader title="成绩统计" subtitle="按班级查看每次作业与考试的得分、提交率和学生排名">
      <el-select
        :model-value="classId"
        placeholder="选择班级"
        class="header__class"
        @update:model-value="(v) => router.replace({ query: { class_id: v } })"
      >
        <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
      <el-button type="primary" :icon="Download" :loading="exporting" :disabled="!data" @click="exportScores">
        导出成绩单
      </el-button>
    </PageHeader>
    <el-card shadow="never">
      <el-empty v-if="!loading && !classes.length" description="还没有班级" />

      <div v-if="data" class="tiles">
        <div class="tile">
          <div class="tile__label">在班学生</div>
          <div class="tile__value">{{ data.summary.member_count }}</div>
        </div>
        <div class="tile">
          <div class="tile__label">作业 / 考试</div>
          <div class="tile__value">{{ data.summary.assignment_count }} / {{ data.summary.exam_count }}</div>
          <div class="tile__sub">已发布且已开始的</div>
        </div>
        <div class="tile">
          <div class="tile__label">班级平均得分率</div>
          <div class="tile__value">{{ data.summary.average_rate }}%</div>
          <div class="tile__sub">各学生总得分率的平均</div>
        </div>
      </div>
    </el-card>

    <template v-if="data && data.works.length">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>各次作业与考试</span>
            <el-switch v-model="trendTable" size="small" active-text="表格" />
          </div>
        </template>
        <el-table v-if="trendTable" :data="data.works" size="small" @row-click="openWork">
          <el-table-column label="名称" min-width="200">
            <template #default="{ row }">{{ workLabel(row) }}</template>
          </el-table-column>
          <el-table-column label="时间" width="170">
            <template #default="{ row }">{{ formatDateTime(row.time) }}</template>
          </el-table-column>
          <el-table-column label="平均得分率" width="110" align="right">
            <template #default="{ row }">{{ row.average_rate }}%</template>
          </el-table-column>
          <el-table-column label="提交率" width="90" align="right">
            <template #default="{ row }">{{ row.submission_rate }}%</template>
          </el-table-column>
        </el-table>
        <template v-else>
          <EChart :option="trendOption" height="280px" label="各次作业与考试的平均得分率和提交率折线图" />
          <div class="works">
            <el-button v-for="work in data.works" :key="`${work.kind}-${work.id}`" size="small" @click="openWork(work)">
              {{ workLabel(work) }}
            </el-button>
          </div>
        </template>
      </el-card>

      <KnowledgeMastery :class-id="classId" />

      <el-card shadow="never">
        <template #header>学生排名（按全部作业与考试的总得分率）</template>
        <el-table :data="data.students" size="small" border max-height="560">
          <el-table-column prop="rank" label="名次" width="64" align="center" fixed />
          <el-table-column prop="student_no" label="学号" width="110" fixed />
          <el-table-column prop="real_name" label="姓名" width="80" fixed />
          <el-table-column label="得分率" width="80" align="right" fixed>
            <template #default="{ row }"><strong>{{ row.rate }}%</strong></template>
          </el-table-column>
          <el-table-column label="总分" width="100" align="right">
            <template #default="{ row }">{{ formatScore(row.total_score) }} / {{ row.full_score }}</template>
          </el-table-column>
          <el-table-column
            v-for="work in data.works"
            :key="`${work.kind}-${work.id}`"
            :label="shortLabel(work.title, 10)"
            min-width="96"
            align="right"
          >
            <template #header>
              <span :title="workLabel(work)">{{ shortLabel(work.title, 10) }}</span>
            </template>
            <template #default="{ row }">
              <span v-if="row.scores[`${work.kind}:${work.id}`] === null" class="missing">未提交</span>
              <span v-else>{{ formatScore(row.scores[`${work.kind}:${work.id}`]) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
    <el-card v-else-if="data" shadow="never">
      <el-empty description="该班级还没有已开始的作业或考试" />
    </el-card>
  </div>
</template>

<style scoped>
.stats-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 300px;
}



.header__class {
  width: 220px;
}


.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.tile {
  padding: 12px 16px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
}

.tile__label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.tile__value {
  margin-top: 4px;
  font-size: 24px;
  font-weight: 600;
}

.tile__sub {
  margin-top: 2px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.works {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.works .el-button {
  margin-left: 0;
}

.missing {
  color: var(--el-color-danger);
  font-size: 12px;
}
</style>
