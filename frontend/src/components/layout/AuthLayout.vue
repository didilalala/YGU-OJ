<script setup>
/** 登录、注册、改密等页面的分栏布局：左侧品牌区，右侧表单（路由出口） */
import BrandLogo from '@/components/layout/BrandLogo.vue'
import ThemeToggle from '@/components/layout/ThemeToggle.vue'
import { useSiteStore } from '@/stores/site'

const site = useSiteStore()
</script>

<template>
  <div class="auth">
    <aside class="auth__brand">
      <BrandLogo light />
      <div class="auth__pitch">
        <h1>{{ site.settings.site_name }}</h1>
        <p>写代码，提交，立刻看到结果。作业、考试与成绩，都在这里。</p>
        <pre class="auth__code" aria-hidden="true"><span class="k">int</span> main() {
    <span class="k">int</span> a, b;
    scanf(<span class="s">"%d %d"</span>, &amp;a, &amp;b);
    printf(<span class="s">"%d\n"</span>, a + b);
    <span class="k">return</span> <span class="n">0</span>;
}</pre>
        <ul class="auth__langs">
          <li v-for="lang in site.languages" :key="lang.key">{{ lang.name }}</li>
        </ul>
      </div>
      <small>YGU Online Judge</small>
    </aside>

    <section class="auth__main">
      <div class="auth__tools"><ThemeToggle /></div>
      <div class="auth__panel">
        <BrandLogo class="auth__mobile-logo" />
        <router-view />
      </div>
    </section>
  </div>
</template>

<style scoped>
.auth {
  display: grid;
  grid-template-columns: minmax(0, 5fr) minmax(0, 6fr);
  min-height: 100vh;
}

.auth__brand {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 40px 48px;
  overflow: hidden;
  background:
    radial-gradient(circle at 85% 12%, rgba(236, 106, 12, 0.22), transparent 38%),
    linear-gradient(160deg, var(--oj-navy-700), var(--oj-navy-900));
  color: #fff;
}

.auth__brand small {
  color: rgba(255, 255, 255, 0.55);
}

.auth__pitch h1 {
  margin: 0 0 12px;
  color: #fff;
  font-size: 30px;
  letter-spacing: -0.01em;
}

.auth__pitch p {
  max-width: 360px;
  margin: 0 0 28px;
  color: rgba(255, 255, 255, 0.78);
  font-size: var(--oj-fs-md);
}

.auth__code {
  max-width: 380px;
  margin: 0 0 20px;
  padding: 18px 20px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--oj-radius-md);
  background: rgba(0, 0, 0, 0.25);
  color: #d5d9ee;
  font-size: 13px;
  line-height: 1.7;
}

.auth__code .k {
  color: #f2a468;
}

.auth__code .s {
  color: #8fd6a9;
}

.auth__code .n {
  color: #9db4ff;
}

.auth__langs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.auth__langs li {
  padding: 2px 12px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: var(--oj-radius-pill);
  font-size: var(--oj-fs-sm);
}

.auth__main {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  background: var(--oj-bg);
}

.auth__tools {
  position: absolute;
  top: 16px;
  right: 16px;
}

.auth__panel {
  width: 100%;
  max-width: 400px;
}

.auth__mobile-logo {
  display: none;
  margin-bottom: 32px;
}

@media (max-width: 900px) {
  .auth {
    display: block;
  }

  .auth__brand {
    display: none;
  }

  .auth__main {
    min-height: 100vh;
    align-items: flex-start;
    padding-top: 72px;
  }

  .auth__mobile-logo {
    display: inline-flex;
  }
}
</style>
