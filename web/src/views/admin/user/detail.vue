<template>
  <div class="user-detail">
    <div class="page-header">
      <h1>User Details</h1>
      <div>
        <el-button @click="goBack">Back</el-button>
        <el-button type="primary" @click="handleEdit">Edit</el-button>
      </div>
    </div>

    <el-card v-loading="loading">
      <template v-if="userDetail">
        <el-descriptions title="Basic Information" :column="2" border>
          <el-descriptions-item label="User ID">{{ userDetail.userid }}</el-descriptions-item>
          <el-descriptions-item label="Username">{{ userDetail.name }}</el-descriptions-item>
          <el-descriptions-item label="Email">{{ userDetail.email }}</el-descriptions-item>
          <el-descriptions-item label="Role">
            <el-tag :type="userDetail.role === 'ADMIN' ? 'danger' : 'primary'">
              {{ userDetail.role === 'ADMIN' ? 'Admin' : 'User' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Registration Time">{{ formatDateTime(userDetail.createdAt) }}</el-descriptions-item>
          <el-descriptions-item label="Last Updated">{{ formatDateTime(userDetail.updatedAt) }}</el-descriptions-item>
        </el-descriptions>

        <el-divider />

        <el-descriptions title="Account Status" :column="2" border>
          <el-descriptions-item label="Verification Status">
            <el-tag :type="userDetail.verificationStatus ? 'success' : 'info'">
              {{ userDetail.verificationStatus ? 'Verified' : 'Unverified' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Account Status">
            <el-tag :type="userDetail.isLocked ? 'danger' : 'success'">
              {{ userDetail.isLocked ? 'Locked' : 'Active' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="userDetail.isLocked">
          <el-divider />
          <el-descriptions title="Lock Information" :column="1" border>
            <el-descriptions-item label="Lock Reason">{{ userDetail.lockReason || 'None' }}</el-descriptions-item>
            <el-descriptions-item label="Lock Time">{{ formatDateTime(userDetail.lockTime) }}</el-descriptions-item>
            <el-descriptions-item label="Unlock Time" v-if="userDetail.unlockTime">{{ formatDateTime(userDetail.unlockTime) }}</el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="action-buttons">
          <el-button 
            :type="userDetail.isLocked ? 'success' : 'danger'"
            @click="userDetail.isLocked ? handleUnlock() : handleLock()"
          >{{ userDetail.isLocked ? 'Unlock Account' : 'Lock Account' }}</el-button>
          <el-button type="warning" @click="handleResetPassword">Reset Password</el-button>
          <el-button type="danger" @click="handleDelete">Delete User</el-button>
        </div>
      </template>
    </el-card>

    <!-- Lock User Dialog -->
    <el-dialog
      title="Lock User"
      v-model="lockDialogVisible"
      width="40%"
      :close-on-click-modal="false"
      :before-close="handleLockDialogClose"
    >
      <el-form :model="lockForm" label-width="100px" :rules="lockRules" ref="lockFormRef">
        <el-form-item label="Reason" prop="reason">
          <el-input 
            v-model="lockForm.reason" 
            type="textarea" 
            rows="3" 
            placeholder="Please enter reason for locking the user"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleLockDialogClose">Cancel</el-button>
          <el-button type="primary" @click="confirmLockUser">Confirm Lock</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Edit User Dialog -->
    <el-dialog
      title="Edit User"
      v-model="editDialogVisible"
      width="40%"
      :close-on-click-modal="false"
      :before-close="handleEditDialogClose"
    >
      <el-form :model="editForm" label-width="100px" :rules="editRules" ref="editFormRef">
        <el-form-item label="Username" prop="name">
          <el-input v-model="editForm.name" placeholder="Please enter username" />
        </el-form-item>
        <el-form-item label="Email" prop="email">
          <el-input v-model="editForm.email" placeholder="Please enter email" />
        </el-form-item>
        <el-form-item label="Role" prop="role">
          <el-select v-model="editForm.role" placeholder="Please select role">
            <el-option label="User" value="USER" />
            <el-option label="Admin" value="ADMIN" />
          </el-select>
        </el-form-item>
        <el-form-item label="Verification">
          <el-switch
            v-model="editForm.verificationStatus"
            :active-value="true"
            :inactive-value="false"
            active-text="Verified"
            inactive-text="Unverified"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleEditDialogClose">Cancel</el-button>
          <el-button type="primary" @click="confirmEditUser">Save Changes</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Reset Password Dialog -->
    <el-dialog
      title="Reset Password"
      v-model="resetPasswordDialogVisible"
      width="40%"
      :close-on-click-modal="false"
      :before-close="handleResetPasswordDialogClose"
    >
      <el-form :model="resetPasswordForm" label-width="100px" :rules="resetPasswordRules" ref="resetPasswordFormRef">
        <el-form-item label="New Password" prop="newPassword">
          <el-input 
            v-model="resetPasswordForm.newPassword" 
            type="password" 
            placeholder="Please enter new password"
            show-password
          />
        </el-form-item>
        <el-form-item label="Confirm Password" prop="confirmPassword">
          <el-input 
            v-model="resetPasswordForm.confirmPassword" 
            type="password" 
            placeholder="Please confirm new password"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleResetPasswordDialogClose">Cancel</el-button>
          <el-button type="primary" @click="confirmResetPassword">Confirm Reset</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  getUserDetail, 
  lockUserWithReason, 
  unlockUser, 
  resetUserPassword,
  updateUser,
  deleteUser
} from '@/api/user'

export default {
  name: 'UserDetail',
  setup() {
    const route = useRoute()
    const router = useRouter()
    
    const loading = ref(false)
    const userDetail = ref(null)
    const userId = ref(route.params.id)

    // Lock form
    const lockDialogVisible = ref(false)
    const lockForm = reactive({
      reason: ''
    })
    const lockFormRef = ref(null)
    const lockRules = {
      reason: [
        { required: true, message: 'Please enter lock reason', trigger: 'blur' },
        { min: 2, max: 200, message: 'Length should be 2 to 200 characters', trigger: 'blur' }
      ]
    }

    // Edit form
    const editDialogVisible = ref(false)
    const editForm = reactive({
      userid: null,
      name: '',
      email: '',
      role: '',
      verificationStatus: false
    })
    const editFormRef = ref(null)
    const editRules = {
      name: [
        { required: true, message: 'Please enter username', trigger: 'blur' },
        { min: 2, max: 20, message: 'Length should be 2 to 20 characters', trigger: 'blur' }
      ],
      email: [
        { required: true, message: 'Please enter email', trigger: 'blur' },
        { type: 'email', message: 'Please enter valid email format', trigger: 'blur' }
      ],
      role: [
        { required: true, message: 'Please select role', trigger: 'change' }
      ]
    }

    // Reset password form
    const resetPasswordDialogVisible = ref(false)
    const resetPasswordForm = reactive({
      newPassword: '',
      confirmPassword: ''
    })
    const resetPasswordFormRef = ref(null)
    const resetPasswordRules = {
      newPassword: [
        { required: true, message: 'Please enter new password', trigger: 'blur' },
        { min: 6, max: 20, message: 'Length should be 6 to 20 characters', trigger: 'blur' }
      ],
      confirmPassword: [
        { required: true, message: 'Please confirm new password', trigger: 'blur' },
        { 
          validator: (rule, value, callback) => {
            if (value !== resetPasswordForm.newPassword) {
              callback(new Error('The two passwords do not match'))
            } else {
              callback()
            }
          }, 
          trigger: 'blur' 
        }
      ]
    }

    // Get user details
    const fetchUserDetail = async () => {
      loading.value = true
      try {
        const response = await getUserDetail(userId.value)
        if (response.code === 200) {
          userDetail.value = response.data
        } else {
          ElMessage.error(response.message || 'Failed to get user details')
        }
      } catch (error) {
        ElMessage.error('Failed to get user details: ' + error.message)
      } finally {
        loading.value = false
      }
    }

    // Go back to previous page
    const goBack = () => {
      router.back()
    }

    // Edit user
    const handleEdit = () => {
      // Copy user details to edit form for display
      if (userDetail.value) {
        editForm.userid = userDetail.value.userid
        editForm.name = userDetail.value.name
        editForm.email = userDetail.value.email 
        editForm.role = userDetail.value.role
        editForm.verificationStatus = userDetail.value.verificationStatus

        // Show edit dialog
        editDialogVisible.value = true
      }
    }

    // Close edit dialog
    const handleEditDialogClose = () => {
      editDialogVisible.value = false
      if (editFormRef.value) {
        editFormRef.value.resetFields()
      }
    }

    // Save edited user
    const confirmEditUser = async () => {
      if (!editFormRef.value) return
      
      editFormRef.value.validate(async (valid) => {
        if (valid) {
          try {
            // Create update object, excluding userid
            const { userid, ...updateData } = editForm

            const response = await updateUser(userid, updateData)
            if (response.code === 200) {
              ElMessage.success('User updated successfully')
              handleEditDialogClose()
              // Refresh user details to show the changes
              fetchUserDetail()
            } else {
              ElMessage.error(response.message || 'Failed to update user')
            }
          } catch (error) {
            ElMessage.error('Failed to update user: ' + error.message)
          }
        } else {
          ElMessage.warning('Please complete the form correctly')
          return false
        }
      })
    }

    // Lock user dialog
    const handleLock = () => {
      lockForm.reason = ''
      lockDialogVisible.value = true
    }

    // Close lock dialog
    const handleLockDialogClose = () => {
      lockDialogVisible.value = false
      if (lockFormRef.value) {
        lockFormRef.value.resetFields()
      }
    }

    // Confirm lock user
    const confirmLockUser = async () => {
      if (!lockFormRef.value) return
      
      lockFormRef.value.validate(async (valid) => {
        if (valid) {
          try {
            const response = await lockUserWithReason(userId.value, lockForm.reason)
            if (response.code === 200) {
              ElMessage.success('User locked successfully')
              handleLockDialogClose()
              fetchUserDetail()
            } else {
              ElMessage.error(response.message || 'Failed to lock user')
            }
          } catch (error) {
            ElMessage.error('Failed to lock user: ' + error.message)
          }
        } else {
          ElMessage.warning('Please complete the form correctly')
          return false
        }
      })
    }

    // Unlock user
    const handleUnlock = async () => {
      try {
        await ElMessageBox.confirm('Are you sure you want to unlock this user?', 'Confirm', {
          confirmButtonText: 'Confirm',
          cancelButtonText: 'Cancel',
          type: 'warning'
        })
        
        const response = await unlockUser(userId.value)
        if (response.code === 200) {
          ElMessage.success('User unlocked successfully')
          fetchUserDetail()
        } else {
          ElMessage.error(response.message || 'Failed to unlock user')
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('Failed to unlock user: ' + error.message)
        }
      }
    }

    // Reset password dialog
    const handleResetPassword = () => {
      resetPasswordForm.newPassword = ''
      resetPasswordForm.confirmPassword = ''
      resetPasswordDialogVisible.value = true
    }

    // Close reset password dialog
    const handleResetPasswordDialogClose = () => {
      resetPasswordDialogVisible.value = false
      if (resetPasswordFormRef.value) {
        resetPasswordFormRef.value.resetFields()
      }
    }

    // Confirm reset password
    const confirmResetPassword = async () => {
      if (!resetPasswordFormRef.value) return

      resetPasswordFormRef.value.validate(async (valid) => {
        if (valid) {
          try {
            const response = await resetUserPassword(userId.value, resetPasswordForm.newPassword)
            if (response.code === 200) {
              ElMessage.success('Password reset successfully')
              handleResetPasswordDialogClose()
            } else {
              ElMessage.error(response.message || 'Failed to reset password')
            }
          } catch (error) {
            ElMessage.error('Failed to reset password: ' + error.message)
          }
        } else {
          ElMessage.warning('Please complete the form correctly')
          return false
        }
      })
    }

    // Delete user
    const handleDelete = async () => {
      try {
        await ElMessageBox.confirm('Are you sure you want to delete this user? This operation cannot be undone!', 'Warning', {
          confirmButtonText: 'Confirm',
          cancelButtonText: 'Cancel',
          type: 'warning'
        })
        
        const response = await deleteUser(userId.value)
        if (response.code === 200) {
          ElMessage.success('User deleted successfully')
          router.push('/admin/users')
        } else {
          ElMessage.error(response.message || 'Failed to delete user')
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('Failed to delete user: ' + error.message)
        }
      }
    }

    // Format date time
    const formatDateTime = (dateTime) => {
      if (!dateTime) return 'None'
      const date = new Date(dateTime)
      return date.toLocaleString()
    }

    onMounted(() => {
      fetchUserDetail()
    })

    return {
      loading,
      userDetail,
      goBack,
      handleEdit,
      
      editDialogVisible,
      editForm,
      editRules,
      editFormRef,
      handleEditDialogClose,
      confirmEditUser,
      
      lockDialogVisible,
      lockForm,
      lockRules,
      lockFormRef,
      handleLock,
      handleLockDialogClose,
      confirmLockUser,
      handleUnlock,
      
      resetPasswordDialogVisible,
      resetPasswordForm,
      resetPasswordRules,
      resetPasswordFormRef,
      handleResetPassword,
      handleResetPasswordDialogClose,
      confirmResetPassword,
      
      handleDelete,
      
      formatDateTime
    }
  }
}
</script>

<style scoped>
.user-detail {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.el-divider {
  margin: 24px 0;
}

.action-buttons {
  margin-top: 30px;
  display: flex;
  justify-content: center;
  gap: 20px;
}
</style> 