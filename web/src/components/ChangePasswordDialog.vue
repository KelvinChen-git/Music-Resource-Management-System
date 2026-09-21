<template>
  <el-dialog
    title="Change Password"
    v-model="dialogVisible"
    width="500px"
    :before-close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="passwordForm"
      :rules="rules"
      label-width="100px"
      status-icon
    >
      <el-form-item label="Current Password" prop="oldPassword">
        <el-input
          v-model="passwordForm.oldPassword"
          type="password"
          placeholder="Enter your current password"
          show-password
        />
      </el-form-item>
      <el-form-item label="New Password" prop="newPassword">
        <el-input
          v-model="passwordForm.newPassword"
          type="password"
          placeholder="Enter your new password"
          show-password
        />
      </el-form-item>
      <el-form-item label="Confirm New Password" prop="confirmPassword">
        <el-input
          v-model="passwordForm.confirmPassword"
          type="password"
          placeholder="Re-enter your new password"
          show-password
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="dialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="submitForm" :loading="loading">
          Confirm
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, defineEmits, defineProps, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { validatePassword } from '@/utils/passwordValidator'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:visible', 'success'])

const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)
const dialogVisible = ref(props.visible)

// 监听visible属性变化
watch(
  () => props.visible,
  (newValue) => {
    dialogVisible.value = newValue
  }
)

// 监听对话框状态，同步更新父组件的visible属性
watch(
  () => dialogVisible.value,
  (newValue) => {
    emit('update:visible', newValue)
    if (!newValue) {
      resetForm()
    }
  }
)

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const rules = {
  oldPassword: [
    { required: true, message: 'Please enter your current password', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: 'Please enter your new password', trigger: 'blur' },
    { validator: validatePassword, trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: 'Please confirm your new password', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.newPassword) {
          callback(new Error('The two passwords do not match'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const handleClose = (done) => {
  if (loading.value) return
  formRef.value.resetFields()
  done()
}

const resetForm = () => {
  formRef.value?.resetFields()
}

const submitForm = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    loading.value = true
    
    await userStore.changePasswordAction({
      oldPassword: passwordForm.oldPassword,
      newPassword: passwordForm.newPassword,
      confirmPassword: passwordForm.confirmPassword
    })
    
    ElMessage.success('Password changed successfully!')
    dialogVisible.value = false
    emit('success')
  } catch (error) {
    if (error.response && error.response.data && error.response.data.message) {
      ElMessage.error(error.response.data.message)
    } else {
      ElMessage.error('Failed to change password. Please try again.')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style> 