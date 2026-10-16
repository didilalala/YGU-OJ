<script setup>
/** 组件与设计令牌预览，只在开发环境（npm run dev）可访问：/dev/ui */
import { ref } from 'vue'

import CodeBlock from '@/components/ui/CodeBlock.vue'
import Countdown from '@/components/ui/Countdown.vue'
import DifficultyBadge from '@/components/ui/DifficultyBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ProgressRing from '@/components/ui/ProgressRing.vue'
import RateBar from '@/components/ui/RateBar.vue'
import SkeletonTable from '@/components/ui/SkeletonTable.vue'
import StatCard from '@/components/ui/StatCard.vue'
import TestcaseGrid from '@/components/ui/TestcaseGrid.vue'
import ThemeToggle from '@/components/layout/ThemeToggle.vue'
import VerdictBadge from '@/components/ui/VerdictBadge.vue'
import { RESULTS } from '@/utils/judge'

const navy = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]
const cases = ['AC', 'AC', 'AC', 'WA', 'TLE', 'MLE', 'RE', 'PAC', 'AC', 'CE'].map((result, i) => ({
  case: i + 1,
  result,
  time: 10 + i * 13,
  memory: 800 + i * 210,
}))
const end = ref(new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString())
const soon = ref(new Date(Date.now() + 5 * 60 * 1000).toISOString())
</script>

<template>
  <div class="oj-container">
    <PageHeader title="UI Kit" subtitle="设计令牌与业务组件预览（仅开发环境）">
      <ThemeToggle />
    </PageHeader>

    <section>
      <h2>品牌色</h2>
      <div class="swatches">
        <div v-for="n in navy" :key="n" class="swatch" :style="{ background: `var(--oj-navy-${n})`, color: n >= 400 ? '#fff' : '#1f2433' }">{{ n }}</div>
        <div class="swatch" style="background: var(--oj-brand-orange); color: #fff">orange</div>
        <div class="swatch" style="background: var(--oj-brand-orange-deep); color: #fff">orange-deep</div>
      </div>
    </section>

    <section>
      <h2>评测状态</h2>
      <div class="row">
        <VerdictBadge v-for="(_, key) in RESULTS" :key="key" :result="key" />
      </div>
      <div class="row"><VerdictBadge v-for="size in ['sm', 'md', 'lg']" :key="size" result="WA" :size="size" /></div>
      <TestcaseGrid :cases="cases" />
    </section>

    <section>
      <h2>难度 / 进度 / 通过率</h2>
      <div class="row">
        <DifficultyBadge difficulty="easy" />
        <DifficultyBadge difficulty="medium" />
        <DifficultyBadge difficulty="hard" />
        <ProgressRing :done="3" :total="5" />
        <ProgressRing :done="5" :total="5" />
        <RateBar :value="62.5" />
        <RateBar :value="null" />
        <Countdown :end="end" />
        <Countdown :end="soon" />
      </div>
    </section>

    <section>
      <h2>统计卡</h2>
      <div class="cards">
        <StatCard accent label="已通过题目" :value="12" unit="/ 80" hint="尝试过 20 题" />
        <StatCard label="通过率" :value="38.5" unit="%" />
        <StatCard label="加载中" loading />
      </div>
    </section>

    <section>
      <h2>代码块 / 空状态 / 骨架屏</h2>
      <div class="cards">
        <CodeBlock title="输入" text="3&#10;1 2 3" />
        <CodeBlock title="编译信息" variant="terminal" text="main.c:4:3: error: expected ';' before 'return'" />
      </div>
      <div class="surface"><EmptyState title="暂无数据" description="这里还没有内容。" /></div>
      <div class="surface"><SkeletonTable :rows="3" /></div>
    </section>
  </div>
</template>

<style scoped>
section {
  margin-bottom: var(--oj-space-6);
}

h2 {
  margin: 0 0 var(--oj-space-3);
  font-size: var(--oj-fs-md);
}

.swatches,
.row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--oj-space-2);
  margin-bottom: var(--oj-space-3);
}

.swatch {
  display: flex;
  align-items: flex-end;
  width: 84px;
  height: 56px;
  padding: 6px 8px;
  border-radius: var(--oj-radius-sm);
  font-size: var(--oj-fs-xs);
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--oj-space-4);
  margin-bottom: var(--oj-space-4);
}
</style>
