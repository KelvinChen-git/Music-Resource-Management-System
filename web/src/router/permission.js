import router from './index'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

// 白名单路由
const whiteList = ['/login', '/register', '/404', '/403']

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  
  // 获取token
  const hasToken = userStore.token
  
  if (hasToken) {
    if (to.path === '/login') {
      // 如果已登录，重定向到首页
      next({ path: '/' })
    } else {
      // 判断是否已获取用户信息
      const hasUserInfo = userStore.userInfo && Object.keys(userStore.userInfo).length > 0
      
      if (hasUserInfo) {
        next()
      } else {
        try {
          // 获取用户信息
          await userStore.getUserInfo()
          next()
        } catch (error) {
          // 获取用户信息失败，可能是token过期
          await userStore.logout()
          ElMessage.error(error.message || '获取用户信息失败')
          next(`/login?redirect=${to.path}`)
        }
      }
    }
  } else {
    // 没有token
    if (whiteList.includes(to.path)) {
      // 在白名单中，直接进入
      next()
    } else {
      // 其他没有访问权限的页面将重定向到登录页面
      next(`/login?redirect=${to.path}`)
    }
  }
})

router.afterEach(() => {
  // 路由切换后的操作，如关闭loading等
}) 