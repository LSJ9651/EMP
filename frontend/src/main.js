import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import { createPinia } from 'pinia'
import router from './router/index.js'
import App from './App.vue'
import './style.scss'

const app = createApp(App)

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus)
app.use(createPinia())
app.use(router)

// 等待路由首轮导航解析完成后再挂载，避免白屏/闪烁
router.isReady().then(() => {
  app.mount('#app')
})
