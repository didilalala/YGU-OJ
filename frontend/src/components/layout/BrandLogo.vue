<script setup>
defineProps({
  text: { type: String, default: 'Online Judge' },
  light: { type: Boolean, default: false },
})
</script>

<template>
  <router-link to="/" class="logo" :class="{ 'logo--light': light }" aria-label="YGU OJ 首页">
    <span class="logo__mark">YGU</span>
    <span class="logo__text">{{ text }}</span>
  </router-link>
</template>

<style scoped>
.logo {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--oj-text);
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.01em;
  text-decoration: none;
  white-space: nowrap;
}

.logo--light {
  color: #fff;
}

.logo__mark {
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--oj-brand-orange-deep);
  color: #fff;
  font-size: 15px;
  letter-spacing: 0.04em;
}
</style>
