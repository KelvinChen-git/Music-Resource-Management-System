<template>
  <div class="register-container">
    <div class="register-card">
      <h2 class="page-title">Register Account</h2>
      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        label-width="0"
        size="large"
      >
        <el-form-item prop="name">
          <el-input
            v-model="registerForm.name"
            placeholder="Enter your username"
            prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="email">
          <el-input
            v-model="registerForm.email"
            placeholder="Enter your email"
            prefix-icon="Message"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="Enter your password"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="Confirm your password"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            class="register-button"
            @click="handleRegister"
          >
            {{ loading ? 'Registering...' : 'Register' }}
          </el-button>
        </el-form-item>
        <div class="register-options">
          <span>Already have an account?</span>
          <el-link type="primary" @click="$router.push('/login')">
            Login now
          </el-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { User, Message, Lock } from '@element-plus/icons-vue'
import { validatePassword } from '@/utils/passwordValidator'

const router = useRouter()
const userStore = useUserStore()
const registerFormRef = ref(null)
const loading = ref(false)

// 注册表单数据
const registerForm = reactive({
  name: '',
  email: '',
  password: '',
  confirmPassword: ''
})

// 表单验证规则
const registerRules = {
  name: [
    { required: true, message: 'Please enter your username', trigger: 'blur' },
    { min: 3, max: 20, message: 'Length should be 3 to 20 characters', trigger: 'blur' }
  ],
  email: [
    { required: true, message: 'Please enter your email', trigger: 'blur' },
    { type: 'email', message: 'Please enter a valid email address', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please enter your password', trigger: 'blur' },
    { validator: validatePassword, trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: 'Please confirm your password', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value === '') {
          callback(new Error('Please confirm your password'))
        } else if (value !== registerForm.password) {
          callback(new Error('Passwords do not match'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 处理注册
const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  try {
    // 表单验证
    await registerFormRef.value.validate()
    
    loading.value = true
    // 调用注册接口
    const { confirmPassword, ...registerData } = registerForm
    await userStore.registerAction(registerData)
    
    ElMessage.success('Registration successful. Please login.')
    // 注册成功后跳转到登录页
    router.push('/login')
  } catch (error) {
    ElMessage.error(error.message || 'Registration failed. Please try again.')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
  background-color: #121212;
}

.register-card {
  width: 100%;
  max-width: 400px;
  background-color: #1e1e1e;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
  padding: 30px;
  transition: all 0.3s ease;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 30px;
  text-align: center;
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

.register-button {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 500;
  letter-spacing: 1px;
  background: linear-gradient(90deg, #ff416c, #ff4b2b);
  border: none;
  transition: all 0.3s ease;
}

.register-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 65, 108, 0.3);
}

.register-options {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 20px;
  gap: 8px;
}

.register-options span {
  color: #909399;
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

/* 响应式设计 */
@media (max-width: 768px) {
  .register-card {
    padding: 20px;
  }
  
  .page-title {
    font-size: 24px;
  }
}
</style> 