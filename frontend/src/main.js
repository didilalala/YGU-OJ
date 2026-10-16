import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'

import './styles/theme.css'
import App from './App.vue'
import router from './router'
import { useSiteStore } from './stores/site'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 先加载网站参数与语言列表，再渲染页面，避免语言名称闪烁
useSiteStore().load().finally(() => app.mount('#app'))
