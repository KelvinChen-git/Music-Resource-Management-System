import { defineStore } from 'pinia'
import { login, register, getProfile, changePassword } from '@/api/auth'
import router from '@/router'

export const useUserStore = defineStore('user', {
  state: () => {
    // Check both localStorage and sessionStorage for token and user info
    const token = localStorage.getItem('token') || sessionStorage.getItem('token') || ''
    let userInfo = {}
    
    try {
      const localUserInfo = localStorage.getItem('userInfo')
      const sessionUserInfo = sessionStorage.getItem('userInfo')
      
      if (localUserInfo) {
        userInfo = JSON.parse(localUserInfo)
      } else if (sessionUserInfo) {
        userInfo = JSON.parse(sessionUserInfo)
      }
    } catch (e) {
      console.error('Error parsing user info:', e)
    }
    
    return {
      token,
      userInfo,
      rememberMe: localStorage.getItem('token') ? true : false
    }
  },

  getters: {
    // 是否已登录
    isLoggedIn: (state) => !!state.token,
    // 获取用户ID
    userId: (state) => state.userInfo.userid || null,
    // 获取用户名
    userName: (state) => state.userInfo.name || '',
    // 获取用户邮箱
    userEmail: (state) => state.userInfo.email || '',
    // 获取用户头像
    userAvatar: (state) => state.userInfo.avatar || '',
    // 获取用户角色
    userRole: (state) => state.userInfo.role || 'USER'
  },

  actions: {
    // 设置token
    setToken(token, rememberMe = false) {
      this.token = token
      this.rememberMe = rememberMe
      
      if (rememberMe) {
        localStorage.setItem('token', token)
      } else {
        sessionStorage.setItem('token', token)
        // Clear localStorage to avoid confusion
        localStorage.removeItem('token')
      }
    },

    // 设置用户信息
    setUserInfo(info, rememberMe = false) {
      this.userInfo = info
      
      if (rememberMe) {
        localStorage.setItem('userInfo', JSON.stringify(info))
      } else {
        sessionStorage.setItem('userInfo', JSON.stringify(info))
        // Clear localStorage to avoid confusion
        localStorage.removeItem('userInfo')
      }
    },

    // 清除用户状态
    clearUserState() {
      this.token = ''
      this.userInfo = {}
      this.rememberMe = false
      
      // Clear both local and session storage
      localStorage.removeItem('token')
      localStorage.removeItem('userInfo')
      sessionStorage.removeItem('token')
      sessionStorage.removeItem('userInfo')
    },

    // 用户登录
    async loginAction(loginData) {
      try {
        const { email, password, rememberMe } = loginData
        const response = await login({ email, password })
        const { data } = response
        
        // Save token and remember me state
        this.setToken(data.token, rememberMe)
        
        // Get user profile
        await this.getUserInfo(rememberMe)
        
        return response
      } catch (error) {
        this.clearUserState()
        throw error
      }
    },

    // 用户注册
    async registerAction(registerData) {
      try {
        const response = await register(registerData)
        const { data } = response
        this.setUserInfo(data, false) // By default, don't remember for new registration
        return response
      } catch (error) {
        this.clearUserState()
        throw error
      }
    },

    // 获取用户信息
    async getUserInfo(rememberMe = this.rememberMe) {
      try {
        const response = await getProfile()
        const { data } = response
        this.setUserInfo(data, rememberMe)
        return data
      } catch (error) {
        console.error('Failed to get user information:', error)
        throw error
      }
    },

    // 退出登录
    async logoutAction() {
      try {
        // 不再调用服务器退出接口
        // await logout()
        
        // 直接清除用户状态
        this.clearUserState()
        
        // 重定向到登录页
        if (router.currentRoute.value.path !== '/login') {
          router.push('/login')
        }
      } catch (error) {
        console.error('Error during logout:', error)
        this.clearUserState()
        throw error
      }
    },

    // 检查并恢复用户会话
    checkSession() {
      const localToken = localStorage.getItem('token')
      const sessionToken = sessionStorage.getItem('token')
      const localUserInfo = localStorage.getItem('userInfo')
      const sessionUserInfo = sessionStorage.getItem('userInfo')
      
      // Check localStorage first (for remembered sessions)
      if (localToken) {
        this.token = localToken
        this.rememberMe = true
        try {
          if (localUserInfo) {
            this.userInfo = JSON.parse(localUserInfo)
          }
        } catch (e) {
          this.clearUserState()
        }
      } 
      // Then check sessionStorage (for non-remembered sessions)
      else if (sessionToken) {
        this.token = sessionToken
        this.rememberMe = false
        try {
          if (sessionUserInfo) {
            this.userInfo = JSON.parse(sessionUserInfo)
          }
        } catch (e) {
          this.clearUserState()
        }
      }
    },

    // 修改密码
    async changePasswordAction(passwordData) {
      try {
        const response = await changePassword(passwordData)
        return response.data
      } catch (error) {
        console.error('Failed to change password:', error)
        throw error
      }
    }
  }
}) 