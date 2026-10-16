
<template>
  <div class="status">
    <div class="status__code">403</div>
    <h1>没有权限访问</h1>
    <p>这个页面需要更高的权限，如有疑问请联系老师或管理员。</p>
    <div class="status__actions">
      <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
      <el-button @click="$router.back()">返回上一页</el-button>
    </div>
  </div>
</template>

<style scoped>
.status {
  padding: 80px 16px;
  text-align: center;
}

.status__code {
  color: var(--oj-navy-200);
  font-family: var(--oj-font-mono);
  font-size: 96px;
  font-weight: 600;
  line-height: 1;
}

html.dark .status__code {
  color: var(--oj-navy-500);
}

.status h1 {
  margin: 16px 0 8px;
  font-size: var(--oj-fs-xl);
}

.status p {
  margin: 0 0 24px;
  color: var(--oj-text-3);
}
</style>
