<template>
  <div class="forgot-password-container">
    <el-card class="box-card">
      <template #header>
        <div class="clearfix">
          <h2 v-if="currentStep === 1">Forgot Password</h2>
          <h2 v-else>Reset Password</h2>
          <p v-if="currentStep === 1">Enter your email address to receive a password reset code.</p>
          <p v-else>Enter the code sent to your email and your new password.</p>
        </div>
      </template>
      <el-form 
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="currentStep === 1 ? handleSendCode() : handleResetSubmit()" 
      >
        <!-- Step 1 & 2 -->
        <el-form-item label="Email Address" prop="email">
          <el-input 
            v-model="form.email" 
            placeholder="Enter your registered email" 
            :prefix-icon="Message" 
            :disabled="currentStep === 2" 
            clearable 
          />
        </el-form-item>

        <!-- Step 2 Only -->
        <template v-if="currentStep === 2">
          <el-form-item label="Verification Code" prop="code">
            <el-input 
              v-model="form.code" 
              placeholder="Enter the 6-digit code" 
              :prefix-icon="Key" 
              clearable 
              maxlength="6"
            />
          </el-form-item>

          <el-form-item label="New Password" prop="newPassword">
            <el-input 
              type="password"
              v-model="form.newPassword" 
              placeholder="Enter your new password" 
              :prefix-icon="Lock" 
              show-password
              clearable 
            />
          </el-form-item>

          <el-form-item label="Confirm New Password" prop="confirmPassword">
            <el-input 
              type="password"
              v-model="form.confirmPassword" 
              placeholder="Confirm your new password" 
              :prefix-icon="Lock" 
              show-password
              clearable 
            />
          </el-form-item>
        </template>
        
        <!-- Step 1 Button -->
        <el-form-item v-if="currentStep === 1">
          <el-button 
            type="primary" 
            native-type="submit" 
            :loading="loading"
            style="width: 100%;"
          >
            Send Reset Code
          </el-button>
        </el-form-item>

        <!-- Step 2 Button -->
         <el-form-item v-if="currentStep === 2">
          <el-button 
            type="primary" 
            native-type="submit" 
            :loading="loading"
            style="width: 100%;"
          >
            Reset Password
          </el-button>
        </el-form-item>

        <div class="links">
          <router-link to="/login">Back to Login</router-link>
          <!-- Optionally show link to resend code in step 2 -->
          <span v-if="currentStep === 2" style="margin-left: 10px;">
             | <el-link type="primary" @click="currentStep = 1" :disabled="loading" style="font-size: 14px; vertical-align: baseline;"> Re-enter Email?</el-link>
          </span>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElForm, ElFormItem, ElInput, ElButton, ElCard } from 'element-plus'
import { Message, Key, Lock } from '@element-plus/icons-vue'
import { forgotPassword, resetPassword } from '@/api/auth' // Import both API functions
import { useRouter } from 'vue-router'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const currentStep = ref(1) // 1: Enter email, 2: Enter code & new password

const form = reactive({
  email: '',
  code: '',         // Added
  newPassword: '',  // Added
  confirmPassword: '' // Added
})

// Custom validator for matching passwords
const validatePassConfirm = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('Please confirm your new password'))
  } else if (value !== form.newPassword) {
    callback(new Error("Passwords don't match!"))
  } else {
    callback()
  }
}

const rules = reactive({
  email: [
    { required: true, message: 'Please enter your email address', trigger: 'blur' },
    { type: 'email', message: 'Please enter a valid email address', trigger: ['blur', 'change'] }
  ],
  code: [
    { required: () => currentStep.value === 2, message: 'Please enter the verification code', trigger: 'blur' }, // Only required in step 2
    { len: 6, message: 'Verification code must be 6 digits', trigger: 'blur' }
  ],
  newPassword: [
    { required: () => currentStep.value === 2, message: 'Please enter a new password', trigger: 'blur' }, // Only required in step 2
    { min: 6, max: 20, message: 'Password length must be between 6 and 20 characters', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: () => currentStep.value === 2, message: 'Please confirm your new password', trigger: 'blur' }, // Only required in step 2
    { validator: validatePassConfirm, trigger: 'blur' }
  ]
})

// Step 1: Send Code
const handleSendCode = async () => {
  if (!formRef.value) return
  // Validate only the email field for step 1
  formRef.value.validateField('email', async (isValid) => {
      if (isValid) {
        loading.value = true
        try {
          const response = await forgotPassword({ email: form.email })
          ElMessage.success(response.message || 'Request submitted. If your email exists, you will receive a reset code.');
          // Move to step 2
          currentStep.value = 2;
        } catch (error) {
          console.error("Forgot password error:", error)
          // Error message handled by interceptor
        } finally {
          loading.value = false
        }
      } else {
        console.log('Email validation failed!');
      }
  });
}

// Step 2: Reset Password
const handleResetSubmit = async () => {
  if (!formRef.value) return
  // Validate all fields relevant for step 2
  formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const response = await resetPassword({
          email: form.email,
          code: form.code,
          newPassword: form.newPassword,
          confirmPassword: form.confirmPassword 
        })
        ElMessage.success(response.message || 'Password reset successfully!');
        router.push('/login'); 
      } catch (error) {
        console.error("Reset password error:", error)
        // Error message handled by interceptor
      } finally {
        loading.value = false
      }
    } else {
      console.log('Full form validation failed!')
      return false
    }
  })
}

</script>

<style scoped>
.forgot-password-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh; /* Ensure it takes full viewport height */
  background-color: #121212; /* Match App background */
  padding: 20px;
}

.box-card {
  width: 100%;
  max-width: 400px;
  background-color: #1e1e1e; /* Dark card background */
  border: 1px solid #333;
  color: #fff;
}

.clearfix h2 {
  margin: 0 0 10px 0;
  text-align: center;
}

.clearfix p {
  margin: 0;
  color: #aaa;
  text-align: center;
  font-size: 14px;
}

/* Override default form item label color */
:deep(.el-form-item__label) {
  color: #ccc;
}

/* Style links */
.links {
  margin-top: 15px;
  text-align: center;
  font-size: 14px;
}

.links a {
  color: #ff6b81; /* Match theme color */
  text-decoration: none;
}

.links a:hover {
  text-decoration: underline;
}

/* Ensure button takes full width */
.el-button {
  width: 100%;
}

.links span {
  color: #aaa; /* Match muted text color */
}
</style> 