<template>
  <div class="user-management">
    <div class="page-header">
      <h1>User Management</h1>
      <el-button type="primary" @click="handleAddUser">Add User</el-button>
    </div>

    <!-- Search Form -->
    <div class="search-container">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="Username">
          <el-input v-model="searchForm.username" placeholder="Search by username" clearable />
        </el-form-item>
        <el-form-item label="Email">
          <el-input v-model="searchForm.email" placeholder="Search by email" clearable />
        </el-form-item>
        <el-form-item label="Role" style="width: 150px;">
          <el-select v-model="searchForm.role" placeholder="All roles" clearable>
            <el-option label="User" value="USER" />
            <el-option label="Admin" value="ADMIN" />
          </el-select>
        </el-form-item>
        <el-form-item label="Status" style="width: 150px;">
          <el-select v-model="searchForm.locked" placeholder="All status" clearable>
            <el-option label="Active" :value="false" />
            <el-option label="Locked" :value="true" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">Search</el-button>
          <el-button @click="resetSearch">Reset</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- User List -->
    <el-table
      v-loading="loading"
      :data="userList"
      border
      style="width: 100%"
    >
      <el-table-column prop="userid" label="ID" width="80" />
      <el-table-column prop="name" label="Username" />
      <el-table-column prop="email" label="Email" />
      <el-table-column prop="role" label="Role" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.role === 'ADMIN' ? 'danger' : 'primary'">
            {{ scope.row.role === 'ADMIN' ? 'Admin' : 'User' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Status" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.isLocked ? 'danger' : 'success'">
            {{ scope.row.isLocked ? 'Locked' : 'Active' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="Registration Time" width="180">
        <template #default="scope">
          {{ formatDateTime(scope.row.createdAt) }}
        </template>
      </el-table-column>
      <el-table-column label="Actions" width="150">
        <template #default="scope">
          <el-dropdown trigger="click">
            <el-button type="primary" size="small">
              Actions<el-icon class="el-icon--right"><arrow-down /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleViewUser(scope.row.userid)">
                  <el-icon><view /></el-icon> View
                </el-dropdown-item>
                <el-dropdown-item @click="handleEditUser(scope.row.userid)">
                  <el-icon><edit /></el-icon> Edit
                </el-dropdown-item>
                <el-dropdown-item @click="handleResetPassword(scope.row.userid)">
                  <el-icon><key /></el-icon> Reset Password
                </el-dropdown-item>
                <el-dropdown-item divided @click="searchMusicByUsername(scope.row)">
                  <el-icon><User /></el-icon> Search Music (Username)
                </el-dropdown-item>
                <el-dropdown-item @click="searchMusicByEmail(scope.row)">
                  <el-icon><Message /></el-icon> Search Music (Email)
                </el-dropdown-item>
                <el-dropdown-item 
                  :class="scope.row.isLocked ? 'text-success' : 'text-danger'"
                  @click="scope.row.isLocked ? handleUnlockUser(scope.row.userid) : handleLockUser(scope.row.userid)"
                >
                  <el-icon>
                    <lock v-if="!scope.row.isLocked" />
                    <unlock v-else />
                  </el-icon>
                  {{ scope.row.isLocked ? 'Unlock' : 'Lock' }}
                </el-dropdown-item>
                <el-dropdown-item divided class="danger-item" @click="handleDeleteUser(scope.row.userid)">
                  <el-icon><delete /></el-icon> Delete
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
    </el-table>

    <!-- Pagination -->
    <div class="pagination-container">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :current-page="currentPage"
        @current-change="handleCurrentChange"
        @size-change="handleSizeChange"
      />
    </div>

    <!-- Add/Edit User Dialog -->
    <el-dialog
      :title="dialogTitle"
      v-model="dialogVisible"
      width="40%"
      :close-on-click-modal="false"
      :before-close="handleDialogClose"
    >
      <el-form :model="userForm" label-width="100px" :rules="rules" ref="userFormRef">
        <el-form-item label="Username" prop="name">
          <el-input v-model="userForm.name" placeholder="Please enter username" />
        </el-form-item>
        <el-form-item label="Email" prop="email">
          <el-input v-model="userForm.email" placeholder="Please enter email" />
        </el-form-item>
        <el-form-item label="Password" prop="password" v-if="isAdd">
          <el-input v-model="userForm.password" type="password" placeholder="Please enter password" show-password />
        </el-form-item>
        <el-form-item label="Role" prop="role">
          <el-select v-model="userForm.role" placeholder="Please select role">
            <el-option label="User" value="USER" />
            <el-option label="Admin" value="ADMIN" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="handleDialogClose">Cancel</el-button>
          <el-button type="primary" @click="submitForm">Confirm</el-button>
        </span>
      </template>
    </el-dialog>

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
            placeholder="Please enter reason for locking"
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
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { 
  getUserList, 
  getUserDetail, 
  createUser, 
  updateUser, 
  deleteUser, 
  lockUser, 
  lockUserWithReason, 
  unlockUser, 
  resetUserPassword 
} from '@/api/user'
import { 
  ArrowDown, 
  View, 
  Edit, 
  Key, 
  Lock, 
  Unlock, 
  Delete,
  Search,
  User,
  Message
} from '@element-plus/icons-vue'

export default {
  name: 'UserManagement',
  components: {
    ArrowDown,
    View,
    Edit,
    Key,
    Lock,
    Unlock,
    Delete,
    Search,
    User,
    Message
  },
  setup() {
    const router = useRouter()
    
    // List data
    const loading = ref(false)
    const userList = ref([])
    const currentPage = ref(1)
    const pageSize = ref(10)
    const total = ref(0)

    // Search form
    const searchForm = reactive({
      username: '',
      email: '',
      role: '',
      locked: null
    })

    // Form data
    const userForm = reactive({
      userid: null,
      name: '',
      email: '',
      password: '',
      role: 'USER'
    })
    const userFormRef = ref(null)
    
    const dialogVisible = ref(false)
    const isAdd = ref(true)
    const dialogTitle = computed(() => isAdd.value ? 'Add User' : 'Edit User')
    
    // Lock form
    const lockDialogVisible = ref(false)
    const currentUserId = ref(null)
    const lockForm = reactive({
      reason: ''
    })
    const lockFormRef = ref(null)

    // Reset password form
    const resetPasswordDialogVisible = ref(false)
    const resetPasswordForm = reactive({
      newPassword: '',
      confirmPassword: ''
    })
    const resetPasswordFormRef = ref(null)

    // Validation rules
    const rules = {
      name: [
        { required: true, message: 'Please enter username', trigger: 'blur' },
        { min: 2, max: 20, message: 'Length should be 2 to 20 characters', trigger: 'blur' }
      ],
      email: [
        { required: true, message: 'Please enter email', trigger: 'blur' },
        { type: 'email', message: 'Please enter valid email format', trigger: 'blur' }
      ],
      password: [
        { required: true, message: 'Please enter password', trigger: 'blur' },
        { min: 6, max: 20, message: 'Length should be 6 to 20 characters', trigger: 'blur' }
      ],
      role: [
        { required: true, message: 'Please select role', trigger: 'change' }
      ]
    }

    const lockRules = {
      reason: [
        { required: true, message: 'Please enter lock reason', trigger: 'blur' },
        { min: 2, max: 200, message: 'Length should be 2 to 200 characters', trigger: 'blur' }
      ]
    }

    const resetPasswordRules = {
      newPassword: [
        { required: true, message: 'Please enter new password', trigger: 'blur' },
        { min: 6, max: 20, message: 'Length should be 6 to 20 characters', trigger: 'blur' }
      ],
      confirmPassword: [
        { required: true, message: 'Please confirm the new password', trigger: 'blur' },
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

    // Get user list with pagination and filtering
    const fetchUserList = async () => {
      loading.value = true
      try {
        // Prepare query parameters
        const params = {
          current: currentPage.value,
          size: pageSize.value
        }
        
        // Add search parameters if they exist
        if (searchForm.username) params.username = searchForm.username
        if (searchForm.email) params.email = searchForm.email
        if (searchForm.role) params.role = searchForm.role
        if (searchForm.locked !== null) params.locked = searchForm.locked
        
        const response = await getUserList(params)
        if (response.code === 200) {
          // Handle paginated response
          userList.value = response.data.records
          total.value = response.data.total
          currentPage.value = response.data.current
          pageSize.value = response.data.size
        } else {
          ElMessage.error(response.message || 'Failed to get user list')
        }
      } catch (error) {
        ElMessage.error('Failed to get user list: ' + error.message)
      } finally {
        loading.value = false
      }
    }

    // Handle pagination
    const handleCurrentChange = (page) => {
      currentPage.value = page
      fetchUserList()
    }
    
    // Handle page size change
    const handleSizeChange = (size) => {
      pageSize.value = size
      currentPage.value = 1 // Reset to first page when changing page size
      fetchUserList()
    }
    
    // Handle search
    const handleSearch = () => {
      currentPage.value = 1 // Reset to first page when searching
      fetchUserList()
    }
    
    // Reset search form
    const resetSearch = () => {
      searchForm.username = ''
      searchForm.email = ''
      searchForm.role = ''
      searchForm.locked = null
      handleSearch()
    }

    // Add user
    const handleAddUser = () => {
      isAdd.value = true
      userForm.userid = null
      userForm.name = ''
      userForm.email = ''
      userForm.password = ''
      userForm.role = 'USER'
      dialogVisible.value = true
    }

    // Edit user
    const handleEditUser = async (userId) => {
      try {
        const response = await getUserDetail(userId)
        if (response.code === 200) {
          isAdd.value = false
          userForm.userid = response.data.userid
          userForm.name = response.data.name
          userForm.email = response.data.email
          userForm.password = '' // Don't show password
          
          // 确保正确回显角色信息
          // 处理角色可能是大写USER/ADMIN和其他格式的情况
          if (response.data.role === 'ADMIN' || response.data.role === 'admin' || response.data.role === 'Admin') {
            userForm.role = 'ADMIN'
          } else {
            userForm.role = 'USER'
          }
          
          // 如果有其他需要回显的字段，可以在这里添加

          dialogVisible.value = true
        } else {
          ElMessage.error(response.message || 'Failed to get user details')
        }
      } catch (error) {
        ElMessage.error('Failed to get user details: ' + error.message)
      }
    }

    // View user
    const handleViewUser = (userId) => {
      // Navigate to user detail page
      router.push(`/admin/users/${userId}`)
    }

    // Handle dialog close
    const handleDialogClose = () => {
      dialogVisible.value = false
      if (userFormRef.value) {
        userFormRef.value.resetFields()
      }
    }

    // Submit form
    const submitForm = async () => {
      if (!userFormRef.value) {
        return ElMessage.warning('Form reference not found')
      }
      
      userFormRef.value.validate(async (valid) => {
        if (!valid) {
          return ElMessage.warning('Please complete the form correctly')
        }

        try {
          if (isAdd.value) {
            // Add user
            const response = await createUser(userForm)
            if (response.code === 200) {
              ElMessage.success('User added successfully')
              handleDialogClose()
              fetchUserList()
            } else {
              ElMessage.error(response.message || 'Failed to add user')
            }
          } else {
            // Edit user - exclude password field when editing
            const { password, ...updateData } = userForm
            const response = await updateUser(updateData.userid, updateData)
            if (response.code === 200) {
              ElMessage.success('User updated successfully')
              handleDialogClose()
              fetchUserList()
            } else {
              ElMessage.error(response.message || 'Failed to update user')
            }
          }
        } catch (error) {
          ElMessage.error((isAdd.value ? 'Failed to add' : 'Failed to update') + ' user: ' + error.message)
        }
      })
    }

    // Lock user
    const handleLockUser = (userId) => {
      currentUserId.value = userId
      lockForm.reason = ''
      lockDialogVisible.value = true
    }

    // Handle lock dialog close
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
            const response = await lockUserWithReason(currentUserId.value, lockForm.reason)
            if (response.code === 200) {
              ElMessage.success('User locked successfully')
              handleLockDialogClose()
              fetchUserList()
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
    const handleUnlockUser = async (userId) => {
      try {
        await ElMessageBox.confirm('Are you sure you want to unlock this user?', 'Confirm', {
          confirmButtonText: 'Confirm',
          cancelButtonText: 'Cancel',
          type: 'warning'
        })
        
        const response = await unlockUser(userId)
        if (response.code === 200) {
          ElMessage.success('User unlocked successfully')
          fetchUserList()
        } else {
          ElMessage.error(response.message || 'Failed to unlock user')
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('Failed to unlock user: ' + error.message)
        }
      }
    }

    // Delete user
    const handleDeleteUser = async (userId) => {
      try {
        await ElMessageBox.confirm('Are you sure you want to delete this user? This operation cannot be undone!', 'Warning', {
          confirmButtonText: 'Confirm',
          cancelButtonText: 'Cancel',
          type: 'warning'
        })
        
        const response = await deleteUser(userId)
        if (response.code === 200) {
          ElMessage.success('User deleted successfully')
          fetchUserList()
        } else {
          ElMessage.error(response.message || 'Failed to delete user')
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('Failed to delete user: ' + error.message)
        }
      }
    }

    // Reset password
    const handleResetPassword = (userId) => {
      currentUserId.value = userId
      resetPasswordForm.newPassword = ''
      resetPasswordForm.confirmPassword = ''
      resetPasswordDialogVisible.value = true
    }

    // Handle reset password dialog close
    const handleResetPasswordDialogClose = () => {
      resetPasswordDialogVisible.value = false
      if (resetPasswordFormRef.value) {
        resetPasswordFormRef.value.resetFields()
      }
    }

    // Confirm reset password
    const confirmResetPassword = async () => {
      if (!resetPasswordFormRef.value) {
        return ElMessage.warning('Form reference not found')
      }
      
      resetPasswordFormRef.value.validate(async (valid) => {
        if (!valid) {
          return ElMessage.warning('Please complete the form correctly')
        }
        
        try {
          const response = await resetUserPassword(currentUserId.value, resetPasswordForm.newPassword)
          if (response.code === 200) {
            ElMessage.success('Password reset successfully')
            handleResetPasswordDialogClose()
          } else {
            ElMessage.error(response.message || 'Failed to reset password')
          }
        } catch (error) {
          ElMessage.error('Failed to reset password: ' + error.message)
        }
      })
    }

    // Format date time
    const formatDateTime = (dateTime) => {
      if (!dateTime) return ''
      const date = new Date(dateTime)
      return date.toLocaleString()
    }

    // Expose new methods
    const searchMusicByUsername = (user) => {
      if (user?.name) {
        router.push({ path: '/music', query: { username: user.name } })
      } else {
        ElMessage.warning('Cannot search: Username is missing.')
      }
    }

    const searchMusicByEmail = (user) => {
      if (user?.email) {
        router.push({ path: '/music', query: { email: user.email } })
      } else {
        ElMessage.warning('Cannot search: Email is missing.')
      }
    }

    onMounted(() => {
      fetchUserList()
    })

    return {
      loading,
      userList,
      currentPage,
      pageSize,
      total,
      handleCurrentChange,
      handleSizeChange,
      
      searchForm,
      handleSearch,
      resetSearch,
      
      dialogVisible,
      dialogTitle,
      isAdd,
      userForm,
      userFormRef,
      rules,
      handleAddUser,
      handleEditUser,
      handleViewUser,
      submitForm,
      handleDialogClose,
      
      currentUserId,
      lockDialogVisible,
      lockForm,
      lockRules,
      handleLockUser,
      handleLockDialogClose,
      confirmLockUser,
      handleUnlockUser,
      
      resetPasswordDialogVisible,
      resetPasswordForm,
      resetPasswordRules,
      handleResetPassword,
      handleResetPasswordDialogClose,
      confirmResetPassword,
      
      handleDeleteUser,
      
      formatDateTime,
      lockFormRef,
      resetPasswordFormRef,
      
      // Expose new methods
      searchMusicByUsername,
      searchMusicByEmail
    }
  }
}
</script>

<style scoped>
.user-management {
  padding: 20px;
  color: #ffffff;
  background-color: #1a1a1a;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  color: #ffffff;
  margin: 0;
}

.search-container {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #2d2d2d;
  border-radius: 4px;
  border: 1px solid #333;
}

.search-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.text-danger {
  color: #F56C6C;
}

.text-success {
  color: #67C23A;
}

.el-dropdown-menu__item .el-icon {
  margin-right: 5px;
}

/* 深度选择器，定制Element Plus组件样式 */
:deep(.el-table) {
  background-color: #1e1e1e;
  color: #ffffff;
  border: none;
}

:deep(.el-table tr) {
  background-color: #1e1e1e;
}

:deep(.el-table th.el-table__cell) {
  background-color: #2d2d2d;
  color: #ffffff;
  border-bottom: 1px solid #333;
}

:deep(.el-table td.el-table__cell) {
  border-bottom: 1px solid #333;
}

:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) {
  background-color: #2d2d2d;
}

:deep(.el-button) {
  border: none;
}

:deep(.el-button--primary) {
  background-color: #ff6b81;
}

:deep(.el-input__wrapper) {
  background-color: #2d2d2d !important;
  border: none !important;
  box-shadow: 0 0 0 1px #444 inset !important;
}

:deep(.el-select .el-input__wrapper) {
  background-color: #2d2d2d !important;
}

:deep(.el-dialog) {
  background-color: #1e1e1e;
  border-radius: 8px;
}

:deep(.el-dialog__title) {
  color: #ffffff;
}

:deep(.el-dialog__body) {
  color: #ffffff;
}

:deep(.el-form-item__label) {
  color: #ffffff;
}

:deep(.el-select-dropdown) {
  background-color: #2d2d2d;
  border: 1px solid #333;
}

:deep(.el-select-dropdown__item) {
  color: #fff;
}

:deep(.el-pagination) {
  --el-pagination-bg-color: transparent;
  --el-pagination-text-color: #fff;
  --el-pagination-button-color: #fff;
  --el-pagination-hover-color: #ff6b81;
}

:deep(.el-tag) {
  background-color: transparent;
}

:deep(.el-tag--success) {
  border-color: #67C23A;
  color: #67C23A;
}

:deep(.el-tag--danger) {
  border-color: #F56C6C;
  color: #F56C6C;
}

:deep(.el-tag--primary) {
  border-color: #409EFF;
  color: #409EFF;
}

/* 添加下拉菜单的深色主题样式 */
:deep(.el-dropdown-menu) {
  background-color: #2d2d2d !important;
  border: 1px solid #444 !important;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.4) !important;
}

:deep(.el-dropdown-menu__item) {
  color: #ffffff !important;
}

:deep(.el-dropdown-menu__item:hover) {
  background-color: #3d3d3d !important;
}

:deep(.el-dropdown-menu__item.danger-item) {
  color: #F56C6C !important;
}

:deep(.el-dropdown-menu__item.danger-item:hover) {
  background-color: rgba(245, 108, 108, 0.1) !important;
}

@media (max-width: 768px) {
  .user-management {
    padding: 10px;
  }

  .search-form {
    gap: 5px;
  }

  .pagination-container {
    justify-content: center;
  }

  :deep(.el-dialog) {
    width: 95% !important;
  }
}
</style> 