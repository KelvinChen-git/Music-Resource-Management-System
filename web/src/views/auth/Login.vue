<template>
  <div class="login-container">
    <div class="login-card">
      <h2 class="page-title">Login</h2>
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        label-width="0"
        size="large"
      >
        <el-form-item prop="email">
          <el-input
            v-model="loginForm.email"
            placeholder="Enter your email"
            prefix-icon="Message"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="Enter your password"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="loginForm.rememberMe">Remember Me</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            class="login-button"
            @click="handleLogin"
          >
            {{ loading ? 'Logging in...' : 'Login' }}
          </el-button>
        </el-form-item>
        <div class="login-options">
          <el-link type="primary" @click="$router.push('/register')">
            Register
          </el-link>
          <router-link to="/forgot-password" class="el-link el-link--primary">Forgot Password?</router-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { Message, Lock } from '@element-plus/icons-vue'
import { validatePassword } from '@/utils/passwordValidator'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const loginFormRef = ref(null)
const loading = ref(false)

// 登录表单数据
const loginForm = reactive({
  email: '',
  password: '',
  rememberMe: false
})

// 表单验证规则
const loginRules = {
  email: [
    { required: true, message: 'Please enter your email', trigger: 'blur' },
    { type: 'email', message: 'Please enter a valid email address', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please enter your password', trigger: 'blur' },
    { validator: validatePassword, trigger: 'blur' }
  ]
}

// 处理登录
const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  try {
    // 表单验证
    await loginFormRef.value.validate()
    
    loading.value = true
    // 调用登录接口
    const response = await userStore.loginAction(loginForm)
    
    if (response.code === 200) {
      ElMessage.success('Login successful')
      // 获取重定向地址
      const redirect = route.query.redirect || '/'
      router.push(redirect)
    }
  } catch (error) {
    ElMessage.error(error.message || 'Login failed, please try again')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
  background-color: #121212;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background-color: #1e1e1e;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  padding: 30px;
  transition: all 0.3s ease;
}

.page-title {
  margin-bottom: 30px;
  text-align: center;
  color: #ffffff;
  font-size: 24px;
  font-weight: 600;
  position: relative;
}

.page-title::after {
  content: "";
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 3px;
  background: linear-gradient(90deg, #ff416c, #ff4b2b);
  border-radius: 3px;
}

.login-button {
  width: 100%;
  margin-top: 10px;
  height: 44px;
  font-size: 16px;
  font-weight: 500;
  letter-spacing: 1px;
  background: linear-gradient(90deg, #ff416c, #ff4b2b);
  border: none;
  transition: all 0.3s ease;
}

.login-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 65, 108, 0.3);
}

.login-options {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
}

:deep(.el-input__wrapper) {
  background-color: #2d2d2d !important;
  box-shadow: none !important;
  border: 1px solid #4a4a4a;
}

:deep(.el-input__wrapper:hover) {
  border-color: #ff416c;
}

:deep(.el-input__inner) {
  color: #ffffff !important;
}

:deep(.el-input__prefix-icon) {
  color: #909399;
}

:deep(.el-input__inner::placeholder) {
  color: #666666;
}

:deep(.el-link) {
  color: #ff416c !important;
  font-size: 14px;
  transition: all 0.3s ease;
}

:deep(.el-link:hover) {
  color: #ff4b2b !important;
  transform: translateY(-1px);
}
</style> 