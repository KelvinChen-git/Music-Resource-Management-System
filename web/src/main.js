import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useUserStore } from './stores/user'

// 先导入Element Plus的基本样式
import 'element-plus/dist/index.css'
// 然后导入Element Plus的暗色主题变量
import 'element-plus/theme-chalk/dark/css-vars.css'
// 最后导入自定义暗色主题样式覆盖
import './styles/dark-theme.css'

// 创建 Pinia 实例
const pinia = createPinia()

// 创建应用实例
const app = createApp(App)

app.use(pinia)

// 检查用户会话
const userStore = useUserStore(pinia)
userStore.checkSession()

app.use(router)
app.mount('#app')