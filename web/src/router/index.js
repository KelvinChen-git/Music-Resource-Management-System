import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
// 导入回收站相关组件
import RecycleBinView from '@/views/RecycleBinView.vue'
import TagListView from '@/views/TagListView.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { title: 'Login' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/Register.vue'),
    meta: { title: 'Register' }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/auth/ForgotPassword.vue'),
    meta: { title: 'Forgot Password' }
  },
  {
    path: '/',
    redirect: '/music'
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true, title: 'Profile' }
  },
  {
    path: '/upload',
    name: 'upload',
    component: () => import('@/views/UploadView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/files',
    name: 'files',
    component: () => import('@/views/FileListView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/music',
    name: 'music',
    component: () => import('@/views/MusicListView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/categories',
    name: 'categories',
    component: () => import('@/views/CategoryListView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/tags',
    name: 'TagList',
    component: TagListView,
    meta: { requiresAuth: true }
  },
  {
    path: '/recyclebin',
    name: 'RecycleBin',
    component: RecycleBinView,
    meta: {
      requiresAuth: true,
      title: '回收站'
    }
  },
  {
    path: '/recyclebin-settings',
    name: 'RecycleBinSettings',
    component: () => import('@/views/RecycleBinSettingsView.vue'),
    meta: {
      requiresAuth: true,
      title: '回收站设置'
    }
  },
  {
    path: '/admin/users',
    name: 'users',
    component: () => import('@/views/admin/user/index.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'User Management' }
  },
  {
    path: '/admin/users/:id',
    name: 'user-detail',
    component: () => import('@/views/admin/user/detail.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'User Details' }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// 白名单路由
const whiteList = ['/login', '/register', '/forgot-password', '/reset-password']

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  const hasToken = userStore.token
  
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - Taffy Music` : 'Taffy Music'
  
  if (hasToken) {
    if (to.path === '/login') {
      // 已登录状态访问登录页，重定向到首页
      next({ path: '/' })
    } else {
      // 已登录，检查用户信息
      const hasUserInfo = Object.keys(userStore.userInfo).length > 0
      if (hasUserInfo) {
        // 检查是否需要管理员权限
        if (to.meta.requiresAdmin && userStore.userInfo.role !== 'ADMIN') {
          next('/music') // 无权限，跳转到音乐页面
        } else {
          next() // 有权限，正常访问
        }
      } else {
        try {
          // 获取用户信息
          await userStore.getUserInfo()
          // 获取成功后再次检查管理员权限
          if (to.meta.requiresAdmin && userStore.userInfo.role !== 'ADMIN') {
            next('/music') // 无权限，跳转到音乐页面
          } else {
            next() // 有权限，正常访问
          }
        } catch (error) {
          // token失效，清除用户信息并重定向到登录页
          await userStore.logoutAction()
          next(`/login?redirect=${to.path}`)
        }
      }
    }
  } else {
    // 未登录
    if (whiteList.includes(to.path)) {
      // 白名单路由直接访问
      next()
    } else {
      // 需要登录的页面重定向到登录页
      next(`/login?redirect=${to.path}`)
    }
  }
})

export default router 